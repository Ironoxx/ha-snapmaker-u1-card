"""Machine controls without Home Assistant: flow, bed mesh, top cover, heads, G-code console.

Facts from Snapmaker's firmware sources (u1-klipper):

- Flow is Klipper's ``gcode_move.extrude_factor`` (1.0 = 100 %), set with ``M221 S<percent>``.
- ``bed_mesh.probed_matrix`` holds the probed points; rows run along Y
  (first row = ``mesh_min`` Y), columns along X.
- The top cover is the ``[purifier]`` object. It is always configured; whether
  the cover is plugged in is ``power_detected`` (ADC on its connector). Modes:
  0 idle, 1 cool chamber, 2 preheat chamber, 3 hot chamber. ``inner_fan_work_time``
  counts seconds of the circulation fan (filter wear). Fans are set with
  ``SET_PURIFIER FAN=exhaust|inner SPEED=0..1``; the firmware refuses a speed
  while no cover is detected. paxx12's firmware keeps the same status shape.
- Each head reports ``state`` from its park detector: ``PARKED`` or ``ACTIVATE``
  (anything else = unknown). ``T<n> A0`` switches to physical head n (without
  ``A0`` the firmware maps the logical tool first; ``T<n>`` is a classic
  G-code command, so Klipper only parses ``A0``, not ``A=0``); ``PARK_<extruder name>``
  parks the head on the carriage. Both home X/Y first if needed.
- Moonraker's gcode store records a script as one ``command`` entry per line,
  each carrying the whole script, followed by the ``response`` lines.
"""

from __future__ import annotations

import math
import re
from typing import Any

EXTRUDER_NAMES = ("extruder", "extruder1", "extruder2", "extruder3")

# ── Flow ───────────────────────────────────────────────────────────────────
FLOW_MIN = 50
FLOW_MAX = 150


def parse_flow(gcode_move: dict[str, Any] | None) -> float | None:
    """Flow in percent from gcode_move.extrude_factor; None if unknown."""
    factor = (gcode_move or {}).get("extrude_factor")
    if not isinstance(factor, (int, float)) or isinstance(factor, bool) or not math.isfinite(factor):
        return None
    return round(float(factor) * 100, 1)


def flow_gcode(percent: float) -> str:
    """M221 for a flow between FLOW_MIN and FLOW_MAX percent."""
    try:
        value = float(percent)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid flow {percent!r}") from err
    if not math.isfinite(value) or not FLOW_MIN <= value <= FLOW_MAX:
        raise ValueError(f"Flow must be between {FLOW_MIN} and {FLOW_MAX} %")
    return f"M221 S{round(value)}"


# ── Bed mesh ───────────────────────────────────────────────────────────────
def _point(value: Any) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return [round(float(value[0]), 1), round(float(value[1]), 1)]
    return None


def parse_bed_mesh(bm: dict[str, Any] | None) -> dict[str, Any] | None:
    """Loaded bed mesh: probed points, extremes and spread; None without a mesh.

    Klipper reports ``[[]]`` while no mesh is loaded. Only a rectangular matrix
    of numbers counts.
    """
    if not isinstance(bm, dict):
        return None
    matrix = bm.get("probed_matrix")
    if not isinstance(matrix, list) or not matrix:
        return None
    cols = len(matrix[0]) if isinstance(matrix[0], list) else 0
    if cols < 2 or len(matrix) < 2:
        return None
    rows: list[list[float]] = []
    for row in matrix:
        if not isinstance(row, list) or len(row) != cols:
            return None
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in row):
            return None
        rows.append([round(float(v), 3) for v in row])
    flat = [v for row in rows for v in row]
    low, high = min(flat), max(flat)
    return {
        "profile": str(bm.get("profile_name") or "") or None,
        "mesh_min": _point(bm.get("mesh_min")),
        "mesh_max": _point(bm.get("mesh_max")),
        "rows": len(rows),
        "cols": cols,
        "matrix": rows,
        "min": low,
        "max": high,
        "range": round(high - low, 3),
        "mean": round(sum(flat) / len(flat), 3),
    }


# ── Top cover (purifier) ───────────────────────────────────────────────────
PURIFIER_MODES = {0: "idle", 1: "cool", 2: "preheat", 3: "hot"}
PURIFIER_FANS = ("exhaust", "inner")


def _percent(fan: Any) -> float | None:
    speed = fan.get("speed") if isinstance(fan, dict) else None
    if not isinstance(speed, (int, float)) or isinstance(speed, bool):
        return None
    return round(max(0.0, min(1.0, float(speed))) * 100)


def _number(value: Any, digits: int = 1) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return round(float(value), digits)
    return None


def parse_purifier(p: dict[str, Any] | None) -> dict[str, Any] | None:
    """Top cover status; None if the firmware has no purifier object."""
    if not isinstance(p, dict) or not p:
        return None
    mode = p.get("mode")
    work = _number(p.get("inner_fan_work_time"), 0)
    desired = _number(p.get("desired_chamber_temp"))
    rpm = p.get("inner_fan_rpm")
    return {
        "present": bool(p.get("power_detected")),
        "mode": PURIFIER_MODES.get(mode, "unknown") if isinstance(mode, int) else None,
        "exhaust": _percent(p.get("exhaust_fan")),
        "inner": _percent(p.get("inner_fan")),
        "inner_rpm": round(rpm) if isinstance(rpm, (int, float)) and math.isfinite(rpm) else None,
        "filter_hours": round(work / 3600, 1) if work is not None else None,
        # 0 = no target (idle / plain cool mode)
        "desired_temp": desired if desired else None,
    }


def purifier_gcode(fan: str, percent: float) -> str:
    """SET_PURIFIER for the exhaust or the inner (circulation) fan."""
    if fan not in PURIFIER_FANS:
        raise ValueError(f"Unknown fan {fan!r}")
    try:
        value = float(percent)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid speed {percent!r}") from err
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("Speed must be between 0 and 100 %")
    return f"SET_PURIFIER FAN={fan} SPEED={value / 100:.2f}"


# ── Heads ──────────────────────────────────────────────────────────────────
def parse_head_states(status: dict[str, Any] | None) -> list[str | None]:
    """Per head: "parked" | "active" | "unknown"; None if the firmware does not report it."""
    out: list[str | None] = []
    for name in EXTRUDER_NAMES:
        state = ((status or {}).get(name) or {}).get("state")
        if not isinstance(state, str) or not state:
            out.append(None)
        elif state.upper() == "PARKED":
            out.append("parked")
        elif state.upper() == "ACTIVATE":
            out.append("active")
        else:
            out.append("unknown")
    return out


def pick_gcode(head: int) -> str:
    """Take physical head 0-3 (parks the current one first)."""
    if not isinstance(head, int) or not 0 <= head < len(EXTRUDER_NAMES):
        raise ValueError(f"Invalid head {head!r}")
    return f"T{head} A0"


def park_gcode(head: int) -> str:
    """Put the head on the carriage (0-3) back into its dock."""
    if not isinstance(head, int) or not 0 <= head < len(EXTRUDER_NAMES):
        raise ValueError(f"Invalid head {head!r}")
    return f"PARK_{EXTRUDER_NAMES[head].upper()}"


# ── G-code console ─────────────────────────────────────────────────────────
CONSOLE_MAX_CHARS = 2000
CONSOLE_MAX_LINES = 20

# Allowed while a print runs: tuning, fans, light, top cover, queries and the
# print actions. Anything that moves axes, homes, probes, switches heads,
# restarts or loads/unloads filament stays locked until the print is over.
PRINT_SAFE_COMMANDS = frozenset({
    "M104", "M140", "M106", "M107", "M220", "M221", "M117", "M118", "M105", "M114", "M115", "M112",
    "SET_FAN_SPEED", "SET_PRESSURE_ADVANCE", "SET_VELOCITY_LIMIT", "SET_HEATER_TEMPERATURE",
    "SET_LED", "SET_PURIFIER", "SET_RETRACTION", "SET_GCODE_OFFSET",
    "RESPOND", "STATUS", "HELP",
    "PAUSE", "RESUME", "CANCEL_PRINT", "EXCLUDE_OBJECT",
})
PRINT_SAFE_PREFIXES = ("GET_", "QUERY_")

_WORD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")


def console_lines(script: str) -> list[str]:
    """Non-empty lines of a console script without comment-only lines."""
    if not isinstance(script, str) or not script.strip():
        raise ValueError("G-code missing")
    if len(script) > CONSOLE_MAX_CHARS:
        raise ValueError(f"At most {CONSOLE_MAX_CHARS} characters")
    lines = [line.strip() for line in script.replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line and not line.startswith(";")]
    if not lines:
        raise ValueError("G-code missing")
    if len(lines) > CONSOLE_MAX_LINES:
        raise ValueError(f"At most {CONSOLE_MAX_LINES} lines")
    return lines


def command_word(line: str) -> str:
    """Command of a G-code line in upper case ("G1", "SET_FAN_SPEED"); "" if none."""
    m = _WORD.match(line.strip())
    return m.group(0).upper() if m else ""


def blocked_while_printing(lines: list[str]) -> list[str]:
    """Commands of ``lines`` that are not allowed during a print (in order, unique)."""
    out: list[str] = []
    for line in lines:
        word = command_word(line)
        if word in PRINT_SAFE_COMMANDS or word.startswith(PRINT_SAFE_PREFIXES):
            continue
        if word not in out:
            out.append(word or line[:20])
    return out


def console_responses(store: list[dict[str, Any]] | None, script: str, limit: int = 50) -> list[str]:
    """Printer responses to ``script`` from Moonraker's gcode store.

    The last ``command`` entry carrying exactly this script marks the start; the
    responses after it belong to it until another command shows up. Clock
    independent, unlike filtering by time.
    """
    entries = [e for e in (store or []) if isinstance(e, dict)]
    start = None
    for i in range(len(entries) - 1, -1, -1):
        e = entries[i]
        if e.get("type") == "command" and str(e.get("message", "")).strip() == script.strip():
            start = i
            break
    if start is None:
        return []
    out: list[str] = []
    for e in entries[start + 1:]:
        if e.get("type") == "command":
            if str(e.get("message", "")).strip() == script.strip():
                continue  # same script, one entry per line
            break
        if e.get("type") == "response":
            out.append(str(e.get("message", "")))
    return out[-limit:]
