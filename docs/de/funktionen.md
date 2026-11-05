# Funktionen im Detail

[← Zurück zum README](../../README.de.md)

**Inhalt:** [Wie die Filamentzuordnung funktioniert](#wie-die-filamentzuordnung-funktioniert) · [Werkzeugwechsel](#werkzeugwechsel) · [Strom, Kosten und Historie](#strom-kosten-und-historie) · [Live-Verbindung und Benachrichtigungen](#live-verbindung-und-benachrichtigungen) · [Bed Mesh, Flussrate, Top Cover und Kammerheizung](#bed-mesh-flussrate-top-cover-und-kammerheizung) · [Kamera](#kamera) · [Dateiverwaltung](#dateiverwaltung) · [Status-Licht (Blueprint)](#status-licht-blueprint) · [Temperaturverlauf](#temperaturverlauf) · [Leerlauf-Abschaltung](#leerlauf-abschaltung) · [Firmware und Selbsttest](#firmware-und-selbsttest) · [Statistik je Material](#statistik-je-material) · [Sprachsteuerung (Assist)](#sprachsteuerung-assist) · [Sicherung der Drucker-Konfiguration](#sicherung-der-drucker-konfiguration) · [Spulenverwaltung mit Spoolman](#spulenverwaltung-mit-spoolman) · [Zeitraffer](#zeitraffer) · [Schichtansicht](#schichtansicht) · [Druckermeldungen](#druckermeldungen)

## Wie die Filamentzuordnung funktioniert

Die Integration startet Drucke genauso wie Snapmaker Orca im LAN-Modus, über den Moonraker-Aufruf `server.files.start_local_print` mit `options.map_table`. Der Drucker setzt das in `SDCARD_PRINT_FILE_WITH_PARAMETERS … MAP_TABLE="[[0, 2], [1, 0]]"` um. Die Firmware prüft dabei wie gewohnt, ob der Drucker frei ist und die Düsen passen.

Belegt ist das aus Snapmakers offenem Quellcode:
[u1-klipper](https://github.com/Snapmaker/u1-klipper) (`klippy/extras/print_task_config.py`) und
[u1-moonraker](https://github.com/Snapmaker/u1-moonraker) (`components/snapmakercloud.py`, `components/klippy_apis.py`).

Der Vorschlag wählt je Filament der Datei einen geladenen Kopf in dieser Reihenfolge: gleiches Material, ähnlichste Farbe, noch frei. Ein leerer Kopf blockiert den Start. Ein abweichendes Material zeigt die Karte nur als Warnung an.

## Werkzeugwechsel

Die Firmware zählt jeden erfolgreichen Kopfwechsel dauerhaft pro Kopf (`switch_count` in `extruder` … `extruder3`, Quelle: `ExtruderSwitchRecorder` in u1-klipper `klippy/kinematics/extruder.py`). Ältere Firmware ohne diese Felder: Die beiden Sensoren sind dann *nicht verfügbar*, die Karte blendet die Zeilen aus.

Einen Zähler pro Druck hat die Firmware nicht. Die Integration merkt sich den Stand bei Druckbeginn und bildet die Differenz bei Druckende. Der Stand wird gespeichert und übersteht einen Neustart von Home Assistant während des Drucks. Mitgezählt wird jeder Wechsel im Druckzeitraum, also auch Aufnahmen für Kalibrierungen am Druckanfang. Läuft Home Assistant während eines ganzen Drucks nicht, fehlt dieser Druck.

Die Wartungsschwelle ist der Firmware-Standard von 25 100 Wechseln je Kopf. Ab 90 % färbt die Karte den Wert gelb. Zurücksetzen nach einer Wartung: `RESET_EXTRUDER_MAINTENANCE_COUNT` in der Konsole.

## Strom, Kosten und Historie

- **Verbrauch je Druck** ist die Differenz des Energiezählers zwischen Druckbeginn und -ende.
- **Stromkosten** werden laufend aufsummiert (Verbrauch seit der letzten Abfrage × Preis in diesem Moment). Dynamische Tarife rechnen so richtig.
- **Filamentkosten**: Gewicht je Material aus den Slicer-Daten der Datei × Preis je kg. Bei abgebrochenen Drucken wird das Gewicht im Verhältnis gefördertes/geplantes Filament gekürzt. Fehlt für ein verwendetes Material ein Preis, entfallen die Filamentkosten statt einer falschen Summe.
- **Gesamtkosten im Verlauf** (Kachel und Diagramm): Drucke, die die Integration erfasst hat, mit ihren echten Kosten (Filament + Strom). Ältere Drucke aus Moonraker, also vor der Installation, werden mit dem Filamentpreis geschätzt; die Kachel zeigt dann „≈“. Damit passen Summe und Material-Tabelle zusammen. *Strom* zählt nur gemessene Drucke.
- **Auto-Aus** greift nur nach *fertig* oder *abgebrochen*, nie nach einem Fehler, und erst wenn alle Düsen und das Bett unter der eingestellten Temperatur sind.
- Ist der Drucker aus, zeigt die Karte Einschalten, Dateien (bei Auto-Ein), Historie und Zeitraffer. Die Filamentzuordnung nutzt dann den Stand vor dem Ausschalten.

**Vorschaubilder** bekommen je nach Helligkeit des Teils einen passenden Grund: dunkle Teile (schwarzes Filament) einen hellen, sehr helle einen dunklen. Die Karte misst dazu die mittlere Helligkeit der deckenden Pixel; Bilder ohne Transparenz bleiben unverändert.

**Kosten vor dem Druck.** Der Startdialog zeigt „≈ 0,48 €“ und darunter die Aufteilung. Filament: Gewicht je Material aus den Slicer-Daten × Preis je kg (fehlt ein Preis, entfällt dieser Teil). Strom: geschätzte Druckzeit × mittlere Leistung aller bisherigen Drucke ab 10 min (Energie ÷ Dauer aus der Historie) × aktueller Strompreis. Vor dem ersten gemessenen Druck gibt es nur den Filamentteil.

## Live-Verbindung und Benachrichtigungen

Die Integration abonniert bei Moonraker `print_stats`, `toolhead`, `virtual_sdcard` und `exception_manager` (`printer.objects.subscribe`), seit 2.0 außerdem jede Heizung, jeden Lüfter, Sensor, jede LED, jeden Ausgang und jede MCU, die der Drucker auflistet (`/printer/objects/list`). Das sind die Werte, die die Karte zeigt; sie kommen innerhalb etwa einer Sekunde an. Die CPU-Temperatur des Druckerrechners kommt mit Moonrakers Prozessstatistik (`notify_proc_stat_update`). Moonraker schickt nur Änderungen, höchstens alle 250 ms. Statuswechsel und neue Meldungen lösen sofort einen Abgleich aus, ein Kopfwechsel aktualisiert die Karte direkt, und die Schichtansicht holt ihre Dateiposition aus dem Abo statt beim Drucker. Steht das Abo, fragt die Integration nur alle 30 s nach (sonst alle 10 s). Bricht die Verbindung ab, verbindet sie mit 5–60 s Abstand neu; bei ausgeschaltetem Drucker gar nicht.

| Anlass | Wann |
|---|---|
| Meldung vom Drucker | neue Firmware-Meldung, während gedruckt wird. Pausiert der Drucker deshalb, kommt nur die Pause-Meldung (mit dem Text) |
| Erste Schicht fertig | Wechsel von Schicht 1 auf 2. Wer erst mitten im Druck einsteigt (Neustart von HA), bekommt keine |
| Gleich fertig | Restzeit (siehe unten) unter der eingestellten Minutenzahl, einmal je Druck |
| Filament reicht nicht | beim Druckstart, wenn laut Spoolman eine Spule weniger Rest hat als die Datei auf diesem Kopf braucht |
| Spule läuft gleich leer | im Druck, wenn eine Spule laut Zeitprofil in weniger als 30 min leer ist. Mit Hinweis, ob die Firmware per **Auto-Nachfüllen** von einem Kopf mit gleichem Material (und gleicher Farbe, außer „Farbe ignorieren“ ist am Drucker an) weitermacht oder pausieren wird |
| Teil entnehmbar | nach einem fertigen Druck, sobald das Bett unter die eingestellte Temperatur (35 °C) gefallen ist |

**Knöpfe in der Benachrichtigung** (Companion-App): bei Meldungen während des Drucks *Pausieren* und *Licht*, bei Pause *Fortsetzen* und *Abbrechen …*. Abbrechen fragt mit einer zweiten Benachrichtigung nach („Ja, abbrechen“), ein versehentlicher Tipp bricht also nichts ab. Die Knöpfe wirken nur, solange der Zustand passt (Pausieren nur im Druck usw.).

**Restzeit.** Beim Druckstart lädt die Integration die Datei einmal vom Drucker. Slicer wie Orca schreiben ihre eigene Restzeit in die Datei (`M73 R<Minuten>`); die Integration liest sie je Dateiposition, Beschleunigung und Werkzeugwechsel sind damit schon enthalten. Diese Slicer-Zeit wird mit der gemessenen Geschwindigkeit skaliert – gemessen ab Beginn der ersten Schicht, die Startsequenz mit Leveling und Kalibrierung verfälscht sie also nicht. Bis genug gedruckt ist, tragen Geschwindigkeitsfaktor und Startdauer aus früheren Drucken die Schätzung. Während der Startsequenz: erwartete restliche Startzeit + Slicer-Zeit des Drucks. Dateien ohne `M73`: Zeitprofil aus den Fahrwegen (Strecke ÷ Vorschub), gewichtet zwischen Slicer-Gesamtzeit und gemessener Geschwindigkeit. Ergebnis als Sensoren *Restzeit* und *Fertig um*; Karte, „Gleich fertig“, Assist und die Fortschritts-Benachrichtigung nutzen sie. Historieneinträge speichern `prep_s` (Startdauer) und `speed_factor` (Ist ÷ Slicer-Zeit).

**Fortschritts-Benachrichtigung (Android).** Schalter *Fortschritts-Benachrichtigung (Android)* (auch im System-Reiter der Karte, standardmäßig aus). Android-Handys unter den Benachrichtigungszielen bekommen eine dauerhafte Benachrichtigung mit Fortschrittsbalken und Countdown bis zum erwarteten Ende. Der Countdown läuft auf dem Handy, die Restzeit kostet also keine Pushes. Updates nur bei einem neuen 10-%-Schritt, wenn sich das Ende um mehr als max(5 min, 10 %) verschiebt, und bei Pause/Fortsetzen; höchstens eins alle 3 min und 25 je Druck, dazu ein Tagesbudget je Handy (Option, Standard 150; die Companion App erlaubt über den Cloud-Dienst etwa 500 Pushes am Tag). Die Benachrichtigung startet nach der Startsequenz, nutzt einen stillen Kanal (`alert_once`, niedrige Wichtigkeit) und verschwindet am Ende. Fertig-, Fehler- und Pause-Meldungen sind vom Budget nicht betroffen. Attribute des Schalters: `sent_today`, `budget`, `targets`.

**Antippen und Bild.** Option *Beim Antippen öffnen* (`notify_click_url`): Ein Tipp auf eine Benachrichtigung der Integration öffnet diesen Pfad oder diese URL (z. B. `/dashboard-drucker/0`). Die „Druck fertig“-Meldung zeigt das Ergebnisfoto, die Fortschritts-Benachrichtigung aufgeklappt das Kamerabild (Option, standardmäßig an).

**Ergebnisfoto.** Mit eingestellter Kamera entsteht das Bild am Druckende, sobald der Kopf das Teil freigibt: Nach der letzten Extrusion liest die Integration bis zu 15 s die Kopfposition (`motion_report`) und löst aus, sobald der Kopf 25 mm außerhalb der Teile-Umrisse (`EXCLUDE_OBJECT_DEFINE`) ist oder das Bett schon 15 mm abgesenkt wurde. Das Innenraumlicht wird fürs Foto eingeschaltet und danach wieder aus, falls es aus war. Ohne Position oder Umriss: 2 s nach der letzten Extrusion; ohne Zeitprofil: in der letzten Schicht ab 99,5 %. Bei Abbruch oder Fehler entsteht das Bild in dem Moment. Es liegt unter `.storage/snapmaker_u1_card/thumbs/<Eintrag>/results/` und erscheint in der Historie neben dem Vorschaubild; Antippen vergrößert es in der Karte (Antippen oder Esc schließt). Gespeichert bleiben die Fotos der Drucke in der Historie.

## Bed Mesh, Flussrate, Top Cover und Kammerheizung

**Bed Mesh.** Die Karte zeigt die Messpunkte des in Klipper geladenen Höhenprofils (`bed_mesh.probed_matrix`) als Heatmap: rot über, blau unter null, die Druckervorderseite unten. Das Profil entsteht bei einem Druckstart mit Bettnivellierung; ohne Profil sagt die Karte das.

**Flussrate** ist Klippers Extrusionsfaktor (`M221`), 100 % = wie gesliced. Klipper behält den Wert, bis er geändert wird oder Klipper neu startet – nach einem Test also wieder auf 100 % stellen.

**Top Cover.** Die optionale Abdeckung ist in der Firmware der `purifier`. Ob eine angeschlossen ist, meldet der Drucker (`power_detected`); erst dann erscheinen Entitäten und Bereich. Den Kammermodus setzt die Firmware beim Druckstart nach Material und regelt die Lüfter während des Drucks nach; die Regler stellen Abluft- und Umluftlüfter von Hand (`SET_PURIFIER`). Den Modus kannst du auch in der Karte oder über die Auswahl-Entität wählen: *Leerlauf*, *Kammer kühlen* (Abluft, bis die Kammer unter dem Sollwert liegt), *Kammer vorheizen* und *Heiße Kammer* (Umluft hält die Wärme), daneben das Kammer-Soll (`SET_PURIFIER_MODE MODE=… DESIRE_TEMP=…`). Die Filter-Laufzeit zählt die Betriebsstunden des Umluftlüfters; der Wartungspunkt *Luftfilter wechseln* zählt diese echten Filterstunden statt Druckstunden. *Noch nicht an einem Drucker mit Abdeckung getestet – Rückmeldung willkommen (Diagnosedatei).*

**Kammerheizung.** Mit der paxx12 Extended Firmware ist eine BIQU Panda Breath (Stock-Firmware) oder eine Panda Breath mit DragonBreath-Firmware ein Klipper-`heater_generic` (`panda_breath` / `dragonbreath`). Die Integration findet sie in Klippers Objektliste; erst dann erscheinen die Entitäten (*Kammerheizung* Temperatur, *Kammerheizung Soll*, bei DragonBreath *Kammerheizung Filter*) und der Bereich im Tab Steuerung. Das Soll geht als `SET_HEATER_TEMPERATURE` an Klipper (0 = aus; Panda Breath 15–80 °C, DragonBreath bis 75 °C), der Slicer setzt es ohnehin mit `M141`/`M191`. paxx12 warnt: nie unbeaufsichtigt heizen, die Hauptplatine braucht zusätzliche Kühlung.

**Kammer warm.** Benachrichtigung *Kammer hat Solltemperatur erreicht* (Ereignis `chamber_ready`, standardmäßig aus): einmal, wenn die Kammerheizung ihr Soll erreicht oder der Kammersensor das Soll der Top Cover im Modus Vorheizen oder Heiß. Ein neues Soll schaltet sie wieder scharf. Der Temperaturverlauf zeigt die Kammerheizung mit ihrem Soll.

**Düse je Kopf.** Die Firmware speichert Durchmesser und Typ (Standard / High Flow) je Kopf (am Display beim Hotend-Wechsel gesetzt). Die Kopfdetails zeigen sie; der Druckdialog warnt, wenn ein Filament auf einen Kopf kommt, dessen Düse von der abweicht, für die die Datei gesliced ist (`nozzle_diameter_list` aus Snapmakers Moonraker).

## Kamera

Ab 1.5 hat die Integration eine eigene Kamera-Entität (*Kamera*) und findet selbst heraus, wie sie an ein Bild kommt (Attribut `mode`, auch im Selbsttest und in der Diagnose):

| `mode` | Wann | Bild |
|---|---|---|
| `live` | Moonraker meldet eine Webcam, deren Stream mit MJPEG antwortet (angepasste Firmware, z. B. paxx12 Extended). Meldet Moonraker eine WebRTC- oder Player-Seite (paxx12 2.x: `/webcam/webrtc`), wird der MJPEG-Stream daneben genutzt (`/webcam/stream.mjpg`) | Livestream, durchgereicht |
| `still` | nur eine Snapshot-Adresse funktioniert | Standbild jede Sekunde |
| `wake` | Stock-Firmware: kein Stream, nur `camera/monitor.jpg`, das sich erst nach `camera.start_monitor` ändert. Das Bild wird vor und nach einem Weckaufruf geholt und muss sich ändern | Standbild alle 1–2 s; die Kamera wird bei Bedarf geweckt (höchstens alle 10 s), solange jemand zuschaut |
| `none` | nichts gefunden | Entität nicht verfügbar; die Karte zeigt einen Hinweis statt einer schwarzen Fläche |

**RTSP.** Antwortet der Drucker auf `rtsp://<drucker>:8554/stream` (paxx12: *RTSP* in `/firmware-config/`, standardmäßig aus), bietet die Kamera-Entität das zusätzlich als Stream-Quelle an (Attribut `rtsp_url`, `supported_features` Stream): Home Assistant streamt dann selbst H.264 (Info-Dialog, Bildkarten, go2rtc/WebRTC). Zu Hause nutzt die Karte das eigene WebRTC des Druckers (siehe unten), unterwegs spielt sie diesen RTSP-Stream über Home Assistant ab.

**WebRTC in der Karte.** Mit paxx12s Kamera (`webrtc-camerastreamer`, Moonraker meldet `/webcam/webrtc`) zeigt die Karte das Livebild per WebRTC: weniger Verzögerung und viel weniger Daten als MJPEG. Der Drucker sendet keine CORS-Header, deshalb kann die Karte nicht direkt aus dem Browser mit ihm sprechen; die Integration leitet die drei kleinen Signalisierungs-Nachrichten weiter (`POST /api/snapmaker_u1_card/webrtc/<eintrag>`, nur an die Kamera, die Moonraker meldet). Das Video läuft dann direkt zwischen Browser und Drucker, zu Hause und per VPN. Bis zum ersten Bild (und wenn WebRTC in 8 s nicht zustande kommt, z. B. unterwegs ohne VPN) zeigt die Karte MJPEG; nach einem Fehlschlag bleibt sie 10 Minuten bei MJPEG. Kartenoption `camera_webrtc: off` schaltet es ab.

**Unterwegs (Nabu Casa, ohne VPN).** Einen direkten Weg zum Drucker gibt es dann nicht; mit eingeschaltetem RTSP (paxx12, `rtsp: true`) spielt die Karte den RTSP-Stream über das eigene Streaming von Home Assistant ab (`ha-camera-stream`: WebRTC über HA, mit den Vermittlungsservern von Nabu Casa, sonst HLS). H.264 braucht viel weniger Daten als MJPEG über den HA-Proxy, das Bild bleibt flüssig. Bei Nabu Casa versucht die Karte das direkte WebRTC gar nicht erst. Kommt in 15 s kein Bild, gilt 10 Minuten MJPEG. Ohne RTSP (Stock-Firmware) ändert sich nichts. Kartenoption `camera_ha_stream: off` schaltet es ab.

**Zweite Kamera.** Eine zweite Webcam (paxx12: USB-Kamera unter `/webcam2/`, RTSP-Port 8555) bekommt eine eigene Entität *Kamera 2*, sobald sie gefunden wird; die Karte zeigt dann einen Umschalter auf dem Bild. Den Display-Spiegel von paxx12 meldet Moonraker ebenfalls als Webcam, er wird aber nie als Kamera genommen (siehe unten).

**Druckerdisplay.** Die paxx12-Firmware spiegelt den Touchscreen unter `/screen/`. Die Integration erkennt ihn getrennt von den Kameras (Displaygröße aus dem Bild, Diagnose: `screen`), die Karte zeigt ihn im eigenen Reiter *Display*: Das Bild kommt frisch über Home Assistant (alle 0,7 s, direkt nach einer Berührung alle 0,2 s), klappt also auch über https und Nabu Casa. Admins können das Display bedienen: Hand antippen, dann gehen Tippen und Wischen auf dem Bild an den Touchscreen. Nach der Sperrzeit der Regler ohne Eingabe schaltet sich die Bedienung selbst ab (`controls_lock`; `manual` = bis zum Ausschalten, `off` = 60 s). Die Integration nimmt Berührungen nur von Admins an, nur innerhalb des Displays, nur für den eingerichteten Drucker und höchstens etwa 20 pro Sekunde. Mit `display_camera: true` ist das Display zusätzlich eine weitere Stufe des Kamera-Umschalters im Kamerabild (Druckerkamera → USB-Kamera → Display), mit demselben Hand-Knopf; `display_tab: false` (oder `hide: [display]`) blendet den Reiter aus. Ohne Spiegel ändert sich nichts.

Die Erkennung läuft, wenn der Drucker online kommt, wenn Bilder wiederholt ausbleiben, und alle 5 Minuten, solange nichts (oder nur die Stock-Kamera) gefunden wurde. Fällt der Livestream aus, wechselt die Kamera auf Standbilder und versucht den Stream nach 5 Minuten erneut – ein Firmwarewechsel braucht also keine Einstellung. Die Karte nutzt diese Entität, solange `camera` nicht gesetzt ist; Benachrichtigungsbild und Ergebnisfoto nutzen sie, solange in den Integrationsoptionen keine Kamera gewählt ist.

## Dateiverwaltung

Über der Dateiliste: Suche (über **alle** Dateien auf dem Drucker, nicht nur die neuesten), Sortierung (neueste, Name, Druckzeit) und Ordner-Chips. Ältere Treffer erscheinen als Liste; Antippen lädt Metadaten und Vorschau nach und öffnet den Druckdialog. Im Druckdialog: *Herunterladen* (der G-Code über Home Assistant, klappt auch unterwegs), *Umbenennen / verschieben* (Unterordner mit `/`, werden angelegt) und *Löschen*. Beides ist gesperrt, solange die Datei gedruckt wird oder in der Warteschlange steht. Dienste: `file_details`, `move_file`, `delete_file`.

**Slicer-Einstellungen.** Der Druckdialog zeigt, womit die Datei geslict wurde: Profil, Schichthöhe (erste Schicht), Wände/obere/untere Schichten, Infill und Muster, Stützen, Brim, Reinigungsturm, Naht, Plattentyp, Geschwindigkeiten sowie Düsen- und Betttemperatur je benutztem Filament (erste Schicht in Klammern). Die Integration liest dafür einmal je Dateiversion den Einstellungsblock am Ende des G-Codes (die letzten 256 KB, Schlüssel von Orca/Snapmaker Orca und PrusaSlicer). Dienst `file_settings` (`path`). Welche Platte auf dem Bett liegt, meldet der Drucker nicht – deshalb gibt es keine Platten-Warnung.

## Status-Licht (Blueprint)

Die Integration legt den Blueprint *Snapmaker U1 – status light* unter `config/blueprints/automation/snapmaker_u1_card/` an. Unter *Einstellungen → Automationen → Blueprints* daraus eine Automation erstellen: den Moonraker-Sensor *Aktueller Druckstatus* und eine oder mehrere Lampen wählen (WLED, LED-Streifen, jede Farblampe). Farben für druckt (optional mit WLED-Effekt wie *Breathe*), Pause, Fehler/Abbruch, fertig (für eine einstellbare Zeit) und bereit (aus, eine Farbe oder unverändert). Ein Update ersetzt die Datei nur, solange sie unverändert ist; sobald du sie änderst, bleibt sie deine. Dasselbe gilt für die Assist-Satzdateien in `config/custom_sentences/`.

## Temperaturverlauf

Im Reiter *Steuerung*: Ist- und Solltemperatur der aktiven Köpfe und des Betts der letzten 20 Minuten. Die Daten speichert Moonraker ohnehin (`/server/temperature_store`); die Karte holt sie alle 10 s über die Integration, nur solange der Reiter sichtbar ist. Außerdem zu sehen: die CPU-Temperatur des Rechners im Drucker (Moonraker sendet sie jede Sekunde, die Integration zeichnet sie auf), Innenraumluft und die Schrittmotortreiber X/Y (nur bei eingeschalteten Motoren; sonst meldet Klipper keine Treibertemperatur). Ein Tipp auf einen Eintrag der Legende blendet die Linie aus oder ein; die Wahl merkt sich der Browser.

## Leerlauf-Abschaltung

Option *Ausschalten nach Leerlauf* (Stunden, 0 = aus): Läuft kein Druck, ist keine Heizung an (auch kein Vorheizen am Display) und ist das länger her als eingestellt, fährt die Integration den Drucker sauber herunter und schaltet die Steckdose aus. Die Firmware selbst kennt nur `idle_timeout` (Heizung und Motoren aus nach 10 min), schaltet aber nie ab.

## Firmware und Selbsttest

- **Update-Entität „Firmware“**: installiert laut Drucker (`/machine/system_info`), neueste aus Snapmakers Release-Commits der Firmware-Quellen auf GitHub (`Snapmaker/u1-moonraker`, `Snapmaker/u1-klipper`), einmal am Tag. Installiert wird weiter am Drucker (Display oder Snapmaker-App); die Entität meldet nur. Hinweis: Snapmaker kann die Veröffentlichung auf GitHub ändern; dann bleibt „neueste“ beim letzten bekannten Stand.
- **Selbsttest** (*System*-Reiter oder Dienst `self_test`): Drucker und Klipper, Live-Verbindung, Firmware, freier Speicher am Drucker (Warnung unter 500 MiB), Moonraker-Integration, Kamera (holt ein Bild), Netzschalter/Energie/Preis-Entitäten, Benachrichtigungsdienste, Spoolman, Assist-Sätze, Medienordner. ✓ in Ordnung, ! Hinweis, ✗ Fehler.

## Statistik je Material

Unter den Monatsdiagrammen: Drucke, Verbrauch, Kosten und Erfolgsquote je Material sowie die meistgenutzten Farben – aus Moonrakers Druckhistorie, also rückwirkend. Abgebrochene Drucke zählen anteilig.

## Sprachsteuerung (Assist)

Die Integration meldet drei Intents an und legt die Sätze unter `/config/custom_sentences/de/snapmaker_u1_card.yaml` (bzw. `en/`) ab:

- „Wie weit ist der Drucker?“, „Wie lange braucht der 3D-Drucker noch?“, „Was macht der Drucker?“, „Status vom Drucker“ → z. B. „benchy ist bei 40 Prozent, Schicht 121 von 300, noch etwa 6 Minuten.“
- „Pausiere den Drucker“, „Druck pausieren“
- „Drucker fortsetzen“, „Setze den Druck fort“, „Druck weiter“

Englisch: „How far is the printer?“, „Pause the printer“, „Resume the print“. Die Dateien aktualisiert die Integration bei jedem Start. Wer eigene Sätze pflegen will, löscht die erste Zeile (`# snapmaker_u1_card: automatisch erzeugt`), dann bleibt die Datei unberührt. Abbrechen per Sprache gibt es absichtlich nicht.

## Sicherung der Drucker-Konfiguration

Einmal am Tag, nie während eines Drucks, holt die Integration alle Dateien aus Moonrakers Wurzel `config` (printer.cfg, moonraker.conf, Makros …) nach `/config/snapmaker_u1_backup/<Drucker>/<Datum_Uhrzeit>/`. Ein neuer Stand entsteht nur, wenn sich etwas geändert hat; die letzten 5 bleiben. Logs, Datenbanken und Dateien über 2 MB werden übersprungen. Weil die Sicherungen im HA-Konfigordner liegen, sind sie auch in jedem Home-Assistant-Backup. Der letzte Stand steht in der Karte unter *System → Wartung*, mit Knopf zum sofortigen Sichern.

## Spulenverwaltung mit Spoolman

Optional. Ohne Spoolman-Adresse erscheint in Karte und Integration nichts davon.

**Bestand.** Der Reiter *Spoolman* (nur mit eingerichtetem Spoolman) zeigt alle aktiven Spulen: Farbe, Hersteller, Material, Ort, in welchem Kopf sie steckt und das Restgewicht als Balken (unter der Warnschwelle orange). Oben Anzahl, verbleibendes Filament in kg und dessen Wert (aus den Spulenpreisen). Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`.

**Neue Spule.** Aus dem Reiter *Spoolman* (*Neue Spule*) oder aus der Spulenauswahl eines Kopfs (*Neue Spule anlegen*, vorausgefüllt mit Material, Hersteller und Farbe des Kopfs, vom RFID-Tag falls vorhanden). Beim Tippen in *Filament suchen* erscheinen Treffer aus deinen Spoolman-Filamenten und aus dem Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (mehrere tausend Filamente bekannter Hersteller, nur 1,75 mm); die Felder Hersteller und Material schlagen bekannte Namen vor. Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule:
- ein eigenes Filament wird so genommen, wie es ist,
- ein Katalog-Eintrag wird einmal in Spoolman übernommen (Hersteller bei Bedarf angelegt, mit Farbe, Dichte und Temperaturen) und für die nächste Spule wiederverwendet.

Ohne Treffer werden Hersteller und Filament wiederverwendet, wenn es sie schon gibt (gleicher Name, Material und Farbe), sonst angelegt (Dichte nach Material, 1,75 mm). Ort und Preis sind optional; im Reiter *Spoolman* wählst du den Kopf im Formular oder keinen. Die Spulenwahl je Kopf bleibt unter den Druckköpfen. Mit SpoolLink wird der Kopf per `SET_SPOOL_ID` gesetzt. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang; sonst werden nur deine eigenen Filamente vorgeschlagen.

Dienst: `snapmaker_u1_card.create_spool` (`slot`, `material`, `vendor`, `name`, `color`, `weight`, `spool_weight`, `price`, `remaining`, `location`, `filament_id` oder `external_id`), liefert `spool_id`.

**Zuordnung Spule → Kopf.** Moonraker kennt für Spoolman nur *eine* aktive Spule; bei vier Köpfen übernimmt das die Integration selbst. Je geladenem Kopf wird eine aktive (nicht archivierte) Spule gesucht:

1. gleiches Material (`PLA-CF` passt zu `PLA`),
2. ähnliche Farbe (Spule ohne Farbangabe: nur Material). Weicht die Farbe deutlich ab, wird **nichts** zugeordnet. Eine falsche Spule wäre schlimmer, weil von ihr abgebucht würde,
3. Unterart im Namen (z. B. „Silk“), gleicher Hersteller,
4. angebrochene, zuletzt benutzte Spule vor neuer.

Jede Spule wird höchstens einem Kopf zugeordnet. In der Karte tippst du auf die Spulenzeile eines Kopfes und wählst „Automatisch“, „Keine Spule“ oder eine bestimmte Spule. Die Wahl einer bestimmten Spule lädt auch ihr Filament in den Drucker: Material (Unterart wie Matte oder Silk aus Material oder Spulenname), Hersteller und Farbe werden in den Slot des Kopfes geschrieben (`SET_PRINT_FILAMENT_CONFIG`), damit Display, Karte und Filamentzuordnung das richtige Filament zeigen. Nicht bei offiziellen Spulen mit RFID-Tag (der Tag gilt) und nicht während eines Drucks. Eine manuelle Wahl bleibt bestehen, bis in dem Kopf ein anderes Filament erkannt wird (Material, Farbe oder Hersteller ändern sich) oder die Spule in Spoolman archiviert wird.

**Abbuchen.** Nach jedem Druck bucht die Integration je Kopf ab: Gewicht laut Slicer je Filament, über die Zuordnungstabelle des Drucks (`print_task_config.extruder_map_table`) auf die Köpfe verteilt; bei Abbruch anteilig nach tatsächlich geförderter Länge. Ist Spoolman gerade nicht erreichbar, wird die Buchung gespeichert und nachgeholt, auch über einen Neustart von Home Assistant hinweg. Die Historie zeigt je Spule das Restgewicht vor und nach dem Druck (`#5 550 g → 460 g`; ⏳ = noch nicht gebucht).

**paxx12 Extended Firmware mit Spoolman (SpoolLink).** Ist Spoolman in `/firmware-config/` eingeschaltet, bucht Moonraker den Verbrauch selbst während des Drucks und der Drucker merkt sich die Spule je Kopf (`print_task_config.filament_spool_id`). Die Integration erkennt beides automatisch:

- Sie **bucht dann nicht ab** (kein doppeltes Abbuchen, egal wie *Verbrauch abbuchen* steht). Der Selbsttest sagt, wer abbucht.
- Die Spule je Kopf kommt vom Drucker; die Spulenwahl in der Karte schickt `SET_SPOOL_ID CHANNEL=<kopf> SPOOL_ID=<id>` an den Drucker, der das Filament der Spule selbst übernimmt. „Automatisch“ gibt es dann nicht.
- Die Historie zeigt trotzdem vorher → nachher, nach dem Druck aus Spoolman gelesen.

Dasselbe gilt für jeden anderen `[spoolman]`-Abschnitt in Moonrakers Konfiguration.

**Entladen und neu einlegen.** Ohne RFID-Tag vergisst der Drucker beim Entladen die Spule (mit SpoolLink setzt er `filament_spool_id` zurück). Wird der Kopf wieder beladen, bietet er seine vorherige Spule an: „Wieder #5 …?“ – ein Tipp übernimmt sie (mit SpoolLink per `SET_SPOOL_ID`). Bis dahin wird nichts gebucht und für diesen Kopf keine andere Spule geraten. Option *Letzte Spule nach dem Neu-Einlegen* (Abschnitt Spoolman): vorschlagen (Standard), automatisch setzen (nicht im Druck; falsche Spule, wenn du eine andere einlegst und das Umstellen vergisst) oder aus.

**Spule wiegen.** In den Kopfdetails (mit zugeordneter Spule) eintragen, was die Waage zeigt: mit Leerspule (deren Gewicht kommt aus Spoolman: Spule, Filament oder Hersteller *Leerspulengewicht*) oder nur das Filament. Die Integration setzt das Restgewicht in Spoolman. Dienst `weigh_spool` (`slot` oder `spool_id`, `weight`, `gross`). Die Oberfläche von Spoolman brauchst du damit nur noch für Details zu Herstellern und Filamenten.

Grenzen: Wechselt die Firmware mitten im Druck automatisch auf einen anderen Kopf (Auto-Nachfüllen bei leerer Spule), wird der gesamte Verbrauch dem zuletzt gemeldeten Kopf zugerechnet.

Dienst zum Zuordnen, z. B. für Automationen:

```yaml
action: snapmaker_u1_card.set_spool
data:
  slot: 2        # Kopf 1–4
  spool_id: 12   # 0 = keine Spule; weglassen = wieder automatisch
```

Die Spule je Kopf steht auch an `sensor.…_slot_1` … `_slot_4` (Attribute `spool`, `spool_remaining`), z. B. für eine Benachrichtigung bei wenig Restfilament.

## Zeitraffer

Die Stock-Firmware legt Zeitraffer im Moonraker-Ordner `camera` ab (`Name_JJJJMMTThhmmss.mp4` mit `_cover.jpg`). Die Integration durchsucht alle Ordner außer Konfiguration und Logs, findet also auch Fluidd-Zeitraffer (`timelapse`). Abgespielt wird über einen angemeldeten Proxy der Integration mit kurzlebig signierten Links. Er liefert nur Dateien aus der Liste aus, nie beliebige Pfade vom Drucker.

**Sichern.** Mit *Zeitraffer sichern* kopiert die Integration jedes neue Video samt Vorschaubild nach `<Medien>/snapmaker_u1/` (im Medienbrowser unter „Lokale Medien“, in der Karte unter „Gesichert in Medien“, abspielbar auch bei ausgeschaltetem Drucker). Während eines Drucks wird nicht kopiert. Damit der Ordner nicht vollläuft, bleiben standardmäßig die neuesten 50 Videos (Option *Im Medienordner behalten*), auf Wunsch zusätzlich eine Altersgrenze in Tagen. Entfernte Sicherungen werden nicht erneut geladen.

**Auf dem Drucker aufräumen.** Moonraker gibt den Ordner `camera` nur lesend frei; löschen kann nur Snapmakers interner Kameradienst (`camera.delete_timelapse_instance`), dessen Parameter nicht dokumentiert sind. Die Integration löscht deshalb nur Videos, die vollständig gesichert sind, sichert vorher immer alles, ermittelt die Parameterform beim ersten Mal und merkt sie sich. Lehnt der Dienst alle Formen ab, bleibt alles stehen und die Karte zeigt „Löschen auf dem Drucker wird von der Firmware nicht unterstützt“.

## Schichtansicht

**Schieberegler.** *Schicht* blättert durch die ganze Datei: frühere Schichten erscheinen gedruckt, spätere als folgend, die Kopfzeile sagt, welche Schicht gerade gedruckt wird; *Live* springt zurück. *Fortschritt* spielt die Schicht in Dateireihenfolge ab (in der Bettansicht mit Düse); ganz nach rechts geschoben gilt wieder die Live-Position.

**G-Code-Vorschau vor dem Druck.** Im Druckdialog zeigt *G-Code-Vorschau* jede Datei Schicht für Schicht mit denselben zwei Reglern. Beim ersten Öffnen lädt die Integration die Datei im Hintergrund und zerlegt sie (bei großen Dateien einige Sekunden); die letzten drei Vorschauen bleiben gespeichert, die Datei des laufenden Drucks wird nicht erneut geladen. Die Farben folgen der Zuordnung im Dialog: Filament → Kopf → dort geladene Spule. API: `/api/snapmaker_u1_card/layers/<entry>?file=<pfad>&layer=<n>`.

**Objekte ausschließen.** Sind in der Datei Objekte definiert (`EXCLUDE_OBJECT_DEFINE`, Orca: „Objekte beschriften“ an), zeichnet die Schichtansicht ihre Umrisse und listet sie darunter. Antippen fragt nach und ruft dann `snapmaker_u1_card.exclude_object` auf (Klipper `EXCLUDE_OBJECT NAME=…`): Der Drucker lässt das Objekt ab sofort aus. Das gerade gedruckte Objekt ist hervorgehoben, ausgeschlossene sind blass. Das letzte verbleibende Objekt lässt sich nicht ausschließen (dafür den Druck abbrechen).

Sobald die Karte die Schichtansicht während eines Drucks zum ersten Mal anfragt, lädt die Integration die Datei einmal vom Drucker und zerlegt sie in Schichten (`;LAYER_CHANGE` bzw. `SET_PRINT_STATS_INFO`). Die Karte holt nur die aktuelle Schicht (`/api/snapmaker_u1_card/layers/…`, angemeldet) und alle 5 s die Dateiposition (`virtual_sdcard.file_position`, aus dem Live-Abo, ohne Anfrage beim Drucker): was davor liegt, ist gedruckt. Farbe je Filament: Kopf laut Zuordnung → Farbe der dort geladenen Spule, sonst die Farbe aus der Datei. Bögen (G2/G3) werden in kurze Stücke zerlegt, Punkte näher als 0,35 mm zusammengefasst. Bei großen Dateien dauert die Vorbereitung einige Sekunden.

## Druckermeldungen

Die U1-Firmware meldet Fehler strukturiert (Modul, Kopf, Code). Die Integration übersetzt bekannte Codes, z. B. „Filament leer (Kopf 2)“, „Vorladen: kein Filament erkannt“, „Spaghetti erkannt“, „PEI-Platte liegt nicht richtig“, und hängt einen Hinweis an. Unbekannte Codes erscheinen mit der Rohmeldung der Firmware. Die Meldungen stehen oben in der Karte, in Benachrichtigungen bei Fehler/Pause und in der Historie.
