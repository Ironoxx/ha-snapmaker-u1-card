# Configuration

[← Back to the README](../README.md)

**Contents:** [Integration settings](#integration-settings) · [Settings in the card](#settings-in-the-card) · [Card options](#card-options) · [Updating](#updating) · [How the card is loaded](#how-the-card-is-loaded) · [Moonraker integration (optional)](#moonraker-integration-optional)

## Integration settings

During setup a second step with all settings follows right after the address. Later they are under *Devices & services → Snapmaker U1 Card → Configure*. All fields are optional; the card picks them up automatically.

| Section | Fields |
|---|---|
| Power and consumption | power switch, power sensor (W), energy meter (kWh), energy price: price entity (EUR/kWh or ct/kWh, dynamic tariffs) **or** a fixed price per kWh; if both are empty, the price from the Home Assistant **energy dashboard** is used, shut down before switching off, auto-on at print start, auto-off after the print (temperature, delay), switch off after idle (hours) |
| Notifications & camera | `notify.mobile_app_…` services, events (finished, cancelled, error, paused, message during print, first layer done, almost done, not enough filament), "almost done" lead time in minutes (10), "part removable" below bed temperature (35 °C), camera for image and result photo, **keep camera awake** (off / during a print / always) |
| Filament prices | price per kg for PLA, PETG, ABS, ASA, TPU, PA and others. `PLA-CF` uses the PLA price. With Spoolman its prices come first: at the end of a print the price of the spool in each head, otherwise the average price per kg of your spools of that material (spool price, else filament price, per net weight). These fields only apply to materials without a price in Spoolman |
| Timelapse backup | on/off, how many of the newest stay on the printer (0 = never delete), how many stay in the media folder (50, 0 = all), delete backups older than x days (0 = never) |
| Maintenance | interval per item in print hours (0 = hide) |
| Spoolman | address (empty = off), book usage per head (on/off), warning threshold in g |
| Files | number of newest files, back up printer configuration (on) |

## Settings in the card

Admins find *System → Settings* in the card: the integration's settings (power, notifications, filament prices, Spoolman, files, timelapse backup, maintenance) grouped by topic, with the current value next to each chosen entity and the Spoolman price next to each filament price. It is the same as *Settings → Devices & services → Snapmaker U1 Card → Configure*, with the same checks; only changed sections are saved and the integration then reloads briefly. Card options (layout, camera display …) stay in the card editor because they belong to the dashboard.

## Card options

All options are optional; except head names and presets they can also be set in the visual editor.

| Option | Default | Meaning |
|---|---|---|
| `layout` | `tabs` | `tabs` = tabs, `scroll` = all sections stacked (in the order of `show`), `tablet` = camera, job and print heads always visible on the left, tabs on the right (tablets, wall monitors; stacks below about 900 px), `bare` = only the sections of `show`, no head and no tabs (the building block card uses it) |
| `show` | all | 2.2: which sections, in this order (`stage`, `display`, `layer`, `job`, `queue`, `files`, `toolheads`, `climate`, `mesh`, `motion`, `console`, `system`, `maintenance`, `charts`, `stats`, `history`, `timelapse`, `spools`, `messages`); `hide` leaves sections out instead |
| `layer_view` | `part` | layer view: `part` = zoomed to the part, `bed` = top view of the whole plate with the parked heads and a nozzle marker. Also switchable in the layer view (grid button, remembered per browser) |
| `bed_image` | – | own background image for the top view, e.g. `/local/u1_top.png` (file in `config/www`); replaces the drawn plate and heads |
| `bed_image_area` | `0, 0, 270, 270` | printer coordinates in mm the image covers (x0, y0, x1, y1). Photo of the whole printer: measure two points, e.g. `-40, -30, 310, 360` |
| `bed_image_opacity` / `bed_grid` | `1` / `false` | opacity of the image, 10/50 mm grid over it |
| `emergency_stop` | `show` | `show` = button with confirmation, `hold` = hold for 1 s (no dialog), `hide` = no button in the card (the HA button entity stays) |
| `camera_direct` | `auto` | `auto` = stream straight from the printer (`camera_direct_url`, default `http://<printer>/webcam/?action=stream`): less delay, no load on HA. Not used on https pages (the browser blocks http streams there); if no frame arrives within 4 s (e.g. away from home) the card uses the HA proxy for 10 min. `off` = always through HA |
| `camera_direct_url` | – | own URL for the direct stream |
| `camera_webrtc` | `auto` | paxx12 Extended Firmware: show the camera over WebRTC (less delay, far less data than MJPEG). The few signalling messages go through Home Assistant, the video directly between browser and printer – works at home and over VPN; if no direct connection comes up within 8 s, MJPEG stays for 10 min. `off` = MJPEG only |
| `camera_ha_stream` | `auto` | away from home (no direct connection, e.g. Nabu Casa): play the RTSP stream through Home Assistant instead of MJPEG. Only with RTSP (paxx12). `off` = MJPEG |
| `display_place` | `overview` | 2.2: printer display (paxx12 display mirror) on the overview at its real size (`overview`), in its own tab (`tab`) or not at all (`off`). The older `display_tab: false` still means off |
| `display_camera` | `false` | printer display as one more step of the camera switch button on the image (printer camera → USB camera → display) |
| `camera_zoom_reset` | `60` | seconds without interaction until the camera zoom goes back to 1×; `0` = never. Leaving the page, switching the app or scrolling the card away always resets it |
| `accent_color` | – | own accent colour for buttons, sliders and highlights (`[255, 152, 0]` or `"#ff9800"`); empty = your theme's primary colour. Also for the mini card |
| `camera_wake` | `true` | while the card is visible and the image stops (no stream, frozen frame), it asks the integration to send `camera.start_monitor` once (at most every 10 s) |
| `camera_overlay` | `true` | progress on the camera image; the printer state is always shown in the top-left corner (`hide_overlay: true` also turns it off) |
| `state_accent` | `true` | frame in the theme colour of the state (printing, paused, error, done) |
| `camera_height` | automatic | height of the camera image in px. Empty = image aspect ratio, at most `camera_max_height` |
| `camera_max_height` | `520` | upper limit for the automatic height in px |
| `camera` | own camera | camera entity. Empty = the integration's own camera (see [Camera](features.md#camera)), else the Moonraker integration's |
| `camera_mode` | `auto` | `auto` = the camera entity decides (live stream or still images), `stream` = force the stream, `still` = still images (saves WiFi) |
| `refresh` | `2` | seconds between still images (`still` and fallback) |
| `camera_fit` | `contain` | `contain`, `cover`, `fill` |
| `show` | all | sections: `stage display layer job queue files toolheads climate mesh motion console system maintenance charts stats history timelapse spools` (`spools` = Spoolman tab, only with Spoolman; `display` = printer display, only with paxx12's display mirror) |
| `hide` | – | sections to hide (counterpart of `show`, used by the editor) |
| `controls_lock` | `60` | lock for temperature and fan sliders, presets, heater switches and homing: `off`, seconds (`30`, `60`, `120`, `300`) until it locks again after the last interaction, or `manual` (open until locked again). During a print the card asks before changing a target temperature. Legacy: `unlock_controls: true` = `off` |
| `timelapse_limit` | `8` | timelapses shown |
| `files_limit` | `12` | files shown |
| `nozzle_presets` / `bed_presets` | `[0,210,240,260]` / `[0,55,65,85]` | quick temperature presets |
| `speed_presets` / `flow_presets` | `[85,100,115]` / `[95,100,105]` | 2.2: quick buttons for speed and flow; the current value is marked |
| `mesh_values` | `true` | 2.2: heights in the bed mesh cells (up to 12 × 12 points) |
| `exclude_objects` | `true` | 2.2.1: object list and outlines for excluding objects in the layer view; `false` hides both (prints with very many parts) |
| `alerts` | with `stage`/`job` | 2.2, section card: printer messages on top (`true` always, `false` never). The section `messages` shows them on its own |
| `toolheads` | – | head names, e.g. `- name: Left` (material and colour come from the printer) |
| `network_tracker` | – | `device_tracker` for a WiFi chip in the header |
| `prefix`, `camera`, `thumbnail`, `filaments_sensor`, `files_sensor` | automatic | only needed with several printers |

> **Another U1 card installed?** The integration [kbaker827/ha-snapmaker-u1](https://github.com/kbaker827/ha-snapmaker-u1) also ships a card called `custom:snapmaker-u1-card`; whichever loads first gets that name. This card is always available as `type: custom:snapmaker-u1-card-ironoxx` too, and the self test points it out.

### Building block card (2.2)

Single sections of the card as cards of their own, to arrange freely in a *Sections* dashboard: *Add card → Snapmaker U1 – Section*, then pick the sections in the editor (their order counts). Same options as the full card.

```yaml
type: custom:snapmaker-u1-section-card
show: [mesh]          # e.g. [stage], [job, toolheads], [console] …
```

With one section the Home Assistant card frame is the panel itself; with several they stack like `layout: scroll`.

### Mini card

```yaml
type: custom:snapmaker-u1-mini-card
navigation_path: /dashboard-printer/0   # optional: go there on tap, otherwise the status dialog
```

| Option | Default | Meaning |
|---|---|---|
| `printer_name` | `U1` | display name |
| `navigation_path` | – | target on tap |
| `hide_filaments` | `false` | hide the filament row |
| `prefix` | automatic | only with several printers |

## Updating

Replace the folder `custom_components/snapmaker_u1_card` (or update in HACS) and restart Home Assistant. Settings, history, queue, maintenance, spool assignment and backed-up timelapses are kept:

| What | Where |
|---|---|
| Settings | config entry (`.storage/core.config_entries`) |
| History, queue, maintenance, Spoolman assignment, pending bookings | `.storage/snapmaker_u1_card.<entry>.print_switches` |
| Thumbnails, layer view (cache, rebuilt automatically) | `.storage/snapmaker_u1_card/` |
| Printer configuration backups | `snapmaker_u1_backup/` |
| Assist sentences (updated on every start) | `custom_sentences/de/…` and `custom_sentences/en/…` |
| Backed-up timelapses | `<media>/snapmaker_u1/` |

Do not delete and re-add the integration: that creates a new entry, and settings and history stay with the old one.

## How the card is loaded

You do not add a resource yourself; the integration loads the card on two paths:

1. through the Home Assistant start page (`add_extra_js_url`),
2. as the dashboard resource `/snapmaker_u1_card/card/snapmaker-u1-card.js?v=…`, which the integration creates, keeps current and removes again with the integration. Leave it under *Dashboards → Resources*.

Both come from the integration itself; nothing is copied into `/config/www`. Up to 2.1.1 the card was copied to `/config/www/snapmaker_u1_card/`; since 2.1.2 the integration moves its resource to the new path and deletes only that old copy of its own file.

If a page is loaded while Home Assistant is still starting (a tab or the app during a restart), the card can show "Custom element doesn't exist: snapmaker-u1-card" until the page is reloaded.

## Moonraker integration (optional)

Not needed since 2.0: the card gets all values and controls from this integration. We recommend not using the [Moonraker integration](https://github.com/marcolivierarsenault/moonraker-home-assistant) next to it: it queries the printer a second time and only adds load. If you keep it, the card prefers its own values and only falls back to the Moonraker entities when they are missing. With several printers set `prefix` in the card.
