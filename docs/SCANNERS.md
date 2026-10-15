# Scannerunterstützung und Community-Tests

PaperDock verwendet SANE. Ein Gerät, das `scanimage -L` meldet, kann grundsätzlich
in der App angeboten werden. Das ist noch keine Zusage, dass jede Option und
jeder Papiereinzug funktioniert. Die Oberfläche liest Fähigkeiten vom jeweiligen
Treiber, statt Unterstützung allein aus einem Modellnamen abzuleiten.

## Durchgeführte Gerätetests

| Modell | Verbindung / Treiber | Getestete Kombination | Stand |
| --- | --- | --- | --- |
| ScanSnap iX1300 | USB / SANE Fujitsu 1.0.139 | ADF Front, Farbe, 300 dpi, A4, eine Seite und PDF | Erfolgreich; WLAN-Schalter OFF |
| ScanSnap iX1300 | WLAN / separater ScanSnap-Treiber, festgelegter Commit | ADF Front, Farbe, 300 dpi, automatische Größe, eine Seite und PDF | Erfolgreicher Einzeltest; experimentell |
| Weitere Modelle | SANE | Noch keine PaperDock-Hardwaretests | Community-Tests gesucht |

Die Gerätetests erfolgten mit PaperDock 0.1.0. 0.2.0 ergänzt Ausrichtung,
Dokumentnamen und Installation; neue Hardwaretests sind dafür nicht vorgetäuscht.
Duplex, der vordere iX1300-Einzug, umfangreiche Stapel und Fehlerbehandlung sind
noch offen. Details: [Testbericht](TEST-REPORT.md), [WLAN](WLAN.md).

## Ein weiteres Modell testen

1. App-Version/Commit, Distribution, SANE-Version, Modell und Verbindung notieren.
2. Mit einem erfundenen, klar nummerierten Textblatt beginnen. Zuerst eine
   Vorderseite scannen und die Vorschau sowie das exportierte PDF prüfen.
3. Erst danach weitere Auflösungen, Farbe/Grau, Duplex und Stapel einzeln testen.
   Die tatsächlich erfassten Seiten zählen; Reihenfolge und Blattränder prüfen.
4. Die automatische Ausrichtung mit absichtlich auf dem Kopf und seitlich
   eingelegten Textseiten prüfen. Fotos und sehr kurze Belege können zu wenig
   Text liefern; das soll als unsicher erkennbar bleiben.
5. Einen Folgescan, regulären Abbruch und Wiederaufnahme prüfen. Keinen
   Papierstau künstlich erzwingen oder Firmware für einen Test verändern.
6. Im Repository ein Issue mit der Vorlage [Scanner testen](https://github.com/designshot/paperdock/issues/new?template=scanner-test.yml) anlegen. Keine
   Dokumentinhalte, API-Token, Passwörter, privaten Adressen oder Gerätekennungen
   veröffentlichen. Bei einem Fehler reichen zunächst bereinigte Meldungen.

Vorhandene Berichte stehen im [Issue-Tracker](https://github.com/designshot/paperdock/issues).

## Unterstützung erweitern

- Wenn ein Modell schon von SANE unterstützt wird, zuerst dessen gemeldete
  Optionen und Ausgabe prüfen. Fähigkeitsabfragen und Parsen gehören nach
  `paperdock/scanner.py`, nicht als modellabhängige Annahmen in die Oberfläche.
- Die Aufnahme liefert vollständige Seiten über `on_page(path)` und beachtet
  das Abbruchereignis. Bereits gespeicherte Seiten müssen bei Fehlern erhalten
  bleiben. Neue Adapter sollen denselben Vertrag einhalten.
- Ausrichtung und Namensvergabe sind unabhängige Module; Scanneradapter sollen
  weder Paperless-Zugangsdaten noch Oberflächeneinstellungen verwalten.
- Neue Protokollimplementierungen brauchen Offline-Tests mit bereinigten
  Antworten. Ein neuer Treiber muss seine Herkunft und Lizenz dokumentieren.
- Änderungen am experimentellen WLAN-Treiber gehören zunächst in dessen Patch
  und Tests. Den festgelegten Commit und die Quellprüfsummen gemeinsam prüfen;
  keine ungetestete neueste Branch-Version stillschweigend übernehmen.

Ein Testbericht ist willkommen, auch wenn ein Gerät nicht funktioniert. Nur
tatsächlich belegte Kombinationen werden als getestet in die Tabelle aufgenommen.
