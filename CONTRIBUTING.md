# An PaperDock mitarbeiten

PaperDock ist eine frühe Alpha. Besonders hilfreich sind nachvollziehbare Gerätetests, bessere Fehlerbehandlung und Verbesserungen der Bedienbarkeit. Deutsch und Englisch sind gleichermaßen willkommen. „PaperDock“ bleibt bis zur Prüfung des Namens ein Arbeitstitel.

## Entwicklungsumgebung

Benötigt werden Python 3.10+, Pillow 10+ und für echte Scans SANE mit `scanimage`. Richte im Projektordner eine virtuelle Umgebung ein:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
python3 -m paperdock --demo --port 0 --data-dir ./dev-data
```

Die Tests verwenden teilweise einen lokalen HTTP-Server. Eine Umgebung, die das Anlegen lokaler Sockets verbietet, kann diese Tests nicht vollständig ausführen. Externe Netzwerkdienste und echte Scans werden für die Tests nicht benötigt.

Nutze einen eigenen Datenordner mit erfundenen Dokumenten. `dev-data`, exportierte Scans und persönliche Einstellungen gehören nicht in Beiträge oder öffentliche Archive.

## Aufbau

| Bereich | Aufgabe |
| --- | --- |
| `paperdock/scanner.py` | SANE-Aufnahme, Seitenprüfung, Bildoperationen und PDF-Export. |
| `paperdock/paperless.py` | Paperless-API, Metadaten, Upload und Aufgabenstatus. |
| `paperdock/server.py` | Lokaler App-Dienst, Stapelverwaltung und dauerhafte Zustände. |
| `paperdock/static/` | Oberfläche ohne externen Frontend-Build. |
| `paperdock/desktop.py` | Optionales GTK4/WebKit6-Fenster. |
| `tests/` | Automatisierte Tests mit kontrollierten Geräte- und HTTP-Antworten. |

## Änderungen vorbereiten

Beschreibe das beobachtete Problem, den Auslöser und das Verhalten nach der Änderung. Füge für veränderte Aufnahme-, Upload- oder Wiederherstellungslogik einen Test hinzu, der einen realistischen Fehlerfall erfasst. Bei Änderungen an der Oberfläche helfen Screenshots mit Demodaten und eine kurze Beschreibung des geprüften Ablaufs.

Bitte erhalte diese Eigenschaften:

- Bereits vollständig gespeicherte Seiten bleiben bei Abbruch oder späterem Scanfehler verfügbar.
- „Upload angenommen“ und „Dokument erfolgreich verarbeitet“ bleiben getrennte Zustände.
- Unklare Upload-Ergebnisse werden nicht automatisch wiederholt.
- Der Paperless-Token wird nicht an die Oberfläche, Logs oder fremde Weiterleitungsziele ausgegeben.
- Der App-Dienst bleibt an Loopback gebunden; Dokumente verlassen den Rechner nur durch den ausdrücklich gestarteten Paperless-Upload.
- Angaben zur Scannerunterstützung unterscheiden zwischen Treiberdokumentation und einem tatsächlich durchgeführten Gerätetest.

Der aktuelle Scanneradapter erhält Gerätekennungen aus der Gerätesuche. Neue Adapter sollten dieselbe Trennung zwischen Erkennung, Fähigkeiten und Aufnahme erhalten. Der WLAN-Forschungsstand steht in [docs/WLAN.md](docs/WLAN.md).

## Einen Fehler oder Gerätetest beschreiben

Ein hilfreicher Bericht enthält:

- App-Version, Distribution, Python-Version und SANE-Version.
- Exaktes Scannermodell, Firmware soweit bekannt und USB/WLAN-Verbindung.
- Gewählte Auflösung, Farbmodus, Einzug und Anzahl der Testblätter.
- Die Schritte, das erwartete Ergebnis und das tatsächliche Ergebnis.
- Bei Paperless-Problemen dessen Version, HTTP-Status und den sichtbaren Aufgabenstatus.
- Ob gespeicherte Seiten und Zustände nach einem App-Neustart erhalten blieben.

Verwende für Beispiele erfundene Dokumente. Entferne API-Token, Passwörter, Seriennummern, private Serveradressen und Dokumentinhalte aus Berichten. Für Gerätetests die Issue-Vorlage [Scanner testen](https://github.com/designshot/paperdock/issues/new?template=scanner-test.yml) verwenden; für andere Probleme [Fehler melden](https://github.com/designshot/paperdock/issues/new?template=bug.yml). Die [Testmatrix](docs/SCANNERS.md) unterscheidet belegte Kombinationen von noch offenen Tests. Änderungen können als Pull Request gegen [designshot/paperdock](https://github.com/designshot/paperdock) eingereicht werden.

## Lizenz und Veröffentlichung

Beiträge müssen unter der Apache-2.0-Lizenz des Projekts weitergegeben werden können. Die Herkunftshinweise in `NOTICE` bei Weitergabe erhalten. Der separate WLAN-Treibercode bleibt unter seiner GPL-Lizenz mit SANE-Ausnahme. Fremden Code nur mit nachvollziehbarer Herkunft und kompatibler Lizenz übernehmen; bloße Protokollkompatibilität ist kein Nachweis für identische Hardwareunterstützung.

Vor einer Veröffentlichung die [Release-Checkliste](docs/RELEASE-CHECKLIST.md) bearbeiten. Ergebnisse und verbleibende Einschränkungen gehören in die Releasebeschreibung. Die erfolgreiche Testsuite allein rechtfertigt keine Aussage, dass der iX1300 über USB oder WLAN vollständig geprüft sei.
