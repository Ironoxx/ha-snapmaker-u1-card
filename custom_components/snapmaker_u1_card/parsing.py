"""Reine Datenaufbereitung ohne Home-Assistant-Abhaengigkeit.

Alles hier ist bewusst frei von HA-Imports, damit es sich isoliert testen
laesst. Die Feldnamen stammen aus Snapmakers offengelegtem Quellcode:

* ``print_task_config`` – u1-klipper/klippy/extras/print_task_config.py
  (DEFAULT_PRINT_TASK_CONFIG, get_status, SET_PRINT_TASK_PARAMETERS)
* Dateimetadaten – u1-moonraker/moonraker/components/file_manager/metadata.py
  (SUPPORTED_DATA, PrusaSlicer-Parser)
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
    """Snapmaker nutzt 'NONE' als Platzhalter fuer leere Felder."""
    if value is None:
        return None
    text = str(value).strip().strip('"').strip()
    if not text or text.upper() == "NONE":
        return None
    return text


def normalize_color(value: Any) -> str | None:
    """'1B5E20FF', '#1b5e20' oder 0xFF1B5E20 -> '#1B5E20'."""
    if value is None:
        return None
    if isinstance(value, int):
        return f"#{value & 0xFFFFFF:06X}"
    match = _HEX6.match(str(value).strip())
    return f"#{match.group(1).upper()}" if match else None


def parse_slots(ptc: dict[str, Any] | None) -> list[dict[str, Any]]:
    """print_task_config -> eine Liste mit vier Slots."""
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
            }
        )
    return slots


def parse_preferences(ptc: dict[str, Any] | None) -> dict[str, bool]:
    ptc = ptc or {}
    return {
        "bed_leveling": bool(ptc.get("auto_bed_leveling", False)),
        "flow_calibration": bool(ptc.get("flow_calibrate", False)),
        "timelapse": bool(ptc.get("time_lapse_camera", False)),
    }


def _split(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [part.strip() for part in str(value).split(";")]


def parse_file_filaments(meta: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Logische Filamente einer Druckdatei (T0, T1, ...)."""
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
    """Gewichtete RGB-Distanz ('redmean'), 0 = gleich. Unbekannt = gross."""
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
    """Vorschlag logisch -> physisch, aehnlich wie Snapmaker Orca.

    Reihenfolge der Kriterien: geladener Slot, gleicher Materialtyp, aehnliche
    Farbe, noch nicht vergebener Slot. Ohne geladene Slots bleibt T<n> auf
    Slot n (Firmware-Standard).
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
    """Format fuer MAP_TABLE: Python-Literal [[logisch, physisch], ...]."""
    pairs = sorted((int(k), int(v)) for k, v in mapping.items())
    for logical, physical in pairs:
        if not 0 <= logical < LOGICAL_EXTRUDERS or not 0 <= physical < PHYSICAL_SLOTS:
            raise ValueError(f"Ungueltige Zuordnung T{logical} -> Slot {physical + 1}")
    return "[" + ", ".join(f"[{a}, {b}]" for a, b in pairs) + "]"


def pick_thumbnail(meta: dict[str, Any] | None, target_width: int = 300) -> str | None:
    """Relativen Pfad des passendsten Vorschaubilds waehlen."""
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
    """Pfad unter /server/files/gcodes/ fuer ein Vorschaubild."""
    folder = posixpath.dirname(file_path)
    return posixpath.normpath(posixpath.join(folder, relative)).lstrip("/")


def describe_file(path: str, entry: dict[str, Any], meta: dict[str, Any] | None) -> dict[str, Any]:
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


# ── Werkzeugwechsel ─────────────────────────────────────────────────────────
# Die Firmware zaehlt jeden erfolgreichen Kopfwechsel dauerhaft pro Kopf
# (u1-klipper/klippy/kinematics/extruder.py, ExtruderSwitchRecorder,
# Felder switch_count, retry_count, error_count, last_maintenance_count im
# Status von extruder ... extruder3). Einen Zaehler pro Druck gibt es nicht;
# den bildet track_print_switches als Differenz.

EXTRUDER_OBJECTS = ("extruder", "extruder1", "extruder2", "extruder3")
SWITCH_FIELDS = ("switch_count", "retry_count", "error_count", "last_maintenance_count")
# Firmware-Standard (individual_maintenance_threshold in [extruder]).
MAINTENANCE_THRESHOLD = 25100
ACTIVE_PRINT_STATES = ("printing", "paused")
# Nach einem eigenen Druckstart meldet print_stats noch kurz den alten Zustand
# (standby/complete). So lange wartet der Zaehler auf "printing".
START_GRACE_S = 120


def parse_tool_changes(status: dict[str, Any] | None) -> dict[str, Any] | None:
    """Zaehler aller Koepfe; None, wenn die Firmware keine liefert."""
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


# Felder des laufenden Drucks, die beim Abschluss in den Datensatz wandern.
_CARRY = ("name", "thumb", "filaments", "filament_total", "filament_used", "print_duration",
          "map_table", "spool_ids", "source", "mapping", "options", "pause_layers")


def _close(active: dict[str, Any], counters: dict[str, float | None],
           result: str | None, now: float) -> dict[str, Any]:
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
    """Gespeicherten Stand aelterer Versionen ins aktuelle Format bringen."""
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
    """Stromkosten laufend aufsummieren: Delta-kWh x Preis zum jeweiligen Zeitpunkt.

    So rechnen dynamische Tarife (Preis je Stunde) richtig, statt den Preis
    beim Druckende auf den ganzen Druck anzuwenden.
    """
    if energy is None:
        return active
    prev = active.get("energy_prev")
    if prev is not None and price is None:
        # Preis kurz unbekannt: Basis stehen lassen, das Delta wird mit dem
        # naechsten bekannten Preis verrechnet statt verloren zu gehen.
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
    """Laufenden bzw. letzten Druck fortschreiben.

    ``counters`` sind monoton steigende Zaehler (Werkzeugwechsel, kWh), deren
    Differenz zwischen Druckbeginn und -ende den Verbrauch des Drucks ergibt.
    ``price`` ist der aktuelle Strompreis je kWh, ``stats`` sind
    print_duration und filament_used aus print_stats.
    Rueckgabe: neuer Zustand, gerade abgeschlossener Druck (oder None), und ob
    sich die Struktur geaendert hat (sofort speichern). ``pending=True`` meldet
    einen eben selbst ausgeloesten Start an.
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
            # Druck ist nie angelaufen: nichts verbuchen.
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

    # Druck beendet oder zwischen zwei Abfragen schon der naechste gestartet.
    if active and (not running or (filename and filename != active.get("file"))):
        last = finished = _close(active, counters, print_state if not running else "unknown", now)
        active = None
        changed = True

    if running and not active:
        active = begin(False)
        changed = True

    if active:
        # Zaehler zurueckgesetzt oder erst jetzt bekannt: Basis nachziehen.
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
    """Verbrauch des laufenden Drucks je Zaehler (None ohne laufenden Druck)."""
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


# ── Filamentverbrauch und Kosten je Druck ─────────────────────────────────
FILAMENT_PRICE_KEYS = ("PLA", "PETG", "ABS", "ASA", "TPU", "PA")


def filament_price_for(ftype: str | None, prices: dict[str, float | None]) -> float | None:
    """Preis je kg fuer einen Materialtyp; 'PLA-CF' faellt auf 'PLA' zurueck."""
    key = (ftype or "").upper()
    for cand in (key, key.split("-")[0].split(" ")[0]):
        if prices.get(cand) is not None:
            return prices[cand]
    return prices.get("OTHER")


def average_kw(history: list[dict[str, Any]]) -> float | None:
    """Mittlere Leistung des Druckers aus fertigen Drucken (kWh / Stunden, ab 10 min)."""
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
    """Kosten vor dem Druck: Slicer-Gewicht x Materialpreis + Druckzeit x mittlere Leistung x Strompreis."""
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
    """Abgeschlossenen Druck um Gewicht, Filament- und Gesamtkosten ergaenzen.

    Das Gewicht kommt aus dem Slicer. Bei abgebrochenen Drucken wird es im
    Verhaeltnis tatsaechlich gefoerderter zu geplanter Laenge gekuerzt
    (print_stats.filament_used / filament_total aus den Dateimetadaten).
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


def price_per_kwh(state: str | None, unit: str | None) -> float | None:
    """Preis-Entitaet in Waehrung je kWh; ct/kWh und je MWh werden umgerechnet."""
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
    """Zustand eines Energiezaehlers in kWh; None wenn unbrauchbar."""
    factor = ENERGY_FACTORS.get(unit or "kWh")
    if factor is None:
        return None
    try:
        return float(state) * factor  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# ── Zeitraffer ──────────────────────────────────────────────────────────────
# Der U1 legt Zeitraffer ueber einen nicht offenen Snapmaker-Dienst ab. Bei
# Stock-Firmware zeigt Moonraker sie im Ordner "camera" (/oem/printer_data/
# camera), Fluidd-Timelapse nutzt "timelapse". Gesucht wird in allen Ordnern
# ausser Konfiguration und Logs.
VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv")
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
TIMELAPSE_SKIP_ROOTS = ("config", "logs", "config_examples", "docs")


# Stock-Firmware: <Druckname>_<YYYYMMDDHHMMSS>.mp4 plus _cover.jpg (gross) und
# .jpg (Miniatur) mit gleichem Stamm.
_STAMP = re.compile(r"^(?P<name>.*?)_(?P<ts>\d{14})$")


def pick_timelapses(root: str, entries: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Videos eines Ordners, neueste zuerst, mit passendem Vorschaubild."""
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
        # Cover vor Miniatur, sonst das erste Bild im selben Unterordner.
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
                # kleines Vorschaubild (U1: <Name>.jpg), falls vorhanden
                "thumb": images.get(stem) if images.get(stem) != poster else None,
            }
        )
    videos.sort(key=lambda v: v.get("modified") or 0, reverse=True)
    return videos[:limit]


# ── Spoolman ────────────────────────────────────────────────────────────────
# Spoolman (github.com/Donkie/Spoolman, API v1): GET /api/v1/spool liefert
# Spulen mit filament{name, material, color_hex, vendor{name}},
# remaining_weight, initial_weight, last_used, archived. Abgebucht wird mit
# PUT /api/v1/spool/{id}/use {"use_weight": g}.
# Moonraker kennt nur EINE aktive Spule; fuer vier Koepfe ordnet deshalb die
# Integration selbst zu und bucht je Kopf ab.


def compact_spool(spool: dict[str, Any]) -> dict[str, Any]:
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
    """Merkmal des geladenen Filaments; aendert es sich, gilt die Zuordnung nicht mehr."""
    if not slot.get("loaded"):
        return None
    return "|".join(str(slot.get(k) or "").upper() for k in ("type", "sub_type", "vendor", "color"))


def _spool_score(slot: dict[str, Any], spool: dict[str, Any]) -> tuple:
    stype, sub = (slot.get("type") or "").upper(), (slot.get("sub_type") or "").upper()
    material = (spool.get("material") or "").upper()
    name = (spool.get("name") or "").upper()
    vendor_ok = bool(slot.get("vendor") and spool.get("vendor")
                     and slot["vendor"].strip().upper() == spool["vendor"].strip().upper())
    return (
        0 if stype and (material == stype or material.split("-")[0] == stype) else 1,
        # Farbe in Stufen, damit fast gleiche Farben gleich zaehlen
        round(color_distance(slot.get("color"), spool.get("color")) / 40),
        0 if not sub or sub in name or sub in material else 1,
        0 if vendor_ok else 1,
        # angebrochene, zuletzt benutzte Spule zuerst
        0 if spool.get("used_weight") else 1,
        "\uffff" if not spool.get("last_used") else _neg(spool["last_used"]),
        spool.get("remaining_weight") if spool.get("remaining_weight") is not None else 1e9,
    )


def _neg(text: str) -> str:
    """Sortierschluessel fuer 'neuestes zuerst' bei ISO-Zeitstempeln."""
    return "".join(chr(255 - ord(c)) if c.isdigit() else c for c in text)


# Gleiche Farbfamilie liegt bei der redmean-Distanz unter ~100 (schwarz/fast
# schwarz 84, creme/weiss 55), verschiedene Farben ueber ~180 (weiss/silber 189).
SPOOL_COLOR_LIMIT = 150


def _color_close(slot: dict[str, Any], spool: dict[str, Any]) -> bool:
    if not slot.get("color") or not spool.get("color"):
        return True  # ohne Farbangabe entscheidet das Material
    return color_distance(slot["color"], spool["color"]) <= SPOOL_COLOR_LIMIT


def suggest_spools(
    slots: list[dict[str, Any]],
    spools: list[dict[str, Any]],
    fixed: dict[int, int | None] | None = None,
) -> dict[int, int | None]:
    """Spulen den geladenen Koepfen zuordnen; ``fixed`` (manuell) bleibt unangetastet.

    Eine Spule steckt physisch nur in einem Kopf: jede wird hoechstens einmal
    vergeben. Passt das Material nicht, wird nichts zugeordnet.
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
            # Lieber keine Zuordnung als eine falsche Spule, von der dann abgebucht wird.
            result[idx] = None
            continue
        result[idx] = best["id"]
        taken.add(best["id"])
    return result


def grams_per_slot(record: dict[str, Any]) -> dict[int, float]:
    """Verbrauch eines Drucks je physischem Kopf.

    Gewicht je logischem Filament (Slicer) x Anteil bei Abbruch, ueber die
    Zuordnungstabelle des Drucks (print_task_config.extruder_map_table:
    Position = logisch, Wert = Kopf) auf die Koepfe verteilt.
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
