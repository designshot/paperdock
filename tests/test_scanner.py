"""Scanner tests use a local fake executable; they never access hardware."""

from pathlib import Path
import json
import os
import re
import stat
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image

from paperdock import scanner


FAKE_SCANNER = r'''
import json
import os
from pathlib import Path
import sys
import time
from PIL import Image

Path(os.environ["PAPERDOCK_TEST_ARGS"]).write_text(json.dumps(sys.argv[1:]))
if any(arg.startswith("--formatted-device-list=") for arg in sys.argv):
    print("fujitsu:usb:test\x1fFUJITSU\x1fiX1300\x1fsheetfed scanner\x1e", end="")
    sys.exit(0)
if "--all-options" in sys.argv:
    print("  --source ADF Front|ADF Duplex [ADF Front]")
    print("  --mode Lineart|Gray|Color [Color]")
    print("  --resolution 50..600dpi [300]")
    print("  --page-width 0..219.428mm [215.872]")
    print("  --page-height 0..3008.67mm [279.364]")
    print("  -x 0..215.872mm [215.872]")
    print("  -y 0..279.364mm [279.364]")
    sys.exit(0)
scenario = os.environ.get("PAPERDOCK_TEST_SCENARIO", "normal")
if os.environ.get("PAPERDOCK_TEST_LOG"):
    print(os.environ["PAPERDOCK_TEST_LOG"], file=sys.stderr)
if scenario == "empty":
    print("scanimage: sane_start: Document feeder out of documents", file=sys.stderr)
    sys.exit(7)
if scenario == "timeout":
    time.sleep(30)
if scenario == "corrupt":
    Path("page-0001.png").write_bytes(b"not a png")
    sys.exit(0)
if scenario == "wifi_control_error":
    print("[fujitsu] Medium error: WiFi control error", file=sys.stderr)
    print("[fujitsu] sane_start: ERROR: cannot load page", file=sys.stderr)
    print("scanimage: sane_start: Error during device I/O", file=sys.stderr)
    print("[fujitsu] cleanup\n" * 700, file=sys.stderr)
    sys.exit(9)
if scenario == "unrelated_usb_error":
    print("[sanei_usb] Some unrelated USB device: Access denied", file=sys.stderr)
    print("scanimage: sane_start: Error during device I/O", file=sys.stderr)
    sys.exit(9)
for number in range(1, 3):
    size = (64, 96)
    if scenario == "geometry":
        dpi = int(next(arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--resolution=")))
        width = float(sys.argv[sys.argv.index("-x") + 1])
        height = float(sys.argv[sys.argv.index("-y") + 1])
        size = (round(width / 25.4 * dpi), round(height / 25.4 * dpi))
    Image.new("RGB", size, (30 * number, 120, 110)).save(f"page-{number:04d}.png")
    if scenario == "cancel":
        time.sleep(30)
    time.sleep(0.05)
if scenario == "hardware_error":
    print("scanimage: sane_start: Document feeder jammed", file=sys.stderr)
    sys.exit(6)
sys.exit(7)
'''


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.executable = self.root / "fake-scanimage"
        self.executable.write_text(f"#!{sys.executable}\n" + FAKE_SCANNER)
        self.executable.chmod(0o755)
        self.args_path = self.root / "arguments.json"
        self.sysfs = self.root / "sysfs"
        self.sysfs.mkdir()
        self.usb_nodes = self.root / "usb-nodes"
        self.usb_patch = patch.multiple(scanner, _USB_SYSFS_ROOT=self.sysfs, _USB_DEVICE_ROOT=self.usb_nodes)
        self.path_patch = patch.object(scanner.shutil, "which", return_value=str(self.executable))
        self.env_patch = patch.dict(os.environ, {"PAPERDOCK_TEST_ARGS": str(self.args_path), "PAPERDOCK_TEST_SCENARIO": "normal"})
        self.path_patch.start()
        self.env_patch.start()
        self.usb_patch.start()

    def tearDown(self):
        self.usb_patch.stop()
        self.env_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def scan(self, scenario="normal", callback=None, cancelled=None, settings=None):
        with patch.dict(os.environ, {"PAPERDOCK_TEST_SCENARIO": scenario}):
            return scanner.scan_pages(
                "fujitsu:usb:test", settings or {"dpi": 300, "source": "ADF Duplex", "mode": "Color", "page_limit": 10},
                self.root / "pages", callback or (lambda page: None), cancelled or threading.Event(),
            )

    def test_discovery_queries_without_scanning(self):
        result = scanner.discover_devices()
        self.assertEqual(result["devices"], [{"id": "fujitsu:usb:test", "vendor": "FUJITSU", "model": "iX1300", "type": "sheetfed scanner"}])
        args = json.loads(self.args_path.read_text())
        self.assertEqual(args, ["--formatted-device-list=" + scanner.DEVICE_FORMAT])
        self.assertFalse(list(self.root.glob("**/*.png")))

    def usb_device(self, vendor="04c5", model="ScanSnap Example", node_present=False):
        device = self.sysfs / "7-4"
        device.mkdir()
        for key, value in {"idVendor": vendor, "manufacturer": "Fujitsu", "product": model, "busnum": "7", "devnum": "11"}.items():
            (device / key).write_text(value)
        if node_present:
            node = self.usb_nodes / "007" / "011"
            node.parent.mkdir(parents=True)
            node.touch()
        return device

    def test_attached_usb_missing_node_is_explained_without_inventing_sane_device(self):
        self.usb_device()
        with patch.object(scanner, "_run_control", return_value=(0, "", "")):
            result = scanner.discover_devices()
        self.assertEqual(result["devices"], [])
        self.assertEqual(result["usb_diagnostics"], [{"vendor": "Fujitsu", "model": "ScanSnap Example", "status": "missing_device_node"}])
        self.assertIn("ist per USB angeschlossen", result["warning"])
        self.assertIn("USB-Gerätedatei", result["warning"])
        self.assertNotIn("iX1300", result["warning"])

    def test_usb_diagnostic_keeps_usable_network_devices_and_sane_warning(self):
        self.usb_device()
        output = scanner.FIELD_SEPARATOR.join(("net:scanner:device", "Other vendor", "Office scanner", "network scanner")) + scanner.RECORD_SEPARATOR
        with patch.object(scanner, "_run_control", return_value=(0, output, "One backend did not respond")):
            result = scanner.discover_devices()
        self.assertEqual(result["devices"][0]["id"], "net:scanner:device")
        self.assertEqual(len(result["devices"]), 1)
        self.assertIn("One backend did not respond", result["warning"])
        self.assertIn("missing_device_node", result["usb_diagnostics"][0]["status"])

    def test_no_usb_hardware_does_not_claim_an_access_problem(self):
        with patch.object(scanner, "_run_control", return_value=(0, "", "")):
            self.assertEqual(scanner.discover_devices(), {"devices": []})

    def test_existing_usb_node_does_not_imply_a_driver_or_permission_diagnosis(self):
        self.usb_device(node_present=True)
        with patch.object(scanner, "_run_control", return_value=(0, "", "")):
            self.assertEqual(scanner.discover_devices(), {"devices": []})

    def test_unrelated_vendor_and_unavailable_sysfs_are_ignored(self):
        self.usb_device(vendor="1234")
        with patch.object(scanner, "_run_control", return_value=(0, "", "")):
            self.assertEqual(scanner.discover_devices(), {"devices": []})
            with patch.object(scanner, "_USB_SYSFS_ROOT", self.root / "absent-sysfs"):
                self.assertEqual(scanner.discover_devices(), {"devices": []})

    def test_missing_sane_keeps_both_actionable_diagnostics(self):
        self.usb_device()
        with patch.object(scanner.shutil, "which", return_value=None):
            result = scanner.discover_devices()
        self.assertIn("SANE fehlt", result["warning"])
        self.assertIn("USB-Gerätedatei", result["warning"])

    def test_capabilities_parse_spaced_sources_and_resolution_range(self):
        result = scanner.device_options("fujitsu:usb:test")
        self.assertEqual(result["sources"], ["ADF Front", "ADF Duplex"])
        self.assertEqual(result["modes"], ["Lineart", "Gray", "Color"])
        self.assertEqual(result["resolutions"], [75, 100, 150, 200, 300, 400, 600])
        self.assertEqual(result["paper_sizes"], ["Driver", "A4", "Letter"])

    def test_a4_geometry_follows_source_mode_resolution_and_sets_paper_before_area(self):
        self.scan(settings={"dpi": 300, "source": "ADF Front", "mode": "Color", "paper_size": "A4"})
        args = json.loads(self.args_path.read_text())
        offset = args.index("--source=ADF Front")
        self.assertEqual(args[offset:], [
            "--source=ADF Front", "--mode=Color", "--resolution=300",
            "--page-width=210", "--page-height=297", "-l", "0", "-t", "0", "-x", "210", "-y", "297",
        ])

    def test_letter_geometry_accepts_generic_adf_source(self):
        self.scan(settings={"source": "ADF", "paper_size": "Letter"})
        args = json.loads(self.args_path.read_text())
        self.assertIn("--page-width=215.9", args)
        self.assertIn("--page-height=279.4", args)
        self.assertEqual(args[-4:], ["-x", "215.9", "-y", "279.4"])

    def test_driver_geometry_remains_unmodified(self):
        self.scan()
        args = json.loads(self.args_path.read_text())
        self.assertFalse(any(arg.startswith("--page-") for arg in args))
        self.assertNotIn("-x", args)

    def test_a4_scan_pdf_preserves_dimensions_from_real_pixel_size(self):
        dpi = 254
        paths = self.scan("geometry", settings={"source": "ADF Front", "paper_size": "A4", "dpi": dpi})
        self.assertEqual(scanner.inspect_page(paths[0]), {"width": 2100, "height": 2970})
        pdf = scanner.export_pdf(paths, self.root / "a4.pdf", dpi=dpi).read_bytes()
        boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
        self.assertEqual(len(boxes), 2)
        self.assertAlmostEqual(float(boxes[0][0]), 210 / 25.4 * 72, places=2)
        self.assertAlmostEqual(float(boxes[0][1]), 297 / 25.4 * 72, places=2)

    def test_batch_retains_pages_when_feeder_empties(self):
        seen = []
        pages = self.scan(callback=lambda path: seen.append((path, scanner.inspect_page(path))))
        self.assertEqual(len(pages), 2)
        self.assertEqual([item[0] for item in seen], pages)
        self.assertEqual(seen[0][1], {"width": 64, "height": 96})
        args = json.loads(self.args_path.read_text())
        self.assertIn("--source=ADF Duplex", args)
        self.assertIn("--batch-count=10", args)
        self.assertIn("--resolution=300", args)
        self.assertFalse(list((self.root / "pages").glob(".scan-*")))

    def test_arguments_are_not_shell_evaluated(self):
        sentinel = self.root / "DO_NOT_CREATE"
        malicious = f"Color; touch {sentinel} $(touch {sentinel})"
        self.scan(settings={"dpi": 150, "mode": malicious, "page_limit": 1})
        args = json.loads(self.args_path.read_text())
        self.assertIn("--mode=" + malicious, args)
        self.assertFalse(sentinel.exists())

    def test_cancel_before_launch_never_starts_process(self):
        cancelled = threading.Event()
        cancelled.set()
        self.assertEqual(self.scan(cancelled=cancelled), [])
        self.assertFalse(self.args_path.exists())

    def test_cancel_during_acquisition_preserves_completed_page(self):
        cancelled = threading.Event()
        pages = self.scan("cancel", callback=lambda path: cancelled.set(), cancelled=cancelled)
        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0].exists())

    def test_empty_feeder_raises_actionable_message(self):
        with self.assertRaisesRegex(scanner.ScannerError, "Keine Seiten"):
            self.scan("empty")

    def test_hardware_error_preserves_completed_pages(self):
        seen = []
        with self.assertRaisesRegex(scanner.ScannerError, "jammed"):
            self.scan("hardware_error", callback=seen.append)
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(path.exists() for path in seen))

    def test_explicit_wifi_error_survives_long_cleanup_tail(self):
        with self.assertRaisesRegex(scanner.ScannerError, "WLAN-Steuerungsfehler") as raised:
            self.scan("wifi_control_error")
        self.assertIn("USB-Scan WLAN am Scanner aus", str(raised.exception))
        self.assertNotIn("cleanup", str(raised.exception))

    def test_unrelated_usb_error_does_not_invent_wifi_or_permissions_fix(self):
        with self.assertRaises(scanner.ScannerError) as raised:
            self.scan("unrelated_usb_error")
        message = str(raised.exception)
        self.assertIn("Error during device I/O", message)
        self.assertNotIn("WLAN", message)
        self.assertNotIn("Berechtigungen", message)
        self.assertNotIn("udev", message)

    def test_timeout_stops_process(self):
        with patch.object(scanner, "SCAN_IDLE_TIMEOUT", 0.02):
            with self.assertRaisesRegex(scanner.ScannerError, "Zeitüberschreitung"):
                self.scan("timeout")

    def test_debug_log_is_opt_in_and_private_on_success(self):
        with patch.dict(os.environ, {"SANE_DEBUG_FUJITSU": "10", "PAPERDOCK_TEST_LOG": "function trace: success"}):
            self.scan()
        log = self.root / "pages" / "scan-debug.log"
        self.assertIn("function trace: success", log.read_text())
        self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_debug_log_retains_bounded_tail_on_failure(self):
        with patch.dict(os.environ, {"SANE_DEBUG_FUJITSU": "10", "PAPERDOCK_TEST_LOG": "first line\n" + "X" * 400}), patch.object(scanner, "SCAN_DEBUG_MAX_BYTES", 128):
            with self.assertRaisesRegex(scanner.ScannerError, "jammed"):
                self.scan("hardware_error")
        log = self.root / "pages" / "scan-debug.log"
        self.assertEqual(log.stat().st_size, 128)
        self.assertNotIn("first line", log.read_text())
        self.assertIn("Document feeder jammed", log.read_text())

    def test_debug_disabled_does_not_persist_log(self):
        with patch.dict(os.environ, {"SANE_DEBUG_FUJITSU": "0", "PAPERDOCK_TEST_LOG": "must not persist"}):
            self.scan()
        self.assertFalse((self.root / "pages" / "scan-debug.log").exists())

    def test_corrupt_output_never_reaches_callback(self):
        seen = []
        with self.assertRaises(scanner.ScannerError):
            self.scan("corrupt", callback=seen.append)
        self.assertEqual(seen, [])

    def test_bad_parameters_fail_before_start(self):
        for settings in ({"dpi": 0}, {"dpi": True}, {"dpi": 300.5}, {"page_limit": 101}, {"mode": "Color\n--test"},
                         {"paper_size": "A3"}, {"paper_size": []}, {"paper_size": "A4", "source": "Card Front"}):
            with self.subTest(settings=settings), self.assertRaises(scanner.ScannerError):
                self.scan(settings=settings)
        self.assertFalse(self.args_path.exists())

    def test_missing_sane_returns_warning(self):
        with patch.object(scanner.shutil, "which", return_value=None):
            result = scanner.discover_devices()
        self.assertEqual(result["devices"], [])
        self.assertIn("SANE fehlt", result["warning"])


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_demo_creates_three_full_size_pages_and_multipage_pdf(self):
        paths = scanner.create_demo(self.root)
        self.assertEqual(len(paths), 3)
        self.assertEqual(scanner.inspect_page(paths[0]), {"width": 1240, "height": 1754})
        destination = scanner.export_pdf(paths, self.root / "demo.pdf", dpi=150)
        pdf = destination.read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 3)
        boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
        self.assertEqual(len(boxes), 3)
        self.assertAlmostEqual(float(boxes[0][0]), 1240 / 150 * 72, places=2)
        self.assertAlmostEqual(float(boxes[0][1]), 1754 / 150 * 72, places=2)

    def test_rotate_is_clockwise_and_retains_resolution(self):
        path = self.root / "page.png"
        with Image.new("RGB", (40, 20), "white") as page:
            page.putpixel((0, 0), (255, 0, 0))
            page.save(path, dpi=(150, 150))
        scanner.rotate_page(path)
        with Image.open(path) as rotated:
            self.assertEqual(rotated.size, (20, 40))
            self.assertEqual(rotated.getpixel((19, 0)), (255, 0, 0))
            self.assertAlmostEqual(rotated.info["dpi"][0], 150, places=1)
        self.assertFalse(list(self.root.glob(".rotate-*")))

    def test_empty_pdf_rejected(self):
        with self.assertRaisesRegex(scanner.ScannerError, "mindestens eine Seite"):
            scanner.export_pdf([], self.root / "empty.pdf")
        self.assertFalse((self.root / "empty.pdf").exists())

    def test_failed_pdf_does_not_replace_previous_file(self):
        destination = self.root / "previous.pdf"
        destination.write_bytes(b"previous content")
        with self.assertRaises(scanner.ScannerError):
            scanner.export_pdf([self.root / "missing.png"], destination)
        self.assertEqual(destination.read_bytes(), b"previous content")

    def test_discrete_capabilities_and_inactive_fields(self):
        options = scanner._parse_options("  --resolution 100|200|300|600dpi [300]\n  --source ADF|Flatbed [inactive]\n")
        self.assertEqual(options["resolutions"], [100, 200, 300, 600])
        self.assertEqual(options["sources"], [])

    def test_paper_sizes_require_geometry_support_and_fitting_page_limits(self):
        self.assertEqual(scanner._parse_options("--source Flatbed\n")["paper_sizes"], ["Driver"])
        raw = "  --page-width 0..210mm [210]\n  --page-height 0..297mm [297]\n  -x 0..210mm [210]\n  -y 0..279mm [279]\n"
        self.assertEqual(scanner._parse_options(raw)["paper_sizes"], ["Driver", "A4"])
        self.assertEqual(scanner._parse_options(raw.replace("297mm", "200mm"))["paper_sizes"], ["Driver"])
        self.assertEqual(scanner._parse_options(raw.replace("[297]", "[inactive]"))["paper_sizes"], ["Driver"])


if __name__ == "__main__":
    unittest.main()
