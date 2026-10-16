"""Pure data processing without Home Assistant dependencies.

Everything here is deliberately free of HA imports so it can be tested in
isolation. The field names come from Snapmaker's published source code:

* ``print_task_config`` - u1-klipper/klippy/extras/print_task_config.py
  (DEFAULT_PRINT_TASK_CONFIG, get_status, SET_PRINT_TASK_PARAMETERS)
* file metadata - u1-moonraker/moonraker/components/file_manager/metadata.py
  (SUPPORTED_DATA, PrusaSlicer parser)
"""

from __future__ import annotations

import posixpath
import re
from typing import Any

PHYSICAL_SLOTS = 4
LOGICAL_EXTRUDERS = 32
PRINTABLE_SUFFIXES = (".gcode", ".3mf")

_HEX6 = re.compile(r"^#?([0-9a-fA-F]{6})")


def _at(seq: Any, idx: int, default: Any = None) -> Any:
    if isinstance(seq, (list, tuple)) and 0 <= idx < len(seq):
        return seq[idx]
    return default


def _clean(value: Any) -> str | None:
    """Snapmaker uses 'NONE' as a placeholder for empty fields."""
    if value is None:
        return None
    text = str(value).strip().strip('"').strip()
    if not text or text.upper() == "NONE":
        return None
    return text


def normalize_color(value: Any) -> str | None:
    """'1B5E20FF', '#1b5e20' or 0xFF1B5E20 -> '#1B5E20'."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"#{value & 0xFFFFFF:06X}"
    match = _HEX6.match(str(value).strip())
    return f"#{match.group(1).upper()}" if match else None


def parse_slots(ptc: dict[str, Any] | None, detect: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """print_task_config -> a list of four slots."""
    ptc = ptc or {}
    slots = []
    for i in range(PHYSICAL_SLOTS):
        multi = _at(ptc.get("filament_color_multi"), i) or {}
        colors = [c for c in (normalize_color(x) for x in multi.get("colors", []) or []) if c]
        nums = multi.get("nums") or len(colors) or 1
        color = normalize_color(_at(ptc.get("filament_color_rgba"), i))
        if color is None:
            color = normalize_color(_at(ptc.get("filament_color"), i))
        if not colors and color:
            colors = [color]
        ftype = _clean(_at(ptc.get("filament_type"), i))
        slots.append(
            {
                "index": i,
                "loaded": bool(_at(ptc.get("filament_exist"), i, False)),
                "type": ftype,
                "sub_type": _clean(_at(ptc.get("filament_sub_type"), i)),
                "vendor": _clean(_at(ptc.get("filament_vendor"), i)),
                "color": color or (colors[0] if colors else None),
                "colors": colors[: max(1, int(nums))],
                "official": bool(_at(ptc.get("filament_official"), i, False)),
                "rfid": parse_rfid(_at((detect or {}).get("info"), i)),
            }
        )
    return slots


# Firmware preferences that can be changed at any time, also during a print
# (u1-klipper print_task_config.py, cmd_SET_PRINT_PREFERENCES): our key ->
# (print_task_config key, SET_PRINT_PREFERENCES parameter).
PRINTER_PREFERENCES: dict[str, tuple[str, str]] = {
    "auto_replenish": ("auto_replenish_filament", "AUTO_REPLENISH_FILAMENT"),
    "replenish_ignore_color": ("replenish_ignore_color", "REPLENISH_IGNORE_COLOR"),
    "entangle_detect": ("filament_entangle_detect", "FILAMENT_ENTANGLE_DETECT"),
    "end_led_off": ("end_led_turn_off", "END_LED_TURN_OFF"),
}
ENTANGLE_SENSITIVITIES = ("low", "medium", "high")


def parse_preferences(ptc: dict[str, Any] | None) -> dict[str, Any]:
    """Print options and firmware preferences currently set on the printer.

    Firmware preferences the printer does not report stay None (older firmware).
    """
    ptc = ptc or {}
    prefs: dict[str, Any] = {
        "bed_leveling": bool(ptc.get("auto_bed_leveling", False)),
        "flow_calibration": bool(ptc.get("flow_calibrate", False)),
        "timelapse": bool(ptc.get("time_lapse_camera", False)),
    }
    for key, (field, _param) in PRINTER_PREFERENCES.items():
        prefs[key] = bool(ptc[field]) if field in ptc else None
    sen = ptc.get("filament_entangle_sen")
    prefs["entangle_sensitivity"] = sen if sen in ENTANGLE_SENSITIVITIES else None
    return prefs


def preference_gcode(key: str, value: Any) -> str:
    """G-code for one firmware preference (validated)."""
    if key == "entangle_sensitivity":
        if value not in ENTANGLE_SENSITIVITIES:
            raise ValueError(f"Invalid sensitivity: {value}")
        return f"SET_PRINT_PREFERENCES FILAMENT_ENTANGLE_SEN={value}"
    if key not in PRINTER_PREFERENCES:
        raise ValueError(f"Unknown preference: {key}")
    return f"SET_PRINT_PREFERENCES {PRINTER_PREFERENCES[key][1]}={1 if value else 0}"


def _tag_number(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def parse_rfid(info: Any) -> dict[str, Any] | None:
    """Data read from a spool's RFID tag (filament_detect.info), None without a tag.

    Field layout: u1-klipper filament_protocol.FILAMENT_INFO_STRUCT. The tag
    stores the diameter in 1/100 mm, weight in g, length in m, drying time in h.
    """
    if not isinstance(info, dict):
        return None
    vendor = _clean(info.get("VENDOR"))
    if not vendor and not info.get("OFFICIAL"):
        return None
    diameter = _tag_number(info.get("DIAMETER"))
    date = str(info.get("MF_DATE") or "")
    nozzle = (_tag_number(info.get("HOTEND_MIN_TEMP")), _tag_number(info.get("HOTEND_MAX_TEMP")))
    return {
        "official": bool(info.get("OFFICIAL")),
        "vendor": vendor,
        "manufacturer": _clean(info.get("MANUFACTURER")),
        "sku": _tag_number(info.get("SKU")),
        "weight_g": _tag_number(info.get("WEIGHT")),
        "length_m": _tag_number(info.get("LENGTH")),
        "diameter_mm": round(diameter / 100, 2) if diameter else None,
        "nozzle_temp": [t for t in nozzle] if any(nozzle) else None,
        "first_layer_temp": _tag_number(info.get("FIRST_LAYER_TEMP")),
        "other_layer_temp": _tag_number(info.get("OTHER_LAYER_TEMP")),
        "bed_temp": _tag_number(info.get("BED_TEMP")),
        "drying_temp": _tag_number(info.get("DRYING_TEMP")),
        "drying_time_h": _tag_number(info.get("DRYING_TIME")),
        "manufactured": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 and date != "19700101" else None,
    }


def filament_gcode(slot: int, ftype: str, sub_type: str, vendor: str,
                   color: str | None = None, force: bool = False) -> str:
    """SET_PRINT_FILAMENT_CONFIG for a slot (0-3), e.g. a spool without RFID tag.

    The firmware wants vendor, type and sub type together and refuses a slot
    with an official spool unless FORCE=1 (print_task_config.py). Klipper cuts
    a command at '#', '*' or ';', and quotes may not appear inside a value.
    """
    def quote(text: str) -> str:
        value = str(text or "").strip() or "NONE"
        if any(c in value for c in "\"'#*;\n\r"):
            raise ValueError(f"Invalid character in {value!r}")
        return f'"{value}"'

    if not 0 <= slot < PHYSICAL_SLOTS:
        raise ValueError(f"Invalid slot {slot + 1}")
    if not str(ftype or "").strip():
        raise ValueError("Filament type missing")
    parts = ["SET_PRINT_FILAMENT_CONFIG", f"CONFIG_EXTRUDER={slot}", f"VENDOR={quote(vendor)}",
             f"FILAMENT_TYPE={quote(str(ftype).upper())}", f"FILAMENT_SUBTYPE={quote(sub_type)}"]
    if color:
        rgb = normalize_color(color)
        if rgb is None:
            raise ValueError(f"Invalid colour {color!r}")
        parts.append(f"FILAMENT_COLOR_RGBA={rgb.lstrip('#')}FF")
    if force:
        parts.append("FORCE=1")
    return " ".join(parts)


def _split(value: Any) -> list[str]:
    """Slicer list value (list or "a;b;c") -> list of strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [part.strip() for part in str(value).split(";")]


def parse_file_filaments(meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Logical filaments of a print file (T0, T1, ...)."""
    meta = meta or {}
    types = _split(meta.get("filament_type"))
    colors = _split(meta.get("filament_colour"))
    names = _split(meta.get("filament_name"))
    weights = meta.get("filament_weight")
    used_mm = meta.get("filament_used_mm")
    count = max(len(types), len(colors), len(names),
                len(weights) if isinstance(weights, list) else 0)
    count = min(count, LOGICAL_EXTRUDERS)

    result = []
    for i in range(count):
        weight = _at(weights, i)
        length = _at(used_mm, i)
        known = isinstance(weights, list) or isinstance(used_mm, list)
        used = True
        if known:
            used = bool((weight or 0) > 0 or (length or 0) > 0)
        result.append(
            {
                "index": i,
                "type": _clean(_at(types, i)),
                "color": normalize_color(_at(colors, i)),
                "name": _clean(_at(names, i)),
                "weight": round(float(weight), 2) if weight is not None else None,
                "used": used,
            }
        )
    return result


def _rgb(color: str | None) -> tuple[int, int, int] | None:
    if not color:
        return None
    hex6 = color.lstrip("#")
    return int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)


def color_distance(a: str | None, b: str | None) -> float:
    """Weighted RGB distance ('redmean'), 0 = identical. Unknown = large."""
    ra, rb = _rgb(a), _rgb(b)
    if ra is None or rb is None:
        return 765.0
    rmean = (ra[0] + rb[0]) / 2
    dr, dg, db = ra[0] - rb[0], ra[1] - rb[1], ra[2] - rb[2]
    return ((2 + rmean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rmean) / 256) * db * db) ** 0.5


def _same_type(a: str | None, b: str | None) -> bool:
    return bool(a and b and a.strip().upper() == b.strip().upper())


def suggest_mapping(
    filaments: list[dict[str, Any]], slots: list[dict[str, Any]]
) -> dict[int, int]:
    """Suggest logical -> physical mapping, similar to Snapmaker Orca.

    Criteria in order: loaded slot, same material type, similar colour, slot
    not yet taken. Without loaded slots T<n> stays on slot n (firmware
    default).
    """
    loaded = [s for s in slots if s.get("loaded")]
    taken: set[int] = set()
    mapping: dict[int, int] = {}
    for fil in (f for f in filaments if f.get("used")):
        idx = fil["index"]
        if not loaded:
            mapping[idx] = idx % PHYSICAL_SLOTS
            continue

        def score(slot: dict[str, Any], fil: dict[str, Any] = fil) -> tuple[int, float, int]:
            return (
                0 if _same_type(fil.get("type"), slot.get("type")) else 1,
                color_distance(fil.get("color"), slot.get("color")),
                1 if slot["index"] in taken else 0,
            )

        best = min(loaded, key=score)
        mapping[idx] = best["index"]
        taken.add(best["index"])
    return mapping


def map_table_option(mapping: dict[int, int]) -> str:
    """Format for MAP_TABLE: Python literal [[logical, physical], ...]."""
    pairs = sorted((int(k), int(v)) for k, v in mapping.items())
    for logical, physical in pairs:
        if not 0 <= logical < LOGICAL_EXTRUDERS or not 0 <= physical < PHYSICAL_SLOTS:
            raise ValueError(f"Invalid mapping T{logical} -> slot {physical + 1}")
    return "[" + ", ".join(f"[{a}, {b}]" for a, b in pairs) + "]"


def pick_thumbnail(meta: dict[str, Any] | None, target_width: int = 300) -> str | None:
    """Pick the relative path of the best-fitting thumbnail."""
    thumbs = [t for t in (meta or {}).get("thumbnails") or [] if t.get("relative_path")]
    if not thumbs:
        return None
    larger = [t for t in thumbs if (t.get("width") or 0) >= target_width]
    pool = larger or thumbs

    def width(t: dict[str, Any]) -> int:
        return t.get("width") or 0

    chosen = min(pool, key=width) if larger else max(pool, key=width)
    return chosen["relative_path"]


def thumbnail_source(file_path: str, relative: str) -> str:
    """Path below /server/files/gcodes/ for a thumbnail."""
    folder = posixpath.dirname(file_path)
    return posixpath.normpath(posixpath.join(folder, relative)).lstrip("/")


def describe_file(path: str, entry: dict[str, Any], meta: dict[str, Any] | None) -> dict[str, Any]:
    """File list entry for the card: name, times, weight, filaments."""
    meta = meta or {}
    name = posixpath.basename(path)
    for suffix in PRINTABLE_SUFFIXES:
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    filament_mm = meta.get("filament_total")
    return {
        "path": path,
        "name": name,
        "modified": entry.get("modified"),
        "size": entry.get("size"),
        "time": meta.get("estimated_time"),
        "layers": meta.get("layer_count"),
        "filament": round(filament_mm / 1000, 2) if isinstance(filament_mm, (int, float)) else None,
        "weight": meta.get("filament_weight_total"),
        "filaments": parse_file_filaments(meta),
        "thumb": None,
    }


# ── Tool changes ────────────────────────────────────────────────────────────
# The firmware permanently counts every successful head change per head
# (u1-klipper/klippy/kinematics/extruder.py, ExtruderSwitchRecorder,
# fields switch_count, retry_count, error_count, last_maintenance_count in
# the status of extruder ... extruder3). There is no per-print counter;
# track_print_switches derives it as a difference.

EXTRUDER_OBJECTS = ("extruder", "extruder1", "extruder2", "extruder3")
SWITCH_FIELDS = ("switch_count", "retry_count", "error_count", "last_maintenance_count")
# Firmware default (individual_maintenance_threshold in [extruder]).
MAINTENANCE_THRESHOLD = 25100
ACTIVE_PRINT_STATES = ("printing", "paused")
# Right after a print started by us, print_stats briefly still reports the
# old state (standby/complete). The counter waits this long for "printing".
START_GRACE_S = 120


def parse_tool_changes(status: dict[str, Any] | None) -> dict[str, Any] | None:
    """Counters of all heads; None if the firmware does not provide any."""
    status = status or {}
    heads = []
    for i, name in enumerate(EXTRUDER_OBJECTS):
        ext = status.get(name) or {}
        if not isinstance(ext.get("switch_count"), int):
            continue
        switches = ext["switch_count"]
        heads.append(
            {
                "index": i,
                "switches": switches,
                "retries": int(ext.get("retry_count") or 0),
                "errors": int(ext.get("error_count") or 0),
                "since_maintenance": max(0, switches - int(ext.get("last_maintenance_count") or 0)),
            }
        )
    if not heads:
        return None
    return {
        "total": sum(h["switches"] for h in heads),
        "heads": heads,
        "maintenance_threshold": MAINTENANCE_THRESHOLD,
    }


def _delta(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return max(0.0, end - start)


# Fields of the running print that move into the record when it finishes.
_CARRY = ("name", "thumb", "filaments", "filament_total", "filament_used", "print_duration",
          "map_table", "spool_ids", "source", "mapping", "options", "pause_layers")


def _close(active: dict[str, Any], counters: dict[str, float | None],
           result: str | None, now: float) -> dict[str, Any]:
    """Turn the active print into a finished record with its consumption."""
    base = active.get("start") or {}
    last: dict[str, Any] = {
        "file": active.get("file"),
        "result": result,
        "started": active.get("started"),
        "ended": now,
    }
    for key, value in counters.items():
        d = _delta(base.get(key), value)
        last[key] = None if d is None else (int(d) if key == "switches" else round(d, 4))
    for key in _CARRY:
        if active.get(key) is not None:
            last[key] = active[key]
    if active.get("energy_cost") is not None:
        last["energy_cost"] = round(active["energy_cost"], 4)
    return last


def migrate_print_state(state: dict[str, Any] | None) -> dict[str, Any]:
    """Bring stored state from older versions into the current format."""
    state = dict(state or {})
    active = state.get("active")
    if isinstance(active, dict) and "start_total" in active:
        active = {k: v for k, v in active.items() if k != "start_total"}
        active["start"] = {"switches": state["active"]["start_total"]}
    history = [h for h in state.get("history") or [] if isinstance(h, dict)]
    last = state.get("last") if isinstance(state.get("last"), dict) else None
    if last and not history:
        history = [last]
    return {
        "active": active if isinstance(active, dict) else None,
        "last": last,
        "history": history,
        "files": [f for f in state.get("files") or [] if isinstance(f, dict)],
        "timelapses": [v for v in state.get("timelapses") or [] if isinstance(v, dict)],
    }


def _accumulate_cost(active: dict[str, Any], energy: float | None, price: float | None) -> dict[str, Any]:
    """Accumulate energy cost continuously: delta kWh x price at that moment.

    This handles dynamic tariffs (hourly prices) correctly instead of
    applying the price at the end of the print to the whole print.
    """
    if energy is None:
        return active
    prev = active.get("energy_prev")
    if prev is not None and price is None:
        # Price briefly unknown: keep the base; the delta is charged at the
        # next known price instead of being lost.
        return active
    out = {**active, "energy_prev": energy}
    if prev is not None and price is not None and energy >= prev:
        out["energy_cost"] = (active.get("energy_cost") or 0.0) + (energy - prev) * price
    return out


def track_print(
    state: dict[str, Any],
    print_state: str | None,
    filename: str | None,
    counters: dict[str, float | None],
    now: float,
    *,
    pending: bool = False,
    price: float | None = None,
    stats: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, bool]:
    """Advance the running or last print.

    ``counters`` are monotonically increasing counters (tool changes, kWh);
    their difference between start and end of a print is its consumption.
    ``price`` is the current energy price per kWh, ``stats`` are
    print_duration and filament_used from print_stats.
    Returns the new state, the print that just finished (or None) and whether
    the structure changed (save immediately). ``pending=True`` registers a
    start that was just triggered by the integration itself.
    """
    rest = {k: v for k, v in state.items() if k not in ("active", "last")}
    active = state.get("active")
    last = state.get("last")
    running = print_state in ACTIVE_PRINT_STATES
    finished = None
    changed = False
    energy = counters.get("energy")

    def begin(pend: bool) -> dict[str, Any]:
        new: dict[str, Any] = {"file": filename, "started": now, "start": dict(counters)}
        if energy is not None:
            new["energy_prev"] = energy
            new["energy_cost"] = 0.0 if price is not None else None
        if pend:
            new["pending"] = True
        return new

    def out() -> dict[str, Any]:
        return {**rest, "active": active, "last": last}

    if pending:
        if active and not active.get("pending"):
            active = _accumulate_cost(active, energy, price)
            last = finished = _close(active, counters, "unknown", now)
        active = begin(True)
        return out(), finished, True

    if active and active.get("pending"):
        if running:
            active = {k: v for k, v in active.items() if k != "pending"}
            changed = True
        elif now - float(active.get("started") or now) > START_GRACE_S:
            # The print never got going: record nothing.
            active = None
            return out(), None, True
        else:
            return state, None, False

    if active:
        active = _accumulate_cost(active, energy, price)
        if running and stats:
            for key in ("print_duration", "filament_used"):
                if isinstance(stats.get(key), (int, float)):
                    active[key] = stats[key]

    # Print finished, or the next one already started between two polls.
    if active and (not running or (filename and filename != active.get("file"))):
        last = finished = _close(active, counters, print_state if not running else "unknown", now)
        active = None
        changed = True

    if running and not active:
        active = begin(False)
        changed = True

    if active:
        # Counter reset or only known now: move the base along.
        base = dict(active.get("start") or {})
        for key, value in counters.items():
            if value is None:
                continue
            if base.get(key) is None or value < base[key]:
                base[key] = value
        if base != (active.get("start") or {}):
            active = {**active, "start": base}
            changed = True

    return out(), finished, changed


def print_progress(state: dict[str, Any], counters: dict[str, float | None]) -> dict[str, Any]:
    """Consumption of the running print per counter (None without a running print)."""
    active = state.get("active")
    if not active or active.get("pending"):
        return {key: None for key in (*counters, "energy_cost")}
    base = active.get("start") or {}
    result: dict[str, Any] = {}
    for key, value in counters.items():
        d = _delta(base.get(key), value)
        result[key] = None if d is None else (int(d) if key == "switches" else round(d, 4))
    cost = active.get("energy_cost")
    result["energy_cost"] = None if cost is None else round(cost, 4)
    return result


# ── Filament usage and cost per print ───────────────────────────────────────
FILAMENT_PRICE_KEYS = ("PLA", "PETG", "ABS", "ASA", "TPU", "PA")


def filament_price_for(ftype: str | None, prices: dict[str, float | None]) -> float | None:
    """Price per kg for a material type; 'PLA-CF' falls back to 'PLA'."""
    key = (ftype or "").upper()
    for cand in (key, key.split("-")[0].split(" ")[0]):
        if prices.get(cand) is not None:
            return prices[cand]
    return prices.get("OTHER")


def average_kw(history: list[dict[str, Any]]) -> float | None:
    """Average printer power from finished prints (kWh / hours, prints of 10 min and more)."""
    kwh = hours = 0.0
    for item in history:
        energy, duration = item.get("energy"), item.get("duration")
        if isinstance(energy, (int, float)) and isinstance(duration, (int, float)) and energy > 0 and duration >= 600:
            kwh += energy
            hours += duration / 3600
    return round(kwh / hours, 4) if hours else None


def estimate_cost(
    file: dict[str, Any], prices: dict[str, float | None], kwh_price: float | None, avg_kw: float | None
) -> dict[str, float] | None:
    """Cost before printing: slicer weight x material price + print time x average power x energy price."""
    out: dict[str, float] = {}
    fils = [f for f in file.get("filaments") or [] if f.get("used") is not False and f.get("weight")]
    if fils:
        costs = [filament_price_for(f.get("type"), prices) for f in fils]
        if all(c is not None for c in costs):
            out["filament"] = round(sum(f["weight"] * c / 1000 for f, c in zip(fils, costs, strict=True)), 2)
    elif file.get("weight") and prices.get("OTHER") is not None:
        out["filament"] = round(file["weight"] * prices["OTHER"] / 1000, 2)
    est = file.get("time")
    if isinstance(est, (int, float)) and est > 0 and kwh_price is not None and avg_kw:
        out["energy_kwh"] = round(est / 3600 * avg_kw, 3)
        out["energy"] = round(out["energy_kwh"] * kwh_price, 2)
    if not out:
        return None
    out["total"] = round(out.get("filament", 0) + out.get("energy", 0), 2)
    return out


def summarize_print(record: dict[str, Any], prices: dict[str, float | None]) -> dict[str, Any]:
    """Add weight, filament cost and total cost to a finished print.

    The weight comes from the slicer. For cancelled prints it is reduced by
    the ratio of actually extruded to planned length
    (print_stats.filament_used / filament_total from the file metadata).
    """
    out = dict(record)
    fils = [f for f in record.get("filaments") or [] if f.get("weight")]
    scale = 1.0
    used, total = record.get("filament_used"), record.get("filament_total")
    if record.get("result") != "complete" and used and total:
        scale = max(0.0, min(1.0, used / total))
    if fils:
        grams = sum(f["weight"] for f in fils) * scale
        out["filament_g"] = round(grams, 1)
        costs = [filament_price_for(f.get("type"), prices) for f in fils]
        if all(c is not None for c in costs):
            out["filament_cost"] = round(
                sum(f["weight"] * scale * c / 1000 for f, c in zip(fils, costs, strict=True)), 2
            )
    elif isinstance(used, (int, float)) and used > 0:
        out["filament_m"] = round(used / 1000, 2)
    parts = [out.get("energy_cost"), out.get("filament_cost")]
    if any(p is not None for p in parts):
        out["total_cost"] = round(sum(p for p in parts if p is not None), 2)
    if out.get("energy_cost") is not None:
        out["energy_cost"] = round(out["energy_cost"], 2)
    started, ended = record.get("started"), record.get("ended")
    out["duration"] = record.get("print_duration") or (
        round(ended - started) if started and ended else None
    )
    out.pop("filaments", None)
    out["materials"] = sorted({f.get("type") for f in fils if f.get("type")})
    return out


def energy_dashboard_price(prefs: Any, states: Any) -> tuple[float | None, str | None]:
    """Grid price from Home Assistant's energy dashboard: (price per kWh, source).

    The first grid import (flow_from) with a price entity or a fixed price is
    used; ``states`` is ``hass.states``. Newer schemas without flow_from are
    read the same way from the grid source itself.
    """
    if not isinstance(prefs, dict):
        return None, None
    for src in prefs.get("energy_sources") or []:
        if not isinstance(src, dict) or src.get("type") != "grid":
            continue
        for flow in src.get("flow_from") or [src]:
            entity = flow.get("entity_energy_price")
            if entity:
                st = states.get(entity)
                price = price_per_kwh(st.state, st.attributes.get("unit_of_measurement")) if st else None
                if price is not None:
                    return price, entity
            number = flow.get("number_energy_price")
            if isinstance(number, (int, float)) and not isinstance(number, bool):
                return float(number), "fixed"
    return None, None


def price_per_kwh(state: str | None, unit: str | None) -> float | None:
    """Price entity in currency per kWh; ct/kWh and per MWh are converted."""
    try:
        value = float(state)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    u = (unit or "").replace(" ", "").lower()
    if u.startswith(("ct", "cent", "c/")):
        value /= 100
    if u.endswith("/mwh"):
        value /= 1000
    elif u.endswith("/wh"):
        value *= 1000
    return value


ENERGY_FACTORS = {"Wh": 0.001, "kWh": 1.0, "MWh": 1000.0}


def energy_kwh(state: str | None, unit: str | None) -> float | None:
    """State of an energy meter in kWh; None if unusable."""
    factor = ENERGY_FACTORS.get(unit or "kWh")
    if factor is None:
        return None
    try:
        return float(state) * factor  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# ── Timelapses ──────────────────────────────────────────────────────────────
# The U1 stores timelapses through a closed Snapmaker service. With stock
# firmware Moonraker shows them in the "camera" folder (/oem/printer_data/
# camera); Fluidd timelapse uses "timelapse". All folders are searched
# except config and logs.
VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
TIMELAPSE_SKIP_ROOTS = ("config", "logs", "config_examples", "docs")


# Stock firmware: <print name>_<YYYYMMDDHHMMSS>.mp4 plus _cover.jpg (large) and
# .jpg (thumbnail) with the same stem.
_STAMP = re.compile(r"^(?P<name>.*?)_(?P<ts>\d{14})$")


def pick_timelapses(root: str, entries: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Videos of a folder, newest first, with the matching preview image."""
    images: dict[str, str] = {}
    by_dir: dict[str, str] = {}
    for e in entries:
        path = str(e.get("path", ""))
        low = path.lower()
        if low.endswith(IMAGE_SUFFIXES):
            images[posixpath.splitext(low)[0]] = path
            by_dir.setdefault(posixpath.dirname(low), path)
    videos = []
    for e in entries:
        path = str(e.get("path", ""))
        if not path.lower().endswith(VIDEO_SUFFIXES) or posixpath.basename(path).startswith("."):
            continue
        stem = posixpath.splitext(path.lower())[0]
        folder = posixpath.dirname(path.lower())
        # Cover before thumbnail, otherwise the first image in the same subfolder.
        poster = (images.get(f"{stem}_cover") or images.get(stem)
                  or (by_dir.get(folder) if folder else None))
        base = posixpath.splitext(posixpath.basename(path))[0]
        match = _STAMP.match(base)
        recorded = None
        if match:
            ts = match["ts"]
            recorded = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
        videos.append(
            {
                "root": root,
                "path": path,
                "name": (match["name"] if match else base).replace("_", " "),
                "recorded": recorded,
                "size": e.get("size"),
                "modified": e.get("modified"),
                "poster": poster,
                # small preview image (U1: <name>.jpg), if present
                "thumb": images.get(stem) if images.get(stem) != poster else None,
            }
        )
    videos.sort(key=lambda v: v.get("modified") or 0, reverse=True)
    return videos[:limit]


# ── Spoolman ────────────────────────────────────────────────────────────────
# Spoolman (github.com/Donkie/Spoolman, API v1): GET /api/v1/spool returns
# spools with filament{name, material, color_hex, vendor{name}},
# remaining_weight, initial_weight, last_used, archived. Usage is booked with
# PUT /api/v1/spool/{id}/use {"use_weight": g}.
# Moonraker only knows ONE active spool; for four heads the integration
# therefore assigns spools itself and books usage per head.


def compact_spool(spool: dict[str, Any]) -> dict[str, Any]:
    """Reduce a Spoolman spool to the fields the card needs."""
    fil = spool.get("filament") or {}
    vendor = (fil.get("vendor") or {}).get("name")
    color = normalize_color(fil.get("color_hex"))
    multi = [c for c in (normalize_color(x) for x in str(fil.get("multi_color_hexes") or "").split(",")) if c]
    return {
        "id": spool.get("id"),
        "name": fil.get("name") or fil.get("material") or f"Spule {spool.get('id')}",
        "vendor": vendor,
        "material": fil.get("material"),
        "color": color or (multi[0] if multi else None),
        "colors": multi or ([color] if color else []),
        "remaining_weight": _round(spool.get("remaining_weight")),
        "initial_weight": _round(spool.get("initial_weight") or fil.get("weight")),
        "location": spool.get("location"),
        "last_used": spool.get("last_used"),
        "used_weight": _round(spool.get("used_weight")),
        "archived": bool(spool.get("archived")),
    }


def _round(value: Any) -> float | None:
    return round(float(value), 1) if isinstance(value, (int, float)) else None


def slot_fingerprint(slot: dict[str, Any]) -> str | None:
    """Fingerprint of the loaded filament; if it changes, the mapping is no longer valid."""
    if not slot.get("loaded"):
        return None
    return "|".join(str(slot.get(k) or "").upper() for k in ("type", "sub_type", "vendor", "color"))


def _spool_score(slot: dict[str, Any], spool: dict[str, Any]) -> tuple:
    """Sort key for how well a spool matches a slot (lower is better)."""
    stype, sub = (slot.get("type") or "").upper(), (slot.get("sub_type") or "").upper()
    material = (spool.get("material") or "").upper()
    name = (spool.get("name") or "").upper()
    vendor_ok = bool(slot.get("vendor") and spool.get("vendor")
                     and slot["vendor"].strip().upper() == spool["vendor"].strip().upper())
    return (
        0 if stype and (material == stype or material.split("-")[0] == stype) else 1,
        # Colour in steps so that nearly identical colours count as equal
        round(color_distance(slot.get("color"), spool.get("color")) / 40),
        0 if not sub or sub in name or sub in material else 1,
        0 if vendor_ok else 1,
        # opened, most recently used spool first
        0 if spool.get("used_weight") else 1,
        "\uffff" if not spool.get("last_used") else _neg(spool["last_used"]),
        spool.get("remaining_weight") if spool.get("remaining_weight") is not None else 1e9,
    )


def _neg(text: str) -> str:
    """Sort key for 'newest first' with ISO timestamps."""
    return "".join(chr(255 - ord(c)) if c.isdigit() else c for c in text)


# The same colour family stays below ~100 in redmean distance (black/almost
# black 84, cream/white 55), different colours are above ~180 (white/silver 189).
SPOOL_COLOR_LIMIT = 150


def _color_close(slot: dict[str, Any], spool: dict[str, Any]) -> bool:
    if not slot.get("color") or not spool.get("color"):
        return True  # without a colour the material decides
    return color_distance(slot["color"], spool["color"]) <= SPOOL_COLOR_LIMIT


def suggest_spools(
    slots: list[dict[str, Any]],
    spools: list[dict[str, Any]],
    fixed: dict[int, int | None] | None = None,
) -> dict[int, int | None]:
    """Assign spools to the loaded heads; ``fixed`` (manual) entries are left alone.

    A spool can physically only sit in one head: each is assigned at most
    once. If the material does not match, nothing is assigned.
    """
    fixed = dict(fixed or {})
    taken = {sid for sid in fixed.values() if sid}
    result: dict[int, int | None] = {}
    for slot in slots:
        idx = slot["index"]
        if idx in fixed:
            result[idx] = fixed[idx]
            continue
        if not slot.get("loaded"):
            result[idx] = None
            continue
        pool = [s for s in spools if not s.get("archived") and s["id"] not in taken]
        best = min(pool, key=lambda s: _spool_score(slot, s), default=None)
        if best is None or _spool_score(slot, best)[0] != 0 or not _color_close(slot, best):
            # Better no assignment than a wrong spool that usage is then booked from.
            result[idx] = None
            continue
        result[idx] = best["id"]
        taken.add(best["id"])
    return result


def grams_per_slot(record: dict[str, Any]) -> dict[int, float]:
    """Consumption of a print per physical head.

    Weight per logical filament (slicer) x share when cancelled, distributed
    to the heads via the print's map table (print_task_config.extruder_map_table:
    position = logical, value = head).
    """
    fils = [f for f in record.get("filaments") or [] if f.get("weight")]
    if not fils:
        return {}
    scale = 1.0
    used, total = record.get("filament_used"), record.get("filament_total")
    if record.get("result") != "complete" and used and total:
        scale = max(0.0, min(1.0, used / total))
    table = record.get("map_table") or []
    out: dict[int, float] = {}
    for pos, fil in enumerate(fils):
        logical = fil.get("index", pos)
        slot = table[logical] if isinstance(logical, int) and 0 <= logical < len(table) else logical
        if not isinstance(slot, int) or not 0 <= slot < PHYSICAL_SLOTS:
            continue
        out[slot] = round(out.get(slot, 0.0) + fil["weight"] * scale, 2)
    return out
