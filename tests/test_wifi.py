"""WLAN setup tests using local fixtures only; never probe a scanner."""
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from paperdock import wifi
from paperdock.server import AppError, Application


class WifiFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="paperdock-wifi-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prefix = self.root / "installation"
        self.release = self.prefix / "releases/test-release"
        self.module = self.release / "wifi/build/lib/libsane-scansnap.so.1"
        self.module.parent.mkdir(parents=True)
        self.module.touch()
        self.manifest = self.prefix / "install.json"
        self.manifest.write_text(json.dumps({
            "format": "paperdock-user-install-v1",
            "prefix": str(self.prefix),
            "release": self.release.name,
        }))
        self.system = self.root / "system-sane"
        self.custom = self.root / "custom-sane"
        self.system.mkdir()
        self.custom.mkdir()
        (self.system / "dll.conf").write_text('"fujitsu"\nhp # enabled\nscansnap\n')
        (self.system / "dll.d").mkdir()
        (self.system / "dll.d/airscan").write_text("airscan\nfujitsu\n")
        (self.custom / "dll.conf").write_text("pixma\n")
        (self.custom / "fujitsu.conf").write_text("# Existing USB settings\nusb\n")
        self.original = {
            "SANE_CONFIG_DIR": str(self.custom),
            "LD_LIBRARY_PATH": "/opt/existing-libraries",
            "UNRELATED_SETTING": "keep-this-value",
        }
        self.environment = wifi.launch_environment(self.prefix, self.release, self.original)

    @property
    def settings_path(self):
        return self.prefix / "config/wifi.json"

    def manager(self, environment=None):
        return wifi.WifiSettings.from_environment(
            self.environment if environment is None else environment,
            system_config=self.system,
        )


class WifiSettingsTests(WifiFixture):
    def test_fresh_managed_installation_offers_setup_without_an_address(self):
        manager = self.manager()
        state = manager.state()
        self.assertTrue(state["available"])
        self.assertFalse(state["configured"])
        self.assertEqual(state["address"], "")
        self.assertTrue(state["message"])
        self.assertFalse(self.settings_path.exists())
        self.assertEqual(manager.environment["SANE_CONFIG_DIR"], self.original["SANE_CONFIG_DIR"])
        self.assertEqual(manager.environment["LD_LIBRARY_PATH"], self.original["LD_LIBRARY_PATH"])

    def test_launcher_records_only_original_sane_variables(self):
        self.assertEqual(self.environment["PAPERDOCK_INSTALL_PREFIX"], str(self.prefix))
        self.assertEqual(self.environment["PAPERDOCK_INSTALL_RELEASE"], str(self.release))
        saved = json.loads(self.environment["PAPERDOCK_SANE_ORIGINAL"])
        self.assertEqual(saved, {key: self.original[key] for key in ("SANE_CONFIG_DIR", "LD_LIBRARY_PATH")})
        self.assertEqual(self.environment["UNRELATED_SETTING"], "keep-this-value")
        self.assertNotIn("PAPERDOCK_INSTALL_PREFIX", self.original)

    def test_missing_module_and_unmanaged_launch_explain_unavailability(self):
        self.module.unlink()
        missing = self.manager().state()
        unmanaged = self.manager(self.original).state()
        for state in (missing, unmanaged):
            self.assertFalse(state["available"])
            self.assertFalse(state["configured"])
            self.assertTrue(state["message"])
        self.assertNotEqual(missing["message"], unmanaged["message"])
        self.assertFalse(self.settings_path.exists())

    def test_foreign_manifest_and_release_outside_installation_are_unavailable(self):
        original_manifest = self.manifest.read_text()
        for change in ({"format": "other-installer"}, {"prefix": str(self.root / "other")}):
            with self.subTest(change=change):
                self.manifest.write_text(json.dumps({**json.loads(original_manifest), **change}))
                self.assertFalse(self.manager().state()["available"])
        self.manifest.write_text(original_manifest)
        outside = self.root / "foreign-release"
        outside.mkdir()
        environment = {**self.environment, "PAPERDOCK_INSTALL_RELEASE": str(outside)}
        self.assertFalse(self.manager(environment).state()["available"])
        self.assertFalse(self.settings_path.exists())

    def test_corrupt_settings_show_repair_hint_and_can_be_saved_again(self):
        setup_message = self.manager().state()["message"]
        self.settings_path.parent.mkdir(parents=True)
        self.settings_path.write_text('{"scanner_ip": broken-json')
        manager = self.manager()
        state = manager.state()
        self.assertTrue(state["available"])
        self.assertFalse(state["configured"])
        self.assertEqual(state["address"], "")
        self.assertTrue(state["message"])
        self.assertNotEqual(state["message"], setup_message)
        self.assertEqual(manager.environment["SANE_CONFIG_DIR"], self.original["SANE_CONFIG_DIR"])
        manager.save("192.168.1.40")
        self.assertEqual(json.loads(self.settings_path.read_text()), {"scanner_ip": "192.168.1.40"})
        self.assertTrue(manager.state()["configured"])
        self.assertEqual(self.manager().state()["address"], "192.168.1.40")

    def test_settings_symlink_is_rejected_without_changing_its_target(self):
        manager = self.manager()
        before_state = manager.state()
        before_environment = manager.environment.copy()
        target = self.root / "unrelated-fixture.json"
        target.write_text('{"belongs_to": "another program"}\n')
        original = target.read_bytes()
        self.settings_path.parent.mkdir(parents=True)
        self.settings_path.symlink_to(target)
        with self.assertRaises(ValueError):
            manager.save("192.168.1.40")
        self.assertTrue(self.settings_path.is_symlink())
        self.assertEqual(self.settings_path.resolve(), target)
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(manager.state(), before_state)
        self.assertEqual(manager.environment, before_environment)

    def test_save_reconfigure_and_disable_preserve_usb_and_existing_library_paths(self):
        manager = self.manager()
        original_usb = (self.custom / "fujitsu.conf").read_bytes()
        for address in ("192.168.1.40", "10.2.3.4"):
            with self.subTest(address=address):
                manager.save(address)
                state = manager.state()
                self.assertTrue(state["configured"])
                self.assertEqual(state["address"], address)
                self.assertEqual(json.loads(self.settings_path.read_text())["scanner_ip"], address)
                self.assertEqual(stat.S_IMODE(self.settings_path.stat().st_mode), 0o600)
                self.assertEqual((self.prefix / "config/sane/scansnap.conf").read_text(), f"net {address}\n")
                backend_names = [line for line in (self.prefix / "config/sane/dll.conf").read_text().splitlines()
                                 if line and not line.startswith("#")]
                self.assertEqual(backend_names, ["pixma", "fujitsu", "hp", "airscan", "scansnap"])
                self.assertEqual(manager.environment["SANE_CONFIG_DIR"].split(":"),
                                 [str(self.prefix / "config/sane"), str(self.custom), str(self.system)])
                self.assertEqual(manager.environment["LD_LIBRARY_PATH"].split(":"),
                                 [str(self.module.parent), "/opt/existing-libraries"])
        manager.save("")
        self.assertFalse(manager.state()["configured"])
        self.assertEqual(manager.state()["address"], "")
        for key, value in self.original.items():
            self.assertEqual(manager.environment[key], value)
        self.assertEqual((self.custom / "fujitsu.conf").read_bytes(), original_usb)

    def test_disable_restores_unset_environment_variables(self):
        environment = wifi.launch_environment(self.prefix, self.release, {"UNRELATED_SETTING": "present"})
        manager = self.manager(environment)
        manager.save("172.16.3.4")
        manager.save("")
        self.assertNotIn("SANE_CONFIG_DIR", manager.environment)
        self.assertNotIn("LD_LIBRARY_PATH", manager.environment)
        self.assertEqual(manager.environment["UNRELATED_SETTING"], "present")

    def test_saved_address_survives_new_manager_without_accumulating_prefixes(self):
        first = self.manager()
        first.save("192.168.2.15")
        restarted = self.manager(first.environment)
        self.assertEqual(restarted.state()["address"], "192.168.2.15")
        self.assertEqual(restarted.environment, first.environment)
        restarted.save("192.168.2.16")
        self.assertEqual(restarted.environment["LD_LIBRARY_PATH"].split(":").count(str(self.module.parent)), 1)
        restarted.save("")
        for key in ("SANE_CONFIG_DIR", "LD_LIBRARY_PATH"):
            self.assertEqual(restarted.environment[key], self.original[key])
        self.assertFalse(self.manager(restarted.environment).state()["configured"])

    def test_invalid_addresses_do_not_change_persisted_or_active_configuration(self):
        manager = self.manager()
        manager.save("192.168.2.15")
        before_file = self.settings_path.read_bytes()
        before_state = manager.state()
        before_environment = manager.environment.copy()
        for address in (True, False, None, 3232236047, [], {}, "8.8.8.8", "127.0.0.1",
                        "169.254.1.1", "::1", "scanner.local", "192.168.2.15\n",
                        "192.168.2.15;touch /tmp/paperdock-wifi-sentinel",
                        "192.168.2.15\nnet 10.0.0.2", "http://192.168.2.15"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                manager.save(address)
            self.assertEqual(self.settings_path.read_bytes(), before_file)
            self.assertEqual(manager.state(), before_state)
            self.assertEqual(manager.environment, before_environment)

    def test_scanner_ip_accepts_only_strict_private_ipv4_strings(self):
        for address in ("10.0.0.1", "172.16.1.2", "172.31.254.2", "192.168.1.2"):
            self.assertEqual(wifi.scanner_ip(address), address)
        for address in (True, 3232235778, b"\xc0\xa8\x01\x02", "", " 192.168.1.2",
                        "192.168.01.2", "10.0.0.0", "10.255.255.255", "172.32.0.1",
                        "192.168.255.255", "0.0.0.0", "224.0.0.1"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                wifi.scanner_ip(address)

    def test_failed_backend_config_write_restores_previous_files_and_active_settings(self):
        manager = self.manager()
        manager.save("192.168.1.40")
        paths = [self.settings_path, self.prefix / "config/sane/dll.conf",
                 self.prefix / "config/sane/scansnap.conf"]
        originals = {path: path.read_bytes() for path in paths}
        before_state = manager.state()
        before_environment = manager.environment.copy()
        real_write = wifi.atomic_write
        failed = False

        def fail_once(path, content, mode=0o600):
            nonlocal failed
            if Path(path) == paths[-1] and not failed:
                failed = True
                raise OSError("simulated configuration write failure")
            return real_write(path, content, mode)

        with patch("paperdock.wifi.atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated"):
                manager.save("192.168.1.41")
        self.assertEqual(manager.state(), before_state)
        self.assertEqual(manager.environment, before_environment)
        for path, contents in originals.items():
            self.assertEqual(path.read_bytes(), contents)


class ApplicationWifiTests(WifiFixture):
    def setUp(self):
        super().setUp()
        self.wifi = self.manager()
        with patch("paperdock.server.wifi.WifiSettings.from_environment", return_value=self.wifi):
            self.app = Application(self.root / "documents")
        self.addCleanup(self.app.shutdown)

    def test_state_includes_setup_status_and_save_invalidates_device_cache(self):
        with patch("paperdock.server.orientation.available", return_value=False):
            self.assertEqual(self.app.state()["wifi"], self.wifi.state())
        self.app.devices = [{"id": "old:scanner"}]
        self.app.capabilities = {"old:scanner": {"sources": ["ADF"]}}
        with patch("paperdock.server.scanner.discover_devices") as discover:
            self.app.set_wifi({"address": "192.168.1.40"})
        discover.assert_not_called()
        self.assertEqual(self.app.wifi.state()["address"], "192.168.1.40")
        self.assertEqual(self.app.devices, [])
        self.assertEqual(self.app.capabilities, {})
        self.assertFalse(self.app.scan_lock.locked())

    def test_save_while_scanner_is_busy_is_rejected_without_changes(self):
        self.app.set_wifi({"address": "192.168.1.40"})
        before = self.settings_path.read_bytes()
        self.app.devices = [{"id": "current:scanner"}]
        self.app.capabilities = {"current:scanner": {"sources": ["ADF"]}}
        self.app.scan_lock.acquire()
        try:
            with self.assertRaises(AppError) as caught:
                self.app.set_wifi({"address": "192.168.1.41"})
            self.assertEqual(caught.exception.status, 409)
        finally:
            self.app.scan_lock.release()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertEqual(self.app.devices, [{"id": "current:scanner"}])
        self.assertIn("current:scanner", self.app.capabilities)

    def test_malformed_settings_body_preserves_configuration_and_device_cache(self):
        self.app.set_wifi({"address": "192.168.1.40"})
        before = self.settings_path.read_bytes()
        self.app.devices = [{"id": "current:scanner"}]
        for body in ({}, {"address": True}, {"address": None}, {"address": []},
                     {"address": "8.8.8.8"}, {"address": "192.168.1.41", "extra": "ignored?"}):
            with self.subTest(body=body), self.assertRaises(AppError):
                self.app.set_wifi(body)
            self.assertEqual(self.settings_path.read_bytes(), before)
            self.assertEqual(self.app.devices, [{"id": "current:scanner"}])
            self.assertFalse(self.app.scan_lock.locked())

    def test_discovery_and_options_use_current_environment_after_save_and_disable(self):
        device = "fixture:scanner"
        result = {"devices": [{"id": device}], "warning": None}
        for address in ("192.168.1.40", "192.168.1.41", ""):
            with self.subTest(address=address):
                self.app.set_wifi({"address": address})
                with patch("paperdock.server.scanner.discover_devices", return_value=result) as discover:
                    self.app.discover()
                discover.assert_called_once_with(environment=self.wifi.environment)
                passed = discover.call_args.kwargs["environment"]
                self.assertIsNot(passed, self.wifi.environment)
                with patch("paperdock.server.scanner.device_options", return_value={"sources": ["ADF"]}) as options:
                    self.app.options(device)
                options.assert_called_once_with(device, environment=self.wifi.environment)
        self.assertEqual(passed["SANE_CONFIG_DIR"], self.original["SANE_CONFIG_DIR"])
        self.assertEqual(passed["LD_LIBRARY_PATH"], self.original["LD_LIBRARY_PATH"])

    def test_scan_receives_a_copy_of_the_configured_environment(self):
        self.app.set_wifi({"address": "192.168.1.40"})
        self.app.devices = [{"id": "fixture:scanner"}]
        with patch.object(self.app, "start_worker"):
            job = self.app.new_job({"device": "fixture:scanner"})
        with patch("paperdock.server.scanner.scan_pages", return_value=[]) as scan:
            self.app._scan(job["id"])
        scan.assert_called_once()
        passed = scan.call_args.kwargs["environment"]
        self.assertEqual(passed, self.wifi.environment)
        self.assertIsNot(passed, self.wifi.environment)
        self.assertFalse(self.app.scan_lock.locked())


if __name__ == "__main__":
    unittest.main()
