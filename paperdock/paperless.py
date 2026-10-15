"""Small, dependency-free Paperless-ngx client.

Uploads are never retried automatically: a lost response can still mean the
server accepted the document. TLS certificates are verified by urllib's default
HTTPS handler. Redirects and foreign pagination links never receive the token.
API reference: https://docs.paperless-ngx.com/api/
"""

from __future__ import annotations

import http.client
import json
import math
import mimetypes
import os
import re
import secrets
import socket
import stat
from pathlib import Path
from typing import BinaryIO, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class PaperlessError(Exception):
    """An actionable error safe to display without disclosing credentials."""

    def __init__(self, message: str, *, uncertain: bool = False):
        super().__init__(message)
        self.uncertain = uncertain


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PaperlessClient:
    MAX_RESPONSE_BYTES = 8 * 1024 * 1024
    MAX_PAGES = 100
    MAX_ITEMS = 20_000

    def __init__(self, url: str, token: str, timeout: float = 20):
        self.url = self.normalize_url(url)
        if not isinstance(token, str) or not re.fullmatch(r"[\x21-\x7e]{1,512}", token):
            raise PaperlessError("Bitte einen gültigen Paperless-API-Token ohne Leerzeichen eingeben.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise PaperlessError("Das Zeitlimit muss eine positive Zahl sein.")
        self._token = token
        self.timeout = timeout
        self._api = self.url + "/api/"
        self._origin = self._origin_of(self._api)
        self._opener = build_opener(_NoRedirect())

    @staticmethod
    def normalize_url(url: str) -> str:
        """Accept an app URL, including reverse-proxy deployment prefixes."""
        message = "Bitte eine vollständige http://- oder https://-Adresse ohne Zugangsdaten, Query oder Fragment eingeben."
        if not isinstance(url, str) or not url or re.search(r"[\s\x00-\x1f\x7f\\]", url):
            raise PaperlessError(message)
        try:
            parts = urlsplit(url)
            port = parts.port
            if (
                parts.scheme not in {"http", "https"}
                or not parts.hostname
                or parts.username is not None
                or parts.password is not None
                or "?" in url
                or "#" in url
                or (port is not None and port < 1)
            ):
                raise ValueError
            host = parts.hostname.encode("idna").decode("ascii").lower()
            if re.search(r"[^a-z0-9.\-:\[\]]", host):
                raise ValueError
            if ":" in host:
                host = "[" + host + "]"
            netloc = host + (f":{port}" if port is not None else "")
            decoded = unquote(parts.path)
            if re.search(r"[\x00-\x1f\x7f\\]", decoded) or any(segment in {".", ".."} for segment in decoded.split("/")):
                raise ValueError
            path = quote(parts.path.rstrip("/"), safe="/%:@!$&'()*+,;=-._~")
            return urlunsplit((parts.scheme, netloc, path, "", ""))
        except (ValueError, UnicodeError):
            raise PaperlessError(message) from None

    @staticmethod
    def _origin_of(url: str) -> tuple:
        parts = urlsplit(url)
        return (parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))

    def _request(self, url: str, *, data=None, content_type: str | None = None, content_length: int | None = None) -> tuple:
        headers = {"Authorization": "Token " + self._token, "Accept": "application/json", "User-Agent": "PaperDock/0.1"}
        if content_type:
            headers["Content-Type"] = content_type
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(raw) > self.MAX_RESPONSE_BYTES:
                    raise PaperlessError("Die Paperless-Antwort ist zu groß. Bitte die Serverkonfiguration prüfen.", uncertain=data is not None)
                versions = {
                    "server_version": self._clean_text(response.headers.get("X-Version", "")),
                    "api_version": self._clean_text(response.headers.get("X-Api-Version", "")),
                }
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if 300 <= code < 400:
                raise PaperlessError("Paperless leitet diese Adresse weiter. Bitte die endgültige Serveradresse in den Einstellungen verwenden.") from None
            if code in (401, 403):
                raise PaperlessError("Paperless hat den Zugriff verweigert. API-Token und Berechtigungen prüfen.") from None
            if code == 404:
                raise PaperlessError("Paperless-Endpunkt nicht gefunden. Serveradresse und gegebenenfalls den Unterpfad prüfen.") from None
            if code == 413:
                raise PaperlessError("Die Datei ist für diesen Paperless-Server zu groß (HTTP 413).") from None
            if code == 400:
                raise PaperlessError("Paperless hat die Anfrage abgelehnt (HTTP 400). Datei und ausgewählte Metadaten prüfen.") from None
            raise PaperlessError(f"Paperless meldet HTTP {code}. Bitte die Serverprotokolle prüfen.", uncertain=data is not None and code >= 500) from None
        except (URLError, OSError, http.client.HTTPException, socket.timeout):
            suffix = " Der Upload kann bereits angekommen sein; vor einem erneuten Versuch in Paperless prüfen." if data is not None else ""
            raise PaperlessError("Paperless ist nicht erreichbar oder die Verbindung wurde unterbrochen. Adresse, Netzwerk und TLS-Zertifikat prüfen." + suffix, uncertain=data is not None) from None
        try:
            return json.loads(raw), versions
        except (ValueError, UnicodeError):
            raise PaperlessError("Paperless hat kein gültiges JSON geliefert. Serveradresse und Reverse-Proxy-Konfiguration prüfen.", uncertain=data is not None) from None

    def _clean_text(self, value) -> str:
        if not isinstance(value, str):
            return ""
        value = value.replace(self._token, "[Token entfernt]")
        value = re.sub(r"(?i)\b(?:Authorization\s*:\s*)?(?:Token|Bearer)\s+\S+", "[Zugangsdaten entfernt]", value)
        return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", value)[:1000]

    def _next_url(self, current: str, link: str, endpoint: str) -> str:
        try:
            if not isinstance(link, str) or not link.isascii() or re.search(r"[\s\x00-\x1f\x7f\\]", link):
                raise ValueError
            target = urljoin(current, link)
            parts = urlsplit(target)
            if parts.username is not None or parts.password is not None or parts.fragment:
                raise ValueError
            if self._origin_of(target) != self._origin or parts.path != urlsplit(endpoint).path:
                raise ValueError
            return target
        except (ValueError, UnicodeError):
            raise PaperlessError("Paperless liefert einen unsicheren Seitenverweis. Reverse-Proxy-Adresse prüfen.") from None

    def _items(self, endpoint: str) -> list:
        url = endpoint
        seen = set()
        items = []
        for _ in range(self.MAX_PAGES):
            if url in seen:
                raise PaperlessError("Paperless liefert eine Schleife bei der Seitennavigation.")
            seen.add(url)
            payload, _ = self._request(url)
            if isinstance(payload, list):
                page, next_link = payload, None
            elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
                page, next_link = payload["results"], payload.get("next")
            else:
                raise PaperlessError("Unerwartetes Antwortformat von Paperless.")
            if not all(isinstance(item, dict) for item in page):
                raise PaperlessError("Unerwartetes Eintragsformat von Paperless.")
            items.extend(page)
            if len(items) > self.MAX_ITEMS:
                raise PaperlessError("Paperless liefert zu viele Einträge. Bitte die Auswahl auf dem Server begrenzen.")
            if not next_link:
                return items
            url = self._next_url(url, next_link, endpoint)
        raise PaperlessError("Paperless liefert zu viele Ergebnisseiten.")

    def test_connection(self) -> dict:
        payload, versions = self._request(self._api + "documents/?page_size=1")
        if not (isinstance(payload, list) or isinstance(payload, dict) and isinstance(payload.get("results"), list)):
            raise PaperlessError("Der Server liefert keine gültige Paperless-Dokumentliste.")
        count = payload.get("count") if isinstance(payload, dict) else len(payload)
        return {"ok": True, "url": self.url, "document_count": count, **versions}

    def metadata(self) -> dict:
        result = {}
        for resource in ("tags", "correspondents", "document_types"):
            entries = self._items(self._api + resource + "/?page_size=100")
            clean = []
            seen = set()
            for item in entries:
                identifier, name = item.get("id"), item.get("name")
                if type(identifier) is not int or identifier < 1 or not isinstance(name, str):
                    raise PaperlessError("Paperless liefert ungültige Metadaten.")
                if identifier not in seen:
                    clean.append({"id": identifier, "name": name})
                    seen.add(identifier)
            result[resource] = clean
        return result

    @staticmethod
    def _id(value, field: str) -> int:
        if type(value) is not int or value < 1:
            raise PaperlessError(f"{field} muss eine positive numerische Paperless-ID sein.")
        return value

    @staticmethod
    def _task_id(value) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", value):
            raise PaperlessError("Paperless hat keine gültige Aufgaben-ID geliefert. Vor erneutem Upload den Dokumenteingang prüfen.")
        return value

    @staticmethod
    def _stream(prefix: bytes, file: BinaryIO, suffix: bytes, size: int) -> Iterable[bytes]:
        yield prefix
        remaining = size
        while remaining:
            chunk = file.read(min(64 * 1024, remaining))
            if not chunk:
                raise OSError("Document changed during upload")
            remaining -= len(chunk)
            yield chunk
        yield suffix

    def upload(self, path: Path, title: str, tags: list[int] | None = None, correspondent: int | None = None, document_type: int | None = None) -> dict:
        if not isinstance(title, str) or len(title) > 4096 or "\x00" in title:
            raise PaperlessError("Bitte einen gültigen Dokumenttitel eingeben.")
        if tags is not None and not isinstance(tags, (list, tuple)):
            raise PaperlessError("Tags müssen als Liste numerischer Paperless-IDs übergeben werden.")
        fields = [("title", title)] if title else []
        fields.extend(("tags", str(self._id(tag, "Tag"))) for tag in (tags or []))
        for key, value in (("correspondent", correspondent), ("document_type", document_type)):
            if value is not None:
                fields.append((key, str(self._id(value, key))))
        path = Path(path)
        filename = re.sub(r"[^a-zA-Z0-9._ ()-]", "_", path.name)[:180].lstrip(".") or "document.pdf"
        boundary = "paperdock-" + secrets.token_hex(24)
        chunks = []
        for name, value in fields:
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\nContent-Type: {mime_type}\r\n\r\n'.encode("ascii"))
        prefix = b"".join(chunks)
        suffix = f"\r\n--{boundary}--\r\n".encode("ascii")
        try:
            with path.open("rb") as file:
                info = os.fstat(file.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size < 1:
                    raise PaperlessError("Bitte eine vorhandene, nicht leere Dokumentdatei auswählen.")
                payload, _ = self._request(
                    self._api + "documents/post_document/",
                    data=self._stream(prefix, file, suffix, info.st_size),
                    content_type="multipart/form-data; boundary=" + boundary,
                    content_length=len(prefix) + info.st_size + len(suffix),
                )
        except OSError:
            raise PaperlessError("Die Dokumentdatei kann nicht gelesen werden.") from None
        task = payload.get("task_id") if isinstance(payload, dict) else payload
        try:
            task = self._task_id(task)
        except PaperlessError as exc:
            exc.uncertain = True
            raise
        return {"status": "submitted", "task_id": task, "document_id": None, "error": None}

    def task_status(self, task_id: str) -> dict:
        task_id = self._task_id(task_id)
        rows = self._items(self._api + "tasks/?" + urlencode({"task_id": task_id}))
        result = {"status": "submitted", "task_id": task_id, "document_id": None, "error": None}
        # A just-accepted task may not be visible yet. Absence is not failure.
        task = next((row for row in rows if row.get("task_id") == task_id), None)
        if task is None:
            return result
        state = str(task.get("status", "")).upper()
        if state == "SUCCESS":
            document_id = task.get("related_document")
            if document_id is None:
                related = task.get("related_document_ids")
                if isinstance(related, list) and related:
                    document_id = related[0]
                elif isinstance(task.get("result_data"), dict):
                    document_id = task["result_data"].get("document_id")
            if isinstance(document_id, str) and document_id.isdecimal():
                document_id = int(document_id)
            if type(document_id) is int and document_id > 0:
                result["document_id"] = document_id
            result["status"] = "success"
        elif state in {"FAILURE", "FAILED", "REVOKED"}:
            result["status"] = "failure"
            error = task.get("result")
            if not isinstance(error, str) and isinstance(task.get("result_data"), dict):
                error = task["result_data"].get("error_message") or task["result_data"].get("reason")
            result["error"] = self._clean_text(error) or "Paperless konnte das Dokument nicht verarbeiten. Details stehen im Paperless-Aufgabenprotokoll."
        elif state not in {"PENDING", "STARTED", "RETRY", "RECEIVED", "QUEUED", "RUNNING"}:
            result["status"] = "unknown"
        return result
