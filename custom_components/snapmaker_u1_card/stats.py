"""Statistik aus der Moonraker-Druckhistorie und Wartungsplaner.

Moonrakers ``[history]`` speichert jeden Druck seit Inbetriebnahme. Daraus
entstehen Monatswerte (rueckwirkend, nicht erst ab Installation dieser
Integration). Strom kennt nur die eigene Historie der Integration. Kosten:
erfasste Drucke mit ihren echten Kosten, alle anderen mit dem Filamentpreis
geschaetzt (wie in der Material-Tabelle), damit Summe und Tabelle passen.

Wartung zaehlt in Druckstunden (Moonraker ``history/totals``), damit der
Stand auch eine Neuinstallation von Home Assistant ueberlebt.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, tzinfo
from typing import Any

from .parsing import filament_price_for, parse_file_filaments

MONTHS = 12
OK_STATUS = ("completed",)
FAIL_STATUS = ("cancelled", "error", "klippy_shutdown", "klippy_disconnect", "interrupted", "server_exit")

# Wartungspunkte: Schluessel, Standardintervall in Druckstunden (0 = aus)
MAINTENANCE_ITEMS: dict[str, int] = {
    "plate": 30,        # Druckplatte reinigen
    "nozzle": 100,      # Duesen und Abstreifer reinigen
    "rails": 300,       # Linearfuehrungen schmieren
    "belts": 500,       # Riemenspannung pruefen
    "filter": 0,        # Luftfilter wechseln (nur mit Luftreiniger)
}


def _month(ts: float, tz: tzinfo) -> str:
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m")


def _month_keys(now: float, tz: tzinfo, count: int = MONTHS) -> list[str]:
    d = datetime.fromtimestamp(now, tz)
    y, m = d.year, d.month
    keys = []
    for _ in range(count):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def job_grams(job: dict[str, Any]) -> float | None:
    """Verbrauchtes Gewicht eines Moonraker-Jobs; abgebrochene anteilig."""
    meta = job.get("metadata") or {}
    total_g = _num(meta.get("filament_weight_total"))
    if total_g is None:
        return None
    if job.get("status") in OK_STATUS:
        return total_g
    used, planned = _num(job.get("filament_used")), _num(meta.get("filament_total"))
    if used is not None and planned:
        return total_g * max(0.0, min(1.0, used / planned))
    return None


def build_stats(
    jobs: list[dict[str, Any]],
    history: list[dict[str, Any]],
    now: float,
    tz: tzinfo = UTC,
    prices: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    """Monatswerte der letzten 12 Monate und Gesamtwerte."""
    keys = _month_keys(now, tz)
    months = {k: {"month": k, "prints": 0, "failed": 0, "hours": 0.0, "filament_g": 0.0,
                  "energy": None, "cost": None} for k in keys}
    files: Counter[str] = Counter()
    total = ok = fail = 0
    hours = grams = 0.0
    longest = 0.0
    mats: dict[str, dict[str, Any]] = {}
    colors: dict[tuple[str, str], float] = {}
    records = [r for r in history if _num(r.get("ended")) is not None]
    used_records: set[int] = set()
    energy = cost = 0.0
    have_energy = have_cost = estimated = False
    for job in jobs:
        status = job.get("status")
        if status == "in_progress":
            continue
        job_cost = _add_materials(job, status, mats, colors, prices or {})
        rec_i = _match_record(job, records, used_records)
        if rec_i is not None:
            used_records.add(rec_i)
            rec_cost = _num(records[rec_i].get("total_cost"))
            if rec_cost is not None:
                job_cost = rec_cost
        elif job_cost is not None:
            estimated = True
        start = _num(job.get("start_time"))
        dur = _num(job.get("print_duration")) or 0.0
        g = job_grams(job) or 0.0
        if job_cost is not None:
            cost += job_cost
            have_cost = True
        total += 1
        hours += dur / 3600
        grams += g
        longest = max(longest, dur)
        if status in OK_STATUS:
            ok += 1
            files[str(job.get("filename") or "")] += 1
        elif status in FAIL_STATUS:
            fail += 1
        if start is None:
            continue
        bucket = months.get(_month(start, tz))
        if bucket is None:
            continue
        if status in OK_STATUS:
            bucket["prints"] += 1
        elif status in FAIL_STATUS:
            bucket["failed"] += 1
        bucket["hours"] += dur / 3600
        bucket["filament_g"] += g
        if job_cost is not None:
            bucket["cost"] = (bucket["cost"] or 0.0) + job_cost
    # Kosten der Drucke ohne Moonraker-Eintrag erst hier (Monat vom Ende)
    matched = {id(records[i]) for i in used_records}
    for rec in history:
        ended = _num(rec.get("ended"))
        e, c = _num(rec.get("energy")), _num(rec.get("total_cost"))
        bucket = months.get(_month(ended, tz)) if ended is not None else None
        if e is not None:
            energy += e
            have_energy = True
            if bucket is not None:
                bucket["energy"] = (bucket["energy"] or 0.0) + e
        if c is not None and id(rec) not in matched:
            cost += c
            have_cost = True
            if bucket is not None:
                bucket["cost"] = (bucket["cost"] or 0.0) + c
    for b in months.values():
        b["hours"] = round(b["hours"], 2)
        b["filament_g"] = round(b["filament_g"], 1)
        for key in ("energy", "cost"):
            if b[key] is not None:
                b[key] = round(b[key], 3 if key == "energy" else 2)
    finished = ok + fail
    return {
        "months": [months[k] for k in keys],
        "totals": {
            "prints": total,
            "completed": ok,
            "failed": fail,
            "success_rate": round(ok / finished * 100, 1) if finished else None,
            "hours": round(hours, 1),
            "filament_kg": round(grams / 1000, 3),
            "longest_h": round(longest / 3600, 2),
            "energy": round(energy, 2) if have_energy else None,
            "cost": round(cost, 2) if have_cost else None,
            "cost_estimated": estimated,
        },
        "top_files": [
            {"file": f, "count": n} for f, n in files.most_common(5) if f
        ],
        "materials": sorted(
            ({**m, "grams": round(m["grams"], 1),
              "cost": round(m["cost"], 2) if m["cost"] is not None else None,
              "success_rate": round(m["ok"] / (m["ok"] + m["failed"]) * 100, 1) if (m["ok"] + m["failed"]) else None}
             for m in mats.values()),
            key=lambda m: -m["grams"],
        ),
        "colors": [
            {"type": t, "color": c, "grams": round(g, 1)}
            for (t, c), g in sorted(colors.items(), key=lambda kv: -kv[1])[:10]
        ],
    }


def _add_materials(job: dict[str, Any], status: Any, mats: dict[str, dict[str, Any]],
                   colors: dict[tuple[str, str], float], prices: dict[str, float | None]) -> float | None:
    """Verbrauch je Material und Farbe (Slicer-Gewichte, Abbrueche anteilig).

    Rueckgabe: geschaetzte Filamentkosten des Jobs, None ohne Preis fuer
    jedes verwendete Material.
    """
    meta = job.get("metadata") or {}
    fils = [f for f in parse_file_filaments(meta) if f.get("used") and f.get("weight")]
    if not fils:
        return None
    job_cost: float | None = 0.0
    scale = 1.0
    if status not in OK_STATUS:
        used, planned = _num(job.get("filament_used")), _num(meta.get("filament_total"))
        scale = max(0.0, min(1.0, used / planned)) if used is not None and planned else 0.0
    seen: set[str] = set()
    for fil in fils:
        kind = (fil.get("type") or "?").upper()
        grams = fil["weight"] * scale
        m = mats.setdefault(kind, {"type": kind, "grams": 0.0, "prints": 0, "ok": 0, "failed": 0, "cost": 0.0})
        m["grams"] += grams
        price = filament_price_for(kind, prices)
        m["cost"] = None if price is None or m["cost"] is None else m["cost"] + grams * price / 1000
        job_cost = None if price is None or job_cost is None else job_cost + grams * price / 1000
        if kind not in seen:
            seen.add(kind)
            m["prints"] += 1
            if status in OK_STATUS:
                m["ok"] += 1
            elif status in FAIL_STATUS:
                m["failed"] += 1
        if fil.get("color"):
            key = (kind, fil["color"])
            colors[key] = colors.get(key, 0.0) + grams
    return job_cost


MATCH_WINDOW_S = 600


def _base(name: Any) -> str:
    return str(name or "").rsplit("/", 1)[-1].lower()


def _match_record(job: dict[str, Any], records: list[dict[str, Any]], used: set[int]) -> int | None:
    """Eigenen Historien-Eintrag zum Moonraker-Job finden (Datei + Ende +-10 min)."""
    end = _num(job.get("end_time"))
    if end is None:
        start, dur = _num(job.get("start_time")), _num(job.get("total_duration"))
        end = start + dur if start is not None and dur is not None else None
    if end is None:
        return None
    name = _base(job.get("filename"))
    best: tuple[float, int] | None = None
    for i, rec in enumerate(records):
        if i in used or _base(rec.get("file")) != name:
            continue
        diff = abs(float(rec["ended"]) - end)
        if diff <= MATCH_WINDOW_S and (best is None or diff < best[0]):
            best = (diff, i)
    return best[1] if best else None


class Maintenance:
    """Wartungspunkte mit Intervall in Druckstunden."""

    def __init__(self, stored: dict[str, Any] | None) -> None:
        self.done: dict[str, dict[str, float]] = {
            k: dict(v) for k, v in (stored or {}).items() if isinstance(v, dict)
        }

    def as_stored(self) -> dict[str, Any]:
        return self.done

    def baseline(self, hours: float | None, now: float) -> bool:
        """Beim ersten Mal den aktuellen Stand als 'erledigt' setzen.

        Sonst waere bei einem schon laenger genutzten Drucker sofort alles faellig.
        """
        if hours is None:
            return False
        changed = False
        for key in MAINTENANCE_ITEMS:
            if key not in self.done:
                self.done[key] = {"hours": round(hours, 2), "at": now}
                changed = True
        return changed

    def mark_done(self, key: str, hours: float | None, now: float) -> None:
        if key not in MAINTENANCE_ITEMS:
            raise KeyError(key)
        prev = self.done.get(key, {})
        self.done[key] = {"hours": round(hours if hours is not None else prev.get("hours", 0.0), 2), "at": now}

    def status(self, hours: float | None, intervals: dict[str, int]) -> list[dict[str, Any]]:
        items = []
        for key, default in MAINTENANCE_ITEMS.items():
            interval = int(intervals.get(key, default) or 0)
            if interval <= 0:
                continue
            done = self.done.get(key) or {}
            used = None if hours is None else max(0.0, hours - float(done.get("hours", hours)))
            items.append({
                "key": key,
                "interval_h": interval,
                "used_h": None if used is None else round(used, 1),
                "remaining_h": None if used is None else round(interval - used, 1),
                "progress": None if used is None else round(min(used / interval, 9.99) * 100),
                "due": used is not None and used >= interval,
                "done_at": done.get("at"),
            })
        return items
