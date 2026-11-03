# Entitäten und Dienste

[← Zurück zum README](../../README.de.md)

**Inhalt:** [Entitäten](#entitäten) · [Dienste](#dienste)

## Entitäten

| Entität | Inhalt |
|---|---|
| `sensor.…_filamente` | Anzahl geladener Slots, Attribut `slots` mit allen vier Köpfen, `preferences` |
| `sensor.…_slot_1` … `_slot_4` | Material des Slots oder `leer`, Farbe und Hersteller als Attribute – gut für Automationen |
| `sensor.…_druckdateien` | neueste Druckdateien mit Filamenten und Vorschaubild |
| `sensor.…_werkzeugwechsel` | Kopfwechsel gesamt (Firmware-Zähler), Attribut `heads` je Kopf mit `switches`, `retries`, `errors`, `since_maintenance` |
| `sensor.…_werkzeugwechsel_druck` | Wechsel im laufenden Druck, sonst im letzten; Attribute `in_progress`, `file`, `result`, `started`, `ended` |
| `switch.…_netzschalter` | sicherer Netzschalter (nur mit eingetragenem Schalter). **Automationen sollten diesen schalten, nicht die Steckdose direkt.** |
| `sensor.…_energie_druck` | kWh des laufenden bzw. letzten Drucks (nur mit Energiezähler) |
| `sensor.…_kosten_druck` | Stromkosten bisher bzw. Gesamtkosten des letzten Drucks; Attribute `energy_cost`, `filament_cost` |
| `sensor.…_druckhistorie` | Anzahl, Attribut `prints` mit den letzten 20 Drucken |
| `sensor.…_zeitraffer` | Anzahl, Attribut `videos`; mit Sicherung `archive` (gesicherte Videos, Status) |
| `sensor.…_warteschlange` | Anzahl Aufträge, Attribut `jobs` (id, Datei, Zuordnung, Optionen, Pause) |
| `sensor.…_druckstunden` | Druckstunden gesamt (Moonraker), Attribute `months`, `totals`, `top_files` |
| `sensor.…_druckerwerte` | 2.0: Zustand von Klipper, Attribute `values` (alle Druckerwerte für die Karte, benannt wie die Entitäten der Moonraker-Integration: `bed_temperature`, `extruder1_target`, `cavity_fan`, `led_cavity_led` …) und `attrs` (Einheit, Reglerbereich). Wird nicht aufgezeichnet |
| `sensor.…_betttemperatur`, `sensor.…_duse_1_temperatur` … `_4_…`, `sensor.…_innenraumtemperatur` | 2.0: Temperaturen |
| `sensor.…_fortschritt`, `sensor.…_druckstatus`, `sensor.…_schicht` | 2.0: Fortschritt in %, Druckzustand (`standby`, `printing`, `paused`, `complete`, `cancelled`, `error`), aktuelle Schicht (Attribut `total_layer`) |
| `number.…_bett_solltemperatur`, `number.…_duse_1_solltemperatur` … `_4_…`, `number.…_bauteillufter`, `number.…_geschwindigkeit` | 2.0: Solltemperaturen, Bauteillüfter, Geschwindigkeit |
| `button.…_druck_pausieren`, `…_druck_fortsetzen`, `…_druck_abbrechen`, `…_not_halt`, `…_referenzfahrt_alle_achsen` | 2.0: Drucksteuerung und Referenzfahrt |
| `light.…_innenraumlicht` | 2.0: Innenraumlicht (und weitere `led`-Objekte des Druckers) |
| `sensor.…_wartung_fallig` | Anzahl fälliger Wartungspunkte, Attribut `items` |
| `sensor.…_druckermeldungen` | Anzahl offener Firmware-Meldungen, Attribut `errors` mit Text (de/en), Hinweis und Rohcode |
| `switch.…_filament_automatisch_nachfullen`, `…_nachfullen_ohne_farbprufung`, `…_verhedderungs_erkennung`, `…_licht_aus_nach_dem_druck` | Firmware-Einstellungen (am Drucker gespeichert) |
| `select.…_empfindlichkeit_verhedderungs_erkennung` | `low`, `medium`, `high` |
| `number.…_flussrate` | Flussrate in % (M221, 50–150), auch während des Drucks |
| `sensor.…_bettnivellierung_spanne` | höchster minus tiefster Messpunkt des geladenen Bed Mesh in mm; Attribute `matrix`, `min`, `max`, `mean`, `profile`, `mesh_min`, `mesh_max` |
| `sensor.…_top_cover`, `number.…_top_cover_abluftlufter`, `number.…_top_cover_umluftlufter` | erst wenn eine Top Cover erkannt wird: Kammermodus (`idle`, `cool`, `preheat`, `hot`), Attribute `exhaust`, `inner`, `inner_rpm`, `filter_hours`, `desired_temp`; Lüfter in % |

Das Attribut `head_states` von `sensor.…_filamente` sagt pro Kopf, ob er `parked` (im Dock) oder `active` (auf dem Schlitten) ist.

Die Slot-Sensoren tragen zusätzlich das Attribut `rfid` mit den Daten des Spulen-Chips.

Ereignis `snapmaker_u1_card_print_finished` bei jedem Druckende, mit `file`, `name`, `result`, `duration_s`, `tool_changes`, `energy_kwh`, `energy_cost`, `filament_g`, `filament_cost`, `total_cost` – für eigene Automationen.

## Dienste

### `snapmaker_u1_card.start_print`

```yaml
action: snapmaker_u1_card.start_print
data:
  filename: Benchy_PLA.gcode
  mapping: {"0": 2, "1": 0}   # Filament 1 → Kopf 3, Filament 2 → Kopf 1; weglassen = automatisch
  bed_leveling: true
  flow_calibration: false
  timelapse: false
```

Ohne `mapping` nimmt der Dienst denselben Vorschlag wie die Karte. Mit `pause_layers: [12, 40]` hält der Drucker vor diesen Schichten an.

**Wie „Pause vor Schicht“ funktioniert.** Klipper und die U1-Firmware haben dafür keinen Befehl. Die Integration legt deshalb eine Kopie der Datei an (`<Name>.u1pause-12-40.gcode`), schreibt dort `PAUSE` vor den Schichtwechsel (`;LAYER_CHANGE` aus Orca/Snapmaker Orca, auch Cura-Markierungen) und druckt die Kopie. Die Firmware behandelt `PAUSE` in Dateien ausdrücklich. Die Kopie ist in der Dateiliste ausgeblendet und wird nach dem Druck gelöscht; die Historie zeigt die Originaldatei. Fortsetzen am Display oder mit dem Knopf in der Karte.

### Warteschlange

```yaml
action: snapmaker_u1_card.queue_add      # gleiche Felder wie start_print
data: {filename: Halter.gcode, mapping: {"0": 1}, pause_layers: [8]}
action: snapmaker_u1_card.queue_start    # ersten Auftrag starten (oder job_id)
action: snapmaker_u1_card.queue_move     # job_id, position (0 = vorne)
action: snapmaker_u1_card.queue_remove   # job_id
action: snapmaker_u1_card.queue_clear
```

Moonrakers eigene Warteschlange (`[job_queue]`) ist auf dem U1 nicht geladen und kennt keine Filamentzuordnung, deshalb führt die Integration die Liste selbst. Sie übersteht Neustarts. Nach einem Druck kommt eine Benachrichtigung „Nächster Auftrag wartet“ (an die eingetragenen Dienste).

### `snapmaker_u1_card.maintenance_done` / `backup_timelapses` / `backup_config`

`item: plate | nozzle | rails | belts | filter | carbon_rods | lead_screws | coupling | pogo` setzt den Wartungszähler zurück. `backup_timelapses` sichert sofort und räumt danach auf dem Drucker auf. `backup_config` sichert die Drucker-Konfiguration sofort und antwortet mit `status` (`saved`, `unchanged`, `empty`), Anzahl Dateien, übersprungenen Dateien und den vorhandenen Ständen.

### `snapmaker_u1_card.set_filament` / `set_preference`

```yaml
action: snapmaker_u1_card.set_filament   # Spule ohne RFID; nicht während eines Drucks
data:
  slot: 2            # Kopf 1–4
  type: PETG
  sub_type: HF       # optional
  vendor: Generic    # optional
  color: "#1B5E20"   # optional
  colors: ["#C0C0C0", "#FFD700"]   # optional: mehrfarbige Spule (bis 5), ersetzt color
  force: false       # true = auch eine offizielle Snapmaker-Spule überschreiben

action: snapmaker_u1_card.set_preference
data:
  preference: auto_replenish   # replenish_ignore_color | entangle_detect | end_led_off | entangle_sensitivity
  value: true                  # entangle_sensitivity: low | medium | high
```

Beides geht an die Firmware (`SET_PRINT_FILAMENT_CONFIG`, `SET_PRINT_PREFERENCES` aus u1-klipper `print_task_config.py`). Der Drucker speichert die Werte selbst, das Display zeigt sie ebenfalls.

### `snapmaker_u1_card.send_gcode` / `tool_change`

```yaml
action: snapmaker_u1_card.send_gcode     # gibt die Antworten des Druckers zurück
data:
  script: |
    M105
    SET_GCODE_OFFSET Z_ADJUST=-0.02
response_variable: antwort               # {script, ok, error, responses}

action: snapmaker_u1_card.tool_change    # nicht während eines Drucks
data:
  head: 3          # 1–4
  action: pick     # pick = diesen Kopf aufnehmen, park = Kopf vom Schlitten ablegen
```

`send_gcode` nimmt höchstens 20 Zeilen. Während eines Drucks sind nur Feineinstellungen erlaubt: Temperaturen (`M104`, `M140`, `SET_HEATER_TEMPERATURE`), Lüfter (`M106`, `M107`, `SET_FAN_SPEED`), Geschwindigkeit und Flussrate (`M220`, `M221`), `SET_GCODE_OFFSET`, `SET_PRESSURE_ADVANCE`, `SET_VELOCITY_LIMIT`, `SET_RETRACTION`, `SET_LED`, `SET_PURIFIER`, Meldungen, `PAUSE`/`RESUME`/`CANCEL_PRINT`, `EXCLUDE_OBJECT`, `M112` und lesende `GET_…`/`QUERY_…`-Befehle. Alles, was fährt, referenziert, misst oder Köpfe wechselt, wird bis zum Druckende abgelehnt. Lehnt die Firmware einen Befehl ab, kommt das als `ok: false` mit der Meldung zurück. Die Antworten stammen aus dem G-Code-Speicher von Moonraker.

`tool_change` nutzt die Befehle der Firmware (`T<n> A0` nimmt den physischen Kopf n ohne Filamentzuordnung, `PARK_EXTRUDER…` legt den Kopf vom Schlitten ab). Bei Bedarf fährt der Drucker vorher X/Y an.

### `snapmaker_u1_card.machine_command`

2.0: Das, was die Bedienelemente der Karte senden, auch für Automationen. `action`: `pause`, `resume`, `cancel`, `emergency_stop`, `home` (`target`: `all`, `x`, `y`, `z`; im Druck gesperrt), `set` (`target`: `bed_target`, `extruder…_target`, `fan_speed`, `speed_factor`, `<lüfter>_speed`; `value`: Zahl) oder `switch` (`target`: `output_pin_<name>`, `led_<name>`; `value`: an/aus). Nur Objekte, die der Drucker meldet; Werte werden begrenzt (Bett 0–120 °C, Düse 0–300 °C, Geschwindigkeit 10–300 %).

```yaml
action: snapmaker_u1_card.machine_command
data: { action: set, target: bed_target, value: 60 }
```

### `snapmaker_u1_card.refresh`

Lädt Dateiliste, Zeitraffer und Filamente sofort neu.

### `snapmaker_u1_card.power_on` / `power_off`

Einschalten (optional `wait: true`: erst zurück, wenn Klipper bereit ist) bzw. sicher ausschalten: herunterfahren (`machine.shutdown`), warten bis der Drucker nicht mehr antwortet plus 10 s, dann Strom aus.

Abgelehnt bzw. abgebrochen wird das Ausschalten, wenn

- ein Druck läuft oder pausiert ist, auch wenn der Drucker gerade kurz nicht antwortet (WLAN-Aussetzer zählt nicht als „fertig“),
- der Drucker direkt vor dem Herunterfahren oder vor dem Abschalten meldet, dass er druckt oder eine Heizung einen Sollwert hat (z. B. Druck am Display gestartet),
- der Drucker gerade über Auto-Ein hochfährt.

Für einen abgestürzten Drucker, der noch als druckend erfasst ist: `force: true` (die Karte bietet das nur an, wenn der Drucker nicht antwortet). Während des Herunterfahrens nimmt `start_print` keine Drucke an.
