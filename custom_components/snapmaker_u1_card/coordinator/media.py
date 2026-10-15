"""Timelapses (list, archive), file list, file management and thumbnails."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import posixpath
from pathlib import Path
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..api import (
    MoonrakerError,
)
from ..archive import list_archive
from ..const import (
    CONF_ARCHIVE_KEEP,
    DEFAULT_ARCHIVE_KEEP,
    DOMAIN,
    THUMB_URL,
)
from ..i18n import tr
from ..jobs import (
    is_pause_copy,
)
from ..parsing import (
    ACTIVE_PRINT_STATES,
    PRINTABLE_SUFFIXES,
    TIMELAPSE_SKIP_ROOTS,
    describe_file,
    pick_thumbnail,
    pick_timelapses,
    thumbnail_source,
)

_LOGGER = logging.getLogger(__name__)
from .helpers import (
    _prune_dir,
    _write,
)

_LOGGER = logging.getLogger(__name__)


class MediaMixin:
    """Timelapses (list, archive), file list, file management and thumbnails."""

    # ── Timelapse backup ───────────────────────────────────────────────────
    def _archive_data(self) -> dict[str, Any] | None:
        """Archive status for the card (None if the backup is disabled)."""
        if self.archive is None:
            return None
        entry = self.config_entry.entry_id
        videos = [
            {**v, "poster_url": f"{THUMB_URL}/{entry}/archive/{Path(v['file']).stem}.jpg"} if v.get("poster") else v
            for v in self._archive_list[:30]
        ]
        return {
            "videos": videos,
            "count": len(self._archive_list),
            "folder": str(self.archive.folder),
            "last_backup": self.archive.last_backup,
            "cleanup": self.archive.cleanup,
            "keep": int(self.options.get(CONF_ARCHIVE_KEEP, DEFAULT_ARCHIVE_KEEP)),
            "busy": self._archive_running,
            "errors": self.archive.errors,
        }

    def _start_archive(self, print_state: str | None, force: bool = False) -> None:
        """Start a timelapse backup in the background when one is due."""
        if self.archive is None or (self._archive_task and not self._archive_task.done()):
            return
        # Not during a print: the printer is recording, and it needs the WiFi
        # for the camera.
        if print_state in ACTIVE_PRINT_STATES and not force:
            return
        videos = list(self._timelapses)
        if not videos:
            return
        self._archive_task = self.hass.async_create_background_task(
            self._run_archive(videos), f"{DOMAIN} timelapse archive"
        )

    async def async_backup_timelapses(self) -> None:
        """Service: back up timelapses now."""
        if self.archive is None:
            raise HomeAssistantError(tr(
                self.hass, "Zeitraffer-Sicherung ist in den Optionen nicht eingeschaltet.",
                "Timelapse backup is not enabled in the options."))
        if self._archive_task and not self._archive_task.done():
            await self._archive_task
            return
        self._start_archive(self.data.print_state if self.data else None)
        if self._archive_task:
            await self._archive_task

    async def _run_archive(self, videos: list[dict[str, Any]]) -> None:
        """Back up missing videos, then prune the printer if configured."""
        assert self.archive is not None
        self._archive_running = True
        if self.data is not None:
            self.data.archive = self._archive_data()
        self.async_update_listeners()
        try:
            await self.archive.backup(self.hass, videos, self._own_dir / "tl", self._own_dir / "archive")
            keep = int(self.options.get(CONF_ARCHIVE_KEEP, DEFAULT_ARCHIVE_KEEP))
            if keep > 0 and not (self.data and self.data.print_state in ACTIVE_PRINT_STATES):
                deleted = await self.archive.cleanup_printer(self.hass, videos, keep)
                if deleted:
                    _LOGGER.info("Deleted on the printer (backed up): %s", ", ".join(deleted))
                    self._force_timelapses = True
            self._archive_list = await self.hass.async_add_executor_job(list_archive, self.archive.folder)
            self._save()
        finally:
            self._archive_running = False
            if self.data is not None:
                self.data.archive = self._archive_data()
            self.async_update_listeners()


    # ── Timelapses ──────────────────────────────────────────────────────────
    async def _load_timelapses(self) -> list[dict[str, Any]]:
        """List timelapse videos from all relevant Moonraker roots."""
        roots = [r for r in await self.client.list_roots() if r not in TIMELAPSE_SKIP_ROOTS]
        # "camera" (stock firmware) and "timelapse" (Fluidd) first.
        roots.sort(key=lambda r: (r not in ("camera", "timelapse"), r))
        found: list[dict[str, Any]] = []
        for root in roots:
            try:
                found += pick_timelapses(root, await self.client.list_files(root))
            except MoonrakerError as err:
                _LOGGER.debug("Folder %s not readable: %s", root, err)
        found.sort(key=lambda v: v.get("modified") or 0, reverse=True)
        found = found[:20]
        await self._cache_timelapse_images(found)
        return found

    async def _cache_timelapse_images(self, videos: list[dict[str, Any]]) -> None:
        """Store timelapse preview images locally.

        Home Assistant then serves them as static files, immediately and also
        with the printer switched off. Through the proxy every request would
        hang while the printer is off and block one of only 6 browser
        connections to Home Assistant (HTTP/1.1, also via Nabu Casa) - enough
        of those and the frontend cannot load anything anymore.
        """
        folder = self._own_dir / "tl"
        sem = asyncio.Semaphore(3)
        keep: set[str] = set()

        async def one(video: dict[str, Any], key: str) -> None:
            source = video.get(key)
            if not source:
                return
            digest = hashlib.sha1(
                f"{video['root']}|{source}|{video.get('modified')}".encode()
            ).hexdigest()[:20]
            name = f"{digest}{Path(source).suffix.lower() or '.jpg'}"
            keep.add(name)
            target = folder / name
            if not await self.hass.async_add_executor_job(target.exists):
                async with sem:
                    try:
                        blob = await self.client.download(source, root=video["root"])
                    except MoonrakerError as err:
                        _LOGGER.debug("Timelapse image %s missing: %s", source, err)
                        return
                await self.hass.async_add_executor_job(_write, target, blob)
            video[f"{key}_url"] = f"{THUMB_URL}/{self.config_entry.entry_id}/tl/{name}"

        await asyncio.gather(*(one(v, k) for v in videos for k in ("thumb", "poster")))
        await self.hass.async_add_executor_job(_prune_dir, folder, keep)

    async def _load_files(self) -> list[dict[str, Any]]:
        """Newest printable files with metadata, plus the full name list."""
        entries = [
            e for e in await self.client.list_files()
            if str(e.get("path", "")).lower().endswith(PRINTABLE_SUFFIXES)
            and not posixpath.basename(str(e.get("path", ""))).startswith(".")
            and not is_pause_copy(e.get("path"))
        ]
        entries.sort(key=lambda e: e.get("modified") or 0, reverse=True)
        # All names (without metadata) for search and folders in the card
        self._all_files = [
            {"path": e["path"], "modified": e.get("modified"), "size": e.get("size")} for e in entries
        ]
        entries = entries[: self.files_limit]
        # Older files opened via search keep their metadata and thumbnail
        by_path = {e["path"]: e for e in self._all_files}
        extra = [by_path[p] for p in self._pinned if p in by_path and p not in {e["path"] for e in entries}]
        self._pinned = {e["path"] for e in extra}

        sem = asyncio.Semaphore(3)
        files = await asyncio.gather(*(self._file_info(e, sem) for e in entries))
        pinned = await asyncio.gather(*(self._file_info(e, sem) for e in extra))

        keep = {(e["path"], float(e.get("modified") or 0)) for e in [*entries, *extra]}
        for stale in [k for k in self._file_cache if k not in keep]:
            del self._file_cache[stale]
        await self.hass.async_add_executor_job(
            self._prune_thumbs, {Path(f["thumb"]).name for f in [*files, *pinned] if f["thumb"]}
        )
        return list(files)

    async def _file_info(self, entry: dict[str, Any], sem: asyncio.Semaphore) -> dict[str, Any]:
        """Metadata and thumbnail for one file, cached per file version."""
        key = (entry["path"], float(entry.get("modified") or 0))
        if key in self._file_cache:
            return self._file_cache[key]
        async with sem:
            try:
                meta = await self.client.file_metadata(entry["path"])
            except MoonrakerError as err:
                _LOGGER.debug("No metadata for %s: %s", entry["path"], err)
                meta = {}
            info = describe_file(entry["path"], entry, meta)
            info["thumb"] = await self._cache_thumbnail(entry["path"], key, meta)
        self._file_cache[key] = info
        return info

    # ── File management ────────────────────────────────────────────────────
    async def async_file_details(self, path: str) -> dict[str, Any]:
        """Metadata of a (possibly older) file, e.g. from the card's search."""
        entry = next((e for e in self._all_files if e["path"] == path), None)
        if entry is None:
            raise HomeAssistantError(tr(self.hass, f"Datei {path} gibt es auf dem Drucker nicht.", f"File {path} does not exist on the printer."))
        info = await self._file_info(entry, asyncio.Semaphore(1))
        self._pinned.add(path)
        return info

    def _check_file_change(self, path: str) -> None:
        """Refuse to change a file that is printing or queued."""
        active = self._print_state.get("active") or {}
        if self.current_print_state() in ACTIVE_PRINT_STATES and path in (active.get("file"), active.get("source")):
            raise HomeAssistantError(tr(self.hass, "Die Datei wird gerade gedruckt.", "The file is being printed."))
        if any(j.get("file") == path for j in self.queue.jobs):
            raise HomeAssistantError(tr(self.hass, "Die Datei steht in der Warteschlange.", "The file is in the queue."))

    async def async_delete_file(self, path: str) -> None:
        """Service: delete a print file on the printer."""
        self._check_file_change(path)
        try:
            await self.client.delete_file(path)
        except MoonrakerError as err:
            raise HomeAssistantError(str(err)) from err
        self._pinned.discard(path)
        self._force_files = True
        await self.async_request_refresh()

    async def async_move_file(self, source: str, dest: str) -> None:
        """Service: rename or move a print file on the printer."""
        self._check_file_change(source)
        dest = dest.strip().lstrip("/")
        if not dest or ".." in dest.split("/"):
            raise HomeAssistantError(tr(self.hass, "Ungültiges Ziel.", "Invalid target."))
        if not dest.lower().endswith(PRINTABLE_SUFFIXES):
            dest += posixpath.splitext(source)[1]
        try:
            await self.client.move_file(source, dest)
        except MoonrakerError as err:
            raise HomeAssistantError(str(err)) from err
        self._force_files = True
        await self.async_request_refresh()

    @property
    def _own_dir(self) -> Path:
        # One subfolder per printer: cleanup never hits other printers' images.
        return self.thumb_dir / self.config_entry.entry_id

    async def _cache_thumbnail(
        self, path: str, key: tuple[str, float], meta: dict[str, Any]
    ) -> str | None:
        """Store the file's thumbnail locally and return its static URL."""
        relative = pick_thumbnail(meta)
        if not relative:
            return None
        # Name from a hash of path and modification time: not guessable, and a
        # new file version automatically gets a new URL (no browser cache).
        digest = hashlib.sha1(f"{key[0]}|{key[1]}".encode()).hexdigest()[:20]
        name = f"{digest}{Path(relative).suffix or '.png'}"
        target = self._own_dir / name
        if not await self.hass.async_add_executor_job(target.exists):
            try:
                blob = await self.client.download(thumbnail_source(path, relative))
            except MoonrakerError as err:
                _LOGGER.debug("Thumbnail for %s missing: %s", path, err)
                return None
            await self.hass.async_add_executor_job(_write, target, blob)
        return f"{THUMB_URL}/{self.config_entry.entry_id}/{name}"

    def _prune_thumbs(self, keep: set[str]) -> None:
        """Delete cached thumbnails that no listed file uses anymore."""
        folder = self._own_dir
        if not folder.is_dir():
            return
        for item in folder.iterdir():
            if item.is_file() and item.name not in keep:
                item.unlink(missing_ok=True)
