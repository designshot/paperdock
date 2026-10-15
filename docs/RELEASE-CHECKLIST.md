# Vor einer Community-Veröffentlichung

Diese Liste beschreibt die Freigabekriterien und ihren bisherigen Stand. Offene Kästchen sind keine bereits erledigten Tests. Version 0.2.0 ist eine Alpha mit neuen Dokumentfunktionen und Installer. Der ursprüngliche Hardwarestand stammt aus 0.1.0; aktuelle Software- und Installationsprüfungen stehen im Testbericht. Echte iX1300-USB-A4- und experimentelle WLAN-Simplexscans mit PDF-Export waren erfolgreich; die Sichtprüfung des WLAN-Ergebnisses bleibt offen. Den Eingang des USB-Scans in Paperless bestätigte der Benutzer. Duplex, unabhängige OCR-Prüfung und der vollständige GTK-Fenstertest stehen noch aus. Einzelheiten stehen im [Testbericht](TEST-REPORT.md).

## Reproduzierbarer Start

- [ ] Ein frisches Quellarchiv auf einem zweiten Linux-System entpacken.
- [ ] Den Ein-Befehl-Installer einschließlich echter apt-Paketinstallation auf einem frischen zweiten Rechner testen; Python-, Pillow- und OSD-Verfügbarkeit prüfen.
- [ ] Installation mit `pip install .` in einer sauberen virtuellen Umgebung testen; den Befehl `paperdock` starten.
- [ ] `python3 -m unittest discover -s tests -v` auch auf dem zweiten Linux-System vollständig erfolgreich ausführen und Umgebung festhalten; den aktuellen vollständigen Lauf im Testbericht festhalten.
- [ ] Demo, leeren Start, `--no-browser`, `--port 0` und einen eigenen `--data-dir` testen.
- [ ] Browserablauf und optionales GTK4/WebKit6-Fenster prüfen, einschließlich PDF-Speicherdialog und Schließen.
- [ ] Tastaturbedienung, Dialogfokus, schmale Fenster und gut erkennbare Fehlerzustände kontrollieren.

## ScanSnap iX1300 über USB

- [ ] Modell, Firmware, Distribution, SANE-Version und USB-Verbindung im Testprotokoll erfassen.
- [x] Erkennung und angebotene Fähigkeiten ohne Scanstart prüfen.
- [x] Ein einzelnes Blatt über ADF Front in Farbe bei 300 dpi erfassen und als PDF exportieren: erfolgreich mit Letter-Treibervorgabe, 2550 × 3300 Pixeln und rückseitigem WLAN-Schalter auf OFF.
- [x] Den tatsächlich aufgetretenen Fujitsu-WLAN-Steuerungsfehler verständlich erklären; keine automatische Scanwiederholung auslösen.
- [x] Einen echten A4-Scan prüfen: vollständiges, lesbares Blatt mit 2480 × 3508 Pixeln bei 300 dpi; PDF mit einer Seite und 209,97 × 297,01 mm. Die verkehrt eingelegte Vorlage wurde in der Oberfläche um 180° gedreht.
- [ ] Die feste Letter-Auswahl zusätzlich zur bereits getesteten Letter-Treibervorgabe am Gerät prüfen.
- [ ] Einen Stapel mit nummerierten Vorder- und Rückseiten über Duplex scannen; Reihenfolge und Vollständigkeit zählen.
- [ ] Den vorderen Einzug beziehungsweise den am Gerät verfügbaren alternativen Einzugsweg gesondert prüfen. Nicht von der Unterstützung des automatischen Stapeleinzuges auf diesen schließen.
- [ ] Die angebotenen Farbmodi und die tatsächlich unterstützten Profilauflösungen prüfen.
- [ ] Seitenlimit bei einseitigen und doppelseitigen Scans prüfen; keine unbemerkten fehlenden Seiten akzeptieren.
- [ ] Leeren Einzug und einen am Gerät sicher simulierbaren Papierstau beziehungsweise offenen Deckel prüfen. Keine Beschädigung durch künstliches Verklemmen verursachen.
- [ ] Einen laufenden Scan abbrechen; bereits gespeicherte Seiten und Bedienbarkeit des Geräts kontrollieren.
- [ ] USB-Verbindung nach einer vollständig gespeicherten Seite unterbrechen und wiederherstellen; Fehleranzeige und Folgescan prüfen.
- [ ] Einen längeren, aber realistischen Stapel scannen und Speicherbedarf sowie Dateivollständigkeit prüfen.

## ScanSnap iX1300 über WLAN

- [x] Gezielte Erkennung, modellgerechte Anmeldung und normale Freigabe prüfen.
- [x] Eine Vorderseite in Farbe bei 300 dpi über PaperDock aufnehmen und als einseitiges PDF lesen.
- [x] Nicht unterstützte Profile deaktivieren; automatische Papiergröße anzeigen.
- [ ] Scaninhalt und automatische Blattränder durch den Benutzer prüfen.
- [ ] Duplex, mehrere Blätter und vorderen Einzug mit PaperDock prüfen.
- [ ] Abbruch, leeren Einzug, Verbindungsfehler und Wiederverbindung prüfen.
- [x] Separates Quell-/Patch-Experiment mit Buildrezept, Tests und Lizenzhinweisen vorbereiten; lokalen Neubau prüfen.
- [ ] Reguläres portables Treiberpaket einschließlich vollständiger Quellen für eine Binärverteilung erstellen.
- [ ] WLAN-Einrichtung und Bau auf einem zweiten Rechner prüfen.

## Seiten und PDF

- [ ] Seiten drehen, umsortieren und entfernen; Vorschau und exportierte Reihenfolge vergleichen.
- [x] Lokale Orientierungserkennung mit synthetischen Textseiten in allen vier Drehlagen prüfen.
- [x] Automatische Drehung, Rücksetzen und erneute Ausrichtung über die Oberfläche prüfen.
- [x] Namensvorlage und Titelwechsel samt UTF-8-Dateiname beim PDF-Export prüfen.
- [ ] Automatische Ausrichtung mit echten Dokumentarten am Gerät prüfen, einschließlich knapper Belege und gemischter Stapel.
- [ ] PDF in einem unabhängigen Betrachter öffnen; Seitenanzahl, Orientierung und lesbaren Inhalt prüfen.
- [ ] Nach einer Änderung erneut exportieren und prüfen, dass das PDF nicht die alte Reihenfolge enthält.
- [ ] Sicherstellen, dass der Export als Bild-PDF ohne lokale OCR erklärt wird.
- [ ] Prüfen, dass das Entfernen einer Seite die ursprüngliche Bilddatei bewusst auf der Festplatte belässt, wie dokumentiert.

## Echte Paperless-ngx-Instanz

- [ ] Einen separaten Testbenutzer mit passenden Berechtigungen und Testdokumenten verwenden.
- [ ] Verbindung über HTTPS sowie gegebenenfalls einen realen URL-Unterpfad testen; Server- und API-Version protokollieren.
- [ ] Tags, Korrespondenten und Dokumenttypen laden, einschließlich mehrseitiger Metadatenlisten.
- [ ] Ein PDF mit Titel, mehreren Tags, Korrespondent und Dokumenttyp senden; alle Felder im erzeugten Dokument vergleichen.
- [ ] Übergang von angenommenem Upload über laufende Verarbeitung bis zum bestätigten Abschluss prüfen.
- [ ] Das archivierte PDF öffnen und die Paperless-OCR prüfen; Seitenzahl und Inhalt vergleichen.
- [ ] Verweigerte Rechte, ungültigen Token, fehlerhafte Metadaten und einen von Paperless abgelehnten Upload prüfen.
- [ ] Einen Verbindungsabbruch während des Uploads testen. Der lokale Status muss unklar sein; kein automatischer zweiter Upload darf entstehen.
- [ ] Bei unklarem Ausgang direkt in Paperless kontrollieren und den vorgesehenen manuellen Abgleich beschreiben.
- [ ] Nach erfolgreichem Upload wiederholt Status abfragen; eine später entfernte historische Aufgabe darf den bestätigten Abschluss nicht zurücksetzen.

## Neustart und lokale Daten

- [ ] App im Leerlauf schließen und öffnen; Stapel, Reihenfolge und Einstellungen vergleichen.
- [ ] App während einer Aufnahme beenden; erhaltene vollständige Seiten nach dem Neustart prüfen.
- [ ] App während eines Uploads beenden; nach dem Neustart muss ein unklarer Ausgang erkennbar sein und erneutes Senden gesperrt bleiben.
- [ ] Stapel mit bereits vorhandener Paperless-Aufgaben-ID nach dem Neustart weiter abfragen.
- [ ] Datenordner `700` und `settings.json`/Metadaten `600` prüfen; keinen Token in Browserantworten oder Protokollen finden.
- [ ] Sicherung und Wiederherstellung eines separaten Testdatenordners ausprobieren.
- [ ] Erklären, dass der API-Token lokal im Klartext und nicht im Schlüsselbund liegt.

## Veröffentlichung

- [ ] Arbeitstitel und Paketname auf mögliche Verwechslungen prüfen und gegebenenfalls ändern.
- [ ] Dokumentation gegen den tatsächlichen Funktionsumfang und die Testergebnisse abgleichen.
- [ ] Ausschließlich belegte Scannerkombinationen als geprüft aufführen; WLAN bleibt trotz erfolgreichem Einzeltest experimentell und erfordert den zusätzlichen Treiber.
- [ ] Lizenzdatei, Herkunft fremder Bestandteile und Paketinhalt kontrollieren.
- [ ] Keine Scans, Token, lokalen Datenordner, privaten Adressen oder temporären Dateien in das Archiv aufnehmen.
- [ ] Version und Alpha-Hinweis in Paket, App und Releasebeschreibung abgleichen.
- [ ] Ziel für öffentliche Fehlerberichte und Beiträge festlegen.
- [ ] Das fertige Archiv erneut entpacken und starten.
- [ ] Erst anschließend ein öffentliches Repository oder Release veröffentlichen; das lokale Quellpaket ist noch keine Veröffentlichung.
