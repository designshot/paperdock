# SPDX-License-Identifier: Apache-2.0
"""Local managed-install WLAN settings. No discovery, sockets or scanner access."""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import tempfile

MARKER = "paperdock-user-install-v1"
ENV_PREFIX = "PAPERDOCK_INSTALL_PREFIX"
ENV_RELEASE = "PAPERDOCK_INSTALL_RELEASE"
ENV_ORIGINAL = "PAPERDOCK_SANE_ORIGINAL"
SANE_KEYS = ("SANE_CONFIG_DIR", "LD_LIBRARY_PATH")


def scanner_ip(value):
    if not isinstance(value, str):
        raise ValueError("Scanner-IP muss eine einzelne IPv4-Adresse sein.")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError("Scanner-IP muss eine einzelne IPv4-Adresse sein.") from exc
    networks = [ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if not any(address in net and address not in (net.network_address, net.broadcast_address) for net in networks):
        raise ValueError("Bitte die lokale IPv4-Adresse deines Scanners aus der Geräteliste des Routers eintragen (z. B. 192.168.1.40).")
    return str(address)


def atomic_write(path, content, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError(f"Symbolischer Link als Schreibziel ist nicht erlaubt: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=".paperdock-", dir=path.parent)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _check_config_paths(prefix):
    for name in ("config", "config/wifi.json", "config/sane", "config/sane/dll.conf", "config/sane/scansnap.conf", "config/sane/dll.d"):
        if (prefix / name).is_symlink():
            raise ValueError("WLAN-Konfiguration darf keine symbolischen Links enthalten.")


def set_wifi(prefix, value):
    address = scanner_ip(value) if value != "" else None
    _check_config_paths(prefix)
    atomic_write(prefix / "config/wifi.json", json.dumps({"scanner_ip": address}) + "\n")


def sane_environment(prefix, release, original, system_config=Path("/etc/sane.d")):
    """Merge backend lists, preserving the caller's unmodified base environment."""
    environment = original.copy()
    module = release / "wifi/build/lib/libsane-scansnap.so.1"
    settings = prefix / "config/wifi.json"
    if not module.is_file() or not settings.is_file():
        return environment
    _check_config_paths(prefix)
    value = json.loads(settings.read_text()).get("scanner_ip")
    if not value:
        return environment
    address = scanner_ip(value)
    private = prefix / "config/sane"
    directories = []
    for entry in [*environment.get("SANE_CONFIG_DIR", "").split(":"), str(system_config)]:
        if not entry:
            continue
        directory = Path(entry).expanduser().resolve()
        if directory != private and directory not in directories:
            directories.append(directory)
    backends = []
    for directory in directories:
        configs = [directory / "dll.conf"]
        extra = directory / "dll.d"
        if extra.is_dir():
            configs.extend(p for p in sorted(extra.iterdir())
                           if p.is_file() and not p.name.startswith(".") and not p.name.endswith(("~", "#")))
        for config in configs:
            if not config.is_file():
                continue
            for line in config.read_text(errors="replace").splitlines():
                try:
                    words = shlex.split(line, comments=True)
                except ValueError:
                    continue
                if not words:
                    continue
                name = words[0]
                if re.fullmatch(r"[A-Za-z0-9_+-]+", name) and name not in ("dll", "scansnap") and name not in backends:
                    backends.append(name)
    backends.append("scansnap")
    atomic_write(private / "dll.conf", "# Generated; system and user backends retained.\n" + "\n".join(backends) + "\n")
    atomic_write(private / "scansnap.conf", f"net {address}\n")
    # SANE uses only the first dll.d. All original fragments were merged above.
    (private / "dll.d").mkdir(exist_ok=True, mode=0o700)
    environment["SANE_CONFIG_DIR"] = ":".join(map(str, [private, *directories]))
    prior = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = str(module.parent) + (":" + prior if prior else "")
    return environment


def launch_environment(prefix, release, original):
    """Pass installation identity and pre-launch paths to the installed app."""
    environment = original.copy()
    environment[ENV_PREFIX] = str(prefix)
    environment[ENV_RELEASE] = str(release)
    environment[ENV_ORIGINAL] = json.dumps({key: original.get(key) for key in SANE_KEYS})
    try:
        return sane_environment(prefix, release, environment)
    except (ValueError, OSError, AttributeError):
        # Keep settings repair available in the UI after a damaged local file.
        return environment


class WifiSettings:
    """Managed WLAN state; callers serialize save() with all scanner activity."""

    @classmethod
    def from_environment(cls, environment=None, system_config=Path("/etc/sane.d")):
        return cls(dict(os.environ if environment is None else environment), system_config)

    def __init__(self, environment, system_config):
        self.environment = environment.copy()
        self.original = environment.copy()
        self.system_config = system_config
        self.managed = False
        self.prefix = self.release = None
        self._available = False
        self._address = ""
        self._message = "WLAN-Einrichtung ist bei diesem Start nicht verfügbar. Bitte PaperDock über den installierten Starter öffnen."
        if not environment.get(ENV_PREFIX) or not environment.get(ENV_RELEASE):
            return
        try:
            prefix = Path(environment[ENV_PREFIX])
            release = Path(environment[ENV_RELEASE])
            if not prefix.is_absolute() or prefix.resolve() != prefix or release.resolve() != release or release.parent != prefix / "releases" or not release.is_dir():
                raise ValueError("Invalid installation paths")
            manifest = prefix / "install.json"
            if manifest.is_symlink():
                raise ValueError("Invalid installation manifest")
            data = json.loads(manifest.read_text())
            if data.get("format") != MARKER or data.get("prefix") != str(prefix):
                raise ValueError("Invalid installation manifest")
            base = json.loads(environment[ENV_ORIGINAL])
            if not isinstance(base, dict) or set(base) != set(SANE_KEYS) or any(value is not None and not isinstance(value, str) for value in base.values()):
                raise ValueError("Invalid original environment")
            for key, value in base.items():
                if value is None:
                    self.original.pop(key, None)
                else:
                    self.original[key] = value
            self.environment = self.original.copy()
            self.prefix, self.release, self.managed = prefix, release, True
            if not (release / "wifi/build/lib/libsane-scansnap.so.1").is_file():
                self._message = "Der WLAN-Treiber fehlt. Bitte PaperDock mit WLAN-Unterstützung erneut installieren. USB bleibt verfügbar."
                return
            self._available = True
            _check_config_paths(prefix)
            settings = prefix / "config/wifi.json"
            if settings.is_file():
                value = json.loads(settings.read_text()).get("scanner_ip")
                self._address = scanner_ip(value) if value else ""
            self.environment = sane_environment(prefix, release, self.original, system_config)
            self._message = self._status_message()
        except (ValueError, OSError, KeyError, TypeError, AttributeError):
            self._address = ""
            self._message = ("Die WLAN-Konfiguration konnte nicht gelesen werden. Bitte die Scanner-Adresse erneut speichern."
                             if self._available else "Die PaperDock-Installation konnte nicht zugeordnet werden. Bitte den installierten Starter verwenden.")

    def _status_message(self):
        if self._address:
            return "WLAN-Adresse gespeichert. Mit „Geräte aktualisieren“ die Verbindung prüfen."
        return "Noch keine WLAN-Adresse eingerichtet. Bitte die private IPv4-Adresse des Scanners eintragen. USB bleibt verfügbar."

    def state(self):
        return {"available": self._available, "configured": bool(self._address), "address": self._address, "message": self._message}

    def save(self, address):
        if not self._available or not (self.release / "wifi/build/lib/libsane-scansnap.so.1").is_file():
            raise ValueError(self._message if not self._available else "Der WLAN-Treiber ist nicht mehr verfügbar. Bitte PaperDock erneut installieren.")
        address = scanner_ip(address) if address != "" else ""
        _check_config_paths(self.prefix)
        paths = [self.prefix / name for name in ("config/wifi.json", "config/sane/dll.conf", "config/sane/scansnap.conf")]
        snapshots = {path: (path.read_text(), path.stat().st_mode & 0o777) if path.is_file() else None for path in paths}
        try:
            set_wifi(self.prefix, address)
            environment = sane_environment(self.prefix, self.release, self.original, self.system_config)
        except (ValueError, OSError, TypeError, AttributeError):
            for path, snapshot in snapshots.items():
                if snapshot is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, *snapshot)
            raise
        self._address = address
        self.environment = environment
        self._message = self._status_message()
        return self.state()
