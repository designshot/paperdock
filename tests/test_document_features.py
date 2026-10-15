"""Document naming and orientation orchestration; synthetic images only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from PIL import Image

from paperdock import scanner
from paperdock.document_names import pdf_disposition, pdf_filename, render_template, validate_template
from paperdock.server import AppError, Application, BUSY, copy_private


def sample_pages(folder):
    result = []
    for number in range(2):
        path = Path(folder) / f'page-{number + 1:04d}.png'
        image = Image.new('RGB', (64, 96), '#fff6e9')
        image.paste('#153a21', (4, 6, 22, 46))
        image.save(path, dpi=(150, 150))
        image.close()
        result.append(path)
    return result


def detected(reason='rotate', rotation=90, confidence=20.0):
    return {'reason': reason, 'rotation': rotation, 'confidence': confidence, 'applied': False}


class NameTests(unittest.TestCase):
    def test_template_local_time_and_padded_counter(self):
        moment = datetime(2026, 10, 15, 8, 9, 7, tzinfo=timezone.utc)
        self.assertEqual(render_template('Scan_{date}_{time}_{counter}', 7, moment), 'Scan_2026-10-15_08-09-07_007')
        self.assertEqual(render_template('{counter}', 1234, moment), '1234')

    def test_templates_reject_fields_paths_and_controls(self):
        for value in ('', '..', '{profile}', '{date.year}', '{date!r}', '{counter:04d}', '{{date}}', '../{date}', 'a\\b', 'a\nb', 'a\x00b', 'a:b', 12, 'x' * 121):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_template(value)
        self.assertEqual(validate_template(' Beleg_{counter} '), 'Beleg_{counter}')

    def test_download_filename_is_utf8_safe_and_header_cannot_be_injected(self):
        header = pdf_disposition('Rechnung Äpfel / Büro "neu"\r\nX-Evil: ja')
        header.encode('ascii')
        self.assertNotIn('\r', header)
        self.assertNotIn('\n', header)
        self.assertIn("filename*=UTF-8''Rechnung%20%C3%84pfel", header)
        self.assertNotIn('/ Büro', header)
        self.assertEqual(pdf_filename('Beleg.pdf'), 'Beleg.pdf')
        self.assertEqual(pdf_filename('..'), 'Scan.pdf')
        self.assertEqual(pdf_filename('CON'), 'Scan_CON.pdf')
        self.assertLessEqual(len(pdf_filename('界' * 200).encode('utf-8')), 184)


class DocumentFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'data'
        self.app = Application(self.root)

    def tearDown(self):
        self.app.shutdown()
        self.temporary.cleanup()

    def wait_ready(self, job_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with self.app.lock:
                job = self.app.get_job(job_id)
                if job['status'] not in BUSY and not self.app.workers:
                    return self.app.public_job(job)
            time.sleep(.01)
        self.fail('Background processing did not finish')

    def demo(self):
        with patch('paperdock.server.scanner.create_demo', side_effect=sample_pages):
            return self.wait_ready(self.app.new_job({'demo': True})['id'])

    def restart(self):
        self.app.shutdown()
        self.app = Application(self.root)

    def path(self, job, index=0):
        page = self.app.get_job(job['id'])['pages'][index]
        return self.app.jobs_dir / job['id'] / page['file']

    def test_preferences_are_separate_private_and_persist_without_paperless(self):
        self.assertEqual(self.app.preference_state()['preferences'], {'auto_orient': True, 'naming_template': 'Scan_{date}_{time}'})
        result = self.app.set_preferences({'auto_orient': False, 'naming_template': 'Archiv_{counter}'})
        self.assertEqual(result['name_preview'], 'Archiv_001')
        self.assertFalse(self.app.public_config()['configured'])
        file = self.root / 'preferences.json'
        self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
        self.restart()
        self.assertEqual(self.app.preference_state(), result)
        self.assertNotIn('next_counter', self.app.state()['preferences'])
        for value in ({'auto_orient': 'true'}, {'auto_orient': 1}, {'naming_template': '{date.year}'}, {'token': 'no'}):
            with self.assertRaises(AppError):
                self.app.set_preferences(value)
        self.assertEqual(self.app.preference_state(), result)

    def test_generated_titles_counter_and_collision_survive_restart(self):
        self.app.set_preferences({'auto_orient': False, 'naming_template': 'Archiv_{counter}'})
        self.app.devices = [{'id': 'fake:scanner'}]
        def capture(device, settings, folder, on_page, cancel):
            on_page(sample_pages(folder)[0])
        with patch('paperdock.server.scanner.scan_pages', side_effect=capture):
            first = self.wait_ready(self.app.new_job({'device': 'fake:scanner', 'title': ''})['id'])
            second = self.wait_ready(self.app.new_job({'device': 'fake:scanner'})['id'])
        self.assertEqual((first['title'], second['title']), ('Archiv_001', 'Archiv_002'))
        self.restart()
        self.assertEqual(self.app.preference_state()['name_preview'], 'Archiv_003')
        self.app.set_preferences({'naming_template': 'Archiv_001'})
        self.assertEqual(self.app.preference_state()['name_preview'], 'Archiv_001_2')
        demo = self.demo()
        self.assertIn('Beispieldokumente', demo['title'])
        self.assertEqual(self.app.preference_state()['name_preview'], 'Archiv_001_2')

    def test_rotation_backs_up_exact_bytes_invalidates_pdf_and_can_be_restored(self):
        job = self.demo()
        before = self.path(job).read_bytes()
        self.app.export(job['id'], {})
        with patch('paperdock.server.orientation.available', return_value=True), patch('paperdock.server.orientation.detect_page', return_value=detected()):
            self.app.auto_orient(job['id'], {'page_id': job['pages'][0]['id']})
            result = self.wait_ready(job['id'])
        self.assertFalse(result['pdf_ready'])
        page = result['pages'][0]
        self.assertEqual((page['width'], page['height']), (96, 64))
        self.assertTrue(page['orientation']['applied'])
        self.assertTrue(page['can_restore_orientation'])
        self.assertNotIn('orientation_backup', page)
        originals = list((self.path(job).parent / 'originals').glob('*.png'))
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0].read_bytes(), before)
        self.assertEqual(stat.S_IMODE(originals[0].stat().st_mode), 0o600)
        edited = self.app.edit_job(job['id'], 'rotate', {'page_id': page['id'], 'degrees': 90})
        self.assertNotIn('orientation', edited['pages'][0])
        self.assertIsNone(edited['orientation_note'])
        self.assertTrue(edited['pages'][0]['can_restore_orientation'])
        restored = self.app.edit_job(job['id'], 'restore-orientation', {'page_id': page['id']})
        self.assertEqual(self.path(job).read_bytes(), before)
        self.assertFalse(restored['pages'][0]['can_restore_orientation'])
        self.assertEqual(restored['pages'][0]['orientation']['reason'], 'restored')
        self.assertEqual(originals[0].read_bytes(), before)

    def test_uncertain_timeout_and_invalid_results_leave_bytes_unchanged(self):
        job = self.demo()
        before = self.path(job).read_bytes()
        for reason in ('uncertain', 'timeout', 'invalid', 'error'):
            with self.subTest(reason=reason), patch('paperdock.server.orientation.available', return_value=True), patch('paperdock.server.orientation.detect_page', return_value=detected(reason, 0, 4.0)):
                self.app.auto_orient(job['id'], {'page_id': job['pages'][0]['id']})
                result = self.wait_ready(job['id'])
            self.assertEqual(self.path(job).read_bytes(), before)
            self.assertFalse(result['pages'][0]['orientation']['applied'])
            self.assertIn('unverändert', result['orientation_note'])
            self.assertFalse(result['pages'][0]['can_restore_orientation'])

    def test_orienting_blocks_edits_upload_export_new_scan_and_can_cancel(self):
        job = self.demo()
        started = threading.Event()
        def pending(path, cancel):
            started.set()
            self.assertTrue(cancel.wait(3))
            return detected('cancelled', 0, None)
        with patch('paperdock.server.orientation.available', return_value=True), patch('paperdock.server.orientation.detect_page', side_effect=pending):
            self.app.auto_orient(job['id'], {})
            self.assertTrue(started.wait(2))
            actions = [lambda: self.app.edit_job(job['id'], 'rotate', {'page_id': job['pages'][0]['id']}),
                       lambda: self.app.edit_job(job['id'], 'rename', {'title': 'Umbenannt'}),
                       lambda: self.app.export(job['id'], {}), lambda: self.app.upload(job['id'], {}),
                       lambda: self.app.new_job({'demo': True})]
            for action in actions:
                with self.assertRaises(AppError) as error:
                    action()
                self.assertEqual(error.exception.status, 409)
            self.app.edit_job(job['id'], 'cancel', {})
            result = self.wait_ready(job['id'])
        self.assertIn('angehalten', result['orientation_note'])
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(self.app.cancellations, {})

    def test_uploaded_documents_prohibit_rename_orient_and_restore(self):
        job = self.demo()
        for status in ('submitted', 'success', 'unknown'):
            self.app.get_job(job['id'])['paperless'] = {'status': status}
            for action in (lambda: self.app.edit_job(job['id'], 'rename', {'title': 'Neu'}),
                           lambda: self.app.auto_orient(job['id'], {}),
                           lambda: self.app.edit_job(job['id'], 'restore-orientation', {'page_id': job['pages'][0]['id']})):
                with self.assertRaises(AppError) as error:
                    action()
                self.assertEqual(error.exception.status, 409)

    def test_pending_rotation_recovers_original_after_restart(self):
        job = self.demo()
        path = self.path(job)
        before = path.read_bytes()
        originals = path.parent / 'originals'
        originals.mkdir(mode=0o700)
        backup = uuid.uuid4().hex + '.png'
        copy_private(path, originals / backup)
        internal = self.app.get_job(job['id'])
        internal.update(status='orienting', pdf_ready=True)
        internal['pages'][0].update(orientation_pending=backup, orientation_backup=backup)
        self.app.save(internal)
        scanner.rotate_page(path, 90)  # Simulate a stop after replacement but before metadata commit.
        self.restart()
        recovered = self.app.get_job(job['id'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(recovered['status'], 'ready')
        self.assertFalse(recovered['pdf_ready'])
        self.assertNotIn('orientation_pending', recovered['pages'][0])
        self.assertEqual(recovered['pages'][0]['orientation']['reason'], 'restored')

    def test_failed_rotation_restores_and_reports_without_original_loss(self):
        job = self.demo()
        before = self.path(job).read_bytes()
        with patch('paperdock.server.orientation.available', return_value=True), patch('paperdock.server.orientation.detect_page', return_value=detected()), patch('paperdock.server.scanner.rotate_page', side_effect=scanner.ScannerError('simulated')):
            self.app.auto_orient(job['id'], {'page_id': job['pages'][0]['id']})
            result = self.wait_ready(job['id'])
        self.assertEqual(self.path(job).read_bytes(), before)
        self.assertEqual(result['pages'][0]['orientation']['reason'], 'error')
        self.assertFalse(result['pdf_ready'])

    def test_scan_applies_saved_preference_after_capture_with_partial_pages_preserved(self):
        self.app.devices = [{'id': 'fake:scanner'}]
        def capture(device, settings, folder, on_page, cancel):
            self.assertTrue(settings['auto_orient'])
            on_page(sample_pages(folder)[0])
            raise scanner.ScannerError('Zweite Seite konnte nicht erfasst werden.')
        with patch('paperdock.server.scanner.scan_pages', side_effect=capture), patch('paperdock.server.orientation.detect_page', return_value=detected()):
            result = self.wait_ready(self.app.new_job({'device': 'fake:scanner'})['id'])
        self.assertEqual(result['status'], 'ready')
        self.assertIn('Zweite Seite', result['error'])
        self.assertTrue(result['pages'][0]['orientation']['applied'])
        self.assertFalse(self.app.scan_lock.locked())

    def test_rename_validates_and_does_not_require_regenerating_pdf(self):
        job = self.demo()
        self.app.export(job['id'], {})
        changed = self.app.edit_job(job['id'], 'rename', {'title': '  Rechnung Büro  '})
        self.assertEqual(changed['title'], 'Rechnung Büro')
        self.assertTrue(changed['pdf_ready'])
        for title in ('', ' ', 'x\ny', 'x' * 201, []):
            with self.assertRaises(AppError):
                self.app.edit_job(job['id'], 'rename', {'title': title})


if __name__ == '__main__':
    unittest.main()
