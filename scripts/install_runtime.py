#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""User installation launch/setup/uninstall support. No scanner probes."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys
import tempfile

MARKER = "paperdock-user-install-v1"


def safe_path(value, label="Pfad"):
    raw = os.fspath(value)
    if not raw or any(ord(ch) < 32 for ch in raw) or ":" in raw:
        raise ValueError(f"{label}: leere Pfade, Steuerzeichen und ':' sind nicht erlaubt.")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise ValueError(f"{label} darf kein symbolischer Link sein.")
    return path.resolve()


def scanner_ip(value):
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError("Scanner-IP muss eine einzelne IPv4-Adresse sein.") from exc
    networks = [ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if not any(address in net and address not in (net.network_address, net.broadcast_address) for net in networks):
        raise ValueError("Scanner-IP muss eine private Unicast-Adresse aus 10/8, 172.16/12 oder 192.168/16 sein.")
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


def manifest(prefix):
    path = prefix / "install.json"
    if path.is_symlink():
        raise ValueError("Installationsmanifest darf kein Link sein.")
    data = json.loads(path.read_text())
    if data.get("format") != MARKER or data.get("prefix") != str(prefix):
        raise ValueError("Kein gültiger PaperDock-Installationsordner.")
    return data


def set_wifi(prefix, value):
    atomic_write(prefix / "config/wifi.json", json.dumps({"scanner_ip": scanner_ip(value)}) + "\n")


def sane_environment(prefix, release, original, system_config=Path("/etc/sane.d")):
    """Merge active backend lists while preserving each backend's own config."""
    environment = original.copy()
    module = release / "wifi/build/lib/libsane-scansnap.so.1"
    settings = prefix / "config/wifi.json"
    if not module.is_file() or not settings.is_file():
        return environment
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
    # Empty dll.d makes SANE use the explicit merged list, without reading a
    # second fragment directory and silently choosing only the first of several.
    (private / "dll.d").mkdir(exist_ok=True, mode=0o700)
    environment["SANE_CONFIG_DIR"] = ":".join(map(str, [private, *directories]))
    prior = environment.get("LD_LIBRARY_PATH", "")
    environment["LD_LIBRARY_PATH"] = str(module.parent) + (":" + prior if prior else "")
    return environment


def wifi_command(prefix, release, arguments):
    parser = argparse.ArgumentParser(prog="paperdock-wifi", description="Lokale Scanner-IP speichern; kein Netzwerkzugriff.")
    parser.add_argument("address", nargs="?")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--disable", action="store_true")
    choice.add_argument("--show", action="store_true")
    args = parser.parse_args(arguments)
    if args.address and (args.disable or args.show):
        parser.error("Adresse und --disable/--show können nicht kombiniert werden.")
    if args.disable:
        atomic_write(prefix / "config/wifi.json", '{"scanner_ip": null}\n')
        print("WLAN deaktiviert. USB bleibt verfügbar.")
        return
    if args.show:
        settings = prefix / "config/wifi.json"
        value = json.loads(settings.read_text()).get("scanner_ip") if settings.exists() else None
        print(value or "Keine WLAN-Adresse eingerichtet.")
        return
    if not (release / "wifi/build/lib/libsane-scansnap.so.1").is_file():
        raise ValueError("WLAN-Modul fehlt; Installer ohne --without-wifi erneut ausführen.")
    address = args.address
    if not address:
        if not sys.stdin.isatty():
            parser.error("Scanner-IP als Argument angeben.")
        address = input("Private IPv4-Adresse des Scanners: ").strip()
    set_wifi(prefix, address)
    print("WLAN-Adresse gespeichert. PaperDock neu starten; erst die App kontaktiert den Scanner.")


def uninstall(prefix, arguments):
    parser = argparse.ArgumentParser(prog="paperdock-uninstall")
    parser.add_argument("--yes", action="store_true", help="Programmdateien entfernen; Dokumente und Einstellungen behalten")
    args = parser.parse_args(arguments)
    data = manifest(prefix)
    if not args.yes:
        if not sys.stdin.isatty() or input("PaperDock-Programmdateien entfernen? Dokumente bleiben erhalten. [j/N] ").lower() not in ("j", "ja"):
            print("Abgebrochen.")
            return
    token = data["installation_id"]
    for filename in data.get("launchers", []):
        path = Path(filename)
        if path.is_file() and not path.is_symlink() and f"# PaperDock installation: {token}" in path.read_text():
            path.unlink()
    desktop = Path(data["desktop_file"])
    if desktop.is_file() and not desktop.is_symlink() and f"X-PaperDock-Installation={token}" in desktop.read_text():
        desktop.unlink()
    current = prefix / "current"
    if current.is_symlink():
        current.unlink()
    for name in ("releases", "config"):
        directory = prefix / name
        if directory.is_symlink():
            raise ValueError("Unerwarteter Link im Installationsordner; manuell prüfen.")
        if directory.is_dir():
            shutil.rmtree(directory)
    (prefix / "install.json").unlink()
    try:
        prefix.rmdir()
    except OSError:
        pass
    print("PaperDock deinstalliert. Dokumente, Paperless-Einstellungen und Systempakete bleiben erhalten.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", required=True)
    parser.add_argument("command", choices=("launch", "wifi", "uninstall"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    remaining = args.arguments
    prefix = safe_path(args.prefix)
    manifest(prefix)
    release = (prefix / "current").resolve()
    if release.parent != prefix / "releases":
        raise ValueError("Ungültiges aktuelles Release.")
    if args.command == "wifi":
        wifi_command(prefix, release, remaining)
    elif args.command == "uninstall":
        uninstall(prefix, remaining)
    else:
        environment = sane_environment(prefix, release, os.environ)
        python = release / "venv/bin/python"
        os.execve(str(python), [str(python), "-m", "paperdock", "--desktop", *remaining], environment)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"PaperDock: {error}", file=sys.stderr)
        sys.exit(1)
