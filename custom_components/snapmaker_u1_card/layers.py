"""Layer view: the paths of the current layer, taken from the print file.

The integration downloads the running file once and splits it into layers
(same markers as "pause at layer"). Per layer only extruding moves are kept,
as polylines per tool (``T<n>`` = logical filament; the printer maps it to a
head through the map table). Each polyline remembers its file position: with
``virtual_sdcard.file_position`` the card shows what has already been
printed in the layer.

Points closer than ``MIN_STEP`` mm to the previous one are dropped; this
keeps infill with many short segments small without changing the picture.

A time profile (``timeline``) is built on the way: per file position the
accumulated move time (distance / feed rate, no acceleration) and the
filament length extruded so far per tool. The integration calibrates the
move time against the real print duration (remaining time) and computes the
remaining demand per head (filament running out).
"""

from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from typing import Any

from .jobs import _MARKERS

MIN_STEP = 0.35  # mm
MAX_POINTS_PER_LAYER = 40000
_NUM = re.compile(r"([XYZEIJ])(-?\d*\.?\d+)")
_TOOL = re.compile(r"^T(\d+)\b")
_OBJECT = re.compile(r"^EXCLUDE_OBJECT_DEFINE\b.*?POLYGON=(\[\[.*?\]\])", re.IGNORECASE)
SAMPLE = 30000  # point sample for the viewport
TIMELINE_ROWS = 400  # samples in the time profile
_DWELL = re.compile(r"([PS])(\d*\.?\d+)")
_FEED = re.compile(r"F(\d*\.?\d+)")
_M73_R = re.compile(r"\bR(\d+(?:\.\d+)?)", re.IGNORECASE)
# Weight of the history/default speed factor, in seconds of slicer time: after
# about this much printed slicer time the measured speed counts as much.
PRIOR_WEIGHT_S = 600.0


def view_box(sample: list[tuple[float, float]], objects: list[list[float]]) -> list[float] | None:
    """Viewport: where the part is printed, without outliers.

    Purge and wipe moves at tool changes sit at the bed edge and are few, long
    moves; the part consists of many points. Hence the 1st-99th percentile,
    then the real bounds of the points within a window around it (do not cut
    off edges). Object polygons from EXCLUDE_OBJECT_DEFINE are always added.
    """
    boxes = []
    if sample:
        xs = sorted(p[0] for p in sample)
        ys = sorted(p[1] for p in sample)
        n = len(xs)
        lo, hi = int(n * 0.01), max(0, math.ceil(n * 0.99) - 1)
        qx0, qx1, qy0, qy1 = xs[lo], xs[hi], ys[lo], ys[hi]
        mx, my = max(5.0, (qx1 - qx0) * 0.15), max(5.0, (qy1 - qy0) * 0.15)
        inner = [p for p in sample if qx0 - mx <= p[0] <= qx1 + mx and qy0 - my <= p[1] <= qy1 + my]
        if inner:
            boxes.append([min(p[0] for p in inner), min(p[1] for p in inner),
                          max(p[0] for p in inner), max(p[1] for p in inner)])
    boxes += objects
    if not boxes:
        return None
    return [round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1)]


def _detect_marker(path: Path) -> tuple[re.Pattern[str], int] | None:
    """First layer change marker found in the file, or None."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for pattern, kind in _MARKERS:
                if pattern.match(line):
                    return pattern, kind
    return None


def parse_layers(path: Path, out: Path) -> dict[str, Any]:
    """Split a file into layers (blocking, run in the executor).

    Layers are written line by line as JSON to ``out``; only the index
    (layer -> position in ``out`` and in the G-code) stays in memory, so even
    a 50 MB file costs very little RAM.
    """
    marker = _detect_marker(path)
    if marker is None:
        raise ValueError("No layer changes found in the file.")
    file_size = path.stat().st_size
    tl_step = max(256, file_size // TIMELINE_ROWS)
    timeline: list[list[float]] = []  # [offset, seconds, e_t0 .. e_t7]
    t_kin = 0.0
    feed = 3000.0  # mm/min
    e_tool: dict[int, float] = {}
    next_row = 0
    last_extrude = 0  # file position of the last extrusion (end G-code follows)
    pattern, kind = marker
    index: list[list[int]] = []  # [number, start in G-code, offset in out, length in out]
    tools_seen: set[int] = set()
    sink = out.open("wb")
    cur: dict[str, Any] | None = None
    x = y = z = 0.0
    e = 0.0
    absolute = True
    abs_e = True
    tool = 0
    poly: list[float] | None = None
    poly_tool = -1
    points = 0
    sample: list[tuple[float, float]] = []
    seen = 0
    rng = random.Random(1)  # reproducible
    objects: list[list[float]] = []
    slicer: list[list[int]] = []  # [file offset, slicer remaining s] from M73 R (Orca/Prusa)

    def take(pt: tuple[float, float]) -> None:
        """Reservoir sample for the viewport."""
        nonlocal seen
        seen += 1
        if len(sample) < SAMPLE:
            sample.append(pt)
        else:
            k = rng.randrange(seen)
            if k < SAMPLE:
                sample[k] = pt
    layer_no = 0
    offset = 0

    tail: tuple[float, float] | None = None  # last extruded point (also when it was skipped)

    def close() -> None:
        nonlocal poly, tail
        if poly is not None and tail is not None and (poly[-2], poly[-1]) != tail:
            poly += [tail[0], tail[1]]
        tail = None
        if cur is not None and poly is not None and len(poly) >= 4:
            cur["segs"].append([poly_tool, poly, poly_start])
            tools_seen.add(poly_tool)
        poly = None

    def flush() -> None:
        if cur is None:
            return
        blob = json.dumps(cur, separators=(",", ":")).encode()
        index.append([cur["n"], cur["start"], sink.tell(), len(blob)])
        sink.write(blob + b"\n")

    poly_start = 0
    with path.open("rb") as fh:
        for raw in fh:
            line_offset = offset
            offset += len(raw)
            if line_offset >= next_row:
                timeline.append([line_offset, round(t_kin, 1), *_e_row(e_tool)])
                next_row = line_offset + tl_step
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            m = pattern.match(line)
            if m:
                close()
                flush()
                if kind == 1:
                    layer_no = int(m.group(1)) + 1
                elif m.groups():
                    layer_no = int(m.group(1))
                else:
                    layer_no += 1
                cur = {"n": layer_no, "z": None, "segs": [], "start": line_offset}
                points = 0
                continue
            if line[0] == ";":
                continue
            line = line.split(";", 1)[0].strip()
            if line[:21].upper() == "EXCLUDE_OBJECT_DEFINE":
                om = _OBJECT.match(line)
                if om:
                    try:
                        pts = json.loads(om.group(1))
                        objects.append([min(p[0] for p in pts), min(p[1] for p in pts),
                                        max(p[0] for p in pts), max(p[1] for p in pts)])
                    except (ValueError, TypeError, IndexError):
                        pass
                continue
            t = _TOOL.match(line)
            if t:
                close()
                tool = int(t.group(1))
                continue
            cmd = line.split(" ", 1)[0].upper()
            # Klipper: G90/G91 only affect XYZ (G91 makes E relative, G90 does not
            # make it absolute again); the E mode comes from M82/M83. Orca writes M83, then G90.
            if cmd == "G90":
                absolute = True
                continue
            if cmd == "G91":
                absolute = False
                continue
            if cmd == "M82":
                abs_e = True
                continue
            if cmd == "M83":
                abs_e = False
                continue
            if cmd == "G92":
                vals = dict(_NUM.findall(line.upper()))
                if "E" in vals:
                    e = float(vals["E"])
                continue
            if cmd == "M73":
                rm = _M73_R.search(line, 3)
                if rm:
                    left = round(float(rm.group(1)) * 60)
                    if not slicer or slicer[-1][1] != left:
                        slicer.append([line_offset, left])
                continue
            if cmd == "G4":
                dw = dict(_DWELL.findall(line.upper()[2:]))
                if "P" in dw:
                    t_kin += float(dw["P"]) / 1000
                elif "S" in dw:
                    t_kin += float(dw["S"])
                continue
            if cmd not in ("G0", "G1", "G2", "G3"):
                continue
            upper = line.upper()
            fpos = upper.find("F")
            if fpos > 0:
                fm = _FEED.match(upper, fpos)
                if fm:
                    feed = max(1.0, float(fm.group(1)))
            vals = dict(_NUM.findall(upper))
            nx, ny, nz = x, y, z
            if "X" in vals:
                nx = float(vals["X"]) if absolute else x + float(vals["X"])
            if "Y" in vals:
                ny = float(vals["Y"]) if absolute else y + float(vals["Y"])
            if "Z" in vals:
                nz = float(vals["Z"]) if absolute else z + float(vals["Z"])
            arc = _arc_points(cmd, x, y, nx, ny, vals) if cmd in ("G2", "G3") else None
            extruding = False
            de = 0.0
            if "E" in vals:
                ev = float(vals["E"])
                e_abs = abs_e and absolute
                de = ev - e if e_abs else ev
                e = ev if e_abs else e + ev
                extruding = de > 0 and (nx != x or ny != y or bool(arc))
                if de:
                    # net: retraction and unretraction cancel out
                    e_tool[tool] = e_tool.get(tool, 0.0) + de
            if arc:
                flat = sum(math.dist(a, b) for a, b in zip([(x, y), *arc[:-1]], arc, strict=True))
                dist = math.sqrt(flat ** 2 + (nz - z) ** 2) or abs(de)
            else:
                dist = math.sqrt((nx - x) ** 2 + (ny - y) ** 2 + (nz - z) ** 2) or abs(de)
            t_kin += dist / (feed / 60)
            if extruding:
                last_extrude = line_offset
            if extruding and cur is not None:
                if cur["z"] is None:
                    cur["z"] = round(nz, 3)
                if poly is None or poly_tool != tool:
                    close()
                    take((x, y))
                    poly = [round(x, 2), round(y, 2)]
                    poly_tool = tool
                    poly_start = line_offset
                for px, py in arc or [(nx, ny)]:
                    lx, ly = poly[-2], poly[-1]
                    if (px - lx) ** 2 + (py - ly) ** 2 >= MIN_STEP * MIN_STEP and points < MAX_POINTS_PER_LAYER:
                        poly += [round(px, 2), round(py, 2)]
                        points += 1
                        take((px, py))
                tail = (round(nx, 2), round(ny, 2))
            elif poly is not None and (nx != x or ny != y or arc):
                close()
            x, y, z = nx, ny, nz
    close()
    flush()
    sink.close()
    timeline.append([offset, round(t_kin, 1), *_e_row(e_tool)])
    # Empty layers (travel only) stay in: numbering matches the firmware.
    return {
        "index": index,
        "total": len(index),
        "bbox": view_box(sample, objects),
        "tools": sorted(tools_seen),
        "size": offset,
        "timeline": timeline,
        "last_extrude": last_extrude,
        # start of the first layer: everything before is the start sequence
        # (homing, leveling, calibration, purge line)
        # (SET_PRINT_STATS_INFO ... CURRENT_LAYER=0 marks the start sequence as layer 0)
        "begin": next((row[1] for row in index if row[0] >= 1), index[0][1] if index else None),
        "slicer": slicer if len(slicer) >= 2 else [],
        "objects": [[round(v, 1) for v in o] for o in objects],
    }


ARC_STEP = 0.5  # mm chord length when splitting G2/G3


def _arc_points(cmd: str, x: float, y: float, nx: float, ny: float,
                vals: dict[str, str]) -> list[tuple[float, float]] | None:
    """Split G2 (clockwise) / G3 (counter-clockwise) arcs with I/J into points.

    Orca writes curves as arcs when "Arc fitting" is on; drawn as a straight
    line they would become a chord. Identical start and end = full circle.
    """
    if "I" not in vals and "J" not in vals:
        return None
    cx, cy = x + float(vals.get("I", 0)), y + float(vals.get("J", 0))
    r = math.hypot(x - cx, y - cy)
    if r < 1e-6:
        return None
    a0 = math.atan2(y - cy, x - cx)
    a1 = math.atan2(ny - cy, nx - cx)
    sweep = a1 - a0
    if cmd == "G2":
        if sweep >= -1e-9:
            sweep -= 2 * math.pi
    elif sweep <= 1e-9:
        sweep += 2 * math.pi
    n = max(1, min(720, math.ceil(abs(sweep) * r / ARC_STEP)))
    pts = [(cx + r * math.cos(a0 + sweep * i / n), cy + r * math.sin(a0 + sweep * i / n)) for i in range(1, n)]
    pts.append((nx, ny))
    return pts


def _e_row(e_tool: dict[int, float]) -> list[float]:
    # fixed column order tool 0..7 (T0-T7), length in mm
    return [round(e_tool.get(i, 0.0), 1) for i in range(8)]


def timeline_at(meta: dict[str, Any] | None, position: int | None) -> dict[str, Any] | None:
    """Move time and filament up to ``position`` (linear between samples)."""
    rows = (meta or {}).get("timeline") or []
    if not rows or position is None:
        return None
    last = rows[-1]
    position = max(0, min(int(position), int(last[0])))
    lo, hi = 0, len(rows) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if rows[mid][0] <= position:
            lo = mid
        else:
            hi = mid
    a, b = rows[lo], rows[hi]
    f = (position - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
    cur = [a[i] + (b[i] - a[i]) * f for i in range(1, len(a))]
    return {"t": cur[0], "t_total": last[1], "e": cur[1:], "e_total": list(last[2:])}


def slicer_left(meta: dict[str, Any] | None, position: int | None) -> float | None:
    """Slicer remaining time (M73 R) at a file position, linear between the marks."""
    pts = (meta or {}).get("slicer") or []
    if len(pts) < 2 or position is None:
        return None
    if position <= pts[0][0]:
        return float(pts[0][1])
    if position >= pts[-1][0]:
        return float(pts[-1][1])
    lo, hi = 0, len(pts) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if pts[mid][0] <= position:
            lo = mid
        else:
            hi = mid
    (o0, v0), (o1, v1) = pts[lo], pts[hi]
    return v0 + (v1 - v0) * (position - o0) / (o1 - o0) if o1 > o0 else float(v0)


def estimate_remaining(
    meta: dict[str, Any] | None, position: int | None, duration: float | None, slicer_total: float | None,
    *, begin_duration: float | None = None, factor: float | None = None, prep_s: float | None = None,
) -> float | None:
    """Remaining time in seconds.

    With slicer marks (M73 R): the slicer's own remaining time at the file
    position, scaled by the measured speed. The speed is measured from the
    start of the first layer (``begin_duration`` = print duration there), so
    the start sequence (leveling, calibration) does not distort it. Before
    enough is printed, ``factor`` (from earlier prints) carries the estimate;
    the measured speed takes over smoothly (PRIOR_WEIGHT_S). Still in the start
    sequence: expected remaining start time (``prep_s`` from earlier prints) +
    slicer time of the print.

    Without marks: move-time profile, weighted between slicer total and
    measured speed (also measured from the first layer when known).
    """
    f0 = factor if factor and 0.3 < factor < 3 else 1.0
    s_now = slicer_left(meta, position)
    begin = (meta or {}).get("begin")
    if s_now is not None:
        s_begin = slicer_left(meta, begin) if begin is not None else None
        if s_begin is None or position is None or begin is None or position < begin:
            prep_left = max(0.0, (prep_s or 0.0) - (duration or 0.0)) if prep_s else 0.0
            return max(0.0, prep_left + (s_begin if s_begin is not None else s_now) * f0)
        done = max(0.0, s_begin - s_now)
        if begin_duration is not None and duration is not None and duration >= begin_duration:
            actual = duration - begin_duration
            f = (f0 * PRIOR_WEIGHT_S + actual) / (PRIOR_WEIGHT_S + done)
        else:
            f = f0  # joined mid-print (e.g. HA restart): no reference point
        return max(0.0, s_now * f)

    at = timeline_at(meta, position)
    if at is None or not at["t_total"]:
        return None
    k = max(0.0, min(1.0, at["t"] / at["t_total"]))
    dur = duration
    kb = 0.0
    if begin_duration is not None and duration is not None and begin is not None:
        b = timeline_at(meta, begin)
        if b and at["t_total"]:
            kb = max(0.0, min(0.99, b["t"] / at["t_total"]))
            dur = duration - begin_duration
    estimates = []
    if slicer_total and slicer_total > 0:
        estimates.append((1 - k, slicer_total * f0 * (1 - k)))
    kk = (k - kb) / (1 - kb) if kb else k
    if dur and dur > 0 and kk >= 0.02:
        estimates.append((k, dur * (1 - kk) / kk))
    weight = sum(w for w, _ in estimates)
    if not weight:
        return None
    return max(0.0, sum(w * v for w, v in estimates) / weight)


def layer_payload(meta: dict[str, Any], store: Path, number: int) -> dict[str, Any] | None:
    """One layer for the card (1-based like the firmware); blocking."""
    index = meta["index"]
    pos = next((i for i, row in enumerate(index) if row[0] == number), None)
    if pos is None:
        return None
    _n, start, off, length = index[pos]
    with store.open("rb") as fh:
        fh.seek(off)
        lay = json.loads(fh.read(length))
    end = index[pos + 1][1] if pos + 1 < len(index) else meta["size"]
    return {
        "layer": number,
        "total": meta["total"],
        "z": lay["z"],
        "bbox": meta["bbox"],
        "tools": meta["tools"],
        "start": start,
        "end": end,
        "segs": lay["segs"],
    }
