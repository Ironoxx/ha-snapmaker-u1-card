"""Job queue and pause at layer.

Queue: Moonraker's ``[job_queue]`` is not loaded on the U1 and knows nothing
about filament mapping anyway. The integration therefore keeps its own list,
with mapping and options per job. A job is never started automatically:
after a print somebody has to clear the bed first.

Pause at layer: neither Klipper nor the U1 firmware has a command for it.
Like the slicer feature, ``PAUSE`` is written straight into a copy of the
file, before the layer change of the requested layer. The firmware handles
``PAUSE`` in files explicitly (virtual_sdcard.process_gcode_line). The copy
is named ``<name>.u1pause-<layers>.gcode``, hidden in the file list and
deleted after the print.
"""

from __future__ import annotations

import posixpath
import re
import time
import uuid
from pathlib import Path
from typing import Any

PAUSE_TAG = ".u1pause-"
_PAUSE_RE = re.compile(r"^(?P<stem>.+)\.u1pause-[\d-]+(?P<ext>\.gcode)$", re.IGNORECASE)

# Layer change markers, preferred first. Number = layer number (1-based)
# or None = count sequentially.
_MARKERS: tuple[tuple[re.Pattern[str], int], ...] = (
    # OrcaSlicer/Snapmaker Orca, PrusaSlicer, BambuStudio
    (re.compile(r"^;\s*LAYER_CHANGE\b"), 0),
    # BambuStudio style
    (re.compile(r"^;\s*CHANGE_LAYER\b"), 0),
    # Cura: ;LAYER:0 is the first layer
    (re.compile(r"^;LAYER:(-?\d+)"), 1),
    # Klipper layer info without comments
    (re.compile(r"^SET_PRINT_STATS_INFO\b.*\bCURRENT_LAYER=(\d+)", re.IGNORECASE), 0),
)


def pause_file_name(path: str, layers: list[int]) -> str:
    """Name of the pause copy for ``path`` and the given layers."""
    stem, _ext = posixpath.splitext(path)
    return f"{stem}{PAUSE_TAG}{'-'.join(str(n) for n in sorted(set(layers)))}.gcode"


def is_pause_copy(path: str | None) -> bool:
    """Whether ``path`` is a pause copy created by the integration."""
    return bool(path) and bool(_PAUSE_RE.match(posixpath.basename(str(path))))


def original_file(path: str | None) -> str | None:
    """Path of the original file for a pause copy (otherwise unchanged)."""
    if not path:
        return path
    head, base = posixpath.split(str(path))
    m = _PAUSE_RE.match(base)
    return posixpath.join(head, f"{m['stem']}{m['ext']}") if m else path


def add_layer_pauses(src: Path, dst: Path, layers: list[int]) -> dict[str, Any]:
    """Copy the file and insert ``PAUSE`` before the requested layers.

    Blocking (run in the executor). Returns which layers were set, the total
    number of layers and the marker used. Without detectable layer changes
    -> ValueError.
    """
    wanted = sorted({int(n) for n in layers if int(n) >= 1})
    if not wanted:
        raise ValueError("No valid layer given.")
    with src.open("r", encoding="utf-8", errors="surrogateescape") as fh:
        marker = None
        for line in fh:
            for pattern, kind in _MARKERS:
                if pattern.match(line):
                    marker = (pattern, kind)
                    break
            if marker:
                break
    if marker is None:
        raise ValueError("No layer changes found in the file (slicer comments missing).")
    pattern, kind = marker
    done: list[int] = []
    layer = 0
    with src.open("r", encoding="utf-8", errors="surrogateescape", newline="") as fh, \
            dst.open("w", encoding="utf-8", errors="surrogateescape", newline="") as out:
        out.write(f"; snapmaker_u1_card: PAUSE vor Schicht {', '.join(map(str, wanted))}\n")
        for line in fh:
            m = pattern.match(line)
            if m:
                if kind == 1:
                    layer = int(m.group(1)) + 1
                elif m.groups():
                    layer = int(m.group(1))
                else:
                    layer += 1
                if layer in wanted and layer not in done:
                    out.write(f"; snapmaker_u1_card: Pause vor Schicht {layer}\nPAUSE\n")
                    done.append(layer)
            out.write(line)
    return {"layers": done, "total": layer, "missing": [n for n in wanted if n not in done]}


class JobQueue:
    """Planned print jobs; persisted together with the coordinator."""

    def __init__(self, stored: list[dict[str, Any]] | None) -> None:
        self.jobs: list[dict[str, Any]] = [
            dict(j) for j in stored or [] if isinstance(j, dict) and j.get("file") and j.get("id")
        ]

    def as_stored(self) -> list[dict[str, Any]]:
        return self.jobs

    def add(self, job: dict[str, Any]) -> dict[str, Any]:
        """Append a job (file, mapping, options) and return it."""
        entry = {
            "id": uuid.uuid4().hex[:8],
            "added": time.time(),
            **{k: v for k, v in job.items() if v is not None},
        }
        if isinstance(entry.get("mapping"), dict):
            entry["mapping"] = {str(k): int(v) for k, v in entry["mapping"].items()}
        self.jobs.append(entry)
        return entry

    def get(self, job_id: str | None) -> dict[str, Any] | None:
        if job_id is None:
            return self.jobs[0] if self.jobs else None
        return next((j for j in self.jobs if j["id"] == job_id), None)

    def remove(self, job_id: str) -> bool:
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j["id"] != job_id]
        return len(self.jobs) != before

    def move(self, job_id: str, position: int) -> bool:
        """Move a job to ``position`` (clamped to the queue length)."""
        job = self.get(job_id)
        if job is None:
            return False
        self.jobs.remove(job)
        position = max(0, min(int(position), len(self.jobs)))
        self.jobs.insert(position, job)
        return True

    def clear(self) -> None:
        self.jobs = []
