"""Back up timelapses to the Home Assistant media folder.

Target: ``<media>/snapmaker_u1/`` ("Local media" in the media browser).
Every video that is not there yet is copied, including its preview image.

Cleaning up on the printer: Moonraker exposes the ``camera`` folder read-only
(snapmakercloud.py: register_data_folder('camera') without full_access).
Deleting only works through Snapmaker's internal camera service
(``camera.delete_timelapse_instance`` over WebSocket, repeater.py), whose
parameters are undocumented. Therefore:
  - only videos proven to be in the media folder are deleted,
  - everything is backed up first (including videos that are kept),
  - the parameter form is probed once and remembered; if none works,
    nothing is deleted and the status says so.
"""

from __future__ import annotations

import logging
import posixpath
import shutil
import time
from pathlib import Path
from typing import Any

from .api import MoonrakerClient, MoonrakerError

_LOGGER = logging.getLogger(__name__)

ARCHIVE_DIR = "snapmaker_u1"
MEDIA_PREFIX = f"media-source://media_source/local/{ARCHIVE_DIR}"
ARCHIVE_LIST = 30


def media_root(media_dirs: dict[str, str], config_path: str) -> Path:
    """Folder behind "Local media" (media_dirs['local']), else /config/media."""
    local = media_dirs.get("local") or next(iter(media_dirs.values()), None)
    return Path(local) if local else Path(config_path) / "media"


def list_archive(folder: Path) -> list[dict[str, Any]]:
    """Backed-up videos, newest first (blocking)."""
    if not folder.is_dir():
        return []
    out = []
    for item in folder.iterdir():
        if item.suffix.lower() not in (".mp4", ".webm", ".mkv") or not item.is_file():
            continue
        st = item.stat()
        cover = item.with_suffix(".jpg")
        out.append({
            "file": item.name,
            "size": st.st_size,
            "modified": st.st_mtime,
            "media_id": f"{MEDIA_PREFIX}/{item.name}",
            "poster": cover.name if cover.exists() else None,
        })
    out.sort(key=lambda v: v["modified"], reverse=True)
    return out


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


class TimelapseArchive:
    """Copies timelapses into the media folder and optionally prunes the printer."""
    def __init__(self, client: MoonrakerClient, folder: Path, stored: dict[str, Any] | None) -> None:
        self.client = client
        self.folder = folder
        stored = stored or {}
        # Working parameter form for delete_timelapse_instance
        self.delete_style: str | None = stored.get("delete_style")
        self.cleanup: str | None = stored.get("cleanup")  # Status for display
        self.last_backup: float | None = stored.get("last_backup")
        self.errors: list[str] = []
        # Retry after every restart (e.g. after a firmware update)
        self._unsupported = False

    def as_stored(self) -> dict[str, Any]:
        return {"delete_style": self.delete_style, "cleanup": self.cleanup, "last_backup": self.last_backup}

    async def backup(
        self, hass: Any, videos: list[dict[str, Any]], poster_dir: Path, poster_cache: Path | None = None
    ) -> list[str]:
        """Back up missing videos. Returns the newly saved file names.

        ``poster_cache``: extra copy of the preview image that Home Assistant
        serves statically (the card then needs no signed media URL).
        """
        have = {v["file"]: v["size"] for v in await hass.async_add_executor_job(list_archive, self.folder)}
        saved: list[str] = []
        self.errors = []
        for video in videos:
            name = posixpath.basename(video["path"])
            size = video.get("size")
            if name in have and (size is None or have[name] == size):
                continue
            target = self.folder / name
            try:
                await self.client.download_to(video["root"], video["path"], target, hass)
            except (MoonrakerError, OSError) as err:
                self.errors.append(f"{name}: {err}")
                _LOGGER.warning("Timelapse %s not saved: %s", name, err)
                continue
            poster = video.get("poster_url")
            if poster:
                src = poster_dir / Path(poster).name
                if await hass.async_add_executor_job(src.exists):
                    await hass.async_add_executor_job(_copy, src, target.with_suffix(".jpg"))
                    if poster_cache is not None:
                        await hass.async_add_executor_job(_copy, src, poster_cache / f"{target.stem}.jpg")
            saved.append(name)
            _LOGGER.info("Timelapse saved: %s", target)
        if saved:
            self.last_backup = time.time()
        return saved

    async def cleanup_printer(self, hass: Any, videos: list[dict[str, Any]], keep: int) -> list[str]:
        """Delete the oldest videos on the printer, keep the newest ``keep``.

        Only videos that are fully backed up.
        """
        if keep <= 0 or self._unsupported:
            return []
        archived = {v["file"]: v["size"] for v in await hass.async_add_executor_job(list_archive, self.folder)}
        ordered = sorted(videos, key=lambda v: v.get("modified") or 0, reverse=True)
        victims = [
            v for v in ordered[keep:]
            if posixpath.basename(v["path"]) in archived
            and (v.get("size") is None or archived[posixpath.basename(v["path"])] == v["size"])
        ]
        deleted: list[str] = []
        for video in victims:
            if await self._delete(video):
                deleted.append(video["path"])
            elif self._unsupported:
                break
        return deleted

    async def _delete(self, video: dict[str, Any]) -> bool:
        """Delete one video on the printer, probing the parameter form on first use."""
        name = posixpath.basename(video["path"])
        stem = posixpath.splitext(name)[0]
        styles = {
            "name": {"name": stem},
            "file_name": {"file_name": name},
            "filename": {"filename": name},
            "path": {"path": video["path"]},
            "names": {"names": [stem]},
        }
        order = [self.delete_style] if self.delete_style else list(styles)
        for style in order:
            params = {"req_id": int(time.time() * 1000) % 2_000_000_000, **styles[style]}
            try:
                result = await self.client.rpc("camera.delete_timelapse_instance", params, response_timeout=15)
            except MoonrakerError as err:
                _LOGGER.debug("delete_timelapse_instance %s: %s", style, err)
                if "not found" in str(err).lower() and "method" in str(err).lower():
                    break  # Endpoint does not exist (no Snapmaker service)
                continue
            if isinstance(result, dict) and result.get("state") == "failed":
                _LOGGER.debug("delete_timelapse_instance %s: %s", style, result)
                continue
            if not await self._exists(video):
                if self.delete_style != style:
                    _LOGGER.info("Deleting timelapses: parameter form '%s' works", style)
                self.delete_style = style
                self.cleanup = "ok"
                return True
        if self.delete_style is None:
            self._unsupported = True
            self.cleanup = "not_supported"
            _LOGGER.warning(
                "Timelapses on the printer cannot be deleted (camera service refuses). "
                "Backups continue, no cleanup."
            )
        return False

    async def _exists(self, video: dict[str, Any]) -> bool:
        """Whether the video is still listed on the printer (True when unsure)."""
        try:
            files = await self.client.list_files(video["root"])
        except MoonrakerError:
            return True  # when in doubt: do not count as deleted
        return any(f.get("path") == video["path"] for f in files)
