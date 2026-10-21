# Architecture

This document explains how the integration and the card fit together. It is
meant for contributors; user documentation lives in the [README](../README.md).

## Overview

```
 Snapmaker U1 (Moonraker + Klipper, Snapmaker firmware)
   │  HTTP (status, files, history)        WebSocket (live subscription, print start)
   ▼                                        ▼
 api.py  MoonrakerClient  ◄──────────────  live.py  LiveListener
   │                                        │ status diffs
   ▼                                        ▼
 coordinator/  U1Coordinator  (one per config entry, polls + live updates)
   │  U1Data snapshot
   ├─► sensor.py / binary_sensor.py / switch.py / update.py   (entities)
   ├─► layer_view.py, video.py, upload.py                      (HTTP views for the card)
   └─► services (__init__.py), voice.py (Assist intents)
                                              ▲
 frontend/src  ──esbuild──►  custom_components/.../frontend/snapmaker-u1-card.js
                             (served by the integration, reads entities + views)
```

The browser never talks to the printer. Everything goes through the Home
Assistant connection, so the card works the same locally, over VPN and through
Nabu Casa.

## Backend (`custom_components/snapmaker_u1_card`)

| Module | Responsibility |
|---|---|
| `__init__.py` | Entry setup, static paths and views, service registration |
| `api.py` | `MoonrakerClient` (HTTP + JSON-RPC over WebSocket) and `SpoolmanClient` |
| `live.py` | WebSocket subscription to `print_stats`, `toolhead`, `virtual_sdcard`, `exception_manager` |
| `coordinator/` | Polling, print tracking and all feature logic (see below) |
| `parsing.py` | Pure data processing (no HA imports): slots, files, mapping, cost, print tracking |
| `layers.py` | G-code parser: layer paths for the layer view and a time profile for remaining time |
| `jobs.py` | Job queue and "pause at layer" copies of a print file |
| `stats.py` | 12-month statistics from Moonraker's history, maintenance planner |
| `spools.py` | Spoolman state: assignment per head, booking usage |
| `archive.py` | Timelapse backup to the HA media folder |
| `backup.py` | Daily backup of the printer configuration |
| `errors.py` | Firmware exception codes to plain language (German/English) |
| `voice.py` | Assist intents and the sentence files they need |
| `resource.py` | Registers the card as a dashboard resource (second loading path) |
| `i18n.py` | German/English choice for messages created in Python |
| `sensor.py`, `binary_sensor.py`, `switch.py`, `select.py`, `update.py` | Entities |
| `layer_view.py`, `video.py`, `upload.py` | Authenticated HTTP endpoints used by the card |
| `config_flow.py`, `diagnostics.py` | Setup/options UI and the diagnostics download |

### The coordinator package

`U1Coordinator` (`coordinator/core.py`) owns all state, persistence and the
poll loop. Feature logic lives in mixins that only add methods:

| Mixin | Topic |
|---|---|
| `SpoolMixin` (`spools.py`) | Spoolman sync and spool assignment |
| `PrintMonitorMixin` (`monitor.py`) | Layer view, firmware messages, print events, run-out checks, live updates |
| `PrintJobMixin` (`jobs.py`) | Starting prints, pause copies, the queue |
| `UpkeepMixin` (`upkeep.py`) | Statistics, maintenance, self test, firmware check, config backup |
| `MediaMixin` (`media.py`) | Timelapses, file list, file management, thumbnails |
| `NotifyMixin` (`notify.py`) | Print end, notifications with actions, result photo |
| `PowerMixin` (`power.py`) | Power switch, clean shutdown, auto-off, idle-off |
| `PrinterSettingsMixin` (`printer.py`) | Firmware preferences, setting a slot's filament, camera wake-up |
| `ProgressNotifyMixin` (`progress.py`) | Ongoing Android progress notification with push budget |

`data.py` holds the `U1Data` snapshot handed to entities; `helpers.py` holds
constants and pure helper functions.

### Data flow of one poll

1. Ask Moonraker for the printer objects (skipped while the power switch is off).
2. Track the print (`parsing.track_print`): start/end detection, energy and
   tool change deltas, cost. A finished print goes to `NotifyMixin._finished`.
3. Side tasks on their own intervals: file list (60 s, rarely while printing),
   timelapses (5 min), statistics, Spoolman, firmware check, backups.
4. Publish a new `U1Data`; entities and the card update.

The live subscription delivers changes immediately (`PrintMonitorMixin._on_live`);
while it is up, polling slows down to a 30 s consistency check.

### Persistence

Everything that must survive a restart (running print baseline, history,
queue, Spoolman bookings, maintenance, archive state) is stored with
`homeassistant.helpers.storage.Store` per config entry
(`.storage/snapmaker_u1_card.<entry_id>.print_switches`).

## Frontend (`frontend/src`)

The card is plain web components without a framework. Sources are ES modules,
bundled by esbuild into the single file the integration ships:

| File | Content |
|---|---|
| `index.js` | Entry point: registers both cards and the card picker entries |
| `const.js`, `i18n.js`, `format.js`, `color.js`, `styles.js`, `editor.js` | Shared constants, translations, formatting, colour helpers, CSS, visual editor |
| `card/card.js` | `SnapmakerU1Card`: lifecycle (config, hass, timers), composed from mixins |
| `card/*.js` | One mixin per topic: state, controls, tabs (overview, files, control, system, history, timelapse), layer view, layout, rendering, zoom, print dialog, camera |
| `card/mini.js` | `SnapmakerU1MiniCard`, a subclass without camera |

Rendering rules that matter:

- A full rebuild only happens when the structure changes (`RenderMixin._render`).
  Values are patched in place, so the camera `<img>` keeps its MJPEG connection.
- The camera stream only runs while the card is visible and not in edit mode;
  browsers allow only six connections per host over HTTP/1.1.
- UI texts are German in the source and translated with `tr()`; English lives
  in `EN` in `i18n.js`.

## Snapmaker specifics

Facts taken from Snapmaker's published firmware sources (u1-klipper, u1-moonraker):

- Prints with filament mapping can only be started over the WebSocket
  (`server.files.start_local_print`), not over HTTP.
- There is no "pause at layer" command; `PAUSE` is inserted into a copy of the file.
- The `camera` root is read-only; deleting timelapses goes through Snapmaker's
  internal camera service with undocumented parameters (probed once).
- Klipper semantics apply to G-code parsing: `G90` does not reset relative
  extrusion set by `M83` (Orca writes both).
- `virtual_sdcard.file_position` runs about 1-2 s ahead of the motion.
- Firmware preferences are changed with `SET_PRINT_PREFERENCES`, a slot's filament with
  `SET_PRINT_FILAMENT_CONFIG` (refused for official spools without `FORCE=1`); both in
  u1-klipper `print_task_config.py`. RFID tag data comes from `filament_detect.info`.
- The stock camera stops after a while; `camera.start_monitor` (WebSocket, proxied by
  u1-moonraker `repeater.py` to the closed camera service) keeps it running.
