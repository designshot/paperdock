# Licenses and attribution

## PaperDock

PaperDock's application code, UI, documentation and installer are licensed under
Apache-2.0. Copyright 2026 designshot and PaperDock contributors. The complete
license is in `LICENSE`; origin notices are in `NOTICE`.

When distributing a derivative work, retain the applicable copyright and
attribution notices and provide the license and a readable copy of the notices
as required by Apache License 2.0, section 4. Changed files must carry notices
that they were changed. A fork may have its own product name. The license does
not require a particular advertising banner or forbid commercial use.

Earlier local 0.1.0 copies were provided under MIT. Those copies keep their
existing permissions; this release does not revoke them. New contributions to
this release are accepted under Apache-2.0 unless explicitly agreed otherwise.

## Experimental ScanSnap Wi-Fi driver

The separate material in `drivers/scansnap-wifi/` is licensed under
**GPL-2.0-or-later WITH SANE-exception**, not Apache-2.0. Its `COPYING`, `LICENSE`
and `SANE-exception.txt` retain the upstream terms. The source project is
[mxovd/sane-backends-scansnap](https://github.com/mxovd/sane-backends-scansnap),
pinned to commit `130b69136f1eedff19acb377cb5019e38d865065`.

The installer downloads that source, applies the included patch and builds the
driver on the user's machine. No driver binary is distributed in the Python
wheel or source archive. If distributing a driver binary, provide its complete
corresponding source and modifications under its license; a link to this small
patch directory alone is not the complete corresponding source.

## Dependencies obtained separately

The installer obtains these projects through the distribution package manager
or PyPI. Their own licenses and notices apply; they are not relicensed by
PaperDock:

- SANE and its backends: GPL with the applicable SANE linking exception.
- Tesseract OCR and the OSD model: Apache-2.0; used for local orientation analysis.
- Pillow: HPND-style Pillow/PIL license.
- Python, GTK, WebKitGTK, libjpeg and their dependencies: their respective
  upstream licenses, as supplied by the package manager.

PaperDock calls `scanimage` and `tesseract` as separate local processes. The UI
uses local assets and system fonts; it loads no third-party CDN or web font.
