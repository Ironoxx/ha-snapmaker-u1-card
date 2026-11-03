# Entities and services

[← Back to the README](../README.md)

**Contents:** [Entities](#entities) · [Services](#services)

## Entities

Entity IDs follow the Home Assistant language at setup time; the English names are:

| Entity | Content |
|---|---|
| `sensor.…_filaments` | number of loaded slots, attribute `slots` with all four heads, `preferences` |
| `sensor.…_slot_1` … `_slot_4` | material of the slot or empty, colour and vendor as attributes, handy for automations |
| `sensor.…_print_files` | newest print files with filaments and thumbnail |
| `sensor.…_tool_changes` | total head changes (firmware counter), attribute `heads` per head with `switches`, `retries`, `errors`, `since_maintenance` |
| `sensor.…_tool_changes_print` | changes in the running print, otherwise the last one; attributes `in_progress`, `file`, `result`, `started`, `ended` |
| `switch.…_power` | safe power switch (only with a configured switch). **Automations should switch this one, not the plug directly.** |
| `sensor.…_energy_print` | kWh of the running or last print (only with an energy meter) |
| `sensor.…_cost_print` | energy cost so far or total cost of the last print; attributes `energy_cost`, `filament_cost` |
| `sensor.…_print_history` | count, attribute `prints` with the last 20 prints |
| `sensor.…_timelapses` | count, attribute `videos`; with backup also `archive` (backed-up videos, status) |
| `sensor.…_queue` | number of jobs, attribute `jobs` (id, file, mapping, options, pauses) |
| `sensor.…_print_hours` | total print hours (Moonraker), attributes `months`, `totals`, `top_files` |
| `sensor.…_maintenance_due` | number of maintenance items due, attribute `items` |
| `sensor.…_printer_messages` | number of open firmware messages, attribute `errors` with text (de/en), hint and raw code |
| `sensor.…_time_remaining` / `sensor.…_finish_time` | remaining time and expected end of the running print |
| `binary_sensor.…_live_connection` | live subscription to Moonraker up or not |
| `sensor.…_printer_values` | 2.0: state of Klipper, attributes `values` (all printer values for the card, named like the Moonraker integration's entities: `bed_temperature`, `extruder1_target`, `cavity_fan`, `led_cavity_led` …) and `attrs` (unit, slider range). Not recorded |
| `sensor.…_bed_temperature`, `sensor.…_nozzle_1_temperature` … `_4_…`, `sensor.…_chamber_temperature` | 2.0: temperatures |
| `sensor.…_progress`, `sensor.…_print_state`, `sensor.…_layer` | 2.0: progress in %, print state (`standby`, `printing`, `paused`, `complete`, `cancelled`, `error`), current layer (attribute `total_layer`) |
| `number.…_bed_target`, `number.…_nozzle_1_target` … `_4_…`, `number.…_part_cooling_fan`, `number.…_speed_factor` | 2.0: target temperatures, part fan, speed |
| `button.…_pause_print`, `…_resume_print`, `…_cancel_print`, `…_emergency_stop`, `…_home_all_axes` | 2.0: print controls and homing |
| `light.…_chamber_light` | 2.0: chamber light (and further `led` objects of the printer) |
| `update.…_firmware` | installed and latest firmware |
| `switch.…_auto_replenish_filament`, `…_replenish_ignoring_colour`, `…_filament_entangle_detection`, `…_light_off_after_print` | firmware preferences (stored on the printer) |
| `select.…_entangle_detection_sensitivity` | `low`, `medium`, `high` |
| `number.…_flow` | flow in % (M221, 50–150), also during a print |
| `sensor.…_bed_mesh_spread` | highest minus lowest probed point of the loaded bed mesh in mm; attributes `matrix`, `min`, `max`, `mean`, `profile`, `mesh_min`, `mesh_max` |
| `sensor.…_top_cover`, `number.…_top_cover_exhaust_fan`, `number.…_top_cover_circulation_fan` | only once a top cover is detected: chamber mode (`idle`, `cool`, `preheat`, `hot`), attributes `exhaust`, `inner`, `inner_rpm`, `filter_hours`, `desired_temp`; fans in % |

The attribute `head_states` of `sensor.…_filaments` says per head whether it is `parked` or `active` (on the carriage).

The event `snapmaker_u1_card_print_finished` fires at every print end with `file`, `name`, `result`, `duration_s`, `tool_changes`, `energy_kwh`, `energy_cost`, `filament_g`, `filament_cost`, `total_cost`, for your own automations.

## Services

### `snapmaker_u1_card.start_print`

```yaml
action: snapmaker_u1_card.start_print
data:
  filename: Benchy_PLA.gcode
  mapping: {"0": 2, "1": 0}   # filament 1 → head 3, filament 2 → head 1; omit = automatic
  bed_leveling: true
  flow_calibration: false
  timelapse: false
```

Without `mapping` the service uses the same suggestion as the card. With `pause_layers: [12, 40]` the printer pauses before these layers.

**How "pause at layer" works.** Neither Klipper nor the U1 firmware has a command for it. The integration therefore creates a copy of the file (`<name>.u1pause-12-40.gcode`), writes `PAUSE` before the layer change (`;LAYER_CHANGE` from Orca/Snapmaker Orca, Cura markers too) and prints the copy. The firmware handles `PAUSE` in files explicitly. The copy is hidden in the file list and deleted after the print; the history shows the original file. Resume on the display or with the button in the card.

### Queue

```yaml
action: snapmaker_u1_card.queue_add      # same fields as start_print
data: {filename: Holder.gcode, mapping: {"0": 1}, pause_layers: [8]}
action: snapmaker_u1_card.queue_start    # start the first job (or job_id)
action: snapmaker_u1_card.queue_move     # job_id, position (0 = front)
action: snapmaker_u1_card.queue_remove   # job_id
action: snapmaker_u1_card.queue_clear
```

Moonraker's own queue (`[job_queue]`) is not loaded on the U1 and knows nothing about filament mapping, so the integration keeps its own list. It survives restarts. After a print a "Next job waiting" notification is sent (to the configured services).

### `snapmaker_u1_card.maintenance_done` / `backup_timelapses` / `backup_config`

`item: plate | nozzle | rails | belts | filter | carbon_rods | lead_screws | coupling | pogo` resets the maintenance counter. `backup_timelapses` backs up right away and then cleans up the printer. `backup_config` backs up the printer configuration right away and responds with `status` (`saved`, `unchanged`, `empty`), the number of files, skipped files and the existing snapshots.

### `snapmaker_u1_card.set_filament` / `set_preference`

```yaml
action: snapmaker_u1_card.set_filament   # spool without RFID tag; not during a print
data:
  slot: 2            # head 1–4
  type: PETG
  sub_type: HF       # optional
  vendor: Generic    # optional
  color: "#1B5E20"   # optional
  colors: ["#C0C0C0", "#FFD700"]   # optional: multi-colour spool (up to 5), replaces color
  force: false       # true = also overwrite an official Snapmaker spool

action: snapmaker_u1_card.set_preference
data:
  preference: auto_replenish   # replenish_ignore_color | entangle_detect | end_led_off | entangle_sensitivity
  value: true                  # entangle_sensitivity: low | medium | high
```

Both go to the firmware (`SET_PRINT_FILAMENT_CONFIG`, `SET_PRINT_PREFERENCES` from u1-klipper `print_task_config.py`). The printer stores the values itself, the display shows them too.

### `snapmaker_u1_card.send_gcode` / `tool_change`

```yaml
action: snapmaker_u1_card.send_gcode     # returns the printer's answers
data:
  script: |
    M105
    SET_GCODE_OFFSET Z_ADJUST=-0.02
response_variable: answer                # {script, ok, error, responses}

action: snapmaker_u1_card.tool_change    # not during a print
data:
  head: 3          # 1–4
  action: pick     # pick = take this head, park = put the head on the carriage back
```

`send_gcode` takes at most 20 lines. While a print runs only tuning is allowed: temperatures (`M104`, `M140`, `SET_HEATER_TEMPERATURE`), fans (`M106`, `M107`, `SET_FAN_SPEED`), speed and flow (`M220`, `M221`), `SET_GCODE_OFFSET`, `SET_PRESSURE_ADVANCE`, `SET_VELOCITY_LIMIT`, `SET_RETRACTION`, `SET_LED`, `SET_PURIFIER`, messages, `PAUSE`/`RESUME`/`CANCEL_PRINT`, `EXCLUDE_OBJECT`, `M112` and read-only `GET_…`/`QUERY_…` commands. Everything that moves, homes, probes or changes heads is refused until the print is over. A refusal by the firmware comes back as `ok: false` with the message. The answers are read from Moonraker's gcode store.

`tool_change` uses the firmware's own commands (`T<n> A0` takes physical head n without filament mapping, `PARK_EXTRUDER…` parks the head on the carriage). The printer homes X/Y first if needed.

### `snapmaker_u1_card.machine_command`

2.0: what the card's controls send, usable in automations too. `action`: `pause`, `resume`, `cancel`, `emergency_stop`, `home` (`target`: `all`, `x`, `y`, `z`; locked during a print), `set` (`target`: `bed_target`, `extruder…_target`, `fan_speed`, `speed_factor`, `<fan>_speed`; `value`: number) or `switch` (`target`: `output_pin_<name>`, `led_<name>`; `value`: on/off). Only objects the printer reports are accepted, values are clamped (bed 0–120 °C, nozzle 0–300 °C, speed 10–300 %).

```yaml
action: snapmaker_u1_card.machine_command
data: { action: set, target: bed_target, value: 60 }
```

### `snapmaker_u1_card.refresh`

Reloads file list, timelapses and filaments right away.

### `snapmaker_u1_card.power_on` / `power_off`

Switch on (optionally `wait: true`: only return once Klipper is ready) or switch off safely: shut down (`machine.shutdown`), wait until the printer stops answering plus 10 s, then cut the power.

Switching off is refused or aborted when

- a print is running or paused, even if the printer briefly does not answer (a WiFi dropout does not count as "finished"),
- the printer reports right before the shutdown or before cutting power that it is printing or a heater has a target (e.g. a print started on the display),
- the printer is booting via auto-on.

For a crashed printer that is still recorded as printing: `force: true` (the card only offers this when the printer does not answer). While shutting down, `start_print` accepts no prints.
