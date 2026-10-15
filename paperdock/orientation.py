"""Read-only, local page orientation with Tesseract's OSD model.

This module never scans, uploads, rotates or writes an input document. A caller
may apply a clockwise correction only when ``reason == 'rotate'``. Confidence
is Tesseract's orientation margin, not a probability or OCR accuracy score.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import threading
import time


# Tesseract documents 15.0 as a reasonably confident orientation margin.
MIN_CONFIDENCE = 15.0
DETECT_TIMEOUT = 15.0
PROBE_TIMEOUT = 3.0
AVAILABILITY_TTL = 60.0
MAX_OUTPUT_BYTES = 32 * 1024
POLL_INTERVAL = 0.05

_probe_lock = threading.Lock()
_availability_cache: tuple[tuple[str, str], float, bool] | None = None


def _result(reason: str, rotation: int = 0, confidence: float | None = None) -> dict:
    return {"rotation": rotation, "confidence": confidence, "applied": False, "reason": reason}


def _stop_process(process: subprocess.Popen) -> None:
    """Stop the entire private session, including children after parent exit."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        pass
    # A child may ignore SIGTERM even if the leader has already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.8)
    except subprocess.TimeoutExpired:
        pass


def _run(arguments: list[str], timeout: float, cancelled: threading.Event | None) -> tuple[str | None, int | None, str, str]:
    """Drain both pipes with bounded memory, runtime and cancellation latency."""
    if cancelled is not None and cancelled.is_set():
        return "cancelled", None, "", ""
    try:
        process = subprocess.Popen(
            arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, start_new_session=True,
            env={**os.environ, "LC_ALL": "C", "OMP_THREAD_LIMIT": "1"},
        )
    except OSError:
        return "error", None, "", ""

    reason = None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    byte_count = 0
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if cancelled is not None and cancelled.is_set():
                    reason = "cancelled"
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    reason = "timeout"
                    break
                for key, _ in selector.select(min(POLL_INTERVAL, remaining)):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    byte_count += len(chunk)
                    if byte_count > MAX_OUTPUT_BYTES:
                        reason = "invalid"
                        break
                    buffers[key.data].extend(chunk)
                if reason is not None:
                    break
    except (OSError, ValueError):
        reason = "error"
    finally:
        if reason is not None or process.poll() is None:
            _stop_process(process)
        process.stdout.close()
        process.stderr.close()
    return (
        reason, process.returncode,
        buffers["stdout"].decode("utf-8", errors="replace"),
        buffers["stderr"].decode("utf-8", errors="replace"),
    )


def _executable(cancelled: threading.Event | None = None) -> tuple[str | None, str | None]:
    """Cache the language probe briefly, allowing newly installed OSD data."""
    global _availability_cache
    if cancelled is not None and cancelled.is_set():
        return None, "cancelled"
    executable = shutil.which("tesseract")
    if not executable:
        return None, "unavailable"
    key = (executable, os.environ.get("TESSDATA_PREFIX", ""))
    deadline = time.monotonic() + PROBE_TIMEOUT
    while not _probe_lock.acquire(timeout=POLL_INTERVAL):
        if cancelled is not None and cancelled.is_set():
            return None, "cancelled"
        if time.monotonic() >= deadline:
            return None, "timeout"
    try:
        if cancelled is not None and cancelled.is_set():
            return None, "cancelled"
        if _availability_cache is not None:
            cached_key, expires, supported = _availability_cache
            if cached_key == key and time.monotonic() < expires:
                return (executable, None) if supported else (None, "unavailable")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "timeout"
        reason, code, output, _ = _run([executable, "--list-langs"], remaining, cancelled)
        if reason == "cancelled":
            return None, reason
        supported = reason is None and code == 0 and "osd" in {line.strip() for line in output.splitlines()}
        _availability_cache = (key, time.monotonic() + AVAILABILITY_TTL, supported)
        return (executable, None) if supported else (None, reason or "unavailable")
    finally:
        _probe_lock.release()


def available() -> bool:
    """Whether Tesseract and its OSD language data are installed locally.

    The probe is cached for 60 seconds per executable/data-directory pair.
    This query does not open a document or contact any scanner.
    """
    executable, _ = _executable()
    return executable is not None


def _parse_output(output: str) -> dict:
    fields = {}
    required = {"Orientation in degrees", "Rotate", "Orientation confidence"}
    for line in output.splitlines():
        name, separator, value = line.partition(":")
        if name in required and separator:
            if name in fields:
                return _result("invalid")
            fields[name] = value.strip()
    if fields.keys() != required:
        return _result("invalid")
    if any(not re.fullmatch(r"(?:0|90|180|270)", fields[name]) for name in ("Orientation in degrees", "Rotate")):
        return _result("invalid")
    if not re.fullmatch(r"\d+(?:\.\d+)?", fields["Orientation confidence"]):
        return _result("invalid")
    confidence = float(fields["Orientation confidence"])
    rotation = int(fields["Rotate"])
    orientation = int(fields["Orientation in degrees"])
    if not math.isfinite(confidence) or not 0 <= confidence <= 100 or (orientation + rotation) % 360:
        return _result("invalid")
    if confidence < MIN_CONFIDENCE:
        return _result("uncertain", confidence=confidence)
    return _result("rotate" if rotation else "upright", rotation, confidence)


def detect_page(path: Path, cancelled: threading.Event | None = None) -> dict:
    """Inspect one image without modifying it or creating an OCR text layer.

    ``rotation`` is the necessary correction clockwise, and is nonzero only
    for a sufficiently confident ``rotate`` result. ``applied`` is always
    false: the caller owns backups and image changes. Reasons are ``upright``,
    ``rotate``, ``uncertain``, ``unavailable``, ``timeout``, ``invalid``,
    ``cancelled`` or ``error``. All failures leave the document unchanged.
    """
    if cancelled is not None and cancelled.is_set():
        return _result("cancelled")
    try:
        path = Path(path).resolve(strict=True)
        if not path.is_file():
            return _result("invalid")
    except (OSError, ValueError, TypeError, RuntimeError):
        return _result("invalid")
    executable, reason = _executable(cancelled)
    if executable is None:
        return _result(reason or "unavailable")
    reason, code, output, error = _run(
        [executable, str(path), "stdout", "-l", "osd", "--psm", "0"],
        DETECT_TIMEOUT, cancelled,
    )
    if cancelled is not None and cancelled.is_set():
        return _result("cancelled")
    if reason is not None:
        return _result(reason)
    if code:
        if "Too few characters" in error or "Empty page" in error:
            return _result("uncertain")
        return _result("error")
    return _parse_output(output)
