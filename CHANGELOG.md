# Changelog

Each `## x.y.z` section becomes the text of the GitHub release, which HACS shows
in the update dialog. Newest first. After updating: restart Home Assistant and
reload the dashboard (the card shows a hint if the browser still has the old one).

## 1.6.0b2

**Beta** – only offered by HACS with "show beta versions" enabled. Contains everything from 1.6.0b1 below.

**Fixed**
- Spoolman: choosing a spool for a head only assigned it for usage booking; the head kept showing what the printer had (stock firmware: "PLA Generic" for every head without RFID tag). Choosing a specific spool now also loads its filament into the printer: material, sub type (Matte, Silk, … from the material or the spool name), vendor and colour. Not for official RFID spools and not during a print. Spools you already assigned: pick them once more.
- Picking a head failed with "unable to parse =0": the command is now sent as `T<n> A0` (Klipper's classic G-code syntax).

---
**Deutsch**
- Behoben: Spoolman – die Wahl einer Spule ordnete sie nur fürs Abbuchen zu; der Kopf zeigte weiter, was im Drucker stand (Stock-Firmware: „PLA Generic“ bei jedem Kopf ohne RFID-Tag). Die Wahl einer bestimmten Spule lädt jetzt auch ihr Filament in den Drucker: Material, Unterart (Matte, Silk … aus Material oder Spulenname), Hersteller und Farbe. Nicht bei offiziellen RFID-Spulen und nicht während eines Drucks. Bereits zugeordnete Spulen einmal neu wählen.
- Behoben: Kopf aufnehmen scheiterte mit „unable to parse =0“; der Befehl geht jetzt als `T<n> A0` raus (klassische G-Code-Schreibweise von Klipper).

## 1.6.0b1

**Beta** – only offered by HACS with "show beta versions" enabled for this repository. Feedback welcome, especially from top cover owners (diagnostics file).

**New**
- **Flow** (M221) as a slider next to the speed in the control tab and as entity `number.…_flow`, changeable during a print.
- **Bed mesh**: heatmap of the probed points in the control tab (red above, blue below zero, front at the bottom) with spread, lowest and highest point; sensor *Bed mesh spread* with the points as attributes.
- **G-code console** in the control tab, showing the printer's answers (arrow keys recall earlier commands). New service `send_gcode` with response. During a print only tuning commands are accepted (temperatures, fans, speed, flow, Z offset, pressure advance, light, top cover, queries); anything that moves or changes heads is refused until the print is over.
- **Pick and park heads** from the head details, and service `tool_change`. Uses the firmware's own commands, locked during a print. The attribute `head_states` shows which head is on the carriage.
- **Top cover** (optional accessory): chamber mode, exhaust and circulation fan, circulation fan speed and filter runtime. The entities and the panel only appear once the printer reports a plugged-in cover. Not yet tested on a printer with a cover – a diagnostics file from an owner would help.
- Diagnostics include flow, bed mesh, head states and the raw top cover status.

Card sections `mesh` and `console` are new; if you list sections with `show:`, add them there.

---
**Deutsch**
- Neu: **Flussrate** (M221) als Regler neben der Geschwindigkeit im Tab Steuerung und als Entität `number.…_flussrate`, auch während des Drucks änderbar.
- Neu: **Bed Mesh** als Heatmap der Messpunkte im Tab Steuerung (rot über, blau unter null, vorne unten) mit Spanne, tiefstem und höchstem Punkt; Sensor *Bettnivellierung Spanne* mit den Punkten als Attribute.
- Neu: **G-Code-Konsole** im Tab Steuerung mit den Antworten des Druckers (Pfeiltasten holen frühere Befehle zurück). Neuer Dienst `send_gcode` mit Antwort. Während eines Drucks nur Feineinstellungen (Temperaturen, Lüfter, Geschwindigkeit, Flussrate, Z-Versatz, Pressure Advance, Licht, Top Cover, Abfragen); alles, was fährt oder Köpfe wechselt, wird bis Druckende abgelehnt.
- Neu: **Köpfe aufnehmen und ablegen** in den Kopfdetails und per Dienst `tool_change`. Nutzt die Befehle der Firmware, während eines Drucks gesperrt. Das Attribut `head_states` zeigt, welcher Kopf auf dem Schlitten ist.
- Neu: **Top Cover** (optionales Zubehör): Kammermodus, Abluft- und Umluftlüfter, Drehzahl und Filter-Laufzeit. Entitäten und Bereich erscheinen erst, wenn der Drucker eine angeschlossene Abdeckung meldet. Noch nicht an einem Drucker mit Abdeckung getestet – eine Diagnosedatei von Besitzern hilft.
- Diagnose enthält Flussrate, Bed Mesh, Kopfzustände und den Rohstatus der Top Cover.

Die Kartenbereiche `mesh` und `console` sind neu; wer Bereiche per `show:` aufzählt, ergänzt sie dort.

## 1.5.2

**New**
- Notifications: new option *Open when tapped* (`notify_click_url`) – tapping a notification of the integration (also the progress notification) opens this dashboard, e.g. `/dashboard-printer/0`.
- Progress notification: shows the camera image when expanded (option *Progress notification: camera image*, on by default; refreshed with each progress update, no extra pushes).

**Fixed**
- The "print finished" notification attached a live camera image taken when the print already counted as finished – the bed was lowered by then. It now shows the result photo (taken once the head has left the part) and waits up to 20 s for it.

---
**Deutsch**
- Neu: Option *Beim Antippen öffnen* (`notify_click_url`) – ein Tipp auf eine Benachrichtigung der Integration (auch die Fortschritts-Benachrichtigung) öffnet dieses Dashboard, z. B. `/dashboard-drucker/0`.
- Neu: Die Fortschritts-Benachrichtigung zeigt aufgeklappt das Kamerabild (Option *Fortschritts-Benachrichtigung: Kamerabild*, standardmäßig an; aktualisiert mit jedem Fortschritts-Update, keine zusätzlichen Pushes).
- Behoben: Die „Druck fertig“-Meldung hängte ein Live-Bild an, das erst entstand, als der Druck schon als fertig galt – da war das Bett bereits abgesenkt. Jetzt kommt das Ergebnisfoto (aufgenommen, sobald der Kopf vom Teil weg ist); die Meldung wartet bis zu 20 s darauf.

## 1.5.1

**Fixed**
- Camera: a live stream could be detected as "still images" when its first frame took longer than 3 s (camera starting up, busy WiFi), and it then stayed on still images for a day. The detection now waits up to 8 s, tries twice, and in still mode checks the stream again every 5 minutes. If the stream check fails, the self test and the camera attribute `stream_error` say why.

---
**Deutsch**
- Behoben: Kamera – ein Livestream konnte als „Standbilder“ erkannt werden, wenn sein erstes Bild länger als 3 s brauchte (Kamera startet, WLAN ausgelastet), und blieb dann einen Tag bei Standbildern. Die Erkennung wartet jetzt bis zu 8 s, versucht es zweimal und prüft den Stream im Standbild-Modus alle 5 Minuten erneut. Scheitert die Prüfung, nennen Selbsttest und das Kamera-Attribut `stream_error` den Grund.

## 1.5.0

Same as the beta 1.5.0b1, now for everyone. Coming from an older version: also see 1.4.0–1.4.4 below (remaining time, progress notification, exclude objects, top view, and the fix for the remaining time shown 60× too high).

**New**
- Own camera entity that works with stock and modified firmware alike. The integration finds out by itself how to get an image: live MJPEG stream (e.g. paxx12 Extended firmware), snapshot images, or the stock camera, which it wakes with `camera.start_monitor` as needed. Shown as attribute `mode` (`live` / `still` / `wake` / `none`), in the self test and the diagnostics. A failing stream falls back to still images and is retried after 5 minutes.
- The card uses this camera automatically (`camera_mode: auto`, new default); notification images and the result photo use it when no camera is set in the options. Without any camera the card shows a short hint instead of a black area.

**Fixed**
- `monitor.jpg` of the stock firmware can never show up as a timelapse preview.

---
**Deutsch**
- Neu: Eigene Kamera-Entität, die mit Stock- und angepasster Firmware funktioniert. Die Integration erkennt selbst, wie sie an ein Bild kommt: MJPEG-Livestream (z. B. paxx12 Extended Firmware), Snapshot-Bilder oder die Stock-Kamera, die sie bei Bedarf per `camera.start_monitor` weckt. Sichtbar als Attribut `mode` (`live` / `still` / `wake` / `none`), im Selbsttest und in der Diagnose. Fällt der Stream aus, gibt es Standbilder, nach 5 Minuten neuer Versuch.
- Neu: Die Karte nutzt diese Kamera automatisch (`camera_mode: auto`, neuer Standard); Benachrichtigungsbild und Ergebnisfoto nutzen sie, wenn in den Optionen keine Kamera gewählt ist. Ganz ohne Kamera zeigt die Karte einen kurzen Hinweis statt einer schwarzen Fläche.
- Behoben: `monitor.jpg` der Stock-Firmware kann nicht mehr als Zeitraffer-Vorschau auftauchen.

## 1.5.0b1

Beta – only offered with "show beta versions" in HACS.

**New**
- Own camera entity that works with stock and modified firmware alike. The integration finds out by itself how to get an image: live MJPEG stream (e.g. paxx12 Extended firmware), snapshot images, or the stock camera, which it wakes with `camera.start_monitor` as needed. Shown as attribute `mode` (`live` / `still` / `wake` / `none`), in the self test and the diagnostics. A failing stream falls back to still images and is retried after 5 minutes.
- The card uses this camera automatically (`camera_mode: auto`, new default); notification images and the result photo use it when no camera is set in the options. Without any camera the card shows a short hint instead of a black area.

**Fixed**
- `monitor.jpg` of the stock firmware can never show up as a timelapse preview.

---
**Deutsch**
- Neu: Eigene Kamera-Entität, die mit Stock- und angepasster Firmware funktioniert. Die Integration erkennt selbst, wie sie an ein Bild kommt: MJPEG-Livestream (z. B. paxx12 Extended Firmware), Snapshot-Bilder oder die Stock-Kamera, die sie bei Bedarf per `camera.start_monitor` weckt. Sichtbar als Attribut `mode` (`live` / `still` / `wake` / `none`), im Selbsttest und in der Diagnose. Fällt der Stream aus, gibt es Standbilder, nach 5 Minuten neuer Versuch.
- Neu: Die Karte nutzt diese Kamera automatisch (`camera_mode: auto`, neuer Standard); Benachrichtigungsbild und Ergebnisfoto nutzen sie, wenn in den Optionen keine Kamera gewählt ist. Ganz ohne Kamera zeigt die Karte einen kurzen Hinweis statt einer schwarzen Fläche.
- Behoben: `monitor.jpg` der Stock-Firmware kann nicht mehr als Zeitraffer-Vorschau auftauchen.

## 1.4.4

**Fixed**
- Remaining time in the card was 60 times too high when the integration's own *Time remaining* sensor was used (e.g. "80 h" instead of 80 min). The card now reads the unit of every duration sensor (h, min, s), so a display unit changed by the user is handled too. The finish time and the calculation itself were not affected.

---
**Deutsch**
- Behoben: Die Restzeit in der Karte war mit dem eigenen Sensor *Restzeit* 60-mal zu hoch (z. B. „80 h“ statt 80 min). Die Karte liest jetzt die Einheit jedes Zeit-Sensors (h, min, s), auch wenn die Anzeigeeinheit geändert wurde. „Fertig um“ und die Berechnung selbst waren nicht betroffen.

## 1.4.3

**New**
- Top view: the nozzle moves smoothly along the paths of the current layer, with a gantry bar across the plate. The printer reports its position every few seconds; the card plays the way in between. Turned off with "reduce motion" in the system settings.
- Own background image for the top view: `bed_image` (e.g. `/local/u1_top.png`) with `bed_image_area` (printer coordinates the image covers in mm, default the plate `0, 0, 270, 270`), `bed_image_opacity` and `bed_grid`. Good for a photo of your own printer taken from above. Also in the card editor under "Top view".

---
**Deutsch**
- Neu: In der Draufsicht fährt die Düse flüssig die Bahnen der aktuellen Schicht ab, mit Querbrücke über der Platte. Der Drucker meldet seine Position alle paar Sekunden, die Karte spielt den Weg dazwischen ab. Aus bei „Bewegung reduzieren“ in den Systemeinstellungen.
- Neu: Eigenes Hintergrundbild für die Draufsicht: `bed_image` (z. B. `/local/u1_oben.png`) mit `bed_image_area` (welche Druckerkoordinaten das Bild abdeckt, Standard die Platte `0, 0, 270, 270`), `bed_image_opacity` und `bed_grid`. Passt z. B. für ein Foto des eigenen Druckers von oben. Auch im Karteneditor unter „Draufsicht“.

## 1.4.2

**New**
- Layer view as a top view of the whole printer (option `layer_view: bed`, or the grid button in the layer view; the choice is remembered per browser): the 270 × 270 mm plate to scale with a 10/50 mm grid, the four heads parked behind it in their filament colours (the active one outlined, shown as "away" while printing) and a nozzle marker where the printer is right now. The zoomed part view stays the default.

---
**Deutsch**
- Neu: Schichtansicht als Draufsicht auf den ganzen Drucker (Option `layer_view: bed` oder Raster-Knopf in der Schichtansicht; die Wahl merkt sich der Browser): Druckplatte 270 × 270 mm im Maßstab mit 10/50-mm-Raster, dahinter die vier geparkten Köpfe in Filamentfarbe (aktiver umrandet, beim Druck als „unterwegs“) und ein Düsen-Marker an der aktuellen Druckstelle. Standard bleibt die vergrößerte Teilansicht.

## 1.4.1

**New**
- Exclude objects during a print: the layer view shows the outline of every object (from `EXCLUDE_OBJECT_DEFINE`). Tap an outline or the object chip below, confirm, and the printer skips that object from now on (Klipper `EXCLUDE_OBJECT`); the rest keeps printing. The object being printed is highlighted, excluded ones are struck through and faded. The last remaining object cannot be excluded. Also available as service `snapmaker_u1_card.exclude_object`.

---
**Deutsch**
- Neu: Objekte während des Drucks ausschließen. Die Schichtansicht zeigt die Umrisse aller Objekte; Umriss oder Objekt-Chip antippen, bestätigen – der Drucker lässt das Objekt ab sofort aus (Klipper `EXCLUDE_OBJECT`), der Rest läuft weiter. Das gerade gedruckte Objekt ist hervorgehoben, ausgeschlossene sind durchgestrichen und blass. Das letzte verbleibende Objekt lässt sich nicht ausschließen. Auch als Dienst `snapmaker_u1_card.exclude_object`.

## 1.4.0

**New**
- Progress notification for Android: ongoing notification with progress bar and a countdown to the expected end. Switch in the card (System tab) and as an entity, off by default. Uses very few pushes: the countdown runs on the phone, updates only every 10 % or when the end time moves noticeably (about 12–15 per print), with a daily budget per phone (option, default 150). End/error/pause notifications are not affected.
- Download the G-code from the print dialog (through Home Assistant, also works remotely).

**Improved**
- Much more accurate remaining time: uses the slicer's own remaining time from the file (Orca `M73`), corrected by the measured speed from the first layer on. The start sequence (leveling, calibration) no longer distorts it, and the integration learns start duration and speed from your previous prints.
- Result photo: taken once the head has moved away from the part (head position from the printer), with the chamber light on, instead of a fixed 2 s after the last line.

---
**Deutsch**
- Neu: Fortschritts-Benachrichtigung für Android mit Balken und Countdown bis zum Ende. Schalter in der Karte (System-Reiter) und als Entität, standardmäßig aus. Sehr sparsam: Der Countdown läuft auf dem Handy, Updates nur alle 10 % oder wenn sich das Ende deutlich verschiebt (etwa 12–15 je Druck), mit Tagesbudget je Handy (Option, Standard 150). Fertig-, Fehler- und Pause-Meldungen sind nicht betroffen.
- Neu: G-Code im Druckdialog herunterladen (über Home Assistant, auch unterwegs).
- Verbessert: Deutlich genauere Restzeit – nutzt die Slicer-Restzeit aus der Datei (Orca `M73`), korrigiert mit der gemessenen Geschwindigkeit ab der ersten Schicht. Die Startsequenz (Leveling, Kalibrierung) verfälscht sie nicht mehr, Startdauer und Tempo lernt die Integration aus deinen bisherigen Drucken.
- Verbessert: Ergebnisfoto entsteht, sobald der Kopf vom Teil weggefahren ist (Kopfposition vom Drucker), mit eingeschaltetem Licht – statt fest 2 s nach der letzten Zeile.

## 1.3.2

**Fixed**
- Diagnostics download: the Spoolman address is now redacted (it was visible in the Spoolman block). Please don't post older diagnostics files publicly without checking.

**Improved**
- Diagnostics include the installed and the latest firmware version.

---
**Deutsch**
- Behoben: Diagnose-Download schwärzt jetzt die Spoolman-Adresse (stand vorher im Spoolman-Abschnitt im Klartext).
- Verbessert: Diagnose enthält die installierte und die neueste Firmware-Version.

## 1.3.1

**New**
- Faster camera: the card loads the stream directly from the printer (`camera_direct: auto`, default) instead of through Home Assistant – less delay, no load on HA. Works when HA is opened via `http://` in your home network; on `https://` or away from home the card automatically uses the HA proxy as before. Own stream address: `camera_direct_url`. Turn off with `camera_direct: off`.

**Improved**
- If the HA camera stream delivers nothing, the card switches to still images after 6 s instead of 10 s.

---
**Deutsch**
- Neu: Schnellere Kamera – Stream direkt vom Drucker statt über HA (`camera_direct: auto`, Standard). Greift, wenn HA im Heimnetz per `http://` geöffnet ist; bei `https://` oder unterwegs nimmt die Karte automatisch den Weg über HA. Eigene Adresse: `camera_direct_url`, abschalten mit `camera_direct: off`.
- Verbessert: Liefert der HA-Stream nichts, wechselt die Karte nach 6 s statt 10 s auf Einzelbilder.

## 1.3.0

**New**
- Emergency stop option `emergency_stop`: `show` (with confirmation), `hold` (hold the button for 1 s) or `hide`. The HA button entity always stays.
- Own confirmation dialog for emergency stop and cancel print (instead of the browser popup).
- Tablet / wall monitor layout (`layout: tablet`): camera and current job on the left, tabs on the right.
- Camera wake-up (`camera_wake`, on by default): if the image freezes on stock firmware, the card asks the printer to restart the camera (new service `snapmaker_u1_card.camera_wake`).
- Notice when the browser still runs an old card after an update, with a reload button.

---
**Deutsch**
- Neu: Not-Halt anzeigen / gesichert (1 s halten) / ausblenden · eigener Bestätigungsdialog · Tablet-/Monitor-Layout · Kamera wecken bei stehendem Bild (Stock-Firmware) · Hinweis bei veralteter Karte im Browser-Cache.

## 1.2.3

- Camera: printer state as a small badge in the corner instead of a dimmed overlay while idle.
- Toolheads: visible "Filament" button to edit the loaded filament.

## 1.2.2

- Electricity price from a price entity, a fixed price or the Energy dashboard.
- Self test: Spoolman check fixed.

## 1.2.1

- Timelapse archive limits (number and age), five config backups.

## 1.2.0

- Printer settings (auto replenish, tangle detection, LED off at the end) as switches and in the card.
- RFID spool data and filament editing per toolhead.
- Option to keep the camera awake on stock firmware.
