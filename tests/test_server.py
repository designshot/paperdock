"""Application and HTTP integration tests; never contact a real scanner/server."""

import errno
import http.client
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image

from paperdock.paperless import PaperlessError
from paperdock.server import AppError, Application, Server


def small_demo(directory):
    paths = []
    for number in range(1, 4):
        path = Path(directory) / f"demo-{number:04d}.png"
        with Image.new("RGB", (64, 96), (number * 30, 120, 110)) as image:
            image.save(path, dpi=(150, 150))
        paths.append(path)
    return paths


class FakePaperless:
    url = "https://paperless.example.test"

    def __init__(self, error=None):
        self.error = error
        self.uploads = []
        self.result = {"status": "submitted", "task_id": "task-1", "document_id": None, "error": None}

    def upload(self, path, **kwargs):
        self.uploads.append((Path(path), kwargs))
        if self.error:
            raise self.error
        return dict(self.result)

    def task_status(self, task_id):
        if task_id != "task-1":
            raise AssertionError("wrong task polled")
        return dict(self.result)


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "data"
        self.app = Application(self.root)

    def tearDown(self):
        self.app.shutdown()
        self.temp.cleanup()

    def ready(self, job_id, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.app.lock:
                job = self.app.get_job(job_id)
                if job["status"] not in {"scanning", "orienting", "uploading", "exporting"}:
                    return self.app.public_job(job)
            time.sleep(0.01)
        self.fail("Background job did not finish in time")

    def demo(self, real=False):
        if real:
            job = self.app.new_job({"demo": True})
            return self.ready(job["id"])
        with patch("paperdock.server.scanner.create_demo", side_effect=small_demo):
            job = self.app.new_job({"demo": True})
            return self.ready(job["id"])

    def restart(self):
        self.app.shutdown()
        self.app = Application(self.root)

    def test_real_demo_edit_export_and_restart_preserve_document(self):
        job = self.demo(real=True)
        self.assertEqual(job["status"], "ready")
        self.assertTrue(job["demo"])
        self.assertEqual(len(job["pages"]), 3)
        self.assertEqual(job["settings"]["dpi"], 150)
        job_id = job["id"]
        page_id = job["pages"][0]["id"]
        rotated = self.app.edit_job(job_id, "rotate", {"page_id": page_id, "degrees": 90})
        self.assertEqual((rotated["pages"][0]["width"], rotated["pages"][0]["height"]), (1754, 1240))
        order = [p["id"] for p in reversed(rotated["pages"])]
        reordered = self.app.edit_job(job_id, "reorder", {"page_ids": order})
        self.assertEqual([p["id"] for p in reordered["pages"]], order)
        removed = reordered["pages"][1]
        edited = self.app.edit_job(job_id, "delete-page", {"page_id": removed["id"]})
        self.assertEqual(len(edited["pages"]), 2)
        self.assertTrue((self.root / "jobs" / job_id / (removed["id"] + ".png")).exists())
        exported = self.app.export(job_id, {})
        self.assertEqual(exported["url"], f"/download/{job_id}/document.pdf")
        pdf = (self.root / "jobs" / job_id / "document.pdf").read_bytes()
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 2)
        self.restart()
        restored = self.app.state()["jobs"][0]
        self.assertEqual(restored["id"], job_id)
        self.assertEqual([p["id"] for p in restored["pages"]], [order[0], order[2]])
        self.assertTrue(restored["pdf_ready"])
        self.assertFalse(any("file" in page for page in restored["pages"]))
        self.assertNotIn("device", restored)

    def test_invalid_new_job_parameters_are_rejected(self):
        for body in ({"demo": "yes"}, {"demo": True, "dpi": 0}, {"demo": True, "dpi": True},
                     {"demo": True, "page_limit": 101}, {"demo": True, "source": []},
                     {"demo": True, "title": ["bad"]}, {"device": "unknown:device"}):
            with self.subTest(body=body), self.assertRaises(AppError):
                self.app.new_job(body)
        self.assertEqual(self.app.state()["jobs"], [])

    def test_fixed_paper_size_requires_adf_capabilities(self):
        self.app.devices = [{'id': 'test:scanner'}]
        with self.assertRaises(AppError):
            self.app.new_job({'device': 'test:scanner', 'paper_size': 'A4', 'source': 'ADF Front'})
        with patch('paperdock.server.scanner.device_options', return_value={'paper_sizes': ['Driver', 'A4', 'Letter']}):
            self.app.options('test:scanner')
        with self.assertRaises(AppError):
            self.app.new_job({'device': 'test:scanner', 'paper_size': 'A4', 'source': 'Card Front'})
        for size in ([], 'A0', '--page-height=999'):
            with self.assertRaises(AppError):
                self.app.new_job({'demo': True, 'paper_size': size})
        def fake_scan(device, settings, directory, on_page, cancelled):
            self.assertEqual(settings['paper_size'], 'A4')
            on_page(small_demo(directory)[0])
        with patch('paperdock.server.scanner.scan_pages', side_effect=fake_scan):
            job = self.app.new_job({'device': 'test:scanner', 'paper_size': 'A4', 'source': 'ADF'})
            result = self.ready(job['id'])
        self.assertEqual(result['settings']['paper_size'], 'A4')
        self.assertEqual(result['status'], 'ready')

    def test_reorder_requires_each_page_once_and_last_page_is_retained(self):
        job = self.demo()
        ids = [p["id"] for p in job["pages"]]
        for order in (ids[:-1], [ids[0]] * 3, [*ids[:-1], "missing"]):
            with self.subTest(order=order), self.assertRaises(AppError):
                self.app.edit_job(job["id"], "reorder", {"page_ids": order})
        for page_id in ids[:2]:
            self.app.edit_job(job["id"], "delete-page", {"page_id": page_id})
        with self.assertRaises(AppError):
            self.app.edit_job(job["id"], "delete-page", {"page_id": ids[2]})

    def test_edit_invalidates_existing_pdf(self):
        job = self.demo()
        self.app.export(job["id"], {})
        self.assertTrue(self.app.get_job(job["id"])["pdf_ready"])
        self.app.edit_job(job["id"], "rotate", {"page_id": job["pages"][0]["id"]})
        self.assertFalse(self.app.get_job(job["id"])["pdf_ready"])

    def test_ocr_request_is_explicitly_rejected(self):
        job = self.demo()
        with self.assertRaisesRegex(AppError, "OCR"):
            self.app.export(job["id"], {"ocr": True})

    def test_secrets_are_private_and_not_in_public_state(self):
        secret = "paperdock-test-secret-9de455"
        result = self.app.settings({"url": "https://paperless.example.test/", "token": secret})
        self.assertTrue(result["configured"])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn(secret, json.dumps(self.app.state()))
        saved = self.root / "settings.json"
        self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        self.assertEqual(json.loads(saved.read_text())["token"], secret)
        self.restart()
        self.assertTrue(self.app.public_config()["configured"])
        self.assertNotIn(secret, json.dumps(self.app.state()))
        with self.assertRaises(AppError):
            self.app.settings({"url": "https://other.example.test"})

    def test_second_instance_using_same_directory_is_refused(self):
        with self.assertRaises(AppError):
            Application(self.root)

    def test_shutdown_waits_for_scanner_cancellation_and_releases_device(self):
        started = threading.Event()
        finished = threading.Event()

        def pending_scan(device, settings, directory, on_page, cancelled):
            started.set()
            self.assertTrue(cancelled.wait(3))
            finished.set()
            return []

        self.app.devices = [{"id": "fake:scanner"}]
        with patch("paperdock.server.scanner.scan_pages", side_effect=pending_scan):
            self.app.new_job({"device": "fake:scanner"})
            self.assertTrue(started.wait(2))
            self.app.shutdown()
        self.assertTrue(finished.is_set())
        self.assertFalse(self.app.scan_lock.locked())
        self.assertEqual(self.app.cancellations, {})
        self.assertEqual(self.app.workers, {})

    def test_scan_cleanup_releases_device_even_if_persistence_fails(self):
        job = self.demo()
        internal = self.app.get_job(job["id"])
        internal.update(demo=False, device="fake:scanner", status="scanning")
        self.app.cancellations[job["id"]] = threading.Event()
        self.app.scan_lock.acquire()
        with patch("paperdock.server.scanner.scan_pages", return_value=[]), patch.object(self.app, "save", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.app._scan(job["id"])
        self.assertFalse(self.app.scan_lock.locked())
        self.assertNotIn(job["id"], self.app.cancellations)

    def test_interrupted_jobs_recover_pages_and_uncertain_upload(self):
        job = self.demo()
        internal = self.app.get_job(job["id"])
        internal["status"] = "uploading"
        internal["paperless"] = {"status": "submitted", "task_id": None, "url": "https://paperless.example.test"}
        self.app.save(internal)
        self.restart()
        restored = self.app.get_job(job["id"])
        self.assertEqual(restored["status"], "ready")
        self.assertEqual(len(restored["pages"]), 3)
        self.assertEqual(restored["paperless"]["status"], "unknown")
        self.assertIn("unterbrochen", restored["error"])

    def test_upload_submission_confirmation_and_duplicate_guard(self):
        job = self.demo()
        client = FakePaperless()
        with patch.object(self.app, "client", return_value=client):
            self.app.upload(job["id"], {"title": "Mein Beleg", "tags": [2], "correspondent": 3})
            uploaded = self.ready(job["id"])
            self.assertEqual(uploaded["paperless"]["status"], "submitted")
            self.assertEqual(len(client.uploads), 1)
            self.assertEqual(client.uploads[0][1]["tags"], [2])
            self.assertTrue(client.uploads[0][0].exists())
            with self.assertRaises(AppError):
                self.app.upload(job["id"], {})
            with self.assertRaises(AppError):
                self.app.edit_job(job["id"], "rotate", {"page_id": job["pages"][0]["id"]})
            client.result.update(status="success", document_id=42)
            confirmed = self.app.paperless_status(job["id"])
            self.assertEqual(confirmed["paperless"]["status"], "success")
            self.assertEqual(confirmed["paperless"]["document_id"], 42)
            client.result.update(status="submitted", document_id=None)
            retained = self.app.paperless_status(job["id"])
            self.assertEqual(retained["paperless"]["status"], "success")
            with self.assertRaises(AppError):
                self.app.upload(job["id"], {})

    def test_uncertain_upload_failure_is_not_automatically_retried(self):
        job = self.demo()
        client = FakePaperless(PaperlessError("Antwort verloren", uncertain=True))
        with patch.object(self.app, "client", return_value=client):
            self.app.upload(job["id"], {})
            uploaded = self.ready(job["id"])
            self.assertEqual(uploaded["paperless"]["status"], "unknown")
            with self.assertRaises(AppError):
                self.app.upload(job["id"], {})
            self.assertEqual(len(client.uploads), 1)

    def test_stale_status_response_does_not_regress_success_or_replace_new_task(self):
        job = self.demo()
        client = FakePaperless()
        for replacement in (
            {"status": "success", "task_id": "task-1", "document_id": 42, "url": client.url},
            {"status": "submitted", "task_id": "task-2", "document_id": None, "url": client.url},
        ):
            with self.subTest(replacement=replacement):
                started = threading.Event()
                release = threading.Event()
                outcomes = []
                internal = self.app.get_job(job["id"])
                internal["paperless"] = {**client.result, "url": client.url}

                def slow_status(task_id):
                    started.set()
                    if not release.wait(3):
                        raise AssertionError("Status request was not released")
                    return {"status": "failure", "task_id": task_id, "error": "stale"}

                def poll():
                    try:
                        outcomes.append(self.app.paperless_status(job["id"]))
                    except Exception as exc:
                        outcomes.append(exc)

                with patch.object(self.app, "client", return_value=client), patch.object(client, "task_status", side_effect=slow_status):
                    worker = threading.Thread(target=poll)
                    worker.start()
                    try:
                        self.assertTrue(started.wait(2))
                        with self.app.lock:
                            internal["paperless"] = dict(replacement)
                    finally:
                        release.set()
                        worker.join(timeout=3)
                self.assertFalse(worker.is_alive())
                self.assertEqual(len(outcomes), 1)
                self.assertIsInstance(outcomes[0], dict)
                self.assertEqual(internal["paperless"], replacement)

    def test_rejected_upload_can_be_retried_after_correction(self):
        job = self.demo()
        client = FakePaperless(PaperlessError("Token abgelehnt"))
        with patch.object(self.app, "client", return_value=client):
            self.app.upload(job["id"], {})
            failed = self.ready(job["id"])
            self.assertEqual(failed["paperless"]["status"], "failure")
            client.error = None
            self.app.upload(job["id"], {})
            self.assertEqual(self.ready(job["id"])["paperless"]["status"], "submitted")
            self.assertEqual(len(client.uploads), 2)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(Path(self.temp.name) / "data")
        try:
            self.server = Server(("127.0.0.1", 0), self.app)
        except OSError as exc:
            self.app.shutdown()
            self.temp.cleanup()
            if exc.errno in (errno.EPERM, errno.EACCES):
                self.skipTest("Loopback bind is blocked by this sandbox")
            raise
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.app.shutdown()
        self.temp.cleanup()

    def request(self, path, method="GET", body=None, headers=None, authenticated=False):
        request_headers = dict(headers or {})
        if authenticated:
            request_headers["X-Paperdock-Token"] = self.app.token
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
            if not isinstance(body, (str, bytes)):
                body = json.dumps(body)
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_session_then_authenticated_state(self):
        code, _, body = self.request("/api/session")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["token"], self.app.token)
        self.assertEqual(self.request("/api/state")[0], 403)
        code, _, body = self.request("/api/state", authenticated=True)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["jobs"], [])

    def test_untrusted_host_origin_and_cross_site_requests_are_refused(self):
        for headers in ({"Host": "evil.example"}, {"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/session", headers=headers)[0], 403)
                self.assertEqual(self.request("/api/jobs", "POST", {"demo": True}, headers=headers, authenticated=True)[0], 403)
        self.assertEqual(self.app.state()["jobs"], [])

    def test_post_requires_session_and_json_object(self):
        self.assertEqual(self.request("/api/jobs", "POST", {"demo": True})[0], 403)
        self.assertEqual(self.request("/api/jobs", "POST", "broken", authenticated=True)[0], 400)
        self.assertEqual(self.request("/api/jobs", "POST", "[]", authenticated=True)[0], 400)
        self.assertEqual(self.request("/api/jobs", "POST", "{}", headers={"Content-Type": "text/plain"}, authenticated=True)[0], 415)
        self.assertEqual(self.app.state()["jobs"], [])

    def test_preferences_and_named_download_are_authenticated_and_utf8_safe(self):
        self.assertEqual(self.request('/api/preferences')[0], 403)
        self.assertEqual(self.request('/api/preferences', 'POST', {'auto_orient': False})[0], 403)
        status, _, payload = self.request('/api/preferences', 'POST', {'auto_orient': False, 'naming_template': 'Beleg_{counter}'}, authenticated=True)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)['name_preview'], 'Beleg_001')
        with patch('paperdock.server.scanner.create_demo', side_effect=small_demo):
            status, _, payload = self.request('/api/jobs', 'POST', {'demo': True}, authenticated=True)
            job = json.loads(payload)
            deadline = time.monotonic() + 5
            while self.app.workers and time.monotonic() < deadline:
                time.sleep(.01)
        self.assertEqual(status, 201)
        status, _, _ = self.request(f"/api/jobs/{job['id']}/rename", 'POST', {'title': 'Rechnung Büro'}, authenticated=True)
        self.assertEqual(status, 200)
        status, _, payload = self.request(f"/api/jobs/{job['id']}/export", 'POST', {}, authenticated=True)
        self.assertEqual(status, 200)
        status, headers, pdf = self.request(json.loads(payload)['url'])
        self.assertEqual(status, 200)
        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertIn("filename*=UTF-8''Rechnung%20B%C3%BCro.pdf", headers['Content-Disposition'])
        with patch('paperdock.server.orientation.available', return_value=False):
            status, _, payload = self.request(f"/api/jobs/{job['id']}/auto-orient", 'POST', {}, authenticated=True)
        self.assertEqual(status, 400)
        self.assertIn('Tesseract', json.loads(payload)['error'])

    def test_static_allowlist_and_response_security_headers(self):
        code, headers, _ = self.request("/")
        self.assertEqual(code, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/../server.py", "/%2e%2e/server.py", "/settings.json", "/.lock"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)


if __name__ == "__main__":
    unittest.main()
