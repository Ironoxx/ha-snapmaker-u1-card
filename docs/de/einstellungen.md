# Einstellungen

[← Zurück zum README](../../README.de.md)

**Inhalt:** [Einstellungen der Integration](#einstellungen-der-integration) · [Einstellungen in der Karte](#einstellungen-in-der-karte) · [Kartenoptionen](#kartenoptionen) · [Update](#update) · [Wie die Karte geladen wird](#wie-die-karte-geladen-wird) · [Moonraker-Integration (optional)](#moonraker-integration-optional)

## Einstellungen der Integration

Bei der Einrichtung kommt nach der Adresse direkt ein zweiter Schritt mit allen Einstellungen. Später stehen sie unter *Geräte & Dienste → Snapmaker U1 Card → Konfigurieren*. Alle Felder sind freiwillig, die Karte übernimmt sie automatisch.

| Abschnitt | Felder |
|---|---|
| Strom und Verbrauch | Netzschalter, Leistungssensor (W), Energiezähler (kWh), Strompreis: Preis-Entität (EUR/kWh oder ct/kWh, dynamische Tarife) **oder** fester Preis je kWh; ist beides leer, gilt der Preis aus dem **Energie-Dashboard** von Home Assistant, vor dem Abschalten herunterfahren, Auto-Ein beim Druckstart, Auto-Aus nach dem Druck (Temperatur, Verzögerung), Ausschalten nach Leerlauf (Stunden) |
| Benachrichtigungen & Kamera | `notify.mobile_app_…`-Dienste, Anlässe (fertig, abgebrochen, Fehler, pausiert, Meldung im Druck, erste Schicht fertig, gleich fertig, Filament reicht nicht), Vorwarnung „gleich fertig“ in Minuten (10), „Teil entnehmbar“ ab Betttemperatur (35 °C), Kamera für Bild und Ergebnisfoto, **Kamera wach halten** (aus / während eines Drucks / immer) |
| Filamentpreise | € je kg für PLA, PETG, ABS, ASA, TPU, PA und sonstige. `PLA-CF` nutzt den PLA-Preis. Mit Spoolman haben dessen Preise Vorrang: am Druckende der Preis der Spule im jeweiligen Kopf, sonst der Durchschnittspreis je kg deiner Spulen dieses Materials (Spulenpreis, sonst Filamentpreis, je Nettogewicht). Diese Felder gelten nur für Materialien ohne Preis in Spoolman |
| Zeitraffer sichern | Ein/aus, wie viele neueste auf dem Drucker bleiben (0 = nie löschen), wie viele im Medienordner bleiben (50, 0 = alle), Sicherungen nach x Tagen löschen (0 = nie) |
| Wartung | Intervall je Punkt in Druckstunden (0 = ausblenden) |
| Spoolman | Adresse (leer = aus), Verbrauch je Kopf abbuchen (an/aus), Warnschwelle in g |
| Dateien | Anzahl neuester Dateien, Drucker-Konfiguration sichern (an) |

## Einstellungen in der Karte

Admins finden in der Karte *System → Einstellungen*: die Einstellungen der Integration (Strom, Benachrichtigungen, Filamentpreise, Spoolman, Dateien, Zeitraffer-Sicherung, Wartung) nach Themen gegliedert, mit dem aktuellen Wert neben jeder gewählten Entität und dem Spoolman-Preis neben jedem Filamentpreis. Das ist dasselbe wie *Einstellungen → Geräte & Dienste → Snapmaker U1 Card → Konfigurieren*, mit denselben Prüfungen; gespeichert werden nur geänderte Bereiche, danach lädt die Integration kurz neu. Kartenoptionen (Layout, Kameradarstellung …) bleiben im Karten-Editor, weil sie zum Dashboard gehören.

## Kartenoptionen

Alle Optionen sind freiwillig und bis auf Kopfnamen und Presets auch im visuellen Editor einstellbar.

| Option | Standard | Bedeutung |
|---|---|---|
| `layout` | `tabs` | `tabs` = Reiter, `scroll` = alle Bereiche untereinander, `tablet` = Kamera, Druckauftrag und Druckköpfe immer links sichtbar, Reiter rechts (Tablets, Wandmonitore; unter ca. 900 px untereinander) |
| `layer_view` | `part` | Schichtansicht: `part` = auf das Teil vergrößert, `bed` = Draufsicht auf die ganze Platte mit geparkten Köpfen und Düsen-Marker. Auch direkt in der Schichtansicht umschaltbar (Raster-Knopf, merkt sich der Browser) |
| `bed_image` | – | eigenes Hintergrundbild für die Draufsicht, z. B. `/local/u1_oben.png` (Datei in `config/www`); ersetzt die gezeichnete Platte und die Köpfe |
| `bed_image_area` | `0, 0, 270, 270` | welche Druckerkoordinaten in mm das Bild abdeckt (x0, y0, x1, y1). Foto des ganzen Druckers: zwei Punkte ausmessen, z. B. `-40, -30, 310, 360` |
| `bed_image_opacity` / `bed_grid` | `1` / `false` | Deckkraft des Bildes, 10/50-mm-Raster darüber |
| `emergency_stop` | `show` | `show` = Button mit Rückfrage, `hold` = 1 s gedrückt halten (ohne Dialog), `hide` = kein Button in der Karte (die HA-Button-Entität bleibt) |
| `camera_direct` | `auto` | `auto` = Stream direkt vom Drucker (`camera_direct_url`, Standard `http://<Drucker>/webcam/?action=stream`): weniger Verzögerung, keine Last auf HA. Nicht auf https-Seiten (der Browser blockiert dort http-Streams); kommt binnen 4 s kein Bild (z. B. unterwegs), nimmt die Karte 10 min den HA-Proxy. `off` = immer über HA |
| `camera_direct_url` | – | eigene Adresse für den Direktstream |
| `camera_webrtc` | `auto` | paxx12 Extended Firmware: Kamera per WebRTC (weniger Verzögerung, viel weniger Daten als MJPEG). Die wenigen Signalisierungs-Nachrichten laufen über Home Assistant, das Video direkt zwischen Browser und Drucker – klappt zu Hause und per VPN; kommt in 8 s keine direkte Verbindung zustande, bleibt 10 min MJPEG. `off` = nur MJPEG |
| `camera_ha_stream` | `auto` | Unterwegs (keine direkte Verbindung, z. B. Nabu Casa): RTSP-Stream über Home Assistant statt MJPEG. Nur mit RTSP (paxx12). `off` = MJPEG |
| `camera_zoom_reset` | `60` | Sekunden ohne Bedienung, bis der Kamera-Zoom auf 1× zurückgeht; `0` = nie. Seite verlassen, App wechseln oder Karte wegscrollen setzt ihn immer zurück |
| `accent_color` | – | eigene Akzentfarbe für Knöpfe, Regler und Hervorhebungen (`[255, 152, 0]` oder `"#ff9800"`); leer = Hauptfarbe deines Designs. Auch für die Mini-Karte |
| `camera_wake` | `true` | Solange die Karte sichtbar ist und das Bild steht (kein Stream, eingefrorenes Bild), lässt sie die Integration einmal `camera.start_monitor` senden (höchstens alle 10 s) |
| `camera_overlay` | `true` | Fortschritt auf dem Kamerabild; der Druckerstatus steht immer oben links (`hide_overlay: true` schaltet es ebenfalls ab) |
| `state_accent` | `true` | Rahmen in der Theme-Farbe des Zustands (druckt, pausiert, Fehler, fertig) |
| `camera_height` | automatisch | Höhe des Kamerabilds in px. Leer = Seitenverhältnis des Bildes, höchstens `camera_max_height` |
| `camera_max_height` | `520` | Obergrenze bei automatischer Höhe in px |
| `camera` | eigene Kamera | Kamera-Entität. Leer = eigene Kamera der Integration (siehe [Kamera](funktionen.md#kamera)), sonst die der Moonraker-Integration |
| `camera_mode` | `auto` | `auto` = die Kamera-Entität entscheidet (Livestream oder Standbilder), `stream` = Stream erzwingen, `still` = Einzelbilder (spart WLAN) |
| `refresh` | `2` | Sekunden zwischen Einzelbildern (`still` und Rückfall) |
| `camera_fit` | `contain` | `contain`, `cover`, `fill` |
| `show` | alle | Bereiche: `stage layer job queue files toolheads climate mesh motion console system maintenance charts stats history timelapse` |
| `hide` | – | Bereiche ausblenden (Gegenstück zu `show`, nutzt der Editor) |
| `controls_lock` | `60` | Sperre für Temperatur- und Lüfterregler, Schnellwahl, Heizungsschalter und Referenzfahrt: `off`, Sekunden (`30`, `60`, `120`, `300`) bis zur automatischen Sperre nach der letzten Bedienung, oder `manual` (offen, bis man wieder sperrt). Im Druck fragt die Karte vor jeder Änderung einer Solltemperatur nach. Alt: `unlock_controls: true` = `off` |
| `timelapse_limit` | `8` | angezeigte Zeitraffer |
| `files_limit` | `12` | angezeigte Dateien |
| `nozzle_presets` / `bed_presets` | `[0,210,240,260]` / `[0,55,65,85]` | Schnellwahl-Temperaturen |
| `toolheads` | – | Kopfnamen, z. B. `- name: Links` (Material und Farbe kommen vom Drucker) |
| `network_tracker` | – | `device_tracker` für einen WLAN-Chip im Kopf |
| `prefix`, `camera`, `thumbnail`, `filaments_sensor`, `files_sensor` | automatisch | nur bei mehreren Druckern nötig |

> **Noch eine U1-Karte installiert?** Die Integration [kbaker827/ha-snapmaker-u1](https://github.com/kbaker827/ha-snapmaker-u1) bringt ebenfalls eine Karte `custom:snapmaker-u1-card` mit; wer zuerst lädt, bekommt den Namen. Diese Karte ist deshalb immer auch als `type: custom:snapmaker-u1-card-ironoxx` erreichbar, der Selbsttest weist darauf hin.

### Mini-Karte

```yaml
type: custom:snapmaker-u1-mini-card
navigation_path: /dashboard-drucker/0   # optional: beim Antippen dorthin, sonst Statusdialog
```

| Option | Standard | Bedeutung |
|---|---|---|
| `printer_name` | `U1` | Anzeigename |
| `navigation_path` | – | Ziel beim Antippen |
| `hide_filaments` | `false` | Filamentreihe ausblenden |
| `prefix` | automatisch | nur bei mehreren Druckern |

## Update

Ordner `custom_components/snapmaker_u1_card` ersetzen (oder in HACS aktualisieren) und Home Assistant neu starten. Einstellungen, Historie, Warteschlange, Wartungsstände, Spulenzuordnung und gesicherte Zeitraffer bleiben erhalten:

| Was | Wo |
|---|---|
| Einstellungen | Konfigurationseintrag (`.storage/core.config_entries`) |
| Historie, Warteschlange, Wartung, Spoolman-Zuordnung, offene Buchungen | `.storage/snapmaker_u1_card.<eintrag>.print_switches` |
| Vorschaubilder, Schichtansicht (Zwischenspeicher, wird neu erzeugt) | `.storage/snapmaker_u1_card/` |
| Sicherungen der Drucker-Konfiguration | `snapmaker_u1_backup/` |
| Sätze für Assist (bei jedem Start aktualisiert) | `custom_sentences/de/…` und `custom_sentences/en/…` |
| gesicherte Zeitraffer | `<Medien>/snapmaker_u1/` |

Nicht die Integration löschen und neu hinzufügen: Das legt einen neuen Eintrag an, Einstellungen und Historie gehören dann zum alten.

## Wie die Karte geladen wird

Eine Ressource legst du nicht selbst an; die Integration lädt die Karte auf zwei Wegen:

1. über die Startseite von Home Assistant (`add_extra_js_url`),
2. als Dashboard-Ressource `/local/snapmaker_u1_card/snapmaker-u1-card.js?v=…`, die die Integration anlegt, aktuell hält und mit der Integration wieder entfernt. Unter *Dashboards → Ressourcen* bitte stehen lassen.

Der zweite Weg ist nötig, weil Home Assistant Seiten schon ausliefert, bevor eigene Integrationen gestartet sind. Wer in diesem Fenster lädt (Tab oder App während eines Neustarts), sähe sonst „Custom element doesn't exist: snapmaker-u1-card“, bis er neu lädt. Gab es `/config/www` vorher nicht, greift der Weg erst nach einem weiteren Neustart.

## Moonraker-Integration (optional)

Seit 2.0 nicht mehr nötig: Die Karte bekommt alle Werte und Steuerungen von dieser Integration. Am besten verzichtest du auf die [Moonraker-Integration](https://github.com/marcolivierarsenault/moonraker-home-assistant) daneben: Sie fragt den Drucker ein zweites Mal ab und belastet ihn nur zusätzlich. Behältst du sie, nimmt die Karte bevorzugt die eigenen Werte und greift nur auf die Moonraker-Entitäten zurück, wenn diese fehlen. Bei mehreren Druckern `prefix` in der Karte setzen.
