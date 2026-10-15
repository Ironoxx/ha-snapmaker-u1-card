"""Schichtansicht: Bahnen der aktuellen Schicht aus der Druckdatei.

Die Integration laedt die laufende Datei einmal vom Drucker und zerlegt sie
in Schichten (gleiche Markierungen wie bei "Pause vor Schicht"). Je Schicht
bleiben nur extrudierende Bahnen, als Polylinien je Werkzeug (``T<n>`` =
logisches Filament; der Drucker setzt es ueber die Zuordnungstabelle auf
einen Kopf um). Zu jeder Polylinie wird die Dateiposition gemerkt: mit
``virtual_sdcard.file_position`` zeigt die Karte, was in der Schicht schon
gedruckt ist.

Punkte naeher als ``MIN_STEP`` mm am letzten werden ausgelassen; das haelt
auch Fuellungen mit vielen kurzen Segmenten klein, ohne das Bild zu aendern.

Nebenbei entsteht ein Zeitprofil (``timeline``): je Dateiposition die
aufsummierte Fahrzeit (Strecke / Vorschub, ohne Beschleunigung) und die
bis dahin gefoerderte Filamentlaenge je Werkzeug. Die Integration eicht die
Fahrzeit mit der echten Druckdauer (Restzeit) und rechnet den Restbedarf je
Kopf aus (Filament reicht nicht mehr).
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
SAMPLE = 30000  # Punkte-Stichprobe fuer den Bildausschnitt
TIMELINE_ROWS = 400  # Stuetzstellen des Zeitprofils
_DWELL = re.compile(r"([PS])(\d*\.?\d+)")
_FEED = re.compile(r"F(\d*\.?\d+)")


def view_box(sample: list[tuple[float, float]], objects: list[list[float]]) -> list[float] | None:
    """Bildausschnitt: wo gedruckt wird, ohne Ausreisser.

    Spuel- und Abstreifbahnen beim Werkzeugwechsel liegen am Bettrand und sind
    wenige, lange Bahnen; das Teil besteht aus vielen Punkten. Deshalb das
    1.-99.-Perzentil, dann die echten Grenzen der Punkte innerhalb eines
    Fensters darum (Kanten nicht abschneiden). Objekt-Polygone aus
    EXCLUDE_OBJECT_DEFINE kommen immer dazu.
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
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            for pattern, kind in _MARKERS:
                if pattern.match(line):
                    return pattern, kind
    return None


def parse_layers(path: Path, out: Path) -> dict[str, Any]:
    """Datei zerlegen (blockierend, im Executor aufrufen).

    Schichten gehen zeilenweise als JSON nach ``out``; im Speicher bleibt nur
    der Index (Schicht -> Dateiposition in ``out`` und im G-Code). So kostet
    auch eine 50-MB-Datei kaum Arbeitsspeicher.
    """
    marker = _detect_marker(path)
    if marker is None:
        raise ValueError("Keine Schichtwechsel in der Datei gefunden.")
    file_size = path.stat().st_size
    tl_step = max(256, file_size // TIMELINE_ROWS)
    timeline: list[list[float]] = []  # [offset, sekunden, e_t0 .. e_t7]
    t_kin = 0.0
    feed = 3000.0  # mm/min
    e_tool: dict[int, float] = {}
    next_row = 0
    last_extrude = 0  # Dateiposition der letzten Extrusion (danach: End-G-Code)
    pattern, kind = marker
    index: list[list[int]] = []  # [nummer, start im G-Code, offset in out, laenge in out]
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
    rng = random.Random(1)  # reproduzierbar
    objects: list[list[float]] = []

    def take(pt: tuple[float, float]) -> None:
        """Stichprobe (Reservoir) fuer den Bildausschnitt."""
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

    tail: tuple[float, float] | None = None  # letzter extrudierter Punkt (auch ausgelassen)

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
            if cmd == "G90":
                absolute = True
                abs_e = True
                continue
            if cmd == "G91":
                absolute = False
                abs_e = False
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
                de = ev - e if abs_e else ev
                if abs_e:
                    e = ev
                extruding = de > 0 and (nx != x or ny != y or bool(arc))
                if de > 0:
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
    # Leere Schichten (nur Fahrten) bleiben drin: Nummerierung gleich der Firmware.
    return {
        "index": index,
        "total": len(index),
        "bbox": view_box(sample, objects),
        "tools": sorted(tools_seen),
        "size": offset,
        "timeline": timeline,
        "last_extrude": last_extrude,
    }


ARC_STEP = 0.5  # mm Sehnenlaenge beim Zerlegen von G2/G3


def _arc_points(cmd: str, x: float, y: float, nx: float, ny: float,
                vals: dict[str, str]) -> list[tuple[float, float]] | None:
    """G2 (im Uhrzeigersinn) / G3 (gegen) mit I/J in Punkte zerlegen.

    Orca schreibt bei "Arc fitting" Rundungen als Boegen; als gerade Linie
    gezeichnet wuerden sie zur Sehne. Gleicher Start und Ziel = Vollkreis.
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
    # feste Spaltenfolge Werkzeug 0..7 (T0-T7), Laenge in mm
    return [round(e_tool.get(i, 0.0), 1) for i in range(8)]


def timeline_at(meta: dict[str, Any] | None, position: int | None) -> dict[str, Any] | None:
    """Fahrzeit und Filament bis ``position`` (linear zwischen Stuetzstellen)."""
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


def estimate_remaining(
    meta: dict[str, Any] | None, position: int | None, duration: float | None, slicer_total: float | None
) -> float | None:
    """Restzeit in s aus Zeitprofil, bisheriger Druckdauer und Slicer-Schaetzung.

    k = Anteil der Fahrzeit bis zur aktuellen Position. Zwei Schaetzungen:
    Slicer (Gesamtzeit nach dem Profil verteilt) und Ist (bisherige Dauer x
    Rest/Erledigt). Gewichtet mit k: am Anfang zaehlt der Slicer, gegen Ende
    die gemessene Geschwindigkeit.
    """
    at = timeline_at(meta, position)
    if at is None or not at["t_total"]:
        return None
    k = max(0.0, min(1.0, at["t"] / at["t_total"]))
    estimates = []
    if slicer_total and slicer_total > 0:
        estimates.append((1 - k, slicer_total * (1 - k)))
    if duration and duration > 0 and k >= 0.02:
        estimates.append((k, duration * (1 - k) / k))
    weight = sum(w for w, _ in estimates)
    if not weight:
        return None
    return max(0.0, sum(w * v for w, v in estimates) / weight)


def layer_payload(meta: dict[str, Any], store: Path, number: int) -> dict[str, Any] | None:
    """Eine Schicht fuer die Karte (1-basiert wie die Firmware); blockierend."""
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
