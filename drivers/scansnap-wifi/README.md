# PaperDock: experimenteller iX1300-WLAN-Baustein

Dieses Zusatzpaket macht einen kleinen, prüfbaren WLAN-Treiber für den ScanSnap
iX1300 lokal baubar. Es enthält den PaperDock-Patch, ein Linux-Buildrezept und
Offline-Tests. Die vollständigen Treiberquellen kommen aus dem unabhängigen
[SANE-Fork von mxovd](https://github.com/mxovd/sane-backends-scansnap).

**Experimenteller Stand vom 15. Oktober 2026:** Ein echter iX1300 hat mit diesem
Ansatz eine Seite über WLAN gescannt; daraus wurde erfolgreich ein PDF erstellt.
Das bestätigt den grundlegenden Scanweg. Duplex, mehrseitige Stapel, beide
Papierwege, Abbruch und Fehlerbehandlung brauchen weitere lokale Hardwaretests.
Es besteht keine Verbindung zum Gerätehersteller; PaperDock ist ein Arbeitstitel.

## Umfang

- iX1300 im lokalen Netzwerk, gezielt konfigurierte IPv4-Adresse.
- Unverschlüsselte VENS-Verbindung mit Interface-Version 16.
- Farbe, 300 dpi, automatische Seitengröße.
- ADF und Rückführungs-/Karteneinzug als getrennte SANE-Geräte; je `ADF Front`
  oder `ADF Duplex`. Diese Kombinationen sind implementiert und werden von
  Upstream als hardwaregetestet beschrieben; unser eigener aktueller Erfolg ist
  auf eine Seite begrenzt.
- Ausgabe als SANE-Modul für bestehende Programme wie `scanimage` und PaperDock.

Andere ScanSnap-Modelle, verschlüsselte Sitzungen und Passwortanmeldung werden
nicht zugesagt. Der Build installiert nichts und kontaktiert weder Scanner noch
Netzwerk. Dieses Paket enthält keine Binärdateien, Zugangsdaten oder Scans.

## Festgelegte Quelle und Änderungen

Repository: <https://github.com/mxovd/sane-backends-scansnap>

Branch zur Orientierung: `scansnap-ix1300`

Verbindlicher Commit: `130b69136f1eedff19acb377cb5019e38d865065`

Der vollständige Patch `paperdock-sane-safety.patch` verändert vier Dateien:

- `backend/scansnap-protocol.c`: ausschließlich normaler Release mit Aktion 0
  und eigener Client-Identität; Bereinigung nach verlorener Bestätigung oder
  teilweise gesendeter Reservierung; kein Release nach ausdrücklicher Ablehnung;
  Fehler mit signiertem Statuscode; korrekte Linux-Zeitzone inklusive Sommerzeit.
- `backend/scansnap.c`: JPEG-Decoderzustand bleibt bei einem `longjmp` gültig;
  Speicher wird auch bei Decoderfehlern freigegeben.
- `tools/scansnap/scansnap_session.py`: normaler Release ohne Force-Parameter.
- `testsuite/backend/scansnap/test_scansnap_session.py`: Prüfung der Release-Bytes.

Die geänderten Quelldateien tragen Änderungshinweise mit Datum. `source-hashes.json`
legt ihren erwarteten Zustand fest; der Build prüft diese Dateien und den Commit.

## Voraussetzungen

Linux mit bereits installiertem Python 3.10+, Git, einem GNU-kompatiblen
C-Compiler (`cc`), Linux-/C-Entwicklungsheadern und libjpeg samt
Entwicklungsheadern. Auf Ubuntu heißen die entsprechenden Pakete typischerweise
`python3`, `git`, `build-essential` und `libjpeg-dev`. Zum späteren Scannen wird
`sane-utils` benötigt. Das Skript lädt und installiert keine Pakete.

Dieses schmale Rezept braucht keine Autotools und kein systemweites `libsane-dev`:
Die nötigen SANE-Header und Hilfsfunktionen stammen aus dem festgelegten Checkout.
Es erzeugt ein lokales Linux-Entwicklungsmodul. Für allgemeine Distributionen und
Release-Pakete bleibt der vollständige Upstream-Build der vorgesehene Weg.

## Quellen holen, Patch prüfen, lokal bauen

Das ZIP so entpacken, dass der Ordner `paperdock-wlan-experiment` im aktuellen
Verzeichnis liegt. Nur das Klonen benötigt eine Internetverbindung:

```sh
git clone https://github.com/mxovd/sane-backends-scansnap.git sane-scansnap-source
git -C sane-scansnap-source checkout --detach 130b69136f1eedff19acb377cb5019e38d865065
git -C sane-scansnap-source apply --check ../paperdock-wlan-experiment/paperdock-sane-safety.patch
git -C sane-scansnap-source apply ../paperdock-wlan-experiment/paperdock-sane-safety.patch
python3 paperdock-wlan-experiment/build.py --source sane-scansnap-source --build sane-scansnap-build --test
```

`--source` und `--build` akzeptieren relative oder absolute Pfade. Der Buildordner
muss neu oder leer sein und außerhalb des Quellordners liegen. Bestehende Builds
werden nicht überschrieben. Es werden keine Upstream-Buildskripte ausgeführt,
keine Systemdateien geändert und keine Scannergeräte gesucht.

Ergebnis: `sane-scansnap-build/lib/libsane-scansnap.so.1` sowie der symbolische
Link `libsane-scansnap.so`. Eine vorhandene systemweite `libsane.so` bleibt
unberührt. Das Modul ist für den Rechner gebaut, auf dem das Rezept ausgeführt
wurde; es ist kein distributionsübergreifend tragbares Binary.

Bei fehlenden Compiler- oder JPEG-Dateien endet der Build mit einer Fehlermeldung.
Nach Behebung der Ursache für den nächsten Versuch einen neuen Buildordner wählen.

## Offline-Prüfungen

`--test` führt 23 vorhandene C-Protokoll-Replays und 6 zusätzliche
Reservierungs-/Cleanupfälle aus. Die zusätzlichen Fälle ersetzen Socketfunktionen
durch Speicherpuffer und prüfen normale Freigabe, Timeout, Verbindungsabbruch,
ungültige Antwort, ausdrückliche Ablehnung und die Zeitzone. Sie greifen nicht
auf das Netzwerk zu.

Die 23 Python-Protokolltests lassen sich zusätzlich ausführen:

```sh
python3 -m unittest discover -s sane-scansnap-source/testsuite/backend/scansnap -p 'test_scansnap_*.py' -v
```

Alle 52 Protokolltests haben den lokalen Stand bestanden. Der JPEG-Fix wurde
zusätzlich isoliert mit einem kleinen gültigen JPEG und künstlichen Fehlerfällen
unter AddressSanitizer/UndefinedBehaviorSanitizer geprüft. Diese Tests ersetzen
keine Hardwaretests und sind keine Aussage über alle denkbaren Bilddaten.

## Einbindung ohne Systeminstallation

Für den Scannerprozess zwei Umgebungsvariablen setzen:

```text
LD_LIBRARY_PATH=<absoluter Buildordner>/lib
SANE_CONFIG_DIR=<absoluter privater Konfigurationsordner>
```

Der private Konfigurationsordner enthält `dll.conf` mit genau `scansnap` und
`scansnap.conf` mit `net <Scanner-IPv4-Adresse>`. Die Platzhalter werden durch die
eigenen lokalen Werte ersetzt. Kein abschließender Doppelpunkt in
`SANE_CONFIG_DIR`: Er würde zusätzliche systemweite Konfigurationen einbeziehen.

Die Gerätenamen sind `scansnap:net:<Scanner-IPv4-Adresse>:adf` und
`scansnap:net:<Scanner-IPv4-Adresse>:return`. Die Quellen heißen `ADF Front` und
`ADF Duplex`. Die erzeugte `empty-config` enthält absichtlich kein Zielgerät.

Eine Geräteauflistung mit dieser aktiven Konfiguration führt bereits eine
gezielte Netzwerkerkennung aus. Erst ein gestarteter Scan reserviert das Gerät.
Die Einbindung daher bewusst als separaten Schritt vornehmen. PaperDock kann
dieses Modul über seinen bestehenden SANE-/`scanimage`-Scanweg verwenden.

## Grenzen und Beiträge

Vor breiter Veröffentlichung prüfen: wiederholte Scans und Freigabe danach,
mehrseitiger ADF, Duplexreihenfolge, Rückführung, leeres Fach, Papierstau, Abbruch,
gleichzeitiger anderer Client und Netzwerkunterbrechung. Die aktuelle synchrone
Netzwerkverarbeitung kann einen Abbruch verzögern; Freigabefehler werden von der
Treiberbereinigung derzeit nicht an die Oberfläche zurückgegeben.

Für Fehlerberichte Modell, Firmware, Distribution, Quellcommit und genaue
Arbeitsschritte angeben. Scans, Passwörter, Seriennummern, MAC-Adressen und private
Netzwerkadressen gehören nicht in öffentliche Berichte. Änderungen möglichst mit
einem Offline-Replay belegen und dem genannten Upstream zur Prüfung anbieten.

## Lizenz und Weitergabe

Die ScanSnap-Quelldateien, der Patch, das Buildskript und der zusätzliche Test
stehen unter **GPL-2.0-or-later WITH SANE-exception**. Die unveränderten Dateien
`COPYING` und `LICENSE` stammen aus dem festgelegten Upstream-Commit;
`SANE-exception.txt` enthält den Ausnahmetext aus dessen SANE-Header. Die jeweiligen
Dateihinweise bleiben maßgeblich.

Die SANE-Ausnahme erlaubt die Verknüpfung mit Programmen anderer Lizenz; sie hebt
die Pflichten für den Treibercode selbst nicht auf. Bei Weitergabe von modifizierten
Treiber-Binaries den zugehörigen vollständigen Quellstand, Änderungen und
Lizenzhinweise entsprechend GPL mitliefern. Dieses Paket verteilt lediglich
Quelländerungen und Buildmaterial; der vollständige SANE-Quellstand wird über das
oben festgelegte Repository bezogen. PaperDocks eigene Apache-2.0-Lizenz ändert die Lizenz
dieses separaten Treibermoduls nicht.
