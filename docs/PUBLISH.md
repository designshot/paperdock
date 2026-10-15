# Releases pflegen und veröffentlichen

Das Projekt wird unter [designshot/paperdock](https://github.com/designshot/paperdock)
gepflegt. Diese Anleitung beschreibt die Vorbereitung weiterer Community-Releases.
Solange die offenen Hardware- und Installationstests bestehen, Veröffentlichungen
auf GitHub ausdrücklich als **Pre-release** kennzeichnen.

## Release vorbereiten

1. Versionsnummer, Änderungsübersicht und Releasebeschreibung auf denselben Stand
   bringen. Die App-Lizenz bleibt Apache-2.0 mit `NOTICE`; das gesonderte
   WLAN-Modul behält seine GPL-Lizenz mit SANE-Ausnahme. Details stehen in
   `THIRD_PARTY_NOTICES.md`.
2. Softwaretests ausführen und den [Testbericht](TEST-REPORT.md) mit dem tatsächlich
   geprüften Stand abgleichen. Historische lokale Testergebnisse sind kein
   Nachweis eines aktuellen CI-Laufs oder neuer Hardwaretests.
3. Den Installer mit `--dry-run`, einer isolierten Installation und möglichst
   einem frischen Testrechner prüfen. Bei Treiberänderungen Quellcommit, Patch
   und Prüfsummen gemeinsam aktualisieren und die Offline-Tests erneut ausführen.
4. Die [Release-Checkliste](RELEASE-CHECKLIST.md) bearbeiten. Offene Hardwaretests
   und bekannte Einschränkungen in der Releasebeschreibung sichtbar lassen.
5. `git status` und die zum Commit vorgemerkten Dateien prüfen. Keine Dokumente,
   Zugangsdaten, privaten Adressen, Geräteseriennummern oder lokalen
   Laufzeitumgebungen veröffentlichen. Die `.gitignore` ersetzt diese Prüfung nicht.

```sh
python3 -m unittest discover -s tests -v
bash install.sh --dry-run
git status --short
git diff --cached --stat
```

Nach dem Commit den zugehörigen Lauf unter
[GitHub Actions](https://github.com/designshot/paperdock/actions) prüfen. Der
Workflow prüft Software; Hardwaretests und eine vollständige Installation mit
Systempaketen bleiben eigene Prüfschritte. Ein grüner Lauf darf nur für den
tatsächlich geprüften Commit angegeben werden.

## Tag und GitHub-Release

Den geprüften Commit mit einer neuen Versionsnummer markieren. Das folgende
Beispiel verwendet `v0.2.0`; für spätere Releases die nächste passende Nummer
einsetzen. Vorhandene veröffentlichte Tags nicht verschieben oder überschreiben.

```sh
git tag -a v0.2.0 -m "PaperDock 0.2.0 community alpha"
git push origin v0.2.0
```

Unter [Releases](https://github.com/designshot/paperdock/releases) einen
**Pre-release** für diesen Tag anlegen. Änderungen, überprüfte Scannerkombinationen,
getestete Installationswege und verbleibende Grenzen beschreiben. Nicht allein
aus einer erfolgreichen Geräteerkennung vollständige Modellunterstützung ableiten.

Das automatisch erzeugte Quellarchiv enthält den Installer. Ein Python-Wheel
enthält die App, aber weder Systempakete noch WLAN-Treiberbinary. Der
Ein-Befehl-Installer ist der vollständige Installationsweg; nach Veröffentlichung
die Downloadlinks und den Bootstrap am gewünschten Tag prüfen. Der Standard-
Einzeiler in der README verwendet den beweglichen Entwicklungsstand `main`.

Falls später Treiber-Binaries veröffentlicht werden, müssen die vollständigen
zugehörigen Treiberquellen einschließlich lokaler Änderungen entsprechend deren
GPL-Lizenz verfügbar sein. Das kleine Patchverzeichnis allein reicht dafür nicht.

## Forks und Herkunft

Die Apache-2.0-Lizenz verlangt bei Weitergabe die einschlägigen Lizenz-, Änderungs-
und Herkunftshinweise nach Abschnitt 4. `NOTICE` nennt das Ursprungsprojekt
**PaperDock von designshot**. Ein Fork darf anders heißen und seine eigenen
Autoren ergänzen. Die Lizenz verlangt keinen ständig sichtbaren Hinweis im
Hauptfenster. Der unveränderte
[offizielle Lizenztext](https://www.apache.org/licenses/LICENSE-2.0.html) ist
maßgeblich. „PaperDock“ bleibt bis zur Prüfung der Namensverfügbarkeit ein Arbeitstitel.
