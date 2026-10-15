#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""User installation launch/setup/uninstall support. No scanner probes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

# The source installer runs before a venv exists. The release launcher instead
# imports the installed package using its fixed venv interpreter.
source_root = Path(__file__).resolve().parents[1]
if (source_root / "paperdock/wifi.py").is_file():
    sys.path.insert(0, str(source_root))
from paperdock.wifi import MARKER, atomic_write, launch_environment, sane_environment, scanner_ip, set_wifi


def safe_path(value, label="Pfad"):
    raw = os.fspath(value)
    if not raw or any(ord(ch) < 32 for ch in raw) or ":" in raw:
        raise ValueError(f"{label}: leere Pfade, Steuerzeichen und ':' sind nicht erlaubt.")
    path = Path(raw).expanduser()
    if path.is_symlink():
        raise ValueError(f"{label} darf kein symbolischer Link sein.")
    return path.resolve()


def manifest(prefix):
    path = prefix / "install.json"
    if path.is_symlink():
        raise ValueError("Installationsmanifest darf kein Link sein.")
    data = json.loads(path.read_text())
    if data.get("format") != MARKER or data.get("prefix") != str(prefix):
        raise ValueError("Kein gültiger PaperDock-Installationsordner.")
    return data


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
        set_wifi(prefix, "")
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
        environment = launch_environment(prefix, release, os.environ)
        python = release / "venv/bin/python"
        os.execve(str(python), [str(python), "-m", "paperdock", "--desktop", *remaining], environment)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"PaperDock: {error}", file=sys.stderr)
        sys.exit(1)
