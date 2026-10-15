# PaperDock mit einem Befehl installieren

Der Installer richtet PaperDock einschließlich OCR und experimentellem
iX1300-WLAN-Modul ein. Vorgesehen sind **Ubuntu 24.04, Pop!_OS 24.04 sowie
Debian 12 und 13**. Den vollständigen isolierten Installationsweg haben wir auf
Pop!_OS 24.04 geprüft; die übrigen Systeme brauchen weitere Installationstests.

## Direkt aus dem Repository

Mit installiertem `curl` startet dieser Befehl den Installer des aktuellen
Alpha-Entwicklungsstands:

```sh
curl -fsSL https://raw.githubusercontent.com/designshot/paperdock/main/bootstrap.sh | bash
```

Der Befehl führt das heruntergeladene [Bootstrap-Skript](https://github.com/designshot/paperdock/blob/main/bootstrap.sh)
aus. Dessen Inhalt vorher ansehen. Der Bootstrap holt den aktuellen `main`-Stand
von [designshot/paperdock](https://github.com/designshot/paperdock) und ruft denselben
lokalen Installer auf, der unten beschrieben ist. Ein bestimmter vorhandener
Branch oder Release-Tag kann als erstes Argument mit `--ref` gewählt werden;
verfügbare Versionen stehen unter [Releases](https://github.com/designshot/paperdock/releases).
Der WLAN-Quellcommit ist unabhängig davon festgelegt und wird vor dem Build geprüft.

## Aus einem Quellarchiv oder Git-Checkout

Archiv entpacken, im PaperDock-Ordner ein Terminal öffnen und ausführen:

```sh
bash install.sh
```

Den Installer als normalen Benutzer starten. Für die Installation der fehlenden
Systempakete fragt `sudo` nach dem Systempasswort. Anwendung und Python-Pakete
werden anschließend ohne sudo in eine eigene virtuelle Umgebung installiert.
Fehlt auf einem minimalen System noch Python 3 selbst, richtet der kleine
Shell-Startschritt es zuerst über apt ein. Ein fehlendes `sudo` muss ein
Administrator bereitstellen oder die benötigten Pakete selbst installieren.

Enthalten sind `sane-utils`, Python/venv, Tesseract einschließlich
Orientierungserkennung sowie die Compiler-/JPEG-Pakete für das WLAN-Modul.
Pillow und die App werden innerhalb der Benutzerumgebung installiert. Das
WLAN-Modul wird aus einem festgelegten öffentlichen Quellstand gebaut und mit
52 Offline-Protokolltests geprüft. Der Installer startet keinen Scanner und
verschickt keine Dokumente.

Nach erfolgreicher Installation erscheint **PaperDock** im Anwendungsmenü.
Alternativ direkt `~/.local/bin/paperdock` starten. Wenn `~/.local/bin` im PATH
liegt, genügt `paperdock`. Der Standardbrowser zeigt die Oberfläche; mit
`bash install.sh --desktop` werden zusätzlich die GTK4-/WebKit6-Pakete für das
eigene Fenster installiert. Ohne verfügbares Desktop-Framework verwendet die
App automatisch den Browser.

## WLAN einrichten

Die private IPv4-Adresse des Scanners steht beispielsweise in der Geräteliste
des Routers. Sie lässt sich bei der Installation mit `--scanner-ip` übergeben
oder anschließend speichern:

```sh
paperdock-wifi 192.168.1.40
```

Die Adresse im Beispiel ersetzen. Der Helfer speichert nur die Konfiguration;
die App kontaktiert den Scanner erst bei ihrer Geräteerkennung bzw. einem Scan.
Eine DHCP-Reservierung im Router verhindert spätere Adressänderungen. Nach einer
Änderung PaperDock neu starten. `paperdock-wifi --show` zeigt die gespeicherte
Adresse; `paperdock-wifi --disable` schaltet die WLAN-Erweiterung ab.

Der Treiber unterstützt derzeit iX1300, Interface 16, Farbe/300 dpi und
automatische Papiergröße. Details und Hardwaregrenzen stehen in [WLAN.md](WLAN.md).
Die aktivierten systemweiten SANE-Backends und ihre Konfiguration bleiben für
USB-Scanner erhalten. Das zusätzliche Modul wird nur für den PaperDock-Prozess
geladen; systemweite SANE-Bibliotheken werden nicht ersetzt.

Nur USB gewünscht:

```sh
bash install.sh --without-wifi
```

## Ablage, Updates und Deinstallation

Standardmäßig liegen die Programme unter
`$XDG_DATA_HOME/paperdock-runtime` bzw. `~/.local/share/paperdock-runtime`.
Jede erfolgreiche Installation erhält einen eigenen Releaseordner. Erst nach
erfolgreichem Build und Tests wird `current` auf das neue Release umgeschaltet;
vorherige Releases bleiben erhalten. Ein erneutes `bash install.sh` aus einem
neuen Quellstand aktualisiert die Anwendung. Änderungen am Installationsort
erfordern passende `--prefix`, `--bin-dir` und `--desktop-dir` wie zuvor.

Die Dokumente und Paperless-Einstellungen liegen weiterhin separat im normalen
PaperDock-Datenordner (`$XDG_DATA_HOME/paperdock` bzw.
`~/.local/share/paperdock`). Der Installer liest diese Zugangsdaten nicht.

```sh
paperdock-uninstall
```

Die Deinstallation bestätigt das Entfernen der Programmdateien. Dokumente,
Paperless-Einstellungen und apt-Systempakete bleiben erhalten. Für eine
unbeaufsichtigte Deinstallation gibt es `paperdock-uninstall --yes`.

## Vorschau, lokale Abhängigkeiten und Testinstallationen

`bash install.sh --dry-run` zeigt den Plan ohne Downloads oder Änderungen.
`--skip-system-packages` überspringt apt, wenn die Voraussetzungen bereits
administrativ eingerichtet sind. Die nötigen Voraussetzungen werden dann vom
Build bzw. Python geprüft; insbesondere muss der gewählte Python-Interpreter
`venv` und `ensurepip` unterstützen.

Eine vollständig lokale Installation verwendet einen vorbereiteten Wheelordner
mit Pillow, setuptools ≥ 68, wheel und deren Abhängigkeiten sowie einen Checkout
des Treibercommits `130b69136f1eedff19acb377cb5019e38d865065`:

```sh
bash install.sh --skip-system-packages --offline \
  --wheelhouse /pfad/zu/wheels --wifi-source /pfad/zu/sane-quellen \
  --prefix /pfad/zu/test-runtime --bin-dir /pfad/zu/test-bin \
  --desktop-dir /pfad/zu/test-menue
```

Relative Pfade funktionieren ebenfalls. `--python /pfad/zu/python3` wählt den
Interpreter der App-Umgebung. Zum Starten des Installers mit einem anderen
Interpreter `PAPERDOCK_INSTALL_PYTHON=/pfad/zu/python3` setzen. Ein vorhandener
WLAN-Checkout darf bereits mit dem mitgelieferten Patch versehen sein. Der
Installer erzeugt daraus einen lokalen Git-Klon des festgelegten Commits und
wendet den Paket-Patch frisch an; unversionierte Dateien werden nicht übernommen.

Die Treiberquellen und der angewandte Patch bleiben samt GPL-/SANE-Lizenzmaterial
im Releaseordner unter `wifi/` erhalten. PaperDock selbst steht unter Apache-2.0;
die GPL-2.0-or-later mit SANE-Ausnahme des gesonderten Treibers bleibt bestehen.

Keine Installation auf einem zweiten Rechner und keine apt-Systemänderung wurden
im bisherigen isolierten Test vorgenommen. Mehrplattform-, GTK- und echte
Paketmanager-Tests bleiben vor einem stabilen Release erforderlich.
