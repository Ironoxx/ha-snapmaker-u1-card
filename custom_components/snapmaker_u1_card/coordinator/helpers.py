"""Constants and pure helper functions used by the coordinator mixins."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


STORE_VERSION = 1
POLL_S = 3  # poll interval while shutting down
EARLY_PHOTO_DELAY_S = 2  # result photo: file position runs ahead of the motion
FILES_PRINTING_S = 600  # file list interval during a print
BOOT_POLL_S = 5  # poll interval while booting
AUTO_OFF_RESULTS = ("complete", "cancelled")

RESULT_TEXT = {
    "complete": "Druck fertig",
    "cancelled": "Druck abgebrochen",
    "error": "Druckfehler",
    "paused": "Druck pausiert",
    "queue": "Nächster Auftrag wartet",
    "alert": "Meldung vom Drucker",
    "first_layer": "Erste Schicht fertig",
    "almost_done": "Gleich fertig",
    "spool_low": "Filament reicht nicht",
    "spool_runout": "Spule läuft gleich leer",
    "bed_cool": "Teil entnehmbar",
    "cancel_confirm": "Druck abbrechen?",
}
RESULT_TEXT_EN = {
    "complete": "Print finished",
    "cancelled": "Print cancelled",
    "error": "Print error",
    "paused": "Print paused",
    "queue": "Next job waiting",
    "alert": "Printer message",
    "first_layer": "First layer done",
    "almost_done": "Almost done",
    "spool_low": "Not enough filament",
    "spool_runout": "Spool about to run out",
    "bed_cool": "Part ready to remove",
    "cancel_confirm": "Cancel print?",
}



def _write(target: Path, blob: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(blob)
    tmp.replace(target)



def head_index(name: Any) -> int | None:
    """'extruder' -> 0, 'extruder2' -> 2; otherwise None."""
    if not isinstance(name, str) or not name.startswith("extruder"):
        return None
    rest = name[len("extruder"):]
    if rest == "":
        return 0
    return int(rest) if rest.isdigit() else None


def _position(vsd: dict[str, Any], meta: dict[str, Any] | None) -> int | None:
    """File position; if it does not match the file (different version), use the progress."""
    pos, progress = vsd.get("file_position"), vsd.get("progress")
    size = (meta or {}).get("size")
    if isinstance(pos, (int, float)) and (not size or 0 <= pos <= size):
        return int(pos)
    if isinstance(progress, (int, float)) and size:
        return int(progress * size)
    return None


_RELEASE = re.compile(r"Release firmware version v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)


def version_tuple(text: str | None) -> tuple[int, ...]:
    """Numeric part of a version string for comparisons ("v1.6.0-12" -> (1, 6, 0))."""
    m = re.search(r"(\d+(?:\.\d+)+)", text or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def latest_release(commits: Any) -> dict[str, Any] | None:
    """Newest "Release firmware version x.y.z" commit from a GitHub commit list."""
    best = None
    for c in commits if isinstance(commits, list) else []:
        msg = ((c.get("commit") or {}).get("message") or "").splitlines()[0] if isinstance(c, dict) else ""
        m = _RELEASE.search(msg)
        if not m:
            continue
        item = {"version": m.group(1), "url": c.get("html_url"),
                "date": ((c.get("commit") or {}).get("committer") or {}).get("date")}
        if best is None or version_tuple(item["version"]) > version_tuple(best["version"]):
            best = item
    return best


def _takeover(slots: list[dict[str, Any]], head: int, ptc: dict[str, Any]) -> int | None:
    """Head the firmware refills from automatically when a spool runs empty (or None)."""
    if not ptc.get("auto_replenish_filament", True):
        return None
    me = next((s for s in slots if s.get("index") == head), None)
    if not me or not me.get("type"):
        return None
    ignore_color = bool(ptc.get("replenish_ignore_color"))
    for slot in slots:
        if slot.get("index") == head or not slot.get("loaded"):
            continue
        if slot.get("type") != me.get("type"):
            continue
        if not ignore_color and (slot.get("color") or "").upper() != (me.get("color") or "").upper():
            continue
        return slot["index"]
    return None


def remaining_seconds(duration: Any, progress: Any) -> float | None:
    """Remaining time from elapsed time and file progress (rough, from 5 %)."""
    if not isinstance(duration, (int, float)) or not isinstance(progress, (int, float)):
        return None
    if not 0.05 <= progress < 1 or duration <= 0:
        return None
    return duration * (1 - progress) / progress


def notify_message(info: dict[str, Any], de: bool = True) -> str:
    """Short text for the notification."""
    name = str(info.get("name") or info.get("file") or ("Druck" if de else "Print"))
    if info.get("text"):
        return f"{info['text']}\n{name}"
    if info.get("runout"):
        r = info["runout"]
        if de:
            text = f"Kopf {r['head']}: Spule in etwa {r['minutes']} min leer."
            text += (f" Kopf {r['takeover']} (gleiches Filament) übernimmt automatisch." if r.get("takeover")
                     else " Ohne gleiches Filament auf einem anderen Kopf pausiert der Druck.")
        else:
            text = f"Head {r['head']}: spool empty in about {r['minutes']} min."
            text += (f" Head {r['takeover']} (same filament) takes over automatically." if r.get("takeover")
                     else " Without the same filament on another head the print will pause.")
        return f"{text}\n{name}"
    if info.get("bed") is not None:
        return (f"{name} – Bett {info['bed']} °C, Teil kann runter." if de
                else f"{name} – bed {info['bed']} °C, part can be removed.")
    if info.get("left_min"):
        return f"{name} – {'noch etwa' if de else 'about'} {info['left_min']} min"
    if info.get("short"):
        rows = [
            (f"Kopf {s['head']}: braucht {s['need']} g, Spule hat {s['rest']} g" if de
             else f"Head {s['head']}: needs {s['need']} g, spool has {s['rest']} g")
            for s in info["short"]
        ]
        return f"{name}\n" + "\n".join(rows)
    if info.get("queue"):
        n = info["queue"]
        if de:
            return f"{info.get('name')} – Druckbett räumen und in der Karte starten ({n} in der Warteschlange)."
        return f"{info.get('name')} – clear the bed and start it from the card ({n} queued)."
    parts = [str(info.get("name") or info.get("file") or ("Druck" if de else "Print"))]
    duration = info.get("duration")
    if duration:
        hours, rest = divmod(int(duration), 3600)
        parts.append(f"{hours} h {rest // 60} min" if hours else f"{rest // 60} min")
    if info.get("filament_g") is not None:
        parts.append(f"{info['filament_g']:.0f} g")
    if info.get("energy") is not None:
        parts.append(f"{info['energy']:.2f} kWh")
    if info.get("total_cost") is not None:
        parts.append(f"{info['total_cost']:.2f} €".replace(".", ","))
    if info.get("switches"):
        parts.append(f"{info['switches']} {'Wechsel' if de else 'changes'}")
    return " · ".join(parts)


def _prune_dir(folder: Path, keep: set[str]) -> None:
    """Delete all files in ``folder`` that are not in ``keep`` (blocking)."""
    if not folder.is_dir():
        return
    for item in folder.iterdir():
        if item.is_file() and item.name not in keep:
            item.unlink(missing_ok=True)
