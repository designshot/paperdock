"""Orientation tests use synthetic images and a local process, never a scanner."""

from pathlib import Path
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image

from paperdock import orientation


FAKE_TESSERACT = r'''
import json
import os
from pathlib import Path
import subprocess
import sys
import time

with open(os.environ["PAPERDOCK_OSD_ARGS"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
if "--list-langs" in sys.argv:
    print("List of available languages (2):\neng")
    if os.environ.get("PAPERDOCK_OSD_LANGUAGE", "yes") == "yes":
        print("osd")
    sys.exit(0)
scenario = os.environ.get("PAPERDOCK_OSD_SCENARIO", "normal")
if scenario in ("child", "orphan"):
    child = subprocess.Popen([sys.executable, "-c",
        "import os, signal, time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "Path(os.environ['PAPERDOCK_OSD_READY']).touch(); time.sleep(30)"])
    while not Path(os.environ["PAPERDOCK_OSD_READY"]).exists():
        time.sleep(0.01)
    Path(os.environ["PAPERDOCK_OSD_PIDS"]).write_text(json.dumps([os.getpid(), child.pid]))
    if scenario == "orphan":
        sys.exit(0)
    time.sleep(30)
if scenario == "timeout":
    time.sleep(30)
if scenario in ("flood_stdout", "flood_stderr"):
    output = sys.stdout if scenario == "flood_stdout" else sys.stderr
    while True:
        output.write("x" * 8192)
        output.flush()
if scenario == "sparse":
    print("Too few characters. Skipping this page", file=sys.stderr)
    sys.exit(1)
if scenario == "error":
    print("Unable to open image", file=sys.stderr)
    sys.exit(1)
print(os.environ["PAPERDOCK_OSD_OUTPUT"])
'''


def osd(rotation=90, confidence="18.52"):
    return (
        f"Page number: 0\nOrientation in degrees: {(-rotation) % 360}\n"
        f"Rotate: {rotation}\nOrientation confidence: {confidence}\n"
        "Script: Latin\nScript confidence: 4.00\n"
    )


class OrientationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.executable = self.root / "fake-tesseract"
        self.executable.write_text(f"#!{sys.executable}\n" + FAKE_TESSERACT)
        self.executable.chmod(0o755)
        self.page = self.root / "page.png"
        Image.new("RGB", (64, 96), "white").save(self.page)
        self.original = self.page.read_bytes()
        self.args = self.root / "arguments.jsonl"
        self.pids = self.root / "pids.json"
        self.path_patch = patch.object(orientation.shutil, "which", return_value=str(self.executable))
        self.env_patch = patch.dict(os.environ, {
            "PAPERDOCK_OSD_ARGS": str(self.args), "PAPERDOCK_OSD_OUTPUT": osd(),
            "PAPERDOCK_OSD_SCENARIO": "normal", "PAPERDOCK_OSD_LANGUAGE": "yes",
            "PAPERDOCK_OSD_PIDS": str(self.pids), "PAPERDOCK_OSD_READY": str(self.root / "ready"),
        })
        self.cache_patch = patch.object(orientation, "_availability_cache", None)
        self.path_patch.start()
        self.env_patch.start()
        self.cache_patch.start()

    def tearDown(self):
        self.assertEqual(self.page.read_bytes(), self.original)
        self.cache_patch.stop()
        self.env_patch.stop()
        self.path_patch.stop()
        self.temp.cleanup()

    def detect(self, scenario="normal", output=None, cancelled=None):
        env = {"PAPERDOCK_OSD_SCENARIO": scenario}
        if output is not None:
            env["PAPERDOCK_OSD_OUTPUT"] = output
        with patch.dict(os.environ, env):
            return orientation.detect_page(self.page, cancelled)

    def calls(self):
        return [json.loads(line) for line in self.args.read_text().splitlines()]

    def test_confident_quarter_turns_are_clockwise_corrections_without_mutation(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                self.assertEqual(self.detect(output=osd(rotation)), {
                    "rotation": rotation, "confidence": 18.52, "applied": False,
                    "reason": "rotate" if rotation else "upright",
                })
        self.assertEqual(len([call for call in self.calls() if call == ["--list-langs"]]), 1)
        self.assertEqual(list(self.root.glob("*.osd")), [])

    def test_low_confidence_never_proposes_rotation(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                result = self.detect(output=osd(rotation, "14.99"))
                self.assertEqual(result["reason"], "uncertain")
                self.assertEqual(result["rotation"], 0)
                self.assertEqual(result["confidence"], 14.99)
        self.assertEqual(self.detect(output=osd(90, "15.00"))["reason"], "rotate")

    def test_malformed_inconsistent_or_nonfinite_output_never_proposes_rotation(self):
        invalid = ["", "Rotate: 90", osd() + "Rotate: 90\n",
                   osd().replace("Rotate: 90", "Rotate: 45"),
                   osd().replace("Rotate: 90", "Rotate: -90"),
                   osd().replace("Orientation in degrees: 270", "Orientation in degrees: 90")]
        invalid.extend(osd(confidence=value) for value in ("NaN", "inf", "-1", "100.01", "1e3", "99%", "9" * 400))
        for output in invalid:
            with self.subTest(output=output[:100]):
                result = self.detect(output=output)
                self.assertEqual(result["reason"], "invalid")
                self.assertEqual(result["rotation"], 0)

    def test_missing_binary_and_osd_are_reported_as_unavailable(self):
        with patch.object(orientation.shutil, "which", return_value=None):
            self.assertFalse(orientation.available())
            self.assertEqual(self.detect()["reason"], "unavailable")
        self.assertFalse(self.args.exists())
        with patch.dict(os.environ, {"PAPERDOCK_OSD_LANGUAGE": "no"}):
            self.assertFalse(orientation.available())
            self.assertEqual(self.detect()["reason"], "unavailable")
        self.assertEqual(self.calls(), [["--list-langs"]])

    def test_availability_is_cached_but_installation_can_be_detected_after_expiry(self):
        with patch.dict(os.environ, {"PAPERDOCK_OSD_LANGUAGE": "no"}):
            self.assertFalse(orientation.available())
        self.assertFalse(orientation.available())
        key, _, supported = orientation._availability_cache
        orientation._availability_cache = (key, 0, supported)
        self.assertTrue(orientation.available())
        self.assertTrue(orientation.available())
        self.assertEqual(self.calls(), [["--list-langs"], ["--list-langs"]])

    def test_data_directory_change_invalidates_availability_cache(self):
        self.assertTrue(orientation.available())
        with patch.dict(os.environ, {"TESSDATA_PREFIX": str(self.root / "different-data")}):
            self.assertTrue(orientation.available())
        self.assertEqual(self.calls(), [["--list-langs"], ["--list-langs"]])

    def test_sparse_page_and_process_error_are_distinguishable(self):
        self.assertEqual(self.detect("sparse")["reason"], "uncertain")
        self.assertEqual(self.detect("error")["reason"], "error")

    def test_invalid_path_does_not_launch_a_process(self):
        for path in (self.root / "missing.png", self.root):
            self.assertEqual(orientation.detect_page(path)["reason"], "invalid")
        self.assertFalse(self.args.exists())

    def test_path_is_passed_literally_and_mode_is_osd_only(self):
        malicious = self.root / "-photo; touch CREATED $(echo boom).png"
        malicious.write_bytes(self.original)
        self.assertEqual(orientation.detect_page(malicious)["reason"], "rotate")
        self.assertEqual(self.calls()[-1], [str(malicious), "stdout", "-l", "osd", "--psm", "0"])
        self.assertFalse((self.root / "CREATED").exists())
        self.assertEqual(malicious.read_bytes(), self.original)

    def test_timeout_returns_without_waiting_for_process(self):
        with patch.object(orientation, "DETECT_TIMEOUT", 0.15):
            started = time.monotonic()
            self.assertEqual(self.detect("timeout")["reason"], "timeout")
            self.assertLess(time.monotonic() - started, 2)

    def test_output_is_bounded_on_each_pipe(self):
        for scenario in ("flood_stdout", "flood_stderr"):
            with self.subTest(scenario=scenario):
                started = time.monotonic()
                self.assertEqual(self.detect(scenario)["reason"], "invalid")
                self.assertLess(time.monotonic() - started, 2)

    def test_cancel_before_launch_never_starts_process(self):
        event = threading.Event()
        event.set()
        self.assertEqual(self.detect(cancelled=event)["reason"], "cancelled")
        self.assertFalse(self.args.exists())

    def assert_processes_stopped(self):
        for pid in json.loads(self.pids.read_text()):
            # A reparented zombie has stopped running and awaits the system reaper.
            stat = Path(f"/proc/{pid}/stat")
            deadline = time.monotonic() + 0.5
            while True:
                try:
                    state = stat.read_text().split(")", 1)[1].split()[0]
                except FileNotFoundError:
                    break
                if state == "Z":
                    break
                if time.monotonic() >= deadline:
                    self.fail(f"Orientation subprocess {pid} still running: {state}")
                time.sleep(0.01)

    def test_cancellation_kills_a_child_that_ignores_sigterm(self):
        event = threading.Event()

        def cancel_when_ready():
            deadline = time.monotonic() + 2
            while not self.pids.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            event.set()

        worker = threading.Thread(target=cancel_when_ready)
        worker.start()
        try:
            self.assertEqual(self.detect("child", cancelled=event)["reason"], "cancelled")
        finally:
            worker.join(timeout=3)
        self.assertTrue(self.pids.exists())
        self.assert_processes_stopped()

    def test_timeout_kills_orphan_child_even_if_process_leader_has_exited(self):
        with patch.object(orientation, "DETECT_TIMEOUT", 0.3):
            self.assertEqual(self.detect("orphan")["reason"], "timeout")
        self.assertTrue(self.pids.exists())
        self.assert_processes_stopped()


if __name__ == "__main__":
    unittest.main()
