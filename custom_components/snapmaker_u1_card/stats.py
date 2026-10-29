"""Statistics from Moonraker's print history and the maintenance planner.

Moonraker's ``[history]`` stores every print since commissioning, so the
monthly values are retroactive (not only since this integration was
installed). Energy is only known from the integration's own history. Cost:
recorded prints with their real cost, all others estimated from the
filament price (as in the material table), so that total and table match.

Maintenance counts in print hours (Moonraker ``history/totals``) so the
state survives a reinstall of Home Assistant, and/or in calendar months
since it was last done (Snapmaker's U1 maintenance guide gives months, not
hours). Whichever is reached first makes an item due.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, tzinfo
from typing import Any

from .parsing import filament_price_for, parse_file_filaments

MONTHS = 12
OK_STATUS = ("completed",)
FAIL_STATUS = ("cancelled", "error", "klippy_shutdown", "klippy_disconnect", "interrupted", "server_exit")

# Maintenance items: key, default interval in print hours (0 = off)
MAINTENANCE_ITEMS: dict[str, int] = {
    "plate": 30,        # clean the build plate
    "nozzle": 100,      # clean nozzles and wipers
    "rails": 300,       # lubricate linear rails
    "belts": 500,       # check belt tension
    "filter": 0,        # replace the air filter (only shown with the top cover)
    "carbon_rods": 0,   # clean the X carbon rods
    "lead_screws": 0,   # clean and grease the Z lead screws and nuts
    "coupling": 0,      # clean the steel pins and balls of the head coupling
    "pogo": 0,          # clean the pogo contacts of the heads
}
# Default interval in calendar months (0 = off), from Snapmaker's U1 core components
# maintenance guide (wiki, updated 21.09.2026): linear shafts/bearings, X carbon rods
# and XY belts monthly, Z lead screws and steel pins/balls quarterly, pogo contacts
# every 4-6 months.
MAINTENANCE_MONTHS: dict[str, int] = {
    "plate": 0, "nozzle": 0, "rails": 1, "belts": 1, "filter": 0,
    "carbon_rods": 1, "lead_screws": 3, "coupling": 3, "pogo": 6,
}
DAYS_PER_MONTH = 30.44
MAINTENANCE_LABELS: dict[str, tuple[str, str]] = {
    "plate": ("Druckplatte reinigen", "Clean the build plate"),
    "nozzle": ("Düsen und Abstreifer reinigen", "Clean nozzles and wipers"),
    "rails": ("Linearführungen reinigen und schmieren", "Clean and lubricate linear shafts"),
    "belts": ("Riemen prüfen", "Check the belts"),
    "filter": ("Luftfilter wechseln", "Replace the air filter"),
    "carbon_rods": ("X-Carbonstangen reinigen", "Clean the X carbon rods"),
    "lead_screws": ("Z-Spindeln und Muttern schmieren", "Grease the Z lead screws and nuts"),
    "coupling": ("Stahlstifte und Kugeln der Kopfaufnahme reinigen", "Clean the steel pins and balls of the head coupling"),
    "pogo": ("Pogo-Kontakte der Köpfe reinigen", "Clean the pogo contacts of the heads"),
}


def maintenance_label(key: str, de: bool = True) -> str:
    label = MAINTENANCE_LABELS.get(key)
    return (label[0] if de else label[1]) if label else key


def _month(ts: float, tz: tzinfo) -> str:
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m")


def _month_keys(now: float, tz: tzinfo, count: int = MONTHS) -> list[str]:
    """The last ``count`` months as "YYYY-MM", oldest first."""
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
    """Filament weight used by a Moonraker job; cancelled jobs pro rata."""
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
    """Monthly values of the last 12 months plus totals."""
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
    # Cost of prints without a Moonraker job is added here (month of the end)
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
    """Usage per material and colour (slicer weights, cancelled jobs pro rata).

    Returns the estimated filament cost of the job, None if a price is
    missing for any material used.
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
    """Find the integration's own history record for a Moonraker job (file + end +-10 min)."""
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
    """Maintenance items with an interval in print hours."""

    def __init__(self, stored: dict[str, Any] | None) -> None:
        self.done: dict[str, dict[str, float]] = {
            k: dict(v) for k, v in (stored or {}).items() if isinstance(v, dict)
        }

    def as_stored(self) -> dict[str, Any]:
        return self.done

    def baseline(self, hours: float | None, now: float) -> bool:
        """On first use, mark the current state as 'done'.

        Otherwise everything would be due right away on a printer that has
        been in use for a while. New items (added in an update) start now too.
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

    def status(self, hours: float | None, intervals: dict[str, int],
               months: dict[str, int] | None = None, now: float | None = None,
               has_filter: bool = False) -> list[dict[str, Any]]:
        """Status of every enabled maintenance item at ``hours`` print hours and time ``now``.

        An item counts in print hours, in months since it was last done, or both;
        the more advanced of the two decides progress, "due" and which remaining
        value is shown (``by``: "hours" or "months"). The air filter only exists
        with the top cover (``has_filter``).
        """
        months = months or {}
        items = []
        for key, default in MAINTENANCE_ITEMS.items():
            if key == "filter" and not has_filter:
                continue
            interval = int(intervals.get(key, default) or 0)
            interval_m = int(months.get(key, MAINTENANCE_MONTHS.get(key, 0)) or 0)
            if interval <= 0 and interval_m <= 0:
                continue
            done = self.done.get(key) or {}
            item: dict[str, Any] = {"key": key, "done_at": done.get("at")}
            progress: dict[str, float] = {}
            due = False
            if interval > 0:
                used = None if hours is None else max(0.0, hours - float(done.get("hours", hours)))
                item.update(
                    interval_h=interval,
                    used_h=None if used is None else round(used, 1),
                    remaining_h=None if used is None else round(interval - used, 1),
                )
                if used is not None:
                    progress["hours"] = used / interval
                    due = due or used >= interval
            if interval_m > 0 and done.get("at") is not None and now is not None:
                period = interval_m * DAYS_PER_MONTH * 86400
                age = max(0.0, now - float(done["at"]))
                item.update(interval_m=interval_m, due_at=float(done["at"]) + period,
                            remaining_d=round((period - age) / 86400, 1))
                progress["months"] = age / period
                due = due or age >= period
            elif interval_m > 0:
                item["interval_m"] = interval_m
            by = max(progress, key=progress.get) if progress else None
            item["by"] = by
            item["progress"] = round(min(progress[by], 9.99) * 100) if by else None
            item["due"] = due
            items.append(item)
        return items
