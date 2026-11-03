"""Printer values the card used to take from the Moonraker integration.

Since 2.0 the integration reads them itself (live subscription plus poll) and
hands them to the card as one attribute dict, named like the Moonraker
integration's entities (``bed_temperature``, ``extruder1_target``,
``cavity_fan`` …) so the card can use either source. Klipper object names
differ between configs, so the objects are taken from ``/printer/objects/list``
and named by the same rules as the Moonraker integration:

* ``temperature_sensor X`` and TMC drivers with a temperature → ``X_temp``
* ``fan`` → ``fan_speed``; ``fan_generic|heater_fan|controller_fan X`` → ``X``
* ``output_pin X`` → ``output_pin_X``; ``led X`` → ``led_X``
* ``mcu`` → ``mcu_load``/``mcu_awake``; ``mcu X`` → ``mcu_X_load``/``mcu_X_awake``
* ``filament_motion_sensor|filament_switch_sensor X`` → ``X``

HA-free, so it can be tested on its own.
"""

from __future__ import annotations

import math
from typing import Any

HEATERS = ("extruder", "extruder1", "extruder2", "extruder3", "heater_bed")
FAN_TYPES = ("fan_generic", "heater_fan", "controller_fan", "temperature_fan")
TMC_PREFIX = "tmc"
SENSOR_TYPES = ("filament_motion_sensor", "filament_switch_sensor")

# Slider ranges for the card (the configured max_temp is not read; sane U1 limits)
BED_MAX = 120
NOZZLE_MAX = 300
SPEED_MIN, SPEED_MAX = 10, 300

STATIC_FIELDS: dict[str, list[str] | None] = {
    "print_stats": ["state", "filename", "info", "print_duration", "total_duration", "filament_used", "message"],
    "virtual_sdcard": ["file_position", "progress"],
    "display_status": ["progress", "message"],
    "toolhead": ["extruder", "position", "homed_axes"],
    "gcode_move": ["speed_factor", "speed", "extrude_factor"],
    "idle_timeout": ["state"],
    "webhooks": ["state", "state_message"],
    "system_stats": ["sysload", "memavail"],
    "fan": ["speed"],
}


def _split(obj: str) -> tuple[str, str]:
    kind, _, name = obj.partition(" ")
    return kind, name.strip()


def subscription(objects: list[str] | None) -> dict[str, list[str] | None]:
    """Objects and fields to subscribe to (only those the printer has)."""
    have = set(objects or [])
    out: dict[str, list[str] | None] = {
        k: v for k, v in STATIC_FIELDS.items() if not objects or k in have or k == "webhooks"
    }
    for obj in objects or []:
        kind, name = _split(obj)
        if obj in HEATERS:
            out[obj] = ["temperature", "target", "power"]
        elif name and (kind == "temperature_sensor" or kind.startswith(TMC_PREFIX)):
            out[obj] = ["temperature"]
        elif kind in FAN_TYPES and name:
            out[obj] = ["speed", "rpm"] if kind != "temperature_fan" else ["speed", "temperature", "target"]
        elif kind == "output_pin" and name:
            out[obj] = ["value"]
        elif kind == "led" and name:
            out[obj] = ["color_data"]
        elif kind in SENSOR_TYPES and name:
            out[obj] = ["filament_detected", "enabled"]
        elif kind == "mcu":
            out[obj] = ["last_stats"]
    return out


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _pct(value: Any, digits: int = 0) -> float | None:
    v = _num(value)
    return None if v is None else round(v * 100, digits)


def _round(value: Any, digits: int = 1) -> float | None:
    v = _num(value)
    return None if v is None else round(v, digits)


def _mcu(stats: Any) -> tuple[float | None, float | None]:
    """Load and awake time in percent, computed like Mainsail/Fluidd."""
    if not isinstance(stats, dict):
        return None, None
    avg, dev, awake = (_num(stats.get(k)) for k in ("mcu_task_avg", "mcu_task_stddev", "mcu_awake"))
    load = round((avg + 3 * dev) / 0.0025 * 100, 2) if avg is not None and dev is not None else None
    return load, (round(awake / 5 * 100, 2) if awake is not None else None)


def build(status: dict[str, Any], extras: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, dict]]:
    """Values (key → state) and per-key attributes (unit, slider range) for the card.

    ``extras``: values from outside Klipper's objects (Moonraker memory, job queue,
    totals, file metadata) under their final keys.
    """
    v: dict[str, Any] = {}
    a: dict[str, dict] = {}

    def put(key: str, value: Any, **attrs: Any) -> None:
        if value is None:
            return
        v[key] = value
        if attrs:
            a[key] = attrs

    wh = status.get("webhooks") or {}
    put("printer_state", wh.get("state"))
    put("printer_message", wh.get("state_message"))

    ps = status.get("print_stats") or {}
    info = ps.get("info") if isinstance(ps.get("info"), dict) else {}
    put("current_print_state", ps.get("state"))
    put("current_print_message", ps.get("message") or None)
    put("filename", ps.get("filename") or None)
    put("current_layer", info.get("current_layer"))
    put("total_layer", info.get("total_layer"))
    dur = _num(ps.get("print_duration"))
    put("print_duration", None if dur is None else round(dur / 60, 2), unit_of_measurement="min")
    used = _num(ps.get("filament_used"))
    put("filament_used", None if used is None else round(used / 1000, 2), unit_of_measurement="m")

    vsd = status.get("virtual_sdcard") or {}
    ds = status.get("display_status") or {}
    progress = _num(vsd.get("progress"))
    if progress is None:
        progress = _num(ds.get("progress"))
    put("progress", None if progress is None else round(progress * 100, 1), unit_of_measurement="%")
    put("current_display_message", ds.get("message") or None)

    put("idle_timeout_state", (status.get("idle_timeout") or {}).get("state"))

    th = status.get("toolhead") or {}
    pos = th.get("position")
    if isinstance(pos, list) and len(pos) >= 3:
        for axis, val in zip("xyz", pos[:3], strict=False):
            put(f"toolhead_position_{axis}", _round(val, 2), unit_of_measurement="mm")

    gm = status.get("gcode_move") or {}
    sf = _num(gm.get("speed_factor"))
    put("speed_factor", None if sf is None else round(sf * 100), unit_of_measurement="%",
        min=SPEED_MIN, max=SPEED_MAX, step=1)
    speed = _num(gm.get("speed"))
    if speed is not None and v.get("current_print_state") == "printing":
        # requested feed rate (mm/min) x speed factor; U1 has no motion_report
        put("print_speed", round(speed / 60 * (sf or 1.0)), unit_of_measurement="mm/s")

    ss = status.get("system_stats") or {}
    put("system_load", _round(ss.get("sysload"), 2))

    for name in HEATERS:
        h = status.get(name)
        if not isinstance(h, dict):
            continue
        key = "bed" if name == "heater_bed" else name
        put(f"{key}_temperature", _round(h.get("temperature")), unit_of_measurement="°C")
        put(f"{key}_target", _round(h.get("target"), 0), unit_of_measurement="°C",
            min=0, max=BED_MAX if name == "heater_bed" else NOZZLE_MAX, step=1)
        put(f"{key}_power", _pct(h.get("power")), unit_of_measurement="%")

    fan = status.get("fan")
    if isinstance(fan, dict):
        put("fan_speed", _pct(fan.get("speed")), unit_of_measurement="%", min=0, max=100, step=1)

    for obj, data in status.items():
        if not isinstance(data, dict):
            continue
        kind, name = _split(obj)
        if not name and kind != "mcu":
            continue
        if kind == "temperature_sensor" or (kind.startswith(TMC_PREFIX) and "temperature" in data):
            put(f"{name}_temp", _round(data.get("temperature")), unit_of_measurement="°C")
        elif kind in FAN_TYPES:
            put(name, _pct(data.get("speed")), unit_of_measurement="%")
            if kind == "fan_generic":
                put(f"{name}_speed", _pct(data.get("speed")), unit_of_measurement="%", min=0, max=100, step=1)
        elif kind == "output_pin":
            val = _num(data.get("value"))
            put(f"output_pin_{name}", None if val is None else ("on" if val > 0 else "off"))
        elif kind == "led":
            colors = data.get("color_data")
            first = colors[0] if isinstance(colors, list) and colors and isinstance(colors[0], list) else []
            level = max((_num(c) or 0.0 for c in first), default=0.0)
            put(f"led_{name}", "on" if level > 0 else "off", brightness=round(level * 255))
        elif kind in SENSOR_TYPES:
            det = data.get("filament_detected")
            if isinstance(det, bool):
                put(name, "on" if det else "off")
        elif kind == "mcu":
            load, awake = _mcu(data.get("last_stats"))
            prefix = f"mcu_{name}" if name else "mcu"
            put(f"{prefix}_load", load, unit_of_measurement="%")
            put(f"{prefix}_awake", awake, unit_of_measurement="%")

    for key, value in (extras or {}).items():
        if isinstance(value, tuple):
            put(key, value[0], **value[1])
        else:
            put(key, value)
    return v, a


# ── Commands ─────────────────────────────────────────────────────────────────
# The card's controls, translated to Klipper commands. Only objects the printer
# reported are accepted, so no free text reaches the printer.

class CommandError(ValueError):
    """Refused command (unknown target, value out of range)."""


def set_gcode(key: str, value: float, objects: list[str]) -> str:
    """G-code for a number the card sets (target temperatures, fans, speed)."""
    have = set(objects)
    try:
        val = float(value)
    except (TypeError, ValueError) as err:
        raise CommandError(f"Invalid value {value!r}") from err
    if not math.isfinite(val):
        raise CommandError(f"Invalid value {value!r}")
    if key == "bed_target" and "heater_bed" in have:
        return f"SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={_clamp(val, 0, BED_MAX):.0f}"
    if key.endswith("_target") and key[: -len("_target")] in HEATERS and key[: -len("_target")] in have:
        return f"SET_HEATER_TEMPERATURE HEATER={key[: -len('_target')]} TARGET={_clamp(val, 0, NOZZLE_MAX):.0f}"
    if key == "fan_speed" and "fan" in have:
        return f"M106 S{round(_clamp(val, 0, 100) * 255 / 100)}"
    if key == "speed_factor":
        return f"M220 S{_clamp(val, SPEED_MIN, SPEED_MAX):.0f}"
    if key.endswith("_speed") and f"fan_generic {key[: -len('_speed')]}" in have:
        return f"SET_FAN_SPEED FAN={key[: -len('_speed')]} SPEED={_clamp(val, 0, 100) / 100:.2f}"
    raise CommandError(f"Unknown setting {key!r}")


def switch_gcode(key: str, on: bool, objects: list[str]) -> str:
    """G-code for an on/off control: ``output_pin_X`` or ``led_X``."""
    have = set(objects)
    if key.startswith("output_pin_") and f"output_pin {key[len('output_pin_'):]}" in have:
        return f"SET_PIN PIN={key[len('output_pin_'):]} VALUE={1 if on else 0}"
    if key.startswith("led_") and f"led {key[len('led_'):]}" in have:
        level = 1 if on else 0
        return f"SET_LED LED={key[len('led_'):]} RED={level} GREEN={level} BLUE={level} WHITE={level}"
    raise CommandError(f"Unknown switch {key!r}")


HOME_AXES = {"all": "G28", "x": "G28 X", "y": "G28 Y", "z": "G28 Z"}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
