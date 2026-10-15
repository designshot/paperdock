"""SANE acquisition and local image utilities.

Device discovery never starts a scan. This module does not implement the
proprietary ScanSnap wireless protocol; it uses devices exposed by SANE.
"""

from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from typing import Callable

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


class ScannerError(Exception):
    """An actionable acquisition or image-processing error."""


FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"
DEVICE_FORMAT = FIELD_SEPARATOR.join(("%d", "%v", "%m", "%t")) + RECORD_SEPARATOR
SCAN_TIMEOUT = 15 * 60
SCAN_IDLE_TIMEOUT = 180
POLL_INTERVAL = 0.12
SCAN_DEBUG_MAX_BYTES = 512 * 1024
SCAN_DIAGNOSTIC_MAX_BYTES = 512 * 1024
PAPER_DIMENSIONS = {"A4": ("210", "297"), "Letter": ("215.9", "279.4")}
_USB_SYSFS_ROOT = Path("/sys/bus/usb/devices")
_USB_DEVICE_ROOT = Path("/dev/bus/usb")


def _executable() -> str:
    executable = shutil.which("scanimage")
    if not executable:
        raise ScannerError("SANE fehlt. Installiere das Paket sane-utils (Debian/Ubuntu) bzw. sane-backends (Fedora/Arch).")
    return executable


def _safe_string(value: object, label: str, *, optional: bool = False) -> str:
    if optional and value in (None, ""):
        return ""
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ScannerError(f"Ungültiger Wert für {label}.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ScannerError(f"Ungültiger Wert für {label}.")
    return value


def _integer(value: object, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ScannerError(f"{label} muss eine ganze Zahl sein.")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ScannerError(f"{label} muss eine ganze Zahl sein.") from exc
    if not minimum <= number <= maximum:
        raise ScannerError(f"{label} muss zwischen {minimum} und {maximum} liegen.")
    return number


def _stop_process(process: subprocess.Popen) -> None:
    """Terminate the scan process and any backend children in its session."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def _run_control(arguments: list[str], timeout: float, environment: dict | None = None) -> tuple[int, str, str]:
    """Run a non-scanning query with a bounded lifetime and C locale."""
    try:
        process = subprocess.Popen(
            [_executable(), *arguments], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", shell=False,
            start_new_session=True, env={**(os.environ if environment is None else environment), "LC_ALL": "C"},
        )
    except OSError as exc:
        raise ScannerError(f"SANE konnte nicht gestartet werden: {exc}") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _stop_process(process)
        process.communicate()
        raise ScannerError("Der Scanner antwortet nicht rechtzeitig. Verbindung und Stromversorgung prüfen.") from exc
    return process.returncode, stdout, stderr


def _add_usb_diagnostics(result: dict) -> dict:
    """Explain USB devices visible in sysfs but absent from this environment.

    Sysfs and stat are read-only. A detected USB device is never advertised as a
    usable SANE scanner, and valid SANE network devices remain available.
    """
    try:
        entries = list(_USB_SYSFS_ROOT.iterdir())
    except OSError:
        return result
    diagnostics = []
    warnings = []
    for entry in entries:
        try:
            if (entry / "idVendor").read_text().strip().lower() != "04c5":
                continue
            bus = int((entry / "busnum").read_text().strip())
            device = int((entry / "devnum").read_text().strip())
            if not (1 <= bus <= 999 and 1 <= device <= 999):
                continue
            node = _USB_DEVICE_ROOT / f"{bus:03d}" / f"{device:03d}"
            try:
                node.stat()
            except FileNotFoundError:
                pass
            else:
                continue
            # Ignore unplugging during the check instead of reporting old data.
            if not (entry / "idVendor").is_file():
                continue
        except (OSError, ValueError):
            continue

        def label(name: str, fallback: str) -> str:
            try:
                value = (entry / name).read_text().strip()
            except OSError:
                return fallback
            clean = "".join(char for char in value if ord(char) >= 32 and ord(char) != 127)[:120]
            return clean or fallback

        vendor = label("manufacturer", "Fujitsu")
        model = label("product", "Fujitsu-USB-Gerät")
        diagnostics.append({"vendor": vendor, "model": model, "status": "missing_device_node"})
        warnings.append(
            f"{model} ist per USB angeschlossen, aber die USB-Gerätedatei ist in dieser Umgebung nicht verfügbar. "
            "PaperDock kann hier nicht auf das Gerät zugreifen. Starte PaperDock in einem normalen Terminal "
            "auf deinem Linux-Rechner und suche erneut."
        )
    if diagnostics:
        result["usb_diagnostics"] = diagnostics
        if result.get("warning"):
            warnings.append(result["warning"])
        result["warning"] = "\n\n".join(warnings)
    return result


def discover_devices(timeout: float = 15, *, environment: dict | None = None) -> dict:
    """Return SANE devices and a warning if discovery is unavailable."""
    try:
        code, output, error = _run_control([f"--formatted-device-list={DEVICE_FORMAT}"], timeout, environment)
    except ScannerError as exc:
        return _add_usb_diagnostics({"devices": [], "warning": str(exc)})
    devices = []
    seen = set()
    malformed = False
    for record in output.split(RECORD_SEPARATOR):
        if not record.strip():
            continue
        fields = record.strip("\n").split(FIELD_SEPARATOR)
        if len(fields) != 4:
            malformed = True
            continue
        try:
            device = _safe_string(fields[0], "Gerät")
        except ScannerError:
            malformed = True
            continue
        if device not in seen:
            devices.append(dict(zip(("id", "vendor", "model", "type"), fields)))
            seen.add(device)
    result = {"devices": devices}
    if error.strip() or code or malformed:
        result["warning"] = (error.strip()[:1500] or "Die Gerätesuche konnte nicht vollständig abgeschlossen werden.")
    return _add_usb_diagnostics(result)


def _parse_options(output: str) -> dict:
    result: dict = {"sources": [], "modes": [], "resolutions": [], "paper_sizes": ["Driver"]}
    names = {"source": "sources", "mode": "modes"}
    for match in re.finditer(r"^\s*--(source|mode|resolution)\s+(.+)$", output, re.MULTILINE):
        name, spec = match.groups()
        if "[inactive]" in spec:
            continue
        constraint = spec.split("[", 1)[0].strip()
        if name in names:
            # String choices may contain spaces, e.g. "ADF Duplex".
            if not constraint.startswith("<"):
                result[names[name]] = [item.strip() for item in constraint.split("|") if item.strip()]
        else:
            interval = re.search(r"(\d+(?:\.\d+)?)\.\.(\d+(?:\.\d+)?)", constraint)
            if interval:
                low, high = map(float, interval.groups())
                result["resolutions"] = [dpi for dpi in (75, 100, 150, 200, 300, 400, 600, 1200) if low <= dpi <= high]
            else:
                result["resolutions"] = sorted({int(number) for number in re.findall(r"\d+", constraint) if 50 <= int(number) <= 1200})
    geometry = {}
    for match in re.finditer(r"^\s*(--page-width|--page-height|-x|-y)\s+(.+)$", output, re.MULTILINE):
        name, spec = match.groups()
        if "[inactive]" in spec:
            continue
        interval = re.match(r"(\d+(?:\.\d+)?)\.\.(\d+(?:\.\d+)?)mm\b", spec)
        if interval:
            geometry[name] = tuple(map(float, interval.groups()))
    if all(name in geometry for name in ("--page-width", "--page-height", "-x", "-y")):
        # Current -x/-y limits describe the current paper (often Letter). Setting
        # page-width/page-height first lets the backend expand those limits.
        for name, (width, height) in PAPER_DIMENSIONS.items():
            low_w, high_w = geometry["--page-width"]
            low_h, high_h = geometry["--page-height"]
            if low_w <= float(width) <= high_w and low_h <= float(height) <= high_h:
                result["paper_sizes"].append(name)
    return result


def device_options(device: str, *, environment: dict | None = None) -> dict:
    """Read capabilities; opening a device for help does not acquire images."""
    device = _safe_string(device, "Gerät")
    code, output, error = _run_control([f"--device-name={device}", "--all-options"], 15, environment)
    if code:
        raise ScannerError(error.strip()[:1500] or "Scanneroptionen konnten nicht gelesen werden.")
    result = _parse_options(output)
    result["raw"] = output[:20000]
    return result


def inspect_page(path: Path) -> dict:
    try:
        with Image.open(path) as page:
            width, height = page.size
            page.verify()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ScannerError("Die Seite ist keine vollständig lesbare Bilddatei.") from exc
    return {"width": width, "height": height}


def _save_scan_debug_log(diagnostics, directory: Path) -> None:
    """Keep an opt-in, private, bounded stderr tail without affecting scanning."""
    try:
        if int(os.environ.get("SANE_DEBUG_FUJITSU", "0")) <= 0:
            return
    except ValueError:
        return
    temporary = None
    try:
        diagnostics.seek(0, os.SEEK_END)
        size = diagnostics.tell()
        diagnostics.seek(max(0, size - SCAN_DEBUG_MAX_BYTES))
        tail = diagnostics.read(SCAN_DEBUG_MAX_BYTES)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".scan-debug-", suffix=".log", delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            stream.write(tail)
        temporary.replace(directory / "scan-debug.log")
    except OSError:
        # Diagnostics must not turn an otherwise successful scan into a failure.
        pass
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _scan_failure_message(device: str, diagnostic: str, returncode: int) -> str:
    """Classify explicit backend causes; generic USB errors prove no cause."""
    if device.startswith("fujitsu:") and re.search(
        r"\[fujitsu\]\s+Medium error:\s+WiFi control error\b", diagnostic
    ):
        return (
            "Der Scanner meldet einen WLAN-Steuerungsfehler. Schalte für den USB-Scan WLAN am Scanner aus "
            "und starte den Scan erneut. Bereits eingelesene Seiten bleiben erhalten."
        )
    return diagnostic[-1500:] or f"SANE hat den Scan mit Fehler {returncode} beendet."


def scan_pages(
    device: str,
    settings: dict,
    directory: Path,
    on_page: Callable[[Path], None],
    cancelled: threading.Event,
    *,
    environment: dict | None = None,
) -> list[Path]:
    """Acquire a batch, reporting only completely written, validated pages.

    The caller must accept only a device ID from its discovery result. Completed
    pages survive a cancellation or later device failure. A cancelled empty scan
    returns []; an empty feeder raises ScannerError. Settings are passed as
    separate arguments, never interpolated into a shell command.
    """
    device = _safe_string(device, "Gerät")
    dpi = _integer(settings.get("dpi", 300), "Auflösung", 50, 1200)
    page_limit = _integer(settings.get("page_limit", 50), "Seitenlimit", 1, 100)
    mode = _safe_string(settings.get("mode"), "Farbmodus", optional=True)
    source = _safe_string(settings.get("source"), "Papiereinzug", optional=True)
    paper_size = settings.get("paper_size", "Driver")
    if not isinstance(paper_size, str) or paper_size not in ("Driver", *PAPER_DIMENSIONS):
        raise ScannerError("Unbekanntes Papierformat. Bitte Treibervorgabe, A4 oder Letter wählen.")
    if paper_size != "Driver" and not re.match(r"^ADF(?:\s|$)", source, re.IGNORECASE):
        raise ScannerError("Feste Papierformate werden nur für den ADF-Papiereinzug unterstützt.")
    if cancelled.is_set():
        return []
    executable = _executable()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    started = last_progress = time.monotonic()
    timed_out = False
    with tempfile.TemporaryDirectory(prefix=".scan-", dir=directory) as scratch_name:
        scratch = Path(scratch_name)
        arguments = [
            executable, f"--device-name={device}", "--format=png",
            "--batch=page-%04d.png", "--batch-start=1",
            f"--batch-count={page_limit}",
        ]
        if source:
            arguments.append(f"--source={source}")
        if mode:
            arguments.append(f"--mode={mode}")
        arguments.append(f"--resolution={dpi}")
        if paper_size != "Driver":
            width, height = PAPER_DIMENSIONS[paper_size]
            arguments.extend([
                f"--page-width={width}", f"--page-height={height}",
                "-l", "0", "-t", "0", "-x", width, "-y", height,
            ])
        # A file avoids pipe deadlocks even for very verbose backend diagnostics.
        with tempfile.TemporaryFile() as diagnostics:
            try:
                process = subprocess.Popen(
                    arguments, cwd=scratch, stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=diagnostics, shell=False,
                    start_new_session=True, env={**(os.environ if environment is None else environment), "LC_ALL": "C"},
                )
            except OSError as exc:
                raise ScannerError(f"SANE konnte nicht gestartet werden: {exc}") from exc

            def collect() -> None:
                nonlocal last_progress
                for candidate in sorted(scratch.glob("page-*.png")):
                    try:
                        inspect_page(candidate)
                    except ScannerError:
                        # PNG exists while SANE is writing; wait for its IEND.
                        continue
                    destination = directory / candidate.name
                    if destination.exists():
                        raise ScannerError("Das Scanverzeichnis enthält bereits Seiten. Bitte einen neuen Scan starten.")
                    candidate.replace(destination)
                    pages.append(destination)
                    last_progress = time.monotonic()
                    on_page(destination)

            try:
                while True:
                    collect()
                    if cancelled.is_set():
                        _stop_process(process)
                        break
                    if process.poll() is not None:
                        break
                    now = time.monotonic()
                    if now - started > SCAN_TIMEOUT or now - last_progress > SCAN_IDLE_TIMEOUT:
                        timed_out = True
                        _stop_process(process)
                        break
                    cancelled.wait(POLL_INTERVAL)
                collect()
            finally:
                try:
                    _stop_process(process)
                finally:
                    _save_scan_debug_log(diagnostics, directory)
            diagnostics.seek(0, os.SEEK_END)
            length = diagnostics.tell()
            diagnostics.seek(max(0, length - SCAN_DIAGNOSTIC_MAX_BYTES))
            detail = diagnostics.read(SCAN_DIAGNOSTIC_MAX_BYTES).decode("utf-8", "replace").strip()
            if cancelled.is_set():
                return pages
            if timed_out:
                raise ScannerError("Scan wegen Zeitüberschreitung beendet. Bereits eingelesene Seiten bleiben erhalten.")
            # SANE_STATUS_NO_DOCS (7) is the normal end of an ADF batch.
            no_paper = process.returncode == 7 or "document feeder out of documents" in detail.lower()
            if process.returncode and not no_paper:
                raise ScannerError(_scan_failure_message(device, detail, process.returncode))
            if not pages:
                raise ScannerError("Keine Seiten eingelesen. Papier einlegen und den richtigen Einzug wählen.")
            if any(item.stat().st_size for item in scratch.glob("page-*.png")):
                raise ScannerError("Eine Seite wurde unvollständig übertragen. Vollständige Seiten bleiben erhalten.")
    return pages


def rotate_page(path: Path, degrees: int = 90) -> None:
    """Rotate clockwise in quarter turns, atomically replacing the PNG."""
    if isinstance(degrees, bool) or degrees not in (90, 180, 270, -90, -180, -270):
        raise ScannerError("Drehung muss 90, 180 oder 270 Grad betragen.")
    path = Path(path)
    temporary = None
    try:
        with Image.open(path) as original:
            dpi = original.info.get("dpi", (300, 300))
            with original.rotate(-degrees, expand=True) as rotated:
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".rotate-", suffix=".png", delete=False) as handle:
                    temporary = Path(handle.name)
                rotated.save(temporary, format="PNG", dpi=dpi)
        temporary.replace(path)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ScannerError("Die Seite konnte nicht gedreht werden.") from exc
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def export_pdf(page_paths: list[Path], destination: Path, dpi: int = 300) -> Path:
    """Write a multipage RGB PDF at the acquisition resolution, atomically."""
    dpi = _integer(dpi, "Auflösung", 50, 1200)
    if not page_paths:
        raise ScannerError("Für den PDF-Export ist mindestens eine Seite nötig.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with ExitStack() as stack:
            pages = []
            for path in page_paths:
                source = stack.enter_context(Image.open(path))
                pages.append(stack.enter_context(source.convert("RGB")))
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".export-", suffix=".pdf", delete=False) as handle:
                temporary = Path(handle.name)
            pages[0].save(temporary, format="PDF", save_all=True, append_images=pages[1:], resolution=dpi)
        temporary.replace(destination)
        return destination
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ScannerError("PDF konnte nicht erstellt werden. Bitte die Seiten prüfen.") from exc
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for directory in (Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")):
        try:
            return ImageFont.truetype(str(directory / name), size)
        except OSError:
            pass
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def create_demo(directory: Path) -> list[Path]:
    """Create three clearly marked fictional documents; never contact hardware."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    ink, muted, accent = "#172a36", "#6d7d88", "#0e8b76"
    paths = []
    for page_number in range(1, 4):
        page = Image.new("RGB", (1240, 1754), "#ffffff")
        draw = ImageDraw.Draw(page)

        def text(x: int, y: int, value: str, size: int = 25, color: str = ink, bold: bool = False):
            draw.text((x, y), value, font=_font(size, bold), fill=color)

        draw.rectangle((0, 0, 1240, 18), fill=accent)
        text(100, 88, "MUSTERATELIER", 24, accent, True)
        text(100, 124, "NORD", 24, accent, True)
        draw.rounded_rectangle((905, 88, 1136, 143), radius=16, fill="#e3f4ee")
        text(936, 101, "DEMO · FIKTIV", 19, accent, True)
        draw.line((100, 1500, 1140, 1500), fill="#dce5e8", width=2)
        text(100, 1530, "Paperdock · Beispieldokument", 20, muted)
        text(100, 1565, "Alle Angaben sind frei erfunden. Kein gültiger Beleg.", 20, muted)
        text(1060, 1530, f"0{page_number}", 22, muted)

        if page_number == 1:
            text(100, 252, "Rechnung", 62, ink, True)
            text(104, 342, "DEMO-2026-014  ·  01.10.2026", 23, muted)
            text(100, 455, "Für", 21, muted)
            text(100, 495, "Musterkunde", 29, ink, True)
            text(100, 540, "Beispielstraße 1", 25)
            text(100, 580, "00000 Musterstadt", 25)
            draw.rounded_rectangle((100, 700, 1140, 770), radius=12, fill="#eef4f5")
            text(125, 720, "Beschreibung", 23, muted, True)
            text(890, 720, "Betrag", 23, muted, True)
            rows = [("Papier & Bürobedarf", "32,00 €"), ("Dokumentenmappe", "18,00 €"), ("Versand", "5,00 €")]
            for row, (label, amount) in enumerate(rows):
                y = 818 + row * 100
                text(125, y, label, 27)
                text(890, y, amount, 27)
                draw.line((125, y + 65, 1110, y + 65), fill="#e4eaed", width=2)
            draw.rounded_rectangle((100, 1190, 1140, 1300), radius=16, fill=ink)
            text(130, 1224, "Gesamtbetrag (Muster)", 26, "#ffffff", True)
            text(888, 1219, "55,00 €", 35, "#ffffff", True)
            text(100, 1370, "Beispiel für einen Beleg in deinem digitalen Archiv.", 23, muted)
        elif page_number == 2:
            text(100, 252, "Alles an einem Ort.", 56, ink, True)
            text(104, 340, "Anlage zur Musterrechnung", 25, muted)
            text(100, 470, "Weniger Papier. Mehr Überblick.", 32, ink, True)
            lines = [
                "Dieses Dokument gehört zum Demo-Stapel von Paperdock.",
                "Du kannst die Seiten ansehen, drehen, neu sortieren", 
                "und gemeinsam als PDF exportieren.",
                "",
                "Mit einer eingerichteten Paperless-ngx-Verbindung", 
                "lassen sich Dokumente direkt an dein Archiv übergeben.",
                "Die Texterkennung übernimmt anschließend Paperless.",
            ]
            for index, line in enumerate(lines):
                text(100, 550 + index * 47, line, 26)
            draw.rounded_rectangle((100, 970, 1140, 1285), radius=22, fill="#eef7f3")
            text(140, 1015, "Dein erster Stapel", 32, accent, True)
            for index, label in enumerate(("01   Seiten prüfen", "02   Reihenfolge festlegen", "03   PDF speichern oder an Paperless senden")):
                text(140, 1090 + index * 55, label, 25)
            text(100, 1370, "Diese Seite enthält ausschließlich Beispieltext.", 23, muted)
        else:
            text(100, 252, "Kassenbeleg", 62, ink, True)
            text(104, 342, "BEISPIEL · 02.10.2026 · 10:24", 23, muted)
            draw.rounded_rectangle((220, 490, 1020, 1360), radius=20, fill="#faf8f2", outline="#eee9dd", width=2)
            text(280, 550, "PAPIERLADEN MUSTER", 30, ink, True)
            text(280, 600, "Fiktiver Einkauf · Demo Nr. 003", 22, muted)
            for y in (680, 1030):
                for x in range(280, 960, 22):
                    draw.line((x, y, x + 10, y), fill="#aab1af", width=2)
            for index, (label, amount) in enumerate((("Notizbuch", "8,50 €"), ("Stift, blau", "2,40 €"), ("Registerset", "4,90 €"))):
                text(280, 735 + index * 87, label, 27)
                text(805, 735 + index * 87, amount, 27)
            text(280, 1085, "SUMME", 31, ink, True)
            text(785, 1085, "15,80 €", 31, ink, True)
            text(280, 1160, "Kein gültiger Zahlungsbeleg", 23, muted)
            text(280, 1250, "Vielen Dank fürs Ausprobieren!", 23, accent)
        path = directory / f"demo-{page_number:04d}.png"
        page.save(path, format="PNG", dpi=(150, 150), optimize=True)
        page.close()
        paths.append(path)
    return paths
