# Changelog

## 0.2.1 — Wi-Fi setup fix

- Show a clear setup hint when the installed Wi-Fi module has no scanner address.
- Add scanner address settings in the app, with immediate activation and device
  refresh; no process restart is needed after saving in the app.
- Preserve existing Wi-Fi configuration and USB backends, validate addresses, and
  prevent configuration changes during scanning or device queries.
- Distinguish missing driver, unmanaged launch and unconfigured Wi-Fi states.

## 0.2.0 — Community alpha

- Local automatic page orientation using Tesseract OSD, conservative confidence
  handling, per-page feedback and recovery of the image before an automatic turn.
- Persistent naming templates, default local date and time, editable document
  titles and matching PDF download names.
- Larger typography, responsive layout and light/dark/system themes.
- User installation for Debian/Ubuntu-family systems, including dependencies and
  local builds of the experimental pinned iX1300 Wi-Fi module.
- Community scanner-test forms, a hardware test matrix and contribution guidance.
- Application licensing changes to Apache-2.0 with a NOTICE identifying PaperDock
  by designshot. The separate Wi-Fi driver retains its own GPL/SANE-exception
  terms. Existing MIT-licensed 0.1.0 copies retain their permissions.

This is an alpha for testing. There is no Flatpak release yet. Hardware results
remain limited to the combinations recorded in `docs/SCANNERS.md`; the installer
and native window need testing on additional clean machines.

## 0.1.0 — Local prototype

- SANE acquisition, multi-page review, image-PDF export and Paperless-ngx upload.
- Successful iX1300 USB A4 simplex and experimental Wi-Fi simplex test scans.
- Local persistence, upload-state tracking and offline tests.
