"""Exercise the real HTTP client against an isolated loopback fake server."""

import json
import tempfile
import threading
import unittest
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from paperdock.paperless import PaperlessClient, PaperlessError


TOKEN = "private-test-token-never-display"
TASK = "9a77b81d-0c8f-4f17-b73e-b4662a9340ff"


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def handle_request(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        request = {"method": self.command, "path": self.path, "headers": dict(self.headers), "body": body}
        self.server.requests.append(request)
        status, payload, headers = self.server.reply(request)
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)


class PaperlessHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHandler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/paperless"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.server.requests = []
        self.server.reply = lambda req: (200, {"results": [], "next": None}, {})
        self.client = PaperlessClient(self.base + "/", TOKEN)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.document = Path(self.tmp.name) / "Rechnung.pdf"
        self.content = b"%PDF-1.4\nreal\x00binary\xfffile\n%%EOF"
        self.document.write_bytes(self.content)

    def reply(self, payload, status=200, headers=None):
        self.server.reply = lambda req: (status, payload, headers or {})

    def test_connection_uses_prefix_and_authentication(self):
        self.reply({"count": 9, "results": []}, headers={"X-Version": "2.20.6", "X-Api-Version": "9"})
        status = self.client.test_connection()
        self.assertEqual(status, {"ok": True, "url": self.base, "document_count": 9, "server_version": "2.20.6", "api_version": "9"})
        request = self.server.requests[0]
        self.assertEqual(request["path"], "/paperless/api/documents/?page_size=1")
        self.assertEqual(request["headers"]["Authorization"], "Token " + TOKEN)
        self.assertNotIn(TOKEN, repr(status))

    def test_metadata_reads_relative_and_absolute_pagination(self):
        routes = {
            "/paperless/api/tags/?page_size=100": {"results": [{"id": 1, "name": "Steuer", "ignored": "private"}], "next": "?page=2"},
            "/paperless/api/tags/?page=2": {"results": [{"id": 2, "name": "Privat"}], "next": self.base + "/api/tags/?page=3"},
            "/paperless/api/tags/?page=3": {"results": [{"id": 2, "name": "Privat"}], "next": None},
            "/paperless/api/correspondents/?page_size=100": [{"id": 3, "name": "Stadt"}],
            "/paperless/api/document_types/?page_size=100": {"results": [{"id": 4, "name": "Rechnung"}], "next": None},
        }
        self.server.reply = lambda req: (200, routes[req["path"]], {})
        self.assertEqual(self.client.metadata(), {
            "tags": [{"id": 1, "name": "Steuer"}, {"id": 2, "name": "Privat"}],
            "correspondents": [{"id": 3, "name": "Stadt"}],
            "document_types": [{"id": 4, "name": "Rechnung"}],
        })
        self.assertEqual(len(self.server.requests), 5)

    def test_upload_has_document_file_and_repeated_tag_fields(self):
        self.reply(TASK)
        result = self.client.upload(self.document, "Rechnung für Büro", [3, 7], correspondent=11, document_type=13)
        self.assertEqual(result, {"status": "submitted", "task_id": TASK, "document_id": None, "error": None})
        request = self.server.requests[0]
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["path"], "/paperless/api/documents/post_document/")
        self.assertEqual(int(request["headers"]["Content-Length"]), len(request["body"]))
        self.assertNotIn("Transfer-Encoding", request["headers"])
        message = BytesParser(policy=policy.default).parsebytes(
            ("Content-Type: " + request["headers"]["Content-Type"] + "\r\nMIME-Version: 1.0\r\n\r\n").encode() + request["body"]
        )
        parts = list(message.iter_parts())
        fields = [(part.get_param("name", header="Content-Disposition"), part.get_payload(decode=True)) for part in parts]
        self.assertEqual(fields, [("title", "Rechnung für Büro".encode()), ("tags", b"3"), ("tags", b"7"), ("correspondent", b"11"), ("document_type", b"13"), ("document", self.content)])
        self.assertEqual(parts[-1].get_filename(), "Rechnung.pdf")
        self.assertEqual(parts[-1].get_content_type(), "application/pdf")

    def test_filename_cannot_inject_multipart_headers(self):
        document = Path(self.tmp.name) / 'evil"\r\nX-Fake: yes.pdf'
        document.write_bytes(self.content)
        self.reply({"task_id": TASK})
        self.client.upload(document, "")
        self.assertNotIn(b"\r\nX-Fake:", self.server.requests[0]["body"])
        self.assertIn(b'filename="evil___X-Fake_ yes.pdf"', self.server.requests[0]["body"])

    def test_tasks_remain_submitted_until_processing_finishes(self):
        for state in (None, "PENDING", "STARTED", "RETRY", "RECEIVED", "QUEUED", "RUNNING"):
            with self.subTest(state=state):
                self.reply([] if state is None else [{"task_id": TASK, "status": state}])
                result = self.client.task_status(TASK)
                self.assertEqual(result["status"], "submitted")
                self.assertIsNone(result["document_id"])
        self.assertEqual(self.server.requests[-1]["path"], "/paperless/api/tasks/?task_id=" + TASK)

    def test_success_supports_legacy_and_v10_document_fields(self):
        variants = [
            [{"task_id": TASK, "status": "SUCCESS", "related_document": "123"}],
            {"results": [{"task_id": TASK, "status": "success", "related_document_ids": [123]}], "next": None},
            {"results": [{"task_id": TASK, "status": "success", "result_data": {"document_id": 123}}]},
        ]
        for payload in variants:
            with self.subTest(payload=payload):
                self.reply(payload)
                result = self.client.task_status(TASK)
                self.assertEqual(result["status"], "success")
                self.assertEqual(result["document_id"], 123)

    def test_failure_reports_safe_error_and_unknown_state_is_distinct(self):
        for fields in ({"result": "Rejected Authorization: Token " + TOKEN}, {"result_data": {"error_message": "Duplicate document"}}):
            with self.subTest(fields=fields):
                self.reply([{"task_id": TASK, "status": "FAILURE", **fields}])
                result = self.client.task_status(TASK)
                self.assertEqual(result["status"], "failure")
                self.assertNotIn(TOKEN, result["error"])
        self.reply([{"task_id": TASK, "status": "SOMETHING_NEW"}])
        self.assertEqual(self.client.task_status(TASK)["status"], "unknown")
        self.reply([{"task_id": "different-task", "status": "FAILURE"}])
        self.assertEqual(self.client.task_status(TASK)["status"], "submitted")

    def test_redirects_never_follow_or_leak_tokens(self):
        for location in ("/redirect-target", "http://example.invalid/" + TOKEN):
            with self.subTest(location=location):
                self.server.requests.clear()
                self.reply({"detail": TOKEN}, status=302, headers={"Location": location})
                with self.assertRaises(PaperlessError) as caught:
                    self.client.test_connection()
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertIn("endgültige", str(caught.exception))
                self.assertEqual(len(self.server.requests), 1)

    def test_pagination_rejects_other_origins_credentials_and_paths(self):
        for link in ("https://example.invalid/?token=" + TOKEN, self.base + "/other/?page=2", self.base.replace("http://", "http://user:pass@") + "/api/tags/?page=2"):
            with self.subTest(link=link):
                self.server.requests.clear()
                self.reply({"results": [], "next": link})
                with self.assertRaises(PaperlessError) as caught:
                    self.client.metadata()
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertEqual(len(self.server.requests), 1)

    def test_pagination_is_bounded_and_rejects_loops(self):
        self.reply({"results": [], "next": "?page_size=100"})
        with self.assertRaisesRegex(PaperlessError, "Schleife"):
            self.client.metadata()
        self.client.MAX_PAGES = 2
        self.server.reply = lambda req: (200, {"results": [], "next": "?page=" + str(len(self.server.requests))}, {})
        with self.assertRaisesRegex(PaperlessError, "Ergebnisseiten"):
            self.client.metadata()

    def test_http_errors_are_safe_and_failed_uploads_mark_uncertainty(self):
        for code, uncertain in ((400, False), (401, False), (403, False), (404, False), (413, False), (500, True), (502, True)):
            with self.subTest(code=code):
                self.reply({"detail": TOKEN}, status=code)
                with self.assertRaises(PaperlessError) as caught:
                    self.client.upload(self.document, "Example")
                self.assertEqual(caught.exception.uncertain, uncertain)
                self.assertNotIn(TOKEN, str(caught.exception))

    def test_malformed_upload_success_is_uncertain(self):
        for payload in (b"not-json-" + TOKEN.encode(), {}, {"task_id": "invalid task"}):
            with self.subTest(payload=payload):
                self.reply(payload)
                with self.assertRaises(PaperlessError) as caught:
                    self.client.upload(self.document, "Example")
                self.assertTrue(caught.exception.uncertain)
                self.assertNotIn(TOKEN, str(caught.exception))

    def test_transport_error_does_not_leak_credentials_or_retry(self):
        with patch.object(self.client._opener, "open", side_effect=URLError(TOKEN)) as mocked:
            with self.assertRaises(PaperlessError) as caught:
                self.client.upload(self.document, "Example")
            self.assertTrue(caught.exception.uncertain)
            self.assertNotIn(TOKEN, str(caught.exception))
            self.assertEqual(mocked.call_count, 1)

    def test_oversized_response_is_rejected(self):
        self.client.MAX_RESPONSE_BYTES = 30
        self.reply({"results": [], "secret": TOKEN})
        with self.assertRaisesRegex(PaperlessError, "zu groß"):
            self.client.test_connection()

    def test_bad_metadata_and_local_inputs_fail_safely(self):
        self.reply({"results": [{"id": "bad", "name": TOKEN}]})
        with self.assertRaises(PaperlessError):
            self.client.metadata()
        self.server.requests.clear()
        for tags in ([False], [0], [-1], ["1"], "1"):
            with self.subTest(tags=tags), self.assertRaises(PaperlessError):
                self.client.upload(self.document, "Example", tags)
        with self.assertRaises(PaperlessError) as caught:
            self.client.upload(Path(self.tmp.name) / "missing.pdf", "Example")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(self.server.requests, [])


class PaperlessValidationTests(unittest.TestCase):
    def test_malformed_urls_are_rejected_without_echo(self):
        urls = ["", "file:///tmp/test", "ftp://server", "paperless.local", "http://", "https://user:" + TOKEN + "@server", "http://server/?x=" + TOKEN, "https://server/#fragment", "https://server/?", "https://server:bad", "https://server:0", "https://server:70000", "https://server/../", "https://server/%2E%2E/", "https://server/\nfoo", " https://server", "https://server\\@other"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(PaperlessError) as caught:
                PaperlessClient(url, TOKEN)
            self.assertNotIn(TOKEN, str(caught.exception))

    def test_tokens_cannot_inject_headers(self):
        for token in ("", "a\r\nHost: attacker", "a\nb", "a b", "token\t", "ü"):
            with self.subTest(token=token), self.assertRaises(PaperlessError):
                PaperlessClient("https://server", token)

    def test_normalization_preserves_deployment_prefix(self):
        self.assertEqual(PaperlessClient("https://SERVER:8000/paperless///", TOKEN).url, "https://server:8000/paperless")
        self.assertEqual(PaperlessClient("http://[::1]:8000/paperless", TOKEN).url, "http://[::1]:8000/paperless")


if __name__ == "__main__":
    unittest.main()
