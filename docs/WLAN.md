# ScanSnap iX1300: USB und experimentelles WLAN

Stand: 15. Oktober 2026. **Ein echter WLAN-Scan mit PaperDock war erfolgreich.** PaperDock verwendet dafür ein zusätzliches experimentelles SANE-Modul. Dieses Modul ist nicht im PaperDock-Wheel enthalten. Der Community-Installer baut es standardmäßig aus dem festgelegten Quellstand; mit `--without-wifi` lässt sich dieser Schritt auslassen.

## An unserem Gerät bestätigt

| Verbindung | Ergebnis |
| --- | --- |
| USB, WLAN-Schalter OFF | ADF Front, Farbe, 300 dpi, A4 erfolgreich; 2480 × 3508 Pixel und vollständiges PDF. |
| WLAN, USB abgezogen | Scanner gefunden, VENS-Interface-Version 16, TCP-Begrüßung und Statusabfrage erfolgreich. |
| WLAN-Anmeldung | Modellgerechte 128-Byte-Anmeldung ohne Gerätepasswort erfolgreich, Status 0. |
| WLAN-Freigabe beim Verbindungstest | Eigene Sitzung mit normaler Freigabe (Aktion 0) beendet, Status 0. |
| WLAN-Aufnahme | Eine Vorderseite über ADF Front, Farbe, 300 dpi; 2481 × 3481 Pixel. |
| WLAN-PDF | Einseitiger Export unabhängig gelesen, 210,06 × 294,72 mm bei automatischem Zuschnitt; Bilddatei erfolgreich dekodiert. |
| Paperless | Erfolgreicher Eingang des USB-Testscans vom Benutzer bestätigt. Der WLAN-Testscan wurde noch nicht hochgeladen. |

Der Scanner erkennt im WLAN-Test die Papiergröße automatisch. Das Ergebnis ist deshalb keine Prüfung einer festen A4-Geometrie oder aller Blattränder. Sichtprüfung durch den Benutzer, Duplex, weitere Blätter und Fehlerfälle bleiben offen. Private Adressen, Seriennummern und Scaninhalte gehören nicht in das Community-Paket. Weitere Einzelheiten stehen im [Testbericht](TEST-REPORT.md).

## Zusätzlicher WLAN-Treiber

Das Projekt [sane-backends-scansnap](https://github.com/mxovd/sane-backends-scansnap/tree/scansnap-ix1300) enthält einen gesonderten `scansnap`-Treiber. Geprüfter Ausgangsstand: `130b69136f1eedff19acb377cb5019e38d865065`. Der Autor berichtet weitere iX1300-Tests mit ADF, vorderem Einzug, Simplex, Duplex und mehrseitigen Stapeln. Diese Berichte ersetzen unsere eigenen PaperDock-Tests nicht. [Treiberbeschreibung](https://github.com/mxovd/sane-backends-scansnap/blob/130b69136f1eedff19acb377cb5019e38d865065/SCANSNAP_BACKEND.md), [Teststand des Projekts](https://github.com/mxovd/sane-backends-scansnap/blob/130b69136f1eedff19acb377cb5019e38d865065/SCANSNAP_ROADMAP.md).

Für den lokalen Test wurde der Treiber ohne Systeminstallation gebaut und korrigiert: normale Freigabe statt erzwungener Freigabe, Bereinigung nach unsicherer Anmeldung, aussagekräftige Fehlercodes, Zeitzone inklusive Sommerzeit sowie sichere JPEG-Fehlerbehandlung. 52 Offline-Protokolltests bestanden; die JPEG-Fehlerbehandlung wurde zusätzlich unter ASan/UBSan geprüft.

Aktuelle Grenzen:

- Nur Farbe mit 300 dpi; keine Graustufen oder weiteren Auflösungen.
- Automatische Papiergröße; keine feste A4-/Letter-Geometrie.
- ADF und vorderer Einzug erscheinen als getrennte logische Geräte.
- Scanner-IP muss lokal konfiguriert werden; eine geänderte DHCP-Adresse erfordert eine neue Konfiguration.
- Verschlüsselte oder passwortgeschützte Protokollvarianten sind nicht implementiert.
- Abbruch, Netzwerkfehler, Wiederverbindung und größere Stapel müssen in PaperDock noch geprüft werden.

PaperDock liest die angebotenen Optionen vom Treiber. Nicht unterstützte Profile werden deaktiviert. Für dieses WLAN-Modul bleibt die Papiergröße auf „Treiberstandard“.

Der zusätzliche Treiber steht unter **GPL-2.0-or-later WITH SANE-exception**. PaperDock selbst steht ab 0.2.0 unter Apache-2.0 mit Herkunftshinweisen in `NOTICE`. Bei einer Weitergabe des Treibers müssen dessen Lizenz, Quellcode und lokale Änderungen entsprechend mitgeliefert werden. Der Treiberbinary gehört nicht zum Python-Wheel oder Quellarchiv. Patch, Bauanleitung und Lizenztexte liegen unter `drivers/scansnap-wifi/`; die vollständigen Quellen werden beim Installieren geholt und lokal behalten.

## Installation und Einrichtung

Der [Community-Installer](INSTALL.md) richtet SANE, die App und den zusätzlich
gebauten WLAN-Treiber im Benutzerkonto ein. Die Scanneradresse wird lokal über
`paperdock-wifi <private IPv4-Adresse>` gesetzt. Danach PaperDock neu starten.
Der WLAN-Schalter am Scanner muss auf ON stehen; beim geprüften WLAN-Test war
USB abgezogen. Der Installer startet keinen Scan und verändert keine Firmware.

Das Quellpaket enthält unter `drivers/scansnap-wifi/` den vollständigen lokalen
Patch, das Buildrezept, zusätzliche Offline-Tests und die Lizenztexte. Der
Neubau aus dem festgelegten Quellstand wurde lokal reproduziert. Es enthält
keine Binärdateien oder private Konfiguration. Der Installer bewahrt den
verwendeten vollständigen Quellcheckout samt Änderungen im Installationsordner
auf. Für ein öffentliches Treiberbinary gelten dessen eigenen Quellcodepflichten.

Die Installation und WLAN-Einrichtung auf einem zweiten Rechner bleiben offen.
Die Community-Alpha wird in [designshot/paperdock](https://github.com/designshot/paperdock)
entwickelt. Ergebnisse weiterer Geräte bitte über die Vorlage
[Scanner testen](https://github.com/designshot/paperdock/issues/new?template=scanner-test.yml)
beisteuern; eine öffentliche Veröffentlichung erweitert den belegten Hardwareumfang
nicht automatisch.

## Warum der iX500-Ansatz nicht genügte

[AirScap](https://github.com/mzyy94/AirScap) dokumentiert das ältere iX500-Verfahren und war hilfreich für die erste Erkennung. Seine 384-Byte-Anmeldung wurde am iX1300 mit Status −1 abgelehnt. Die iX1300-spezifischen Quellen verwenden 128 Bytes, Interface-Version 16 und die MAC-Kennung des lokalen Netzwerkadapters. Dieses Format wurde anschließend am eigenen Gerät bestätigt.

Die frühere Annahme eines aus der Seriennummer abgeleiteten iX1300-Gerätepassworts ist nicht belegt und wird nicht weiterverwendet. Das aktuelle [Ricoh-Handbuch zum Scanner-Passwort](https://www.pfu.ricoh.com/imaging/downloads/manual/scansnap-wifitool/win/en/help/topic/opr_name.html) kennzeichnet diese Einstellung ausdrücklich als iX100-Funktion. Gemeint ist das Verbindungsverfahren zum Scanner, nicht das Passwort des WLAN-Routers.

Die [offizielle SANE-Geräteliste](https://sane-project.gitlab.io/website/sane-backends.html) beschreibt den regulären Fujitsu-Treiber. Dessen iX1300-Unterstützung über USB ist von diesem zusätzlichen experimentellen WLAN-Modul zu unterscheiden.
