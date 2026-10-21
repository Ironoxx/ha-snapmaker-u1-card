# Changelog

Each `## x.y.z` section becomes the text of the GitHub release, which HACS shows
in the update dialog. Newest first. After updating: restart Home Assistant and
reload the dashboard (the card shows a hint if the browser still has the old one).

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
