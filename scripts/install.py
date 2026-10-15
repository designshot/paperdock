#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Ubuntu/Pop!_OS 24.04 and Debian 12/13 user installation."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import uuid

from install_runtime import MARKER, atomic_write, manifest, safe_path, scanner_ip, set_wifi

SOURCE = Path(__file__).resolve().parents[1]
WIFI_URL = "https://github.com/mxovd/sane-backends-scansnap.git"
WIFI_PIN = "130b69136f1eedff19acb377cb5019e38d865065"
BASE_PACKAGES = ["python3", "python3-venv", "sane-utils", "tesseract-ocr", "tesseract-ocr-osd", "ca-certificates"]
WIFI_PACKAGES = ["build-essential", "git", "libjpeg-dev"]


def distribution(release=None):
    info = platform.freedesktop_os_release() if release is None else release
    identifier, version = info.get("ID", ""), info.get("VERSION_ID", "")
    if identifier in ("ubuntu", "pop") and version == "24.04":
        return identifier, version
    if identifier == "debian" and version.split(".")[0] in ("12", "13"):
        return identifier, version
    raise ValueError("Installer unterstützt Ubuntu/Pop!_OS 24.04 und Debian 12/13. Andere Systeme: manuelle Installation.")


def desktop_exec(path):
    escaped = str(path).replace("%", "%%")
    for character in ("\\", '"', "`", "$"):
        escaped = escaped.replace(character, "\\" + character)
    # Exec quoting and Desktop Entry string escaping are two separate layers.
    return ('"' + escaped + '"').replace("\\", "\\\\")


def launcher(prefix, command, token):
    python = prefix / "current/venv/bin/python"
    runtime = prefix / "current/support/install_runtime.py"
    return (f"#!/bin/sh\n# PaperDock installation: {token}\n"
            f"exec {shlex.quote(str(python))} {shlex.quote(str(runtime))} "
            f"--prefix {shlex.quote(str(prefix))} {command} \"$@\"\n")


def check_output_target(path, token, desktop=False):
    if path.is_symlink():
        raise ValueError(f"Vorhandener Link wird nicht überschrieben: {path}")
    marker = f"X-PaperDock-Installation={token}" if desktop else f"# PaperDock installation: {token}"
    if path.exists() and (not path.is_file() or marker not in path.read_text()):
        raise ValueError(f"Fremde Datei wird nicht überschrieben: {path}; anderen --bin-dir/--desktop-dir wählen.")


def run(command, **kwargs):
    print("+ " + shlex.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def copy_application_source(source, target):
    """Copy only distributable project files, never arbitrary checkout contents."""
    target.mkdir()
    top_files = ("pyproject.toml", "README.md", "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md",
                 "CONTRIBUTING.md", "CHANGELOG.md", "MANIFEST.in", "install.sh", "bootstrap.sh", "start.sh")
    selected = [source / name for name in top_files if (source / name).is_file()]
    for relative, suffixes in (("paperdock", {".py", ".js", ".css", ".svg", ".html"}),
                               ("docs", {".md"}), ("scripts", {".py"}),
                               ("tests", {".py"})):
        directory = source / relative
        if directory.is_dir():
            selected.extend(path for path in directory.rglob("*")
                            if path.is_file() and not path.is_symlink() and path.suffix in suffixes
                            and not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(directory).parts))
    driver = source / "drivers/scansnap-wifi"
    for name in ("README.md", "COPYING", "LICENSE", "SANE-exception.txt", "build.py",
                 "source-hashes.json", "session_cleanup_test.c", "paperdock-sane-safety.patch"):
        if (driver / name).is_file():
            selected.append(driver / name)
    for path in selected:
        if path.is_symlink():
            raise ValueError(f"Unerwarteter Quell-Link: {path.relative_to(source)}")
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def install(args):
    identifier, version = distribution()
    prefix = safe_path(args.prefix, "Installationsordner")
    bin_dir = safe_path(args.bin_dir, "Launcherordner")
    desktop_dir = safe_path(args.desktop_dir, "Desktopordner")
    if "=" in str(bin_dir):
        raise ValueError("Launcherpfade dürfen laut Desktop-Entry-Spezifikation kein '=' enthalten.")
    if prefix in (Path("/"), Path.home().resolve(), SOURCE) or prefix in SOURCE.parents or SOURCE in prefix.parents:
        raise ValueError("Installationsordner muss vom Quellordner und vom Benutzerstamm getrennt sein.")
    if prefix == bin_dir or prefix == desktop_dir or prefix in bin_dir.parents or prefix in desktop_dir.parents:
        raise ValueError("Launcher-/Desktopordner müssen außerhalb des Installationsordners liegen.")
    if args.scanner_ip and args.without_wifi:
        raise ValueError("--scanner-ip kann nicht mit --without-wifi verwendet werden.")
    address = scanner_ip(args.scanner_ip) if args.scanner_ip else None
    if args.offline and not args.skip_system_packages:
        raise ValueError("--offline benötigt --skip-system-packages.")
    if args.offline and (not args.wheelhouse or (not args.without_wifi and not args.wifi_source)):
        raise ValueError("--offline benötigt --wheelhouse sowie für WLAN --wifi-source.")
    for value, label in ((args.wheelhouse, "Wheelordner"), (args.wifi_source, "WLAN-Quellordner")):
        if value and not safe_path(value, label).is_dir():
            raise ValueError(f"{label} existiert nicht.")
    previous = None
    if (prefix / "install.json").exists():
        previous = manifest(prefix)
    elif prefix.exists() and any(prefix.iterdir()):
        raise ValueError("Nichtleerer fremder Installationsordner wird nicht verwendet.")
    for name in ("releases", "config"):
        if (prefix / name).is_symlink():
            raise ValueError("Unerwarteter Link im Installationsordner.")
    if (prefix / "current").exists() and not (prefix / "current").is_symlink():
        raise ValueError("current muss ein verwalteter Release-Link sein.")
    if (prefix / "current").is_symlink() and (prefix / "current").resolve().parent != prefix / "releases":
        raise ValueError("current verweist nicht auf einen verwalteten Releaseordner.")
    if (prefix / "config/wifi.json").is_symlink():
        raise ValueError("WLAN-Konfiguration darf kein symbolischer Link sein.")
    token = previous["installation_id"] if previous else uuid.uuid4().hex
    launcher_paths = [bin_dir / name for name in ("paperdock", "paperdock-wifi", "paperdock-uninstall")]
    desktop_file = desktop_dir / "paperdock.desktop"
    if previous and (previous["launchers"] != list(map(str, launcher_paths)) or previous["desktop_file"] != str(desktop_file)):
        raise ValueError("Bei Updates dieselben --bin-dir/--desktop-dir wie bei der Erstinstallation verwenden.")
    for path in launcher_paths:
        check_output_target(path, token)
    check_output_target(desktop_file, token, desktop=True)
    packages = BASE_PACKAGES + ([] if args.without_wifi else WIFI_PACKAGES)
    if args.desktop:
        packages += ["python3-gi", "gir1.2-gtk-4.0", "gir1.2-webkit-6.0"]
    print(f"PaperDock: {identifier} {version}; Benutzerinstallation in {prefix}")
    print("Systempakete: " + ", ".join(packages))
    if args.dry_run:
        print("Vorschau: keine Installation, Downloads, Konfigurationsänderungen oder Scannerzugriffe.")
        return
    if os.geteuid() == 0:
        raise ValueError("Installer als normaler Benutzer starten, nicht mit sudo. Nur apt erhält bei Bedarf sudo.")
    if not args.skip_system_packages:
        if not shutil.which("sudo"):
            raise ValueError("sudo fehlt. Pakete administrativ installieren und --skip-system-packages verwenden.")
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y", *packages])
    python = shutil.which(args.python) if not Path(args.python).is_absolute() else args.python
    if not python or not Path(python).is_file():
        raise ValueError("Gewählter Python-Interpreter fehlt.")
    run([python, "-c", "import sys; assert sys.version_info >= (3,10), 'Python >= 3.10 required'; import venv, ensurepip"])
    prefix.mkdir(parents=True, exist_ok=True, mode=0o700)
    release_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    release = prefix / "releases" / release_id
    release.mkdir(parents=True, mode=0o700)
    outputs = [prefix / "install.json", *launcher_paths, desktop_file]
    if address:
        outputs.append(prefix / "config/wifi.json")
    snapshots = {path: (path.read_text(), path.stat().st_mode & 0o777) if path.is_file() else None for path in outputs}
    link = None
    try:
        app_source = release / "app-source"
        copy_application_source(SOURCE, app_source)
        run([python, "-m", "venv", release / "venv"])
        venv_python = release / "venv/bin/python"
        pip_options = ["--disable-pip-version-check"]
        if args.wheelhouse:
            pip_options += ["--find-links", str(safe_path(args.wheelhouse, "Wheelordner"))]
        if args.offline:
            pip_options += ["--no-index"]
        run([venv_python, "-m", "pip", "install", *pip_options, "setuptools>=68", "wheel", "Pillow>=10.0"])
        run([venv_python, "-m", "pip", "install", *pip_options, "--no-build-isolation", app_source])
        if not args.without_wifi:
            wifi = release / "wifi"
            wifi.mkdir()
            material = app_source / "drivers/scansnap-wifi"
            source = wifi / "source"
            if args.wifi_source:
                local_source = safe_path(args.wifi_source, "WLAN-Quellordner")
                run(["git", "clone", "--local", "--no-hardlinks", "--no-checkout", "--", local_source, source])
                run(["git", "-C", source, "checkout", "--detach", WIFI_PIN])
            else:
                run(["git", "clone", "--", WIFI_URL, source])
                run(["git", "-C", source, "checkout", "--detach", WIFI_PIN])
            commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            if commit != WIFI_PIN:
                raise ValueError("WLAN-Quellen müssen exakt dem festgelegten Commit entsprechen.")
            patch = material / "paperdock-sane-safety.patch"
            check = subprocess.run(["git", "-C", str(source), "apply", "--check", str(patch)], capture_output=True)
            if check.returncode == 0:
                run(["git", "-C", source, "apply", patch])
            else:
                run(["git", "-C", source, "apply", "--reverse", "--check", patch])
            run([python, material / "build.py", "--source", source, "--build", wifi / "build", "--test"])
            run([python, "-m", "unittest", "discover", "-s", source / "testsuite/backend/scansnap", "-p", "test_scansnap_*.py", "-q"])
            shutil.copytree(material, wifi / "license-and-patch")
        (release / "support").mkdir()
        shutil.copy2(SOURCE / "scripts/install_runtime.py", release / "support/install_runtime.py")
        run([venv_python, "-m", "paperdock", "--help"], cwd=release)
        if address:
            set_wifi(prefix, address)
        desktop = ("[Desktop Entry]\nType=Application\nName=PaperDock\nComment=Dokumente lokal scannen und an Paperless senden\n"
                   f"Exec={desktop_exec(launcher_paths[0])}\nIcon=scanner\nTerminal=false\nCategories=Office;Scanning;\n"
                   f"X-PaperDock-Installation={token}\n")
        # Prepare activation; current stays unchanged until all output writes succeed.
        link = prefix / (".current-" + uuid.uuid4().hex)
        link.symlink_to(Path("releases") / release_id)
        data = {"format": MARKER, "installation_id": token, "prefix": str(prefix),
                "launchers": list(map(str, launcher_paths)), "desktop_file": str(desktop_file),
                "release": release_id, "wifi": not args.without_wifi}
        atomic_write(prefix / "install.json", json.dumps(data, indent=2) + "\n")
        for path, command in zip(launcher_paths, ("launch", "wifi", "uninstall")):
            atomic_write(path, launcher(prefix, command, token), 0o755)
        atomic_write(desktop_file, desktop, 0o644)
        os.replace(link, prefix / "current")
    except BaseException:
        # Never remove an activated release or touch an older working release.
        if not (prefix / "current").is_symlink() or (prefix / "current").resolve() != release:
            shutil.rmtree(release)
            if link is not None and link.is_symlink():
                link.unlink()
            for path, snapshot in snapshots.items():
                try:
                    if snapshot is None:
                        path.unlink(missing_ok=True)
                    else:
                        atomic_write(path, *snapshot)
                except OSError as rollback_error:
                    print(f"Installationsdatei konnte nicht zurückgesetzt werden: {path}: {rollback_error}", file=sys.stderr)
            for directory in (prefix / "config", prefix / "releases", prefix):
                try:
                    directory.rmdir()
                except OSError:
                    pass
        raise
    print(f"Fertig. Starten: {launcher_paths[0]}")
    if not args.without_wifi and not address:
        print(f"WLAN einrichten: {launcher_paths[1]} <private Scanner-IP>")
    print("Dokumente liegen weiterhin im normalen PaperDock-Datenordner. Es wurde kein Scanner kontaktiert.")


def main():
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default=str(data_home / "paperdock-runtime"))
    parser.add_argument("--bin-dir", default=str(Path.home() / ".local/bin"))
    parser.add_argument("--desktop-dir", default=str(data_home / "applications"))
    parser.add_argument("--python", default="python3")
    parser.add_argument("--scanner-ip")
    parser.add_argument("--without-wifi", action="store_true")
    parser.add_argument("--desktop", action="store_true", help="Optionale GTK4-/WebKit6-Pakete mitinstallieren")
    parser.add_argument("--skip-system-packages", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--wifi-source", help="Vorhandener Checkout des festgelegten Commits, optional bereits gepatcht")
    parser.add_argument("--wheelhouse", help="Lokaler Ordner mit Python-Wheels")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        install(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Installation fehlgeschlagen: {error}\n")


if __name__ == "__main__":
    main()
