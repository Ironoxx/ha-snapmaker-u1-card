# Features in detail

[← Back to the README](../README.md)

**Contents:** [How the filament mapping works](#how-the-filament-mapping-works) · [Tool changes](#tool-changes) · [Energy, cost and history](#energy-cost-and-history) · [Live connection and notifications](#live-connection-and-notifications) · [Bed mesh, flow, top cover and chamber heater](#bed-mesh-flow-top-cover-and-chamber-heater) · [Camera](#camera) · [File management](#file-management) · [Status light (blueprint)](#status-light-blueprint) · [Temperature chart](#temperature-chart) · [Idle shutdown](#idle-shutdown) · [Firmware and self test](#firmware-and-self-test) · [Statistics per material](#statistics-per-material) · [Voice control (Assist)](#voice-control-assist) · [Printer configuration backup](#printer-configuration-backup) · [Spool management with Spoolman](#spool-management-with-spoolman) · [Timelapses](#timelapses) · [Layer view](#layer-view) · [Printer messages](#printer-messages)

## How the filament mapping works

The integration starts prints exactly like Snapmaker Orca in LAN mode, via the Moonraker call `server.files.start_local_print` with `options.map_table`. The printer turns that into `SDCARD_PRINT_FILE_WITH_PARAMETERS … MAP_TABLE="[[0, 2], [1, 0]]"`. The firmware checks as usual whether the printer is free and the nozzles fit.

This is documented in Snapmaker's open source code:
[u1-klipper](https://github.com/Snapmaker/u1-klipper) (`klippy/extras/print_task_config.py`) and
[u1-moonraker](https://github.com/Snapmaker/u1-moonraker) (`components/snapmakercloud.py`, `components/klippy_apis.py`).

The suggestion picks a loaded head for each filament of the file in this order: same material, closest colour, still free. An empty head blocks the start. A different material only shows a warning.

## Tool changes

The firmware permanently counts every successful head change per head (`switch_count` in `extruder` … `extruder3`, source: `ExtruderSwitchRecorder` in u1-klipper `klippy/kinematics/extruder.py`). With older firmware without these fields both sensors are *unavailable* and the card hides the rows.

The firmware has no per-print counter. The integration remembers the counter at print start and takes the difference at the end. This baseline is stored and survives a Home Assistant restart during the print. Every change during the print counts, including pickups for calibrations at the start. If Home Assistant is down for a whole print, that print is missing.

The maintenance threshold is the firmware default of 25,100 changes per head. From 90 % the card shows the value in yellow. Reset after maintenance: `RESET_EXTRUDER_MAINTENANCE_COUNT` in the console.

## Energy, cost and history

- **Consumption per print** is the difference of the energy meter between start and end of the print.
- **Energy cost** is accumulated continuously (consumption since the last poll × price at that moment), so dynamic tariffs are handled correctly.
- **Filament cost**: weight per material from the file's slicer data × price per kg. For cancelled prints the weight is reduced by the ratio of extruded to planned filament. If a price is missing for a material used, the filament cost is left out instead of showing a wrong total.
- **Total cost in the history** (tile and chart): prints recorded by the integration with their real cost (filament + energy). Older prints from Moonraker, i.e. before installation, are estimated from the filament price; the tile then shows "≈". This way the total matches the material table. *Energy* only counts measured prints.
- **Auto-off** only triggers after *complete* or *cancelled*, never after an error, and only once all nozzles and the bed are below the configured temperature.
- While the printer is off, the card shows power on, files (with auto-on), history and timelapses. The filament mapping then uses the state before switching off.

**Thumbnails** get a background that fits the brightness of the part: dark parts (black filament) a light one, very light parts a dark one. The card measures the average brightness of the opaque pixels; images without transparency stay unchanged.

**Cost before printing.** The start dialog shows "≈ €0.48" with the breakdown below. Filament: weight per material from the slicer data × price per kg (left out if a price is missing). Energy: estimated print time × average power of all previous prints of 10 min and more (energy ÷ duration from the history) × current energy price. Before the first measured print only the filament part is shown.

## Live connection and notifications

The integration subscribes to `print_stats`, `toolhead`, `virtual_sdcard` and `exception_manager` in Moonraker (`printer.objects.subscribe`), and since 2.0 also to every heater, fan, sensor, LED, output pin and MCU the printer lists (`/printer/objects/list`). These are the values the card shows; they reach it within about a second. The CPU temperature of the printer's computer comes with Moonraker's process statistics (`notify_proc_stat_update`). Moonraker only sends changes, at most every 250 ms. State changes and new messages trigger an immediate poll, a head change updates the card directly, and the layer view takes its file position from the subscription instead of asking the printer. While the subscription is up, the integration polls only every 30 s (otherwise every 10 s). If the connection drops it reconnects with 5–60 s backoff; not at all while the printer is off.

| Event | When |
|---|---|
| Printer message | new firmware message during a print. If the printer pauses because of it, only the pause notification (with the text) is sent |
| First layer done | change from layer 1 to 2. Joining in the middle of a print (HA restart) does not send one |
| Almost done | remaining time (see below) below the configured minutes, once per print |
| Not enough filament | at print start, when according to Spoolman a spool has less left than the file needs on that head |
| Spool about to run out | during the print, when a spool will be empty in less than 30 min according to the time profile. With a hint whether the firmware will continue via **auto-replenish** from a head with the same material (and colour, unless "ignore colour" is on at the printer) or pause |
| Part ready to remove | after a finished print, once the bed has cooled below the configured temperature (35 °C) |

**Buttons in the notification** (Companion app): *Pause* and *Light* for messages during a print, *Resume* and *Cancel …* when paused. Cancel asks again with a second notification ("Yes, cancel"), so an accidental tap cancels nothing. The buttons only act while the state fits (pause only while printing, etc.).

**Remaining time.** At print start the integration downloads the file once. Slicers like Orca write their own remaining time into the file (`M73 R<minutes>`); the integration reads it per file position, so acceleration and tool changes are already included. It scales this slicer time by the measured speed, measured from the start of the first layer (the start sequence with leveling and calibration does not distort it). Until enough is printed, the speed factor and the start duration learned from earlier prints carry the estimate. During the start sequence: expected remaining start time + slicer time of the print. Files without `M73`: a time profile from the moves (distance ÷ feed rate), weighted between slicer total and measured speed. Result: the sensors *Time remaining* and *Finish time*; the card, "almost done", Assist and the progress notification use them. History entries record `prep_s` (start duration) and `speed_factor` (actual ÷ slicer time).

**Progress notification (Android).** Switch *Progress notification (Android)* (also in the card's system tab, off by default). Android phones among the notification targets get an ongoing notification with a progress bar and a countdown to the expected end. The countdown runs on the phone, so the remaining time costs no pushes. Updates only on a 10 % step, when the expected end moves by more than max(5 min, 10 %), and on pause/resume; at most one every 3 min and 25 per print, plus a daily budget per phone (option, default 150; the companion app allows about 500 pushes per day through the cloud relay). The notification starts after the start sequence, uses a silent channel (`alert_once`, low importance) and is removed at the end. End, error and pause notifications are not affected by the budget. Switch attributes: `sent_today`, `budget`, `targets`.

**Tap and image.** Option *Open when tapped* (`notify_click_url`): tapping any notification of the integration opens this path or URL (e.g. `/dashboard-printer/0`). The "print finished" notification shows the result photo; the progress notification shows the camera image when expanded (option, on by default).

**Result photo.** With a camera configured, the integration takes the image at the end of the print once the head has left the part: after the last extrusion it reads the head position (`motion_report`) for up to 15 s and shoots as soon as the head is 25 mm outside the parts' outline (`EXCLUDE_OBJECT_DEFINE`) or the bed has already dropped by 15 mm. The chamber light is switched on for the photo and back off afterwards if it was off. Without position or outline: 2 s after the last extrusion; without a time profile: in the last layer from 99.5 %. On cancel or error the image is taken at that moment. It is stored under `.storage/snapmaker_u1_card/thumbs/<entry>/results/` and appears in the history next to the thumbnail; tapping enlarges it in the card (tap or Esc closes). Photos are kept for the prints in the history.

## Bed mesh, flow, top cover and chamber heater

**Bed mesh.** The card shows the probed points of the mesh Klipper has loaded (`bed_mesh.probed_matrix`) as a heatmap: red above, blue below zero, the front of the printer at the bottom. The mesh is created when a print starts with bed leveling; without one the card says so.

**Flow** is Klipper's extrusion factor (`M221`), 100 % = as sliced. Klipper keeps the value until it is changed or Klipper restarts, so set it back to 100 % after a test.

**Top cover.** The optional cover is the firmware's `purifier`. Whether one is plugged in is reported by the printer (`power_detected`); only then do the entities and the panel appear. The firmware sets the chamber mode from the material at print start and keeps adjusting the fans during the print; the sliders set exhaust and circulation fan by hand (`SET_PURIFIER`). The mode can also be chosen in the card or with the select entity: *idle*, *cool* (exhaust until the chamber is below the target), *preheat* and *hot* (circulation keeps the heat), with the chamber target next to it (`SET_PURIFIER_MODE MODE=… DESIRE_TEMP=…`). Filter runtime counts the hours of the circulation fan; the maintenance item *Replace the air filter* counts these real filter hours, not print hours. *Not yet tested on a printer with a cover – feedback welcome (diagnostics file).*

**Chamber heater.** With the paxx12 Extended Firmware a BIQU Panda Breath (stock firmware) or a Panda Breath with DragonBreath firmware is a Klipper `heater_generic` (`panda_breath` / `dragonbreath`). The integration finds it in Klipper's object list; only then do the entities (*Chamber heater* temperature, *Chamber heater target*, for DragonBreath *Chamber heater filter*) and the panel in the control tab appear. The target goes to Klipper as `SET_HEATER_TEMPERATURE` (0 = off; Panda Breath 15–80 °C, DragonBreath up to 75 °C), the slicer sets it with `M141`/`M191` anyway. paxx12 warns: never heat unattended, the mainboard needs extra cooling.

**Chamber warm.** Notification *Chamber reached its target* (event `chamber_ready`, off by default): once when the chamber heater reaches its target, or the chamber sensor reaches the top cover's target in preheat or hot mode. A new target arms it again. The temperature chart shows the chamber heater with its target.

**Nozzle per head.** The firmware keeps diameter and type (standard / high flow) per head (set on the display when a hotend is changed). The head details show them; the print dialog warns when a filament goes to a head whose nozzle differs from the one the file was sliced for (`nozzle_diameter_list` of Snapmaker's Moonraker).

## Camera

From 1.5 the integration has its own camera entity (*Camera*) and finds out by itself how to get an image (attribute `mode`, also shown in the self test and diagnostics):

| `mode` | When | Image |
|---|---|---|
| `live` | Moonraker lists a webcam whose stream answers with MJPEG (modified firmware, e.g. paxx12 Extended). If Moonraker announces a WebRTC or player page (paxx12 2.x: `/webcam/webrtc`), the MJPEG stream next to it (`/webcam/stream.mjpg`) is used | live stream, passed through |
| `still` | only a snapshot URL works | still image every second |
| `wake` | stock firmware: no stream, only `camera/monitor.jpg`, which only changes after `camera.start_monitor`. The image is fetched twice around a wake call and must change | still image every 1–2 s; the camera is woken as needed (at most every 10 s) while someone watches |
| `none` | nothing found | entity unavailable; the card shows a hint instead of a black area |

**RTSP.** If the printer answers on `rtsp://<printer>:8554/stream` (paxx12: *RTSP* in `/firmware-config/`, off by default), the camera entity also offers it as stream source (attribute `rtsp_url`, `supported_features` stream): Home Assistant then streams H.264 itself (more-info dialog, picture cards, go2rtc/WebRTC). At home the card uses the printer's own WebRTC (below); away from home it plays this RTSP stream through Home Assistant.

**WebRTC in the card.** With paxx12's camera (`webrtc-camerastreamer`, Moonraker lists `/webcam/webrtc`) the card shows the live image over WebRTC: less delay and far less data than MJPEG. The printer sends no CORS headers, so the card cannot talk to it from the browser; the integration relays the three small signalling messages (`POST /api/snapmaker_u1_card/webrtc/<entry>`, only to the camera Moonraker reports). The video then flows directly between browser and printer, at home and over VPN. Until the first frame (and if WebRTC does not come up within 8 s, e.g. away from home without VPN) the card shows MJPEG; after a failure it stays on MJPEG for 10 minutes. Card option `camera_webrtc: off` turns it off.

**Away from home (Nabu Casa, no VPN).** There is no direct path to the printer, so with RTSP enabled (paxx12, `rtsp: true`) the card plays the RTSP stream through Home Assistant's own streaming (`ha-camera-stream`: WebRTC via HA, with Nabu Casa's relay servers, else HLS). H.264 needs far less data than MJPEG through the HA proxy, so the picture stays smooth. With Nabu Casa the card does not even try the direct WebRTC. If no frame arrives within 15 s, MJPEG is used for 10 minutes. Without RTSP (stock firmware) nothing changes. Card option `camera_ha_stream: off` turns it off.

**Second camera.** A second webcam (paxx12: USB camera at `/webcam2/`, RTSP port 8555) gets its own entity *Camera 2* once it is found; the card shows a switch button on the image.

Detection runs when the printer comes online, when images keep failing and every 5 minutes while nothing (or only the stock camera) was found. If the live stream fails, the camera switches to still images and tries the stream again after 5 minutes, so a firmware change needs no setting. The card uses this entity unless `camera` is set; notification images and the result photo use it unless a camera is set in the integration options.

## File management

Above the file list: search (across **all** files on the printer, not only the newest), sorting (newest, name, print time) and folder chips. Older matches appear as a list; tapping loads metadata and thumbnail and opens the print dialog. In the print dialog: *Download* (the G-code through Home Assistant, also works remotely), *Rename / move* (subfolders with `/` are created) and *Delete*. Both are blocked while the file is printing or queued. Services: `file_details`, `move_file`, `delete_file`.

**Slicer settings.** The print dialog shows what the file was sliced with: profile, layer height (first layer), walls/top/bottom layers, infill and pattern, supports, brim, prime tower, seam, plate type, speeds and nozzle/bed temperature per used filament (first layer in brackets). The integration reads the settings block at the end of the G-code once per file version (the last 256 KB, Orca/Snapmaker Orca and PrusaSlicer key names). Service `file_settings` (`path`). The printer does not report which plate is on the bed, so there is no plate warning.

## Status light (blueprint)

The integration installs the blueprint *Snapmaker U1 – status light* into `config/blueprints/automation/snapmaker_u1_card/`. In *Settings → Automations → Blueprints* create an automation from it: choose the Moonraker sensor *Current print state* and one or more lights (WLED, LED strips, any colour light). Colours for printing (optionally with a WLED effect such as *Breathe*), paused, error/cancelled, finished (for a set time) and idle (off, a colour or unchanged). A copy you edited stays untouched when you remove the line `managed: snapmaker_u1_card` from the file; otherwise updates replace it.

## Temperature chart

In the *Control* tab: actual and target temperature of the active heads and the bed over the last 20 minutes. Moonraker stores this data anyway (`/server/temperature_store`); the card fetches it every 10 s through the integration, only while the tab is visible. Also shown: the CPU temperature of the printer's computer (sent by Moonraker once a second, recorded by the integration), chamber air and the X/Y stepper drivers (only while the motors are on; Klipper reports no driver temperature otherwise). Tap an entry in the legend to hide or show its line; the choice is remembered per browser.

## Idle shutdown

Option *Switch off after idle* (hours, 0 = off): when no print is running, no heater is on (including preheating on the display) and that has lasted longer than configured, the integration shuts the printer down cleanly and switches off the plug. The firmware itself only knows `idle_timeout` (heaters and motors off after 10 min) but never powers off.

## Firmware and self test

- **Update entity "Firmware"**: installed version from the printer (`/machine/system_info`), latest from Snapmaker's release commits of the firmware sources on GitHub (`Snapmaker/u1-moonraker`, `Snapmaker/u1-klipper`), once a day. Updating still happens on the printer (display or Snapmaker app); the entity only reports. Note: Snapmaker may change how it publishes on GitHub; "latest" then stays at the last known version.
- **Self test** (*System* tab or service `self_test`): printer and Klipper, live connection, firmware, free space on the printer (warning below 500 MiB), Moonraker integration, camera (fetches an image), power switch/energy/price entities, notification services, Spoolman, Assist sentences, media folder. ✓ fine, ! note, ✗ error.

## Statistics per material

Below the monthly charts: prints, consumption, cost and success rate per material plus the most used colours, from Moonraker's print history, so retroactive. Cancelled prints count pro rata.

## Voice control (Assist)

The integration registers three intents and writes the sentences to `/config/custom_sentences/en/snapmaker_u1_card.yaml` (and `de/`):

- "How far is the printer?", "How long until the print is done?", "What is the printer doing?", "Printer status" → e.g. "benchy is at 40 percent, layer 121 of 300, about 6 minutes left."
- "Pause the printer", "Pause the print"
- "Resume the print", "Continue the printer"

German: "Wie weit ist der Drucker?", "Pausiere den Drucker", "Drucker fortsetzen". The integration updates the files on every start. To maintain your own sentences, delete the first line (`# snapmaker_u1_card: automatisch erzeugt`) and the file is left alone. Cancelling by voice is deliberately not offered.

## Printer configuration backup

Once a day, never during a print, the integration fetches all files from Moonraker's `config` root (printer.cfg, moonraker.conf, macros …) to `/config/snapmaker_u1_backup/<printer>/<date_time>/`. A new snapshot is only created when something changed; the last 5 are kept. Logs, databases and files above 2 MB are skipped. Because the backups live in the HA config folder, they are part of every Home Assistant backup. The latest snapshot is shown in the card under *System → Maintenance*, with a button to back up right away.

## Spool management with Spoolman

Optional. Without a Spoolman address none of this appears in the card or the integration.

**Stock.** The tab *Spoolman* (only with Spoolman set up) lists every active spool: colour, vendor, material, location, which head it is in and the remaining weight as a bar (below the warning threshold in orange). On top the number of spools, the filament left in kg and its value (from the spool prices). Filter by material, search by name, vendor, location or `#ID`.

**New spool.** From the *Spoolman* tab (*New spool*) or the spool picker of a head (*Create new spool*, prefilled with the head's material, vendor and colour, from the RFID tag if there is one). Typing in *Search filament* shows matches from your own Spoolman filaments and from Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (several thousand filaments of known vendors, 1.75 mm only); vendor and material fields suggest the known names. A pick fills vendor, material, name, colour, net weight and empty spool weight:
- an own filament is used as it is,
- a catalogue entry is imported into Spoolman once (vendor created if needed, with its colour, density and temperatures) and reused for the next spool.

Without a pick, vendor and filament are reused if they exist (same name, material and colour), otherwise created (density by material, 1.75 mm). Location and price are optional; from the *Spoolman* tab you choose the head in the form or none. Picking a spool for a head stays under the print heads. With SpoolLink the head is set via `SET_SPOOL_ID`. The catalogue needs Spoolman 0.18 or newer with internet access; without it only your own filaments are suggested.

Service: `snapmaker_u1_card.create_spool` (`slot`, `material`, `vendor`, `name`, `color`, `weight`, `spool_weight`, `price`, `remaining`, `location`, `filament_id` or `external_id`), returns `spool_id`.

**Assigning spools to heads.** Moonraker only knows *one* active spool for Spoolman; with four heads the integration handles this itself. For each loaded head an active (not archived) spool is chosen by:

1. same material (`PLA-CF` matches `PLA`),
2. similar colour (spool without colour: material only). If the colour differs clearly, **nothing** is assigned; a wrong spool would be worse because usage would be booked from it,
3. sub type in the name (e.g. "Silk"), same vendor,
4. opened, most recently used spool before a new one.

Each spool is assigned to at most one head. In the card, tap the spool row of a head and choose "Automatic", "No spool" or a specific spool. Choosing a specific spool also loads its filament into the printer: material (sub type such as Matte or Silk from the material or the spool name), vendor and colour are written to the head's slot (`SET_PRINT_FILAMENT_CONFIG`), so the display, the card and the filament mapping show the right filament. Not for official spools with RFID tag (the tag wins) and not during a print. A manual choice stays until a different filament is detected in that head (material, colour or vendor change) or the spool is archived in Spoolman.

**Booking usage.** After every print the integration books usage per head: weight per filament from the slicer, distributed to the heads via the print's map table (`print_task_config.extruder_map_table`); for cancelled prints pro rata by the actually extruded length. If Spoolman is unreachable, the booking is stored and retried later, even across Home Assistant restarts. The history shows the remaining weight per spool before and after the print (`#5 550 g → 460 g`; ⏳ = not booked yet).

**paxx12 Extended Firmware with Spoolman (SpoolLink).** If Spoolman is enabled in `/firmware-config/`, Moonraker books the usage itself while printing and the printer keeps the spool per head (`print_task_config.filament_spool_id`). The integration detects both automatically:

- It **does not book** usage then (no double booking, whatever *Book usage* is set to). The self test says who books.
- The spool per head comes from the printer; choosing a spool in the card sends `SET_SPOOL_ID CHANNEL=<head> SPOOL_ID=<id>` to the printer, which loads the spool's filament itself. "Automatic" is not offered.
- The history still shows before → after, read back from Spoolman after the print.

The same applies to any other `[spoolman]` section in Moonraker's configuration.

**Unloading and reloading.** Without an RFID tag the printer forgets the spool when the filament is unloaded (with SpoolLink it clears `filament_spool_id`). When the head is loaded again, it offers its previous spool: "Use #5 … again?" – one tap restores it (with SpoolLink via `SET_SPOOL_ID`). Until then nothing is booked and no other spool is guessed for that head. Option *Last spool after reloading a head* (Spoolman section): offer (default), set automatically (not during a print; wrong spool if you load a different one and forget to change it), or off.

**Weighing a spool.** In the head details (with a spool assigned) enter what the scale shows: with the empty spool (its weight comes from Spoolman: spool, filament or vendor *empty spool weight*) or the filament only. The integration sets the remaining weight in Spoolman. Service `weigh_spool` (`slot` or `spool_id`, `weight`, `gross`). Spoolman's own interface is then only needed for details of vendors and filaments.

Limitation: if the firmware switches to another head automatically during a print (auto-replenish on an empty spool), the whole usage is attributed to the last reported head.

Service for assigning, e.g. in automations:

```yaml
action: snapmaker_u1_card.set_spool
data:
  slot: 2        # head 1–4
  spool_id: 12   # 0 = no spool; omit = automatic again
```

The spool per head is also available on `sensor.…_slot_1` … `_slot_4` (attributes `spool`, `spool_remaining`), e.g. for a notification when filament runs low.

## Timelapses

The stock firmware stores timelapses in the Moonraker folder `camera` (`Name_YYYYMMDDhhmmss.mp4` with `_cover.jpg`). The integration searches all folders except config and logs, so Fluidd timelapses (`timelapse`) are found too. Playback goes through an authenticated proxy of the integration with short-lived signed links. It only serves files from the list, never arbitrary paths from the printer.

**Backup.** With *Timelapse backup* the integration copies every new video including its preview to `<media>/snapmaker_u1/` ("Local media" in the media browser, "Saved in media" in the card, playable even with the printer off). Nothing is copied during a print. So the folder does not fill up, only the newest 50 videos are kept by default (option *Keep in media folder*); optionally also an age limit in days. Removed backups are not downloaded again.

**Cleaning up on the printer.** Moonraker exposes the `camera` folder read-only; only Snapmaker's internal camera service (`camera.delete_timelapse_instance`) can delete, and its parameters are undocumented. The integration therefore only deletes videos that are fully backed up, always backs up everything first, probes the parameter form once and remembers it. If the service refuses all forms, everything stays and the card shows that deleting on the printer is not supported by the firmware.

## Layer view

**Sliders.** *Layer* browses the whole file: earlier layers show as printed, later ones as pending, the head line says which layer is printing; *Live* goes back to it. *Progress* plays the current layer in file order (with the nozzle in the bed view); dragging it fully to the right goes back to the live position.

**G-code preview before printing.** In the print dialog, *G-code preview* shows any file layer by layer with the same two sliders. The integration downloads and splits the file in the background on first opening (a few seconds for large files) and keeps the last three previews; the running print's file is not downloaded again. The colours follow the mapping chosen in the dialog: filament → head → spool loaded there. API: `/api/snapmaker_u1_card/layers/<entry>?file=<path>&layer=<n>`.

**Exclude objects.** With objects defined in the file (`EXCLUDE_OBJECT_DEFINE`, Orca: "Label objects" on), the layer view draws their outlines and lists them below. Tapping one asks for confirmation and then calls `snapmaker_u1_card.exclude_object` (Klipper `EXCLUDE_OBJECT NAME=…`): the printer skips the object from now on. The object being printed is highlighted, excluded ones are faded. The last remaining object cannot be excluded (cancel the print instead).

As soon as the card requests the layer view during a print for the first time, the integration downloads the file once and splits it into layers (`;LAYER_CHANGE` or `SET_PRINT_STATS_INFO`). The card only fetches the current layer (`/api/snapmaker_u1_card/layers/…`, authenticated) and every 5 s the file position (`virtual_sdcard.file_position`, from the live subscription, without asking the printer): everything before it is printed. Colour per filament: head from the mapping → colour of the spool loaded there, otherwise the colour from the file. Arcs (G2/G3) are split into short segments, points closer than 0.35 mm are merged. For large files the preparation takes a few seconds.

## Printer messages

The U1 firmware reports errors in a structured way (module, head, code). The integration translates known codes, e.g. "Filament runout (head 2)", "Preload: no filament detected", "Spaghetti detected", "PEI plate not seated correctly", and adds a hint. Unknown codes appear with the firmware's raw message. The messages are shown at the top of the card, in notifications on error/pause and in the history.
