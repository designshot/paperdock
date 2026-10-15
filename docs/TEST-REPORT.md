# Teststand vom 15. Oktober 2026

## PaperDock 0.2.0: Dokumentfunktionen und Community-Installer

- **113 automatisierte Tests bestanden** im vollständigen Lauf: bisherige
  Scan-/Paperless-/HTTP-Prüfungen plus Ausrichtung, Namensvergabe, sichere
  Downloadnamen, Wiederherstellung und Installer-Fehlerfälle.
- Echtes Tesseract 5.3.4 mit OSD-Daten lokal geprüft: Eine ausschließlich
  synthetische Textvorlage wurde in allen vier Orientierungen korrekt erkannt.
  Die Konfidenz lag bei 16,88 bis 20,76, oberhalb der verwendeten Grenze 15.
  Ein schwächeres Muster mit 14,23 wurde bewusst nicht automatisch gedreht.
- Vollständiger Browserablauf mit einer künstlichen Scannerquelle: automatische
  180°-Korrektur nach Erfassung, pixelgenaue Übereinstimmung mit der aufrechten
  Vorlage, Rücksetzen, erneutes Ausrichten, Namensvorlage speichern und Titel
  beim Export übernehmen. Der UTF-8-Downloadname enthält auch Umlaute korrekt;
  das PDF wurde unabhängig als einseitiges Bild-PDF ohne Textschicht gelesen.
- Allgemeine Einstellungen und Paperless-Verbindung sind getrennt speicherbar.
  Dialog bei 390 Pixel Breite ohne horizontales Überlaufen geprüft; der Inhalt
  ist vertikal scrollbar. Gespeicherter Dokumentname und Orientierung bleiben
  nach erneutem Laden der Oberfläche erhalten.
- Isolierte Installation auf Pop!_OS 24.04: neue virtuelle Umgebung, Pillow,
  PaperDock 0.2.0, lokaler Neubau des gepinnten und gepatchten WLAN-Moduls,
  52 Treiber-Offlineprüfungen und Start des installierten Kommandozeilenprogramms.
  Der Test verwendete vorbereitete lokale Quellen/Wheels und einen separaten
  Installationspfad mit Leerzeichen. Er führte keine apt-Systemänderung aus.
- Installer-Tests decken unter anderem USB-Backend-Erhalt, Pfadquotierung,
  ungültige Scanneradressen, ausgeschlossene lokale Daten, fehlgeschlagene
  Erstinstallation, Rollback bei fehlgeschlagener Aktivierung und Deinstallation
  mit Erhalt der Dokumente ab.
- Die bestehende WLAN-App wurde auf 0.2.0 aktualisiert; vorhandene Stapel und
  Scanoptionen wurden erhalten. In dieser Änderungsrunde wurde kein echter
  Scan und kein Upload durchgeführt.

Noch offen: echte apt-Erstinstallation auf einem frischen zweiten Rechner,
Debian-12/13- und weitere Ubuntu-/Pop!_OS-Installationen, vollständiger nativer
GTK-Fensterablauf, Ausrichtung vielfältiger echter Belege sowie die unten
aufgeführten Hardwarefälle. Es gibt noch kein Flatpak. Der Internet-Bootstrap
kann erst nach Veröffentlichung von `designshot/paperdock` gegen das öffentliche
Repository geprüft werden. CI-Dateien sind vorbereitet, aber noch nicht auf
GitHub ausgeführt.

## Historischer Ausgangsstand 0.1.0

PaperDock 0.1.0 Alpha wurde auf einem Pop!_OS 24.04-Rechner mit der bereitgestellten Python-Laufzeit geprüft.

- **70 automatisierte Tests bestanden**, keine übersprungenen Tests im abschließenden Lauf. Enthalten sind Scanner-Prozesssimulation, Bildverarbeitung/PDF, Paperless-HTTP gegen einen lokalen Testserver, Wiederherstellung, parallele Zugriffe und Schutz der lokalen API. Neuere Prüfungen decken außerdem USB-Diagnose, begrenzte private Scanprotokolle, WLAN-Fehlerklassifizierung und feste Papierformate ab.
- Browserablauf geprüft: leerer Start, explizite Demo mit drei Seiten, Drehung, geänderte Reihenfolge, PDF-Download, erneutes Laden des gespeicherten Stapels sowie Öffnen/Schließen der Paperless-Einstellungen.
- Das über die Oberfläche heruntergeladene PDF wurde mit einem unabhängigen PDF-Parser gelesen: drei Seiten, A4-Hochformat und die gedrehte Seite im A4-Querformat.
- Darstellung bei schmaler Fensterbreite und 1440 × 1024 geprüft; Desktop-Seitenvorschau passt sich in den verfügbaren Bereich ein.
- Frontend ohne JavaScript-Fehler in den geprüften Abläufen. Syntax und Referenzen auf HTML-Bedienelemente geprüft.
- Python-Wheel erfolgreich ohne zusätzliche Build-Abhängigkeiten gebaut; Paket enthält die lokalen Oberflächendateien.
- GTK4/WebKit6-Import und benötigte API-Eigenschaften geprüft; der native Fensterablauf wurde nicht vollständig ausgeführt.

**Noch nicht am Gerät geprüft:** Duplex, alternativer Einzugsweg, weitere Farbmodi und Auflösungen sowie die übrigen Fehler- und Abbruchfälle der Release-Checkliste. Ebenfalls offen sind die unabhängige Prüfung der Paperless-OCR, der vollständige GTK-Speicherdialog und die Installation auf einem zweiten Rechner. Ein WLAN-Simplexscan mit dem zusätzlichen experimentellen Treiber und PDF-Export war erfolgreich; dessen Sichtprüfung durch den Benutzer steht noch aus.

Die automatisierten Paperless-Tests verwenden ausschließlich synthetische Dokumente und Test-Zugangsdaten. Zusätzlich wurde die Verbindung zur echten Paperless-ngx-Instanz des Benutzers geprüft (Version 3.1.3, API-Version 10): HTTPS-Verbindung, Metadaten und Dokumentberechtigung waren verfügbar. Nach dem Upload des USB-Testscans bestätigte der Benutzer den erfolgreichen Eingang in Paperless. OCR-Qualität und vollständige Übernahme aller Metadaten wurden nicht unabhängig geprüft.

## Echter USB-Test am selben Tag

Der reale ScanSnap iX1300 wurde zunächst vom Linux-System als USB-Gerät erkannt. Der direkte Gerätezugriff aus der Entwicklungs-Sandbox blieb nicht verfügbar: Die zugehörige USB-Gerätedatei war dort ausgeblendet. Nach dem Start von PaperDock durch den Benutzer in einem normalen Linux-Terminal funktionierten auch die SANE-Gerätesuche und das Auslesen der Fähigkeiten.

| Prüfung | Ergebnis |
| --- | --- |
| Gerät und Verbindung | ScanSnap iX1300 über USB |
| Treiber | SANE 1.2.1, Fujitsu-Backend 1.0.139 |
| Fähigkeiten ohne Scanstart | Einzüge, Farbmodi, Auflösungen und Papiergrenzen ausgelesen |
| Erster Aufnahmeversuch mit aktivem WLAN | Fehlgeschlagen; Fujitsu-Diagnose bestätigte `WiFi control error` beim Einziehen der Seite |
| Aufnahme nach rückseitigem WLAN-Schalter auf OFF | Erfolgreich: einseitig, ADF Front, Color, 300 dpi |
| Erster erfolgreicher Scan | Letter-Treibervorgabe, 2550 × 3300 Pixel; PDF-Export erfolgreich |
| A4 mit expliziten Papiermaßen | Am Gerät erfolgreich: ADF Front, Color, 300 dpi, eine Seite; 2480 × 3508 Pixel |
| A4-PDF-Export | Erfolgreich; unabhängiger Parser bestätigt eine Seite mit 209,97 × 297,01 mm, entsprechend der SANE-Pixelrundung |
| A4-Sichtprüfung | Vollständiges, lesbares Blatt; um 180° verkehrt eingelegte Vorlage über zweimaliges Drehen in der Oberfläche korrigiert |
| Erneuter Export nach Drehung | Erfolgreich; die alte PDF wurde verworfen, das neue Dokument enthält eine Seite im A4-Hochformat. Download über die Oberfläche bestätigt. |

Der erfolgreiche Einzeltest bestätigt diese konkrete Kombination. Er bestätigt weder Duplex noch den alternativen Einzugsweg oder die übrigen Auflösungen. Die Firmwareversion wurde für dieses Protokoll nicht erfasst.

Die A4-Korrektur setzt die Papiermaße vor dem Scanbereich und verhindert damit die Übernahme der kürzeren Letter-Vorgabe. Neben den automatisierten Prüfungen von Treiberargumenten und PDF-Abmessungen bestätigt jetzt der echte A4-Scan die vollständige Aufnahme für die oben genannte Kombination.

Private Scaninhalte, Geräteseriennummern und Adressen des Testrechners sind nicht Bestandteil dieses Berichts oder des Quellpakets.

## WLAN-Verbindung am selben Tag

Der Benutzer schaltete WLAN ein und zog USB ab. Die WLAN-Anzeige leuchtete blau. Eine gezielte lokale Suche erkannte den iX1300 mit VENS-Interface-Version 16; die TCP-Begrüßung und eine Statusabfrage antworteten erfolgreich.

Der erste Verbindungsversuch nach dem älteren iX500-Format wurde mit Status −1 abgelehnt. Die anschließende Recherche ergab ein abweichendes iX1300-Format: 128 statt 384 Bytes, Interface-Version 16, lokale MAC-Kennung und kein Gerätepasswort. Nach ausdrücklicher Freigabe wurde diese Variante genau einmal am Gerät ausgeführt: **Anmeldung Status 0, Interface-Version 16; anschließende normale Freigabe mit Aktion 0 ebenfalls Status 0**. Es wurde dabei keine Seite gescannt und keine dauerhafte Einstellung verändert.

Anschließend wurde ein separat gebautes experimentelles SANE-Modul geladen. Die App erkannte den oberen und den vorderen Einzug als getrennte Geräte. Die Oberfläche zeigt den WLAN-Treiber als experimentell an, deaktiviert nicht unterstützte Profile und bietet nur die vorhandenen Fähigkeiten an.

Nach Bestätigung des eingelegten Testblatts wurde genau ein WLAN-Scan gestartet: **ADF Front, Farbe, 300 dpi, eine Seite, automatische Papiergröße**. PaperDock meldete den Stapel ohne Fehler als bereit. Die RGB-PNG-Datei ist 2481 × 3481 Pixel groß und wurde erfolgreich dekodiert. Der anschließende lokale PDF-Export enthält eine Seite mit 210,06 × 294,72 mm; Seitenzahl und Maße wurden unabhängig mit einem PDF-Parser geprüft. Der automatische Zuschnitt ist keine Bestätigung einer festen A4-Geometrie oder der Vollständigkeit aller Blattränder. Die Sichtprüfung durch den Benutzer bleibt offen. Der WLAN-Testscan wurde nicht an Paperless gesendet.

52 Offline-Protokolltests des angepassten WLAN-Moduls bestanden. Zusätzlich wurde die korrigierte JPEG-Fehlerbehandlung mit ASan/UBSan und gezielten Allokationsfehlern geprüft. Alle 70 PaperDock-Tests bestanden nach der Integration erneut. Quellen, lokale Treiberkorrekturen, Abgrenzung und Einschränkungen stehen in [WLAN.md](WLAN.md).

## Überarbeitete Oberfläche und Darkmode

Die Oberfläche verwendet jetzt 16 Pixel Grundschrift, 15–16 Pixel für Eingaben und Schaltflächen, 12–13 Pixel für Beschriftungen und 13 Pixel für Hinweise. Abstände, Kontraste und Schaltflächen wurden vergrößert. Die Optionen System, Hell und Dunkel werden lokal im Browser gespeichert; System reagiert auf Änderungen des Betriebssystemdesigns.

- Hell, Dunkel und System im Browser geprüft, einschließlich gespeicherter Auswahl nach erneutem Laden.
- Fensterbreiten von 390, 640 und 1440 Pixel ohne horizontales Überlaufen geprüft. Der dunkle Einstellungsdialog bleibt bei 390 Pixel Breite bedienbar und vertikal scrollbar.
- Dokumentvorschau ohne Farbfilter auf weißem Hintergrund geprüft.
- Die vier vorhandenen HTTP-Tests bestanden nach Aufnahme der neuen Designdatei. HTML und `theme.js` werden mit korrekten Inhaltstypen ausgeliefert; die Einschränkung auf lokale Skripte bleibt aktiv. JavaScript-Syntax geprüft.
- Die laufende WLAN-Oberfläche wurde aktualisiert und mit dem vorhandenen Stapel sowie den bisherigen Scanoptionen geprüft. Dafür wurde kein weiterer Scan und kein Upload ausgelöst.

Der vollständige Lauf mit 70 Tests gehört zur vorherigen WLAN-Integration; für die anschließende Darstellungsänderung wurden gezielt die oben genannten Prüfungen durchgeführt. Die Sichtprüfung ersetzt keine vollständige Prüfung auf Barrierefreiheit. Quellarchiv und Python-Wheel wurden mit der neuen Oberfläche aktualisiert.
