"""Sicherung der Drucker-Konfiguration (Moonraker-Wurzel "config").

Einmal taeglich (und per Dienst ``backup_config``) holt die Integration alle
Dateien aus der Wurzel ``config`` (printer.cfg, moonraker.conf, Makros ...)
und legt sie unter ``/config/snapmaker_u1_backup/<YYYY-MM-DD_HHMMSS>/`` ab.
Ein neuer Stand entsteht nur, wenn sich der Inhalt geaendert hat; die
letzten ``BACKUP_KEEP`` bleiben. Dateien ueber ``BACKUP_MAX_BYTES`` (Logs,
Datenbanken) werden uebersprungen.

Die Sicherungen liegen im HA-Konfigordner und sind damit auch in jedem
HA-Backup enthalten.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

from homeassistant.util import dt as dt_util

from .api import MoonrakerClient, MoonrakerError
from .const import BACKUP_KEEP, BACKUP_MAX_BYTES

_LOGGER = logging.getLogger(__name__)
SKIP_SUFFIXES = (".log", ".bak", ".db", ".tmp", ".part")


def _safe(path: str) -> str | None:
    parts = [p for p in path.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    return "/".join(parts)


def _write_snapshot(folder: Path, name: str, blobs: dict[str, bytes], keep: int) -> Path:
    target = folder / name
    for rel, blob in blobs.items():
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
    snapshots = sorted(p for p in folder.iterdir() if p.is_dir())
    for old in snapshots[:-keep] if keep > 0 else []:
        shutil.rmtree(old, ignore_errors=True)
    return target


def list_snapshots(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted((p.name for p in folder.iterdir() if p.is_dir()), reverse=True)


async def backup_config(
    hass: Any, client: MoonrakerClient, folder: Path, last_digest: str | None, keep: int = BACKUP_KEEP
) -> dict[str, Any]:
    """Eine Sicherung; Rueckgabe: {status: saved|unchanged|empty, digest, snapshot, files, skipped}."""
    entries = await client.list_files("config")
    blobs: dict[str, bytes] = {}
    skipped: list[str] = []
    for entry in sorted(entries, key=lambda e: str(e.get("path"))):
        rel = _safe(str(entry.get("path") or ""))
        if rel is None:
            continue
        size = entry.get("size") or 0
        if size > BACKUP_MAX_BYTES or rel.lower().endswith(SKIP_SUFFIXES):
            skipped.append(rel)
            continue
        try:
            blobs[rel] = await client.download(rel, root="config")
        except MoonrakerError as err:
            _LOGGER.debug("Sicherung: %s nicht geladen: %s", rel, err)
            skipped.append(rel)
    if not blobs:
        return {"status": "empty", "digest": last_digest, "files": 0, "skipped": skipped}
    digest = hashlib.sha256()
    for rel, blob in blobs.items():
        digest.update(rel.encode() + b"\0" + hashlib.sha256(blob).digest())
    hexdigest = digest.hexdigest()
    if hexdigest == last_digest:
        return {"status": "unchanged", "digest": hexdigest, "files": len(blobs), "skipped": skipped}
    name = dt_util.now().strftime("%Y-%m-%d_%H%M%S")
    target = await hass.async_add_executor_job(_write_snapshot, folder, name, blobs, keep)
    _LOGGER.info("Drucker-Konfiguration gesichert: %s (%d Dateien)", target, len(blobs))
    return {"status": "saved", "digest": hexdigest, "snapshot": name, "files": len(blobs), "skipped": skipped}
