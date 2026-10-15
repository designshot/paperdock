"""Installer checks without apt, package downloads or scanner access."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import install as installer
import install_runtime as runtime


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="paperdock-install-test-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_supported_platforms_and_rejection(self):
        for identifier, version in (("ubuntu", "24.04"), ("pop", "24.04"), ("debian", "12"), ("debian", "13.1")):
            self.assertEqual(installer.distribution({"ID": identifier, "VERSION_ID": version}), (identifier, version))
        for identifier, version in (("ubuntu", "22.04"), ("debian", "11"), ("fedora", "42"), ("debian", "testing")):
            with self.assertRaises(ValueError):
                installer.distribution({"ID": identifier, "VERSION_ID": version})

    def test_private_ipv4_only(self):
        for address in ("10.0.0.1", "172.16.1.12", "192.168.1.100"):
            self.assertEqual(runtime.scanner_ip(address), address)
        for address in ("127.0.0.1", "0.0.0.0", "8.8.8.8", "224.0.0.1", "169.254.1.1", "192.168.255.255", "10.0.0.0", "localhost", "::1", "192.168.1.2\n", "http://192.168.1.2", "192.168.1.2;touch /tmp/x"):
            with self.assertRaises(ValueError, msg=address):
                runtime.scanner_ip(address)

    def test_paths_reject_control_colon_and_symlink(self):
        for value in ("", "/tmp/a:b", "/tmp/a\nb", "/tmp/a\x00b"):
            with self.assertRaises(ValueError):
                runtime.safe_path(value)
        target = self.root / "target"
        target.mkdir()
        link = self.root / "linked"
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            runtime.safe_path(link)

    def test_atomic_write_mode_and_symlink_refusal(self):
        target = self.root / "config/wifi.json"
        runtime.atomic_write(target, "first\n")
        runtime.atomic_write(target, "second\n")
        self.assertEqual(target.read_text(), "second\n")
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        link = self.root / "link"
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            runtime.atomic_write(link, "changed")
        self.assertEqual(target.read_text(), "second\n")

    def test_wifi_keeps_system_usb_and_fragment_backends(self):
        prefix, release, system, custom = [self.root / part for part in ("prefix", "release", "system", "custom")]
        library = release / "wifi/build/lib/libsane-scansnap.so.1"
        library.parent.mkdir(parents=True)
        library.touch()
        system.mkdir()
        (system / "dll.conf").write_text('"fujitsu"\nhp # enabled\n# test\nscansnap\n')
        (system / "dll.d").mkdir()
        (system / "dll.d/airscan").write_text("airscan\nfujitsu\n")
        custom.mkdir()
        (custom / "dll.conf").write_text("pixma\n")
        runtime.set_wifi(prefix, "192.168.1.40")
        environment = runtime.sane_environment(prefix, release, {"SANE_CONFIG_DIR": str(custom), "LD_LIBRARY_PATH": "/opt/example"}, system)
        backends = (prefix / "config/sane/dll.conf").read_text().splitlines()
        self.assertEqual(backends[1:], ["pixma", "fujitsu", "hp", "airscan", "scansnap"])
        self.assertEqual((prefix / "config/sane/scansnap.conf").read_text(), "net 192.168.1.40\n")
        self.assertEqual(environment["SANE_CONFIG_DIR"].split(":"), [str(prefix / "config/sane"), str(custom), str(system)])
        self.assertEqual(environment["LD_LIBRARY_PATH"], str(library.parent) + ":/opt/example")

    def test_without_config_or_module_environment_is_unchanged(self):
        original = {"SANE_CONFIG_DIR": "/existing", "OTHER": "value"}
        self.assertEqual(runtime.sane_environment(self.root, self.root / "release", original), original)
        self.assertFalse((self.root / "config").exists())

    def test_shell_launcher_preserves_spaces_quotes_and_dollar(self):
        prefix = self.root / "space ' dollar $ prefix"
        python = prefix / "current/venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n")
        python.chmod(0o755)
        command = self.root / "paperdock"
        command.write_text(installer.launcher(prefix, "launch", "test-token"))
        argument = "a'; $(touch SENTINEL); $HOME"
        result = subprocess.run(["sh", str(command), argument], cwd=self.root, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines()[-1], argument)
        self.assertFalse((self.root / "SENTINEL").exists())

    def test_desktop_exec_quotes_metacharacters(self):
        value = installer.desktop_exec(Path('/tmp/a " $ ` % path'))
        self.assertEqual(value, '"/tmp/a \\\\" \\\\$ \\\\` %% path"')

    def test_foreign_launcher_is_never_overwritten(self):
        target = self.root / "paperdock"
        target.write_text("another app\n")
        with self.assertRaises(ValueError):
            installer.check_output_target(target, "ours")
        target.write_text(installer.launcher(self.root, "launch", "ours"))
        installer.check_output_target(target, "ours")

    def test_uninstall_keeps_documents_and_unowned_launcher(self):
        prefix = self.root / "runtime"
        release = prefix / "releases/one"
        release.mkdir(parents=True)
        (prefix / "current").symlink_to("releases/one")
        (release / "file").write_text("code")
        data = self.root / "paperdock-data"
        data.mkdir()
        (data / "settings.json").write_text('{"saved": true}')
        owned, changed, desktop = [self.root / name for name in ("paperdock", "paperdock-wifi", "paperdock.desktop")]
        owned.write_text(installer.launcher(prefix, "launch", "our-token"))
        changed.write_text("user replaced this\n")
        desktop.write_text("X-PaperDock-Installation=our-token\n")
        runtime.atomic_write(prefix / "install.json", json.dumps({"format": runtime.MARKER, "prefix": str(prefix), "installation_id": "our-token", "launchers": [str(owned), str(changed)], "desktop_file": str(desktop)}))
        runtime.uninstall(prefix, ["--yes"])
        self.assertFalse(prefix.exists())
        self.assertFalse(owned.exists())
        self.assertFalse(desktop.exists())
        self.assertEqual(changed.read_text(), "user replaced this\n")
        self.assertEqual((data / "settings.json").read_text(), '{"saved": true}')

    def test_dry_run_leaves_no_files(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "install.py"), "--dry-run", "--prefix", str(self.root / "runtime"), "--bin-dir", str(self.root / "bin"), "--desktop-dir", str(self.root / "apps")], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("keine Installation", result.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_source_installer_imports_shared_wifi_from_another_directory(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "install.py"), "--help"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scanner-ip", result.stdout)

    def test_installed_support_imports_shared_wifi_from_venv(self):
        # Emulate the installed pure-Python package, without pip or downloads.
        release = self.root / "release"
        venv = release / "venv"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                       check=True, capture_output=True)
        python = venv / "bin/python"
        library = Path(subprocess.check_output(
            [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip())
        package = library / "paperdock"
        package.mkdir()
        for name in ("__init__.py", "wifi.py"):
            shutil.copy2(SCRIPTS.parent / "paperdock" / name, package / name)
        support = release / "support/install_runtime.py"
        support.parent.mkdir()
        shutil.copy2(SCRIPTS / "install_runtime.py", support)
        result = subprocess.run([str(python), "-I", str(support), "--help"],
                                cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("launch", result.stdout)

    def test_offline_missing_inputs_fails_without_mutation(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "install.py"), "--offline", "--skip-system-packages", "--prefix", str(self.root / "runtime"), "--bin-dir", str(self.root / "bin"), "--desktop-dir", str(self.root / "apps")], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--wheelhouse", result.stderr)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_source_copy_excludes_local_data_and_nested_runtime(self):
        source, target = self.root / "source", self.root / "copy"
        allowed = ("pyproject.toml", "CHANGELOG.md", "paperdock/__init__.py", "paperdock/static/app.js", "docs/INSTALL.md", "scripts/install.py")
        forbidden = ("settings.json", "preferences.json", ".venv/bin/python", ".local-data/page.png", "dev-data/jobs/document.pdf", "jobs/document.pdf", "debug.log", "runtime/app-source/copy.py", "paperdock/settings.json", "paperdock/__pycache__/module.pyc")
        for relative in (*allowed, *forbidden):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
        installer.copy_application_source(source, target)
        for relative in allowed:
            self.assertTrue((target / relative).is_file(), relative)
        for relative in forbidden:
            self.assertFalse((target / relative).exists(), relative)

    def test_failed_activation_restores_manifest_wrappers_and_wifi(self):
        prefix = self.root / "runtime"
        previous_release = prefix / "releases/old"
        previous_release.mkdir(parents=True)
        (prefix / "current").symlink_to("releases/old")
        bin_dir, desktop_dir = self.root / "bin", self.root / "applications"
        paths = [bin_dir / name for name in ("paperdock", "paperdock-wifi", "paperdock-uninstall")]
        desktop = desktop_dir / "paperdock.desktop"
        original_manifest = {"format": runtime.MARKER, "prefix": str(prefix), "installation_id": "previous", "launchers": list(map(str, paths)), "desktop_file": str(desktop), "release": "old"}
        runtime.atomic_write(prefix / "install.json", json.dumps(original_manifest))
        runtime.set_wifi(prefix, "192.168.1.2")
        for path in paths:
            runtime.atomic_write(path, "#!/bin/sh\n# PaperDock installation: previous\n# Old launcher\n", 0o755)
        runtime.atomic_write(desktop, "[Desktop Entry]\nX-PaperDock-Installation=previous\n", 0o644)
        originals = {p: p.read_bytes() for p in [prefix / "install.json", prefix / "config/wifi.json", desktop, *paths]}
        arguments = SimpleNamespace(prefix=str(prefix), bin_dir=str(bin_dir), desktop_dir=str(desktop_dir), scanner_ip="192.168.1.3", without_wifi=False, offline=False, skip_system_packages=True, dry_run=False, desktop=False, python=sys.executable, wheelhouse=None, wifi_source=None)
        # Avoid all actual build/download work; fail after new metadata and
        # wrappers have been written, before switching current.
        arguments.without_wifi = True
        arguments.scanner_ip = None
        real_write = runtime.atomic_write
        def fail_desktop(path, content, mode=0o600):
            if Path(path) == desktop and "Name=PaperDock" in content:
                raise OSError("simulated desktop write failure")
            return real_write(path, content, mode)
        with patch.object(installer, "run"), patch.object(installer, "atomic_write", side_effect=fail_desktop), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(OSError, "simulated"):
                installer.install(arguments)
        self.assertEqual((prefix / "current").resolve(), previous_release)
        self.assertEqual(list((prefix / "releases").iterdir()), [previous_release])
        for path, contents in originals.items():
            self.assertEqual(path.read_bytes(), contents, str(path))

    def test_first_install_failure_leaves_no_partial_manifest(self):
        args = SimpleNamespace(prefix=str(self.root / "runtime"), bin_dir=str(self.root / "bin"), desktop_dir=str(self.root / "apps"), scanner_ip=None, without_wifi=True, offline=False, skip_system_packages=True, dry_run=False, desktop=False, python=sys.executable, wheelhouse=None, wifi_source=None)
        def fail_pip(command, **kwargs):
            if "pip" in command:
                raise subprocess.CalledProcessError(1, command)
        with patch.object(installer, "run", side_effect=fail_pip), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install(args)
        self.assertFalse((self.root / "runtime").exists())
        self.assertFalse((self.root / "bin/paperdock").exists())
        args.dry_run = True
        with contextlib.redirect_stdout(io.StringIO()) as output:
            installer.install(args)
        self.assertIn("keine Installation", output.getvalue())
        self.assertFalse((self.root / "runtime").exists())


if __name__ == "__main__":
    unittest.main()
