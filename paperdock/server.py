"""Loopback-only HTTP application and durable scan job orchestration."""
from __future__ import annotations
import copy
import fcntl
import json
import mimetypes
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import __version__, orientation, scanner, wifi
from .document_names import DEFAULT_TEMPLATE, pdf_disposition, render_template, unique_name, validate_template, validate_title
from .paperless import PaperlessClient, PaperlessError

BUSY = {'scanning', 'orienting', 'exporting', 'uploading'}
PROFILES = [
    {'id': 'everyday', 'name': 'Alltag', 'description': 'Briefe & Dokumente', 'dpi': 300, 'mode': 'Color', 'source': 'ADF Duplex'},
    {'id': 'receipts', 'name': 'Belege', 'description': 'Kompakt & gut lesbar', 'dpi': 200, 'mode': 'Gray', 'source': 'ADF Front'},
    {'id': 'archive', 'name': 'Archiv', 'description': 'Details bewahren', 'dpi': 600, 'mode': 'Color', 'source': 'ADF Duplex'},
]

class AppError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def private_json(path: Path, value):
    """Atomically replace a file; secrets never pass through permissive temp files."""
    tmp = path.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise AppError(f'{name}: Bitte einen Wert von {minimum} bis {maximum} angeben.')
    return value


def copy_private(source: Path, destination: Path):
    """Preserve exact page bytes and replace only after the durable copy exists."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.page-', delete=False) as stream:
            temporary = Path(stream.name)
            with source.open('rb') as original:
                shutil.copyfileobj(original, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


ORIENTATION_MESSAGES = {
    'upright': 'Die Textausrichtung ist bereits richtig.',
    'rotate': 'Die Seite wurde anhand ihrer Textausrichtung gedreht.',
    'uncertain': 'Zu wenig sicher erkennbarer Text: Die Seite bleibt unverändert. Bitte selbst prüfen.',
    'unavailable': 'Automatische Ausrichtung nicht verfügbar: Dafür wird Tesseract mit OSD-Sprachdaten benötigt.',
    'timeout': 'Die Ausrichtungsprüfung dauerte zu lange. Die Seite bleibt unverändert.',
    'invalid': 'Die Textausrichtung konnte nicht sicher bestimmt werden. Die Seite bleibt unverändert.',
    'cancelled': 'Die Ausrichtungsprüfung wurde angehalten. Die Seite bleibt unverändert.',
    'error': 'Die Textausrichtung konnte nicht geprüft werden. Die Seite bleibt unverändert.',
    'restored': 'Die Seite wurde auf den Stand vor der automatischen Drehung zurückgesetzt.',
}


class Application:
    def __init__(self, data_dir: Path):
        self.root = data_dir.expanduser().resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self._instance_lock = (self.root / '.instance.lock').open('a+')
        try:
            fcntl.flock(self._instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._instance_lock.close()
            raise AppError('PaperDock verwendet diesen Datenordner bereits. Bitte die laufende App öffnen.', 409)
        self.jobs_dir = self.root / 'jobs'
        self.jobs_dir.mkdir(mode=0o700, exist_ok=True)
        self.lock = threading.RLock()
        self.scan_lock = threading.Lock()
        self.wifi = wifi.WifiSettings.from_environment()
        self.token = secrets.token_urlsafe(32)
        self.jobs = {}
        self.cancellations = {}
        self.workers = {}
        self.closing = False
        self.devices = []
        self.capabilities = {}
        self.config = {'url': '', 'token': ''}
        self.preferences = {'auto_orient': True, 'naming_template': DEFAULT_TEMPLATE}
        self.next_counter = 1
        self.active_job_id = None
        self.startup_warning = None
        preference_path = self.root / 'preferences.json'
        if preference_path.exists():
            try:
                saved = json.loads(preference_path.read_text())
                if not isinstance(saved.get('auto_orient'), bool):
                    raise ValueError('Invalid automatic orientation preference')
                self.preferences = {'auto_orient': saved['auto_orient'], 'naming_template': validate_template(saved['naming_template'])}
                self.next_counter = integer(saved.get('next_counter', 1), 'Zähler', 1, 2147483647)
                os.chmod(preference_path, 0o600)
            except (ValueError, OSError, TypeError, KeyError, AttributeError, AppError):
                self.preferences = {'auto_orient': True, 'naming_template': DEFAULT_TEMPLATE}
                self.startup_warning = 'Die gespeicherten Scan- und Namenseinstellungen konnten nicht gelesen werden. Standardwerte werden verwendet.'
        config_path = self.root / 'settings.json'
        if config_path.exists():
            try:
                self.config.update(json.loads(config_path.read_text()))
                os.chmod(config_path, 0o600)
            except (ValueError, OSError, TypeError):
                self.startup_warning = 'Die gespeicherten Einstellungen konnten nicht gelesen werden.'
        for path in self.jobs_dir.glob('*/job.json'):
            try:
                job = json.loads(path.read_text())
                if job['id'] != path.parent.name:
                    continue
                for page in job['pages']:
                    if page.get('orientation_pending'):
                        self._restore_page(job, page, page['orientation_pending'])
                        job['pdf_ready'] = False
                self.next_counter = max(self.next_counter, job.get('naming_counter', 0) + 1)
                if job['status'] in BUSY:
                    if job['status'] == 'uploading':
                        job['paperless'] = {'status': 'unknown', 'error': 'Upload unterbrochen. Vor erneutem Senden bitte in Paperless prüfen.', 'url': self.config['url']}
                    job['status'] = 'ready' if job['pages'] else 'error'
                    job['error'] = 'Die vorherige Sitzung wurde unterbrochen. Bereits gespeicherte Seiten wurden wiederhergestellt.'
                self.jobs[job['id']] = job
                self.save(job)
            except (ValueError, KeyError, TypeError, OSError, scanner.ScannerError):
                self.startup_warning = 'Mindestens ein Stapel konnte nicht geladen werden. Die Dateien bleiben im Datenordner erhalten.'
        if self.jobs:
            self.active_job_id = max(self.jobs.values(), key=lambda j: j['created_at'])['id']

    def start_worker(self, name, target, *args):
        def run():
            try:
                target(*args)
            finally:
                with self.lock:
                    self.workers.pop(name, None)
        thread = threading.Thread(target=run, daemon=True)
        self.workers[name] = thread
        thread.start()

    def save(self, job):
        private_json(self.jobs_dir / job['id'] / 'job.json', job)

    def public_config(self):
        return {'url': self.config['url'], 'configured': bool(self.config['url'] and self.config['token'])}

    def public_job(self, job):
        value = copy.deepcopy(job)
        for page in value['pages']:
            page['url'] = f"/media/{job['id']}/{page['id']}.png?v={page.get('revision', 0)}"
            page.pop('file', None)
            page['can_restore_orientation'] = bool(page.pop('orientation_backup', None))
            page.pop('orientation_pending', None)
        value.pop('device', None)
        return value

    def state(self):
        with self.lock:
            return {'version': __version__, 'jobs': [self.public_job(j) for j in sorted(self.jobs.values(), key=lambda j: j['created_at'], reverse=True)],
                    'profiles': PROFILES, 'paperless': self.public_config(), 'active_job_id': self.active_job_id, 'wifi': self.wifi.state(),
                    **self.preference_state(),
                    'system': {'scanimage': bool(shutil.which('scanimage')), 'pillow': True, 'ocr': False, 'orientation': orientation.available()},
                    'warning': self.startup_warning}

    def preference_state(self):
        with self.lock:
            preview = render_template(self.preferences['naming_template'], self.next_counter)
            preview = unique_name(preview, (job['title'] for job in self.jobs.values()))
            return {'preferences': dict(self.preferences), 'name_preview': preview}

    def set_preferences(self, body):
        with self.lock:
            if set(body) - {'auto_orient', 'naming_template'}:
                raise AppError('Unbekannte Scaneinstellung.')
            candidate = {**self.preferences, **body}
            if not isinstance(candidate['auto_orient'], bool):
                raise AppError('Automatische Ausrichtung muss true oder false sein.')
            try:
                candidate['naming_template'] = validate_template(candidate['naming_template'])
            except ValueError as exc:
                raise AppError(str(exc)) from exc
            private_json(self.root / 'preferences.json', {**candidate, 'next_counter': self.next_counter})
            self.preferences = candidate
            return self.preference_state()

    def get_job(self, job_id):
        try:
            return self.jobs[job_id]
        except KeyError:
            raise AppError('Dieser Stapel wurde nicht gefunden.', 404)

    def ensure_idle(self, job, edit=False):
        if job['status'] in BUSY:
            raise AppError('Dieser Stapel wird gerade verarbeitet.', 409)
        if any(page.get('orientation_pending') for page in job['pages']):
            raise AppError('Eine Seitenänderung wurde unterbrochen. Bitte PaperDock neu starten, um die gesicherte Seite wiederherzustellen.', 409)
        if edit and (job.get('paperless') or {}).get('status') in {'submitted', 'success', 'unknown'}:
            raise AppError('Dieser Stapel wurde bereits an Paperless übergeben. Seine Seiten bleiben für den Abgleich unverändert.', 409)

    def client(self):
        if not self.public_config()['configured']:
            raise AppError('Bitte zuerst Paperless-Adresse und API-Token in den Einstellungen hinterlegen.')
        return PaperlessClient(self.config['url'], self.config['token'])

    def wifi_state(self):
        with self.lock:
            return self.wifi.state()

    def set_wifi(self, body):
        if set(body) != {'address'} or not isinstance(body.get('address'), str):
            raise AppError('Bitte ausschließlich eine Scanner-Adresse als Text angeben.')
        if not self.scan_lock.acquire(blocking=False):
            raise AppError('Der Scanner ist gerade beschäftigt. Bitte vor einer WLAN-Änderung den Vorgang abschließen oder anhalten.', 409)
        try:
            with self.lock:
                if self.closing:
                    raise AppError('PaperDock wird gerade beendet.', 409)
                try:
                    result = self.wifi.save(body['address'])
                except ValueError as exc:
                    raise AppError(str(exc)) from exc
                except OSError as exc:
                    raise AppError('Die WLAN-Einstellung konnte nicht gespeichert werden. Bitte Schreibrechte der Installation prüfen.', 500) from exc
                self.devices = []
                self.capabilities = {}
                return result
        finally:
            self.scan_lock.release()

    def scanner_environment(self):
        # Avoid process-global changes; each scanner subprocess gets a snapshot.
        return {'environment': self.wifi.environment.copy()} if self.wifi.managed else {}

    def discover(self):
        if not self.scan_lock.acquire(blocking=False):
            raise AppError('Der Scanner ist gerade beschäftigt.', 409)
        try:
            result = scanner.discover_devices(**self.scanner_environment())
            wlan = self.wifi.state()
            if wlan['available'] and not wlan['configured']:
                result['warning'] = '\n\n'.join(filter(None, [result.get('warning'), wlan['message']]))
            with self.lock:
                self.devices = result['devices']
                known_ids = {d['id'] for d in self.devices}
                self.capabilities = {key: value for key, value in self.capabilities.items() if key in known_ids}
            return result
        finally:
            self.scan_lock.release()

    def options(self, device):
        if not self.scan_lock.acquire(blocking=False):
            raise AppError('Der Scanner ist gerade beschäftigt.', 409)
        try:
            with self.lock:
                if device not in {d['id'] for d in self.devices}:
                    raise AppError('Bitte zuerst nach Scannern suchen und ein erkanntes Gerät auswählen.')
            result = scanner.device_options(device, **self.scanner_environment())
            with self.lock:
                self.capabilities[device] = result
            return result
        finally:
            self.scan_lock.release()

    def new_job(self, body):
        demo = body.get('demo', False)
        if not isinstance(demo, bool):
            raise AppError('demo muss true oder false sein.')
        dpi = integer(body.get('dpi', 300), 'Auflösung', 50, 1200)
        page_limit = integer(body.get('page_limit', 40), 'Seitenlimit', 1, 100)
        mode = body.get('mode', 'Color')
        source = body.get('source', 'ADF Duplex')
        if not isinstance(mode, str) or not isinstance(source, str) or len(mode) > 100 or len(source) > 100:
            raise AppError('Ungültiger Scanmodus oder Einzug.')
        paper_size = body.get('paper_size', 'Driver')
        if not isinstance(paper_size, str) or paper_size not in {'Driver', 'A4', 'Letter'}:
            raise AppError('Unbekanntes Papierformat.')
        title = body.get('title', '')
        if not isinstance(title, str):
            raise AppError('Der Dokumentname muss Text sein.')
        try:
            title = validate_title(title) if title.strip() else ''
        except ValueError as exc:
            raise AppError(str(exc)) from exc
        device = body.get('device', '')
        with self.lock:
            if self.closing:
                raise AppError('PaperDock wird gerade beendet.', 409)
            if any(job['status'] == 'orienting' for job in self.jobs.values()):
                raise AppError('Bitte die laufende Ausrichtungsprüfung abwarten oder anhalten.', 409)
            if not demo and device not in {d['id'] for d in self.devices}:
                raise AppError('Kein Scanner ausgewählt. Bitte USB verbinden oder WLAN in den Einstellungen einrichten und Geräte aktualisieren.')
            if not demo and paper_size != 'Driver':
                if not re.match(r'^ADF(?:\s|$)', source, re.IGNORECASE) or paper_size not in self.capabilities.get(device, {}).get('paper_sizes', []):
                    raise AppError('Dieses Papierformat ist für den gewählten Einzug nicht bestätigt. Bitte Scanneroptionen neu laden oder Treiberstandard wählen.')
            if not demo and not self.scan_lock.acquire(blocking=False):
                raise AppError('Es läuft bereits ein Scan.', 409)
            job_id = uuid.uuid4().hex
            folder = self.jobs_dir / job_id
            previous_active = self.active_job_id
            try:
                counter = self.next_counter
                if not title:
                    title = 'Beispieldokumente' if demo else render_template(self.preferences['naming_template'], counter)
                    title = unique_name(title, (job['title'] for job in self.jobs.values()))
                if not demo:
                    self.next_counter += 1
                    private_json(self.root / 'preferences.json', {**self.preferences, 'next_counter': self.next_counter})
                folder.mkdir(mode=0o700)
                job = {'id': job_id, 'title': title.strip(), 'status': 'scanning',
                       'created_at': datetime.now(timezone.utc).isoformat(), 'demo': demo,
                       'settings': {'dpi': 150 if demo else dpi, 'mode': mode, 'source': source, 'page_limit': page_limit, 'paper_size': 'Driver' if demo else paper_size, 'auto_orient': self.preferences['auto_orient'] and not demo},
                       'naming_counter': 0 if demo else counter, 'orientation_note': None,
                       'device': device, 'pages': [], 'error': None, 'paperless': None, 'pdf_ready': False}
                self.jobs[job_id] = job
                self.cancellations[job_id] = threading.Event()
                self.active_job_id = job_id
                self.save(job)
            except Exception:
                self.jobs.pop(job_id, None)
                self.cancellations.pop(job_id, None)
                self.active_job_id = previous_active
                if not demo:
                    self.scan_lock.release()
                raise
            self.start_worker('scan-' + job_id, self._scan, job_id)
            return self.public_job(job)

    def _scan(self, job_id):
        job = self.jobs[job_id]
        folder = self.jobs_dir / job_id
        cancel = self.cancellations[job_id]
        def on_page(path):
            path = Path(path)
            with self.lock:
                if any(p['file'] == path.name for p in job['pages']):
                    return
                page = {'id': path.stem, 'file': path.name, 'revision': 0, **scanner.inspect_page(path)}
                job['pages'].append(page)
                self.save(job)
        try:
            if job['demo']:
                for page in scanner.create_demo(folder):
                    if cancel.is_set():
                        break
                    on_page(page)
            else:
                scanner.scan_pages(job['device'], job['settings'], folder, on_page, cancel, **self.scanner_environment())
            with self.lock:
                if cancel.is_set():
                    job['error'] = 'Scan angehalten. Bereits erfasste Seiten bleiben erhalten.'
                if not job['pages'] and not job['error']:
                    job['error'] = 'Keine Seiten erfasst. Bitte Papier einlegen und erneut starten.'
        except scanner.ScannerError as exc:
            with self.lock:
                job['error'] = str(exc)
        except Exception:
            with self.lock:
                job['error'] = 'Der Scan konnte nicht abgeschlossen werden. Bereits erfasste Seiten bleiben erhalten.'
        finally:
            try:
                if job['pages'] and job['settings'].get('auto_orient') and not cancel.is_set():
                    with self.lock:
                        job['status'] = 'orienting'
                        self.save(job)
                    try:
                        self._orient_pages(job, list(job['pages']), cancel)
                    except Exception:
                        with self.lock:
                            job['orientation_note'] = 'Die Ausrichtungsprüfung konnte nicht abgeschlossen werden. Bitte die Seiten selbst prüfen.'
                with self.lock:
                    job['status'] = 'ready' if job['pages'] else 'error'
                    self.save(job)
            finally:
                with self.lock:
                    self.cancellations.pop(job_id, None)
                if not job['demo']:
                    self.scan_lock.release()

    def _backup_path(self, job, name):
        if not isinstance(name, str) or not re.fullmatch(r'[a-f0-9]{32}\.png', name):
            raise scanner.ScannerError('Die Sicherung dieser Seite konnte nicht zugeordnet werden.')
        return self.jobs_dir / job['id'] / 'originals' / name

    def _restore_page(self, job, page, backup):
        path = self.jobs_dir / job['id'] / page['file']
        source = self._backup_path(job, backup)
        scanner.inspect_page(source)
        copy_private(source, path)
        page.update(scanner.inspect_page(path))
        page['revision'] = page.get('revision', 0) + 1
        page.pop('orientation_pending', None)
        page.pop('orientation_backup', None)
        page['orientation'] = {'rotation': 0, 'confidence': None, 'applied': False, 'reason': 'restored', 'message': ORIENTATION_MESSAGES['restored']}

    def _orient_pages(self, job, pages, cancel):
        checked = rotated = uncertain = 0
        for page in pages:
            if cancel.is_set():
                break
            path = self.jobs_dir / job['id'] / page['file']
            result = dict(orientation.detect_page(path, cancel))
            result['message'] = ORIENTATION_MESSAGES.get(result['reason'], ORIENTATION_MESSAGES['error'])
            with self.lock:
                if cancel.is_set():
                    break
                if result['reason'] == 'rotate' and result['rotation'] in (90, 180, 270):
                    originals = path.parent / 'originals'
                    originals.mkdir(mode=0o700, exist_ok=True)
                    backup = uuid.uuid4().hex + '.png'
                    copy_private(path, originals / backup)
                    # Recovery journal is durable before replacing page bytes.
                    page['orientation_pending'] = backup
                    page['orientation_backup'] = backup
                    job['pdf_ready'] = False
                    self.save(job)
                    try:
                        scanner.rotate_page(path, result['rotation'])
                        page.update(scanner.inspect_page(path))
                        page['revision'] = page.get('revision', 0) + 1
                        page.pop('orientation_pending', None)
                        result['applied'] = True
                        rotated += 1
                    except Exception:
                        self._restore_page(job, page, backup)
                        result = {'rotation': 0, 'confidence': None, 'applied': False, 'reason': 'error', 'message': ORIENTATION_MESSAGES['error']}
                page['orientation'] = result
                checked += 1
                if result['reason'] not in {'rotate', 'upright'}:
                    uncertain += 1
                self.save(job)
        with self.lock:
            note = f'{checked} Seiten geprüft, {rotated} automatisch gedreht.'
            if uncertain:
                note += f' {uncertain} Seiten konnten nicht sicher ausgerichtet werden und bleiben unverändert. Bitte selbst prüfen.'
            if cancel.is_set():
                note += ' Prüfung angehalten; bereits bearbeitete Seiten bleiben erhalten.'
            job['orientation_note'] = note

    def auto_orient(self, job_id, body):
        with self.lock:
            if self.closing:
                raise AppError('PaperDock wird gerade beendet.', 409)
            job = self.get_job(job_id)
            self.ensure_idle(job, edit=True)
            if not orientation.available():
                raise AppError(ORIENTATION_MESSAGES['unavailable'])
            page_id = body.get('page_id')
            pages = list(job['pages']) if page_id is None else [p for p in job['pages'] if p['id'] == page_id]
            if not pages:
                raise AppError('Keine passende Seite für die Ausrichtungsprüfung gefunden.', 404)
            previous_status, previous_note = job['status'], job.get('orientation_note')
            job['status'] = 'orienting'
            job['orientation_note'] = 'Die Textausrichtung wird lokal geprüft.'
            self.cancellations[job_id] = threading.Event()
            try:
                self.save(job)
            except Exception:
                job['status'], job['orientation_note'] = previous_status, previous_note
                self.cancellations.pop(job_id, None)
                raise
            self.start_worker('orient-' + job_id, self._orient, job_id, pages)
            return self.public_job(job)

    def _orient(self, job_id, pages):
        job = self.jobs[job_id]
        try:
            self._orient_pages(job, pages, self.cancellations[job_id])
        except Exception:
            with self.lock:
                job['orientation_note'] = 'Die Ausrichtungsprüfung konnte nicht abgeschlossen werden. Bitte die Seiten selbst prüfen.'
        finally:
            try:
                with self.lock:
                    job['status'] = 'ready'
                    self.save(job)
            finally:
                with self.lock:
                    self.cancellations.pop(job_id, None)

    def edit_job(self, job_id, action, body):
        with self.lock:
            job = self.get_job(job_id)
            if action == 'cancel':
                event = self.cancellations.get(job_id)
                if event:
                    event.set()
                return self.public_job(job)
            self.ensure_idle(job, edit=True)
            pages = job['pages']
            if action == 'rename':
                try:
                    job['title'] = validate_title(body.get('title'))
                except ValueError as exc:
                    raise AppError(str(exc)) from exc
                self.save(job)
                return self.public_job(job)
            if action == 'reorder':
                ids = body.get('page_ids')
                if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(ids) != len(pages) or set(ids) != {p['id'] for p in pages}:
                    raise AppError('Die Seitenreihenfolge muss jede vorhandene Seite genau einmal enthalten.')
                by_id = {p['id']: p for p in pages}
                job['pages'] = [by_id[i] for i in ids]
            else:
                page = next((p for p in pages if p['id'] == body.get('page_id')), None)
                if not page:
                    raise AppError('Diese Seite wurde nicht gefunden.', 404)
                path = self.jobs_dir / job_id / page['file']
                if action == 'rotate':
                    degrees = body.get('degrees', 90)
                    if degrees not in (90, 180, 270):
                        raise AppError('Drehung muss 90, 180 oder 270 Grad betragen.')
                    scanner.rotate_page(path, degrees)
                    page.update(scanner.inspect_page(path))
                    page['revision'] += 1
                    page.pop('orientation', None)
                    job['orientation_note'] = None
                elif action == 'delete-page':
                    if len(pages) <= 1:
                        raise AppError('Mindestens eine Seite muss im Stapel bleiben.')
                    # Retain original bytes on disk for recovery; exclude from export/UI.
                    job['pages'] = [p for p in pages if p['id'] != page['id']]
                    job['orientation_note'] = None
                elif action == 'restore-orientation':
                    backup = page.get('orientation_backup')
                    if not backup:
                        raise AppError('Für diese Seite gibt es keine automatische Drehung zum Zurücksetzen.')
                    page['orientation_pending'] = backup
                    job['pdf_ready'] = False
                    self.save(job)
                    self._restore_page(job, page, backup)
                    job['orientation_note'] = ORIENTATION_MESSAGES['restored']
                else:
                    raise AppError('Aktion nicht gefunden.', 404)
            job['pdf_ready'] = False
            self.save(job)
            return self.public_job(job)

    def export(self, job_id, body):
        if body.get('ocr'):
            raise AppError('Durchsuchbare PDFs mit OCR-Textschicht sind in dieser Version noch nicht enthalten. Paperless übernimmt die Texterkennung nach dem Upload.')
        with self.lock:
            job = self.get_job(job_id)
            self.ensure_idle(job)
            if not job['pages']:
                raise AppError('Dieser Stapel enthält keine Seiten.')
            job['status'] = 'exporting'
            self.save(job)
        try:
            self._pdf(job)
        finally:
            with self.lock:
                job['status'] = 'ready'
                self.save(job)
        return {'url': f'/download/{job_id}/document.pdf'}

    def _pdf(self, job):
        folder = self.jobs_dir / job['id']
        path = folder / 'document.pdf'
        if not job['pdf_ready'] or not path.exists():
            scanner.export_pdf([folder / p['file'] for p in job['pages']], path, dpi=job['settings']['dpi'])
            with self.lock:
                job['pdf_ready'] = True
                self.save(job)
        return path

    def upload(self, job_id, body):
        with self.lock:
            job = self.get_job(job_id)
            self.ensure_idle(job)
            if not job['pages']:
                raise AppError('Dieser Stapel enthält keine Seiten.')
            if (job.get('paperless') or {}).get('status') in {'submitted', 'success', 'unknown'}:
                raise AppError('Dieser Stapel wurde bereits übergeben. Bitte zuerst den Status in Paperless prüfen.', 409)
            title = body.get('title') or job['title']
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
                raise AppError('Bitte einen Titel mit höchstens 200 Zeichen angeben.')
            tags = body.get('tags', [])
            if not isinstance(tags, list) or len(tags) > 100:
                raise AppError('Ungültige Schlagwörter.')
            tags = [integer(v, 'Schlagwort-ID', 1, 2147483647) for v in tags]
            meta = {key: body.get(key) for key in ('correspondent', 'document_type')}
            for key, value in meta.items():
                if value is not None:
                    integer(value, key, 1, 2147483647)
            client = self.client()
            job['title'] = title.strip()
            job['status'] = 'uploading'
            job['error'] = None
            job['paperless'] = {'status': 'submitted', 'task_id': None, 'url': client.url}
            self.save(job)
            self.start_worker('upload-' + job_id, self._upload, job_id, client, tags, meta)
            return self.public_job(job)

    def _upload(self, job_id, client, tags, meta):
        job = self.jobs[job_id]
        submitted = False
        try:
            path = self._pdf(job)
            submitted = True
            result = client.upload(path, title=job['title'], tags=tags, **meta)
            result['url'] = client.url
            with self.lock:
                job['paperless'] = result
        except Exception as exc:
            uncertain = getattr(exc, 'uncertain', submitted and not isinstance(exc, PaperlessError))
            with self.lock:
                job['paperless'] = {'status': 'unknown' if uncertain else 'failure', 'url': client.url, 'task_id': None,
                                    'error': str(exc) if isinstance(exc, PaperlessError) else 'Das Dokument konnte nicht übertragen werden.'}
                job['error'] = job['paperless']['error']
        finally:
            with self.lock:
                job['status'] = 'ready'
                self.save(job)

    def paperless_status(self, job_id):
        with self.lock:
            job = self.get_job(job_id)
            self.ensure_idle(job)
            previous = job.get('paperless') or {}
            task_id = previous.get('task_id')
            if not task_id:
                raise AppError('Keine Aufgaben-ID vorhanden. Bitte den Eingang direkt in Paperless prüfen.')
            client = self.client()
            if previous.get('url') != client.url:
                raise AppError('Dieser Stapel wurde an eine andere Paperless-Instanz gesendet.')
        result = client.task_status(task_id)
        with self.lock:
            # Do not regress confirmed completion when a server purges historical tasks.
            current = job.get('paperless') or {}
            if (job['status'] != 'uploading' and current.get('task_id') == task_id
                    and current.get('url') == client.url and current.get('status') != 'success'):
                job['paperless'] = {**result, 'url': client.url}
                self.save(job)
            return self.public_job(job)

    def settings(self, body):
        with self.lock:
            url = body.get('url', self.config['url'])
            token = body.get('token') or self.config['token']
            if not isinstance(url, str) or not isinstance(token, str):
                raise AppError('Adresse und Token müssen Text sein.')
            if not token:
                raise AppError('Bitte einen Paperless-API-Token eingeben.')
            client = PaperlessClient(url.strip(), token.strip())
            if self.config['url'] and client.url != self.config['url'] and not body.get('token'):
                raise AppError('Bei einer neuen Serveradresse bitte den passenden API-Token erneut eingeben.')
            config = {'url': client.url, 'token': token.strip()}
            private_json(self.root / 'settings.json', config)
            self.config = config
            return self.public_config()

    def shutdown(self):
        with self.lock:
            self.closing = True
            for cancel in self.cancellations.values():
                cancel.set()
            workers = list(self.workers.values())
        deadline = time.monotonic() + 30
        for worker in workers:
            worker.join(timeout=max(0, deadline - time.monotonic()))
        # A still-running worker retains the instance lock until process exit.
        if not any(worker.is_alive() for worker in workers) and not self._instance_lock.closed:
            fcntl.flock(self._instance_lock, fcntl.LOCK_UN)
            self._instance_lock.close()


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, app):
        if address[0] != '127.0.0.1':
            raise ValueError('PaperDock may only bind to IPv4 loopback.')
        super().__init__(address, Handler)
        self.app = app
        self.origin = f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    server_version = f'PaperDock/{__version__}'
    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, *_):
        pass  # Document names and API payloads are deliberately not logged.

    def headers_safe(self, api=False):
        port = self.server.server_port
        if self.headers.get('Host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
            raise AppError('Unzulässiger Host.', 403)
        origin = self.headers.get('Origin')
        if origin and origin not in {self.server.origin, f'http://localhost:{port}'}:
            raise AppError('Zugriff von einer fremden Website abgelehnt.', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise AppError('Zugriff von einer fremden Website abgelehnt.', 403)
        if api and not secrets.compare_digest(self.headers.get('X-Paperdock-Token', ''), self.server.app.token):
            raise AppError('Sitzung abgelaufen. Bitte die App neu laden.', 403)

    def send_bytes(self, content, mime='application/json; charset=utf-8', status=200, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

    def json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False).encode(), status=status)

    def body(self):
        if self.headers.get_content_type() != 'application/json':
            raise AppError('JSON als Inhalt erwartet.', 415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise AppError('Ungültige Anfragelänge.')
        if not 0 <= size <= 65536:
            raise AppError('Die Anfrage ist zu groß.', 413)
        try:
            value = json.loads(self.rfile.read(size) or b'{}')
        except (ValueError, UnicodeError):
            raise AppError('Ungültiges JSON.')
        if not isinstance(value, dict):
            raise AppError('Ein JSON-Objekt wurde erwartet.')
        return value

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, post):
        try:
            path = urlsplit(self.path).path
            self.headers_safe(api=path.startswith('/api/') and path != '/api/session')
            app = self.server.app
            if post:
                body = self.body()
                if path == '/api/jobs':
                    return self.json(app.new_job(body), 201)
                if path == '/api/settings/paperless':
                    return self.json(app.settings(body))
                if path == '/api/preferences':
                    return self.json(app.set_preferences(body))
                if path == '/api/wifi':
                    return self.json(app.set_wifi(body))
                if path == '/api/paperless/test':
                    return self.json(app.client().test_connection())
                match = re.fullmatch(r'/api/jobs/([a-f0-9]{32})/([a-z-]+)', path)
                if match:
                    job_id, action = match.groups()
                    if action in {'rotate', 'reorder', 'delete-page', 'cancel', 'rename', 'restore-orientation'}:
                        return self.json(app.edit_job(job_id, action, body))
                    if action == 'auto-orient':
                        return self.json(app.auto_orient(job_id, body), 202)
                    if action == 'export':
                        return self.json(app.export(job_id, body))
                    if action == 'upload':
                        return self.json(app.upload(job_id, body), 202)
                    if action == 'paperless-status':
                        return self.json(app.paperless_status(job_id))
                raise AppError('Aktion nicht gefunden.', 404)
            if path == '/api/session':
                return self.json({'token': app.token})
            if path == '/api/state':
                return self.json(app.state())
            if path == '/api/preferences':
                return self.json(app.preference_state())
            if path == '/api/wifi':
                return self.json(app.wifi_state())
            if path == '/api/devices':
                return self.json(app.discover())
            if path == '/api/device-options':
                device = parse_qs(urlsplit(self.path).query).get('device', [''])[0]
                return self.json(app.options(device))
            if path == '/api/paperless/metadata':
                return self.json(app.client().metadata())
            media = re.fullmatch(r'/media/([a-f0-9]{32})/([a-zA-Z0-9_-]+)\.png', path)
            download = re.fullmatch(r'/download/([a-f0-9]{32})/document\.pdf', path)
            if media:
                job_id, page_id = media.groups()
                with app.lock:
                    job = app.get_job(job_id)
                    page = next((p for p in job['pages'] if p['id'] == page_id), None)
                    if not page:
                        raise AppError('Seite nicht gefunden.', 404)
                    file = app.jobs_dir / job_id / page['file']
                return self.send_bytes(file.read_bytes(), 'image/png')
            if download:
                job_id = download.group(1)
                with app.lock:
                    job = app.get_job(job_id)
                    if not job['pdf_ready']:
                        raise AppError('Bitte das PDF zuerst exportieren.', 404)
                    file = app.jobs_dir / job_id / 'document.pdf'
                    disposition = pdf_disposition(job['title'])
                return self.send_bytes(file.read_bytes(), 'application/pdf', extra={'Content-Disposition': disposition})
            static = Path(__file__).parent / 'static'
            allowed = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js', '/theme.js': 'theme.js', '/styles.css': 'styles.css', '/icon.svg': 'favicon.svg', '/favicon.svg': 'favicon.svg'}
            if path in allowed:
                file = static / allowed[path]
                if not file.exists():
                    raise AppError('Oberfläche wird vorbereitet.', 503)
                mime = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
                return self.send_bytes(file.read_bytes(), mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
            raise AppError('Nicht gefunden.', 404)
        except (AppError, scanner.ScannerError, PaperlessError) as exc:
            self.json({'error': str(exc)}, getattr(exc, 'status', 400))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.json({'error': 'Ein interner Fehler ist aufgetreten. Deine gespeicherten Seiten bleiben erhalten.'}, 500)
