# PaperDock

Eine lokale Scan-App für Linux mit moderner Oberfläche und direkter Paperless-ngx-Anbindung. **Version 0.2.1 ist eine Alpha zum Ausprobieren und Weiterentwickeln.** „PaperDock“ ist ein Arbeitstitel; die Verfügbarkeit des Namens wurde noch nicht geprüft. Das Projekt ist unabhängig von Fujitsu, PFU/Ricoh und Paperless-ngx.

**ScanSnap iX1300: USB funktioniert; ein WLAN-Testscan war ebenfalls erfolgreich.** USB wurde mit ADF Front, Farbe, 300 dpi und A4 samt PDF-Export geprüft: 2480 × 3508 Pixel, vollständiges und lesbares Blatt; dafür musste der rückseitige WLAN-Schalter auf **OFF** stehen. WLAN verwendet ein zusätzliches experimentelles SANE-Modul: Eine Vorderseite in Farbe bei 300 dpi mit automatischem Zuschnitt und PDF-Export gelang. Der Installer kann dieses Modul aus dem festgelegten Quellstand bauen; im Python-Wheel ist es nicht enthalten. [Testbericht](docs/TEST-REPORT.md), [WLAN-Treiber und Einschränkungen](docs/WLAN.md).

## Was die Alpha bereits enthält

- Scanner über SANE suchen und die angebotenen Einzüge, Farbmodi und Auflösungen auslesen.
- WLAN-Einrichtung direkt in den Einstellungen, mit Hinweis auf eine fehlende Scanneradresse.
- Profile für Alltag, Belege und Archiv, mit anpassbaren Scanoptionen.
- Treibervorgabe, A4 und Letter für geeignete ADF-Geräte; feste Formate werden anhand der gemeldeten Papiergrenzen angeboten.
- Mehrseitige Stapel mit Vorschau, Drehung, Seitenreihenfolge und Entfernen einzelner Seiten.
- Lokaler Export als mehrseitiges **Bild-PDF** mit passendem Dateinamen.
- Automatische Seitenausrichtung anhand von Text, mit Sicherheitsgrenze und Rückgängig-Funktion.
- Einstellbare Dokumentnamen; standardmäßig Datum und Uhrzeit.
- Paperless-Verbindung mit API-Token, Verbindungstest, Tags, Korrespondent und Dokumenttyp.
- Nachverfolgung des Paperless-Verarbeitungsstatus: Übertragen bedeutet noch nicht archiviert.
- Gespeicherte Stapel und Wiederaufnahme der Oberfläche nach einem Neustart.
- Ein gekennzeichneter Demostapel zum Ausprobieren ohne Scanner.
- Optionales eigenes GTK/WebKit-Fenster; alternativ dieselbe Oberfläche im Browser.
- Größere Schrift und Bedienelemente, anpassbare Fensteraufteilung sowie helles, dunkles und automatisches Design.

Eine lokale PDF-Textschicht, Dateiimport, manuelles Zuschneiden, automatische Seitentrennung und automatische Leerseitenentfernung sind **noch nicht enthalten**. Tesseract wird lokal ausschließlich für die Seitenausrichtung verwendet. Das Quellpaket enthält das Bau- und Patchmaterial für den experimentellen WLAN-Treiber; dessen vollständige Quellen lädt der Installer separat. Der zusätzliche WLAN-Treiber übernimmt seinen automatischen Zuschnitt im Scanner. Nach einem Upload übernimmt deine Paperless-Instanz die OCR gemäß ihrer Konfiguration. Ein lokal exportiertes PDF hat keine Textschicht.

## Installation mit einem Befehl

Auf Ubuntu 24.04, Pop!_OS 24.04 oder Debian 12/13 (vorgesehener
Installationsbereich) installiert dieser Befehl den aktuellen Alpha-Stand:

```sh
curl -fsSL https://raw.githubusercontent.com/designshot/paperdock/main/bootstrap.sh | bash
```

Der Befehl lädt und startet das [Bootstrap-Skript](https://github.com/designshot/paperdock/blob/main/bootstrap.sh)
aus [designshot/paperdock](https://github.com/designshot/paperdock). Den Quelltext
vorher ansehen; `main` enthält den aktuellen Entwicklungsstand. Der lokal geprüfte
Installationsweg ersetzt noch keinen Test auf einem frischen zweiten Rechner.
Die bestätigten iX1300-Scans und offenen Hardwaretests sind oben beschrieben.

Alternativ im heruntergeladenen und entpackten Quellarchiv oder Git-Checkout:

```sh
bash install.sh
```

Der Installer richtet die App im Benutzerkonto ein und installiert die nötigen
Systempakete über `apt`: SANE, Python, Texterkennung und die Werkzeuge zum Bau des
experimentellen iX1300-WLAN-Treibers. Für die Systempakete wird `sudo` benötigt.
Er startet keinen Scan. Danach PaperDock über das Anwendungsmenü oder mit
`~/.local/bin/paperdock` öffnen.

**Für WLAN einmal die Scanneradresse unter Setup → Scanner / WLAN eintragen.**
Die Adresse steht in der Geräteliste des Routers. Speichern und anschließend
nach Geräten suchen; ein Neustart ist dafür nicht nötig. Der WLAN-Treiber
ersetzt keine systemweite SANE-Bibliothek. USB-Geräte verwenden weiter die
regulären SANE-Treiber.
Optionen, Installationsprüfung, WLAN-Einrichtung und Deinstallation:
[Installationsanleitung](docs/INSTALL.md).

Ein Flatpak ist noch nicht enthalten. Der Ein-Befehl-Installer ist der erste
Verteilungsweg. Die Installation auf einem frischen zweiten Rechner gehört zur
Community-Testphase; unterstützte Paketnamen allein sind kein Hardwaretest.

### Entwicklung oder manueller Start

Python 3.10+, Pillow 10+ und `scanimage` sind nötig. Für die automatische
Ausrichtung zusätzlich Tesseract mit `osd`-Sprachdaten installieren:

```sh
sudo apt install python3-venv sane-utils tesseract-ocr tesseract-ocr-osd
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
python3 -m paperdock --demo
```

Ohne Tesseract ist manuelles Drehen weiterhin möglich. Die lokale App läuft
standardmäßig unter `http://127.0.0.1:8756`; `Strg+C` beendet den Dienst. Stapel
bleiben gespeichert. `--desktop` versucht ein GTK4/WebKit6-Fenster und verwendet
bei fehlenden Komponenten den Browser. Der vollständige native Fensterablauf
ist weiterhin gesondert zu prüfen.

## Darstellung

Oben unter **Design** stehen **System**, **Hell** und **Dunkel** zur Auswahl. „System“ folgt dem hellen oder dunklen Erscheinungsbild des Betriebssystems. Die Auswahl bleibt im jeweiligen Browser für die verwendete lokale App-Adresse gespeichert. Felder, Dialoge und Statusanzeigen passen sich an; gescannte Seiten behalten ihre Originalfarben. Bei schmalen Fenstern werden die Arbeitsbereiche untereinander angeordnet.

## Ausrichtung und Dokumentnamen

Unter **Setup** werden die allgemeinen Einstellungen unabhängig von Paperless
gespeichert. Die automatische Ausrichtung ist standardmäßig eingeschaltet und
wird auf neue Scans angewendet. Bei bestehenden Seiten kann sie aus der Vorschau
angestoßen werden. Tesseract erkennt die Textausrichtung in 90°-Schritten; nur
bei ausreichender Sicherheit wird gedreht. Bei wenig Text, Fotos oder unklaren
Ergebnissen bleibt die Seite unverändert und ein Hinweis erscheint. Das ist keine
Korrektur kleiner schiefer Einzugswinkel. Vor einer automatischen Drehung bleibt
eine lokale Sicherung erhalten, sodass sich die Änderung zurücknehmen lässt.

Der Standardname ist `Scan_{date}_{time}`, beispielsweise
`Scan_2026-10-15_14-32-08`. `{date}` und `{time}` beziehen sich auf die lokale Zeit
der Aufnahme, `{counter}` ergänzt eine laufende Nummer. Eigene Vorlagen werden
vor dem Speichern geprüft und als Beispiel angezeigt. Bereits vorhandene
Dokumente werden durch eine Änderung der Vorlage nicht umbenannt. Ein Titel kann
auch von Hand vergeben werden; er wird für den PDF-Dateinamen und Paperless
verwendet. Ungeeignete Dateizeichen werden für den Download bereinigt.

## Den ersten Scan testen

1. Den eingeschalteten iX1300 per USB anschließen, den rückseitigen WLAN-Schalter auf **OFF** stellen und eine unkritische Testseite einlegen.
2. PaperDock starten und die Scannerliste aktualisieren.
3. Das Gerät und einen vom Treiber angebotenen Einzug auswählen. Die Kombination **ADF Front, Farbe, 300 dpi, A4, eine Seite** wurde am Gerät geprüft. A4 bewusst auswählen; die Treibervorgabe war beim Test das kürzere Letter-Format.
4. Den Scan starten, jede Seite prüfen und bei Bedarf drehen oder umsortieren.
5. Das PDF exportieren und in einem PDF-Betrachter kontrollieren, bevor wichtige Originale verarbeitet werden.

Falls das Gerät nicht erscheint, zeigt `scanimage -L`, ob SANE den Scanner grundsätzlich erkennt. Eine alte SANE-Version, fehlende Geräteberechtigungen oder eine reine WLAN-Verbindung können die Ursache sein. PaperDock selbst sollte als normaler Benutzer laufen.

Ist das USB-Gerät im Linux-System sichtbar, aber seine Gerätedatei in einer abgeschotteten Startumgebung nicht verfügbar, weist PaperDock darauf hin. Starte die App für den USB-Test dann in einem normalen Linux-Terminal. Bei der konkreten Meldung „WLAN-Steuerungsfehler“ den rückseitigen WLAN-Schalter prüfen und den Scan anschließend bewusst erneut starten; die App wiederholt ihn nicht automatisch.

Die Profile sind Vorgaben. Welche Kombinationen tatsächlich funktionieren, bestimmt der jeweilige Treiber. Besonders Duplex und der vordere Einzug des iX1300 müssen noch am Gerät geprüft werden. Das Seitenlimit zählt erfasste Seiten; bei Duplex entstehen pro Blatt üblicherweise zwei Seiten.

## Paperless verbinden

1. In deiner Paperless-ngx-Instanz im Benutzerprofil einen API-Token erzeugen oder kopieren.
2. In PaperDock unter „Setup“ die **Basisadresse** eintragen, etwa `https://paperless.example.de` oder `https://example.de/paperless`. `/api/` wird von der App ergänzt.
3. Token einfügen, die Verbindung testen und speichern. Der Benutzer benötigt passende Rechte zum Lesen der Metadaten und Hochladen von Dokumenten.
4. Einen Stapel prüfen, Titel und optionale Metadaten auswählen und ausdrücklich an Paperless senden.
5. Mit „Status bei Paperless prüfen“ die Verarbeitung abfragen.

Der Client verwendet die [offizielle Paperless-ngx-API](https://docs.paperless-ngx.com/api/). Er unterstützt die älteren und die aktuellen Aufgabenantworten, einschließlich paginierter Listen. HTTP und HTTPS werden akzeptiert; HTTPS-Zertifikate werden geprüft. Weiterleitungen werden abgelehnt: Verwende bei einer entsprechenden Meldung die endgültige Serveradresse.

Neben den automatisierten Tests gegen einen lokalen Testserver wurden HTTPS-Verbindung und Metadaten einer echten Paperless-ngx-Instanz geprüft. Der Benutzer bestätigte den erfolgreichen Eingang des USB-Testscans in Paperless. Eine unabhängige Prüfung von OCR-Qualität und vollständiger Metadatenübernahme steht noch aus.

Ein angenommener Upload wird als **übertragen/in Verarbeitung** geführt. Erst eine erfolgreiche Aufgabenantwort bestätigt den Abschluss. Bei Verbindungsabbruch kann Paperless die Datei schon erhalten haben; PaperDock kennzeichnet das Ergebnis dann als **unklar** und verhindert ein blindes erneutes Senden. Prüfe den Eingang direkt in Paperless. Bestätigt übertragene, abgeschlossene und unklare Stapel bleiben für den Abgleich gegen Seitenänderungen gesperrt. Es gibt keine automatischen Upload-Wiederholungen.

## Lokale Daten

Standardmäßig liegen die Daten unter `$XDG_DATA_HOME/paperdock`, sonst unter `~/.local/share/paperdock`:

```text
paperdock/
  settings.json        Paperless-Adresse und API-Token
  preferences.json     Ausrichtung, Namensvorlage und fortlaufender Zähler
  jobs/
    <stapel-id>/
      job.json         Seitenreihenfolge und Verarbeitungsstatus
      <seite>.png      Erfasste Seiten
      originals/      Sicherungen vor automatischen Drehungen
      document.pdf    Export, sobald erstellt
```

Der Datenordner wird mit Dateirechten `700` angelegt; `settings.json` und die Stapel-Metadaten mit `600`. **Der API-Token liegt dort im Klartext**, geschützt durch die Dateirechte, nicht in einem Schlüsselbund. Er wird nach dem Speichern nicht an die Oberfläche zurückgegeben. Wer Zugriff auf dein Benutzerkonto oder dessen Sicherungen hat, kann diese Datei lesen.

Beim Entfernen einer Seite wird sie aus dem Stapel und dem nächsten PDF ausgeschlossen. Ihre Bilddatei bleibt zur Wiederherstellung im Datenordner. Die App hat noch keine Funktion zum vollständigen Löschen von Stapeln. Lokale Sicherungen sollten den gesamten Datenordner einschließen; eine exportierte PDF-Datei ersetzt diese Sicherung nicht.

Die Oberfläche und der App-Dienst kommunizieren ausschließlich über die lokale Adresse `127.0.0.1`. PaperDock ist kein Mehrbenutzerserver und kein Dienst für eine öffentliche Freigabe. Dokumente werden nur nach ausdrücklichem Senden an die konfigurierte Paperless-Instanz übertragen; Verbindungstests und Metadatenabfragen kontaktieren diese Instanz ebenfalls. Es gibt keine Cloud-Pflicht und keine Telemetrie.

## Startoptionen

Alle Optionen funktionieren mit `python3 -m paperdock` sowie dem installierten Befehl `paperdock`:

| Option | Bedeutung |
| --- | --- |
| `--demo` | Beim Start einen gekennzeichneten Beispielsatz anlegen. |
| `--desktop` | Eigenes GTK/WebKit-Fenster versuchen, sonst Browser öffnen. |
| `--no-browser` | Weder Browser noch Desktopfenster automatisch öffnen. |
| `--port 8756` | Lokalen Port festlegen; `--port 0` wählt einen freien Port. |
| `--data-dir /pfad` | Einen anderen lokalen Datenordner verwenden. |

Beispiel für einen isolierten Demotest:

```sh
python3 -m paperdock --demo --no-browser --port 0 --data-dir ./demo-data
```

Öffne anschließend die im Terminal angezeigte lokale Adresse. Für getrennte Instanzen sind getrennte Datenordner erforderlich. Ein gemeinsamer Datenordner darf nicht gleichzeitig von mehreren Instanzen verwendet werden.

## Community und Entwicklungsstand

PaperDock steht ab 0.2.0 unter [Apache-2.0](LICENSE) mit einer [NOTICE-Datei](NOTICE), die den Ursprung **PaperDock von designshot** nennt. Weitergegebene Ableitungen müssen die einschlägigen Lizenz- und Herkunftshinweise nach Abschnitt 4 erhalten. Ein eigener Fork-Name ist erlaubt; ein Hinweis in der Oberfläche ist nicht zwingend. Der zusätzliche WLAN-Treiber behält seine eigene GPL-Lizenz mit SANE-Ausnahme. [Lizenzen und Herkunft](THIRD_PARTY_NOTICES.md).

Quellcode und Beiträge: [designshot/paperdock](https://github.com/designshot/paperdock).
[Fehler melden](https://github.com/designshot/paperdock/issues/new?template=bug.yml)
oder einen [Scanner-Test einreichen](https://github.com/designshot/paperdock/issues/new?template=scanner-test.yml).
Die öffentliche Community-Alpha ist noch keine produktive Freigabe: Insbesondere
Duplex, alternativer Einzug, Fehlerfälle und die offenen Paperless-Prüfungen
stehen aus. Siehe [Mitmachen](CONTRIBUTING.md), [Scanner-Testmatrix](docs/SCANNERS.md),
[Release-Anleitung](docs/PUBLISH.md) und [Release-Checkliste](docs/RELEASE-CHECKLIST.md).

Automatisierte Tests:

```sh
python3 -m unittest discover -s tests -v
```

Im letzten vollständigen Lauf bestanden alle **133 automatisierten Tests**. Sie prüfen Scan- und Bildverarbeitung mit kontrollierten Testdaten sowie HTTP-Abläufe gegen einen lokalen Testserver. Sie benötigen keine echte Paperless-Instanz und keinen echten Scanner. Sie ersetzen keine Prüfung des Papiereinzugs, der Firmware oder der Scanqualität.

**English overview:** PaperDock is an Apache-2.0 licensed early Linux scanning workspace with a local UI, SANE acquisition, local text-based orientation detection, configurable document names, image-PDF export and Paperless-ngx integration. Real iX1300 USB A4 simplex and experimental Wi-Fi simplex scans in color at 300 dpi succeeded, including PDF export. The Debian/Ubuntu-family installer builds the separate GPL-licensed experimental Wi-Fi module from pinned sources; no driver binary is bundled. Receipt of the USB scan in Paperless was confirmed by the user; independent OCR verification, duplex, recovery tests and the native window workflow remain pending. Contributions in English or German are welcome.
