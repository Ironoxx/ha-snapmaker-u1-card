"""Which camera does the printer have, and how do we get an image?

Detection order (``detect``):

1. ``/server/webcams/list`` (plus the usual default paths): a stream URL that
   answers with ``multipart/x-mixed-replace`` and a first JPEG -> ``live``
   (modified firmware, e.g. paxx12 Extended).
2. A snapshot URL that returns a JPEG -> ``still``.
3. Stock firmware: no stream, only ``camera/monitor.jpg``, which the camera
   service only refreshes after ``camera.start_monitor``. The image is fetched
   twice around a wake call; only if it changed does it count as working ->
   ``wake`` (an old file would otherwise look fine).
4. Otherwise ``none``.

Detection runs when the printer comes online, when images keep failing, and
every few minutes while nothing was found. A failing live stream falls back
to still images and the stream is tried again after STREAM_RETRY_S.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

from .api import MoonrakerClient, MoonrakerError

_LOGGER = logging.getLogger(__name__)

MODES = ("live", "still", "wake", "none")
STREAM_RETRY_S = 300  # live stream failed: still images, try the stream again after this
NONE_RETRY_S = 300  # nothing found: look again after this
WAKE_GAP_S = 10  # at most one camera.start_monitor per this many seconds
WAKE_SETTLE_S = 3  # stock: time for the camera service to write a new monitor.jpg
CACHE_S = 1.0  # image cache for several viewers / the HA MJPEG loop
FAIL_LIMIT = 3  # images in a row without result -> detect again
MONITOR = "monitor.jpg"
# Moonraker integration's defaults (crowsnest / ustreamer on the printer)
DEFAULT_STREAM = "/webcam/?action=stream"
DEFAULT_SNAPSHOT = "/webcam/?action=snapshot"


def _digest(blob: bytes | None) -> str | None:
    return hashlib.sha1(blob).hexdigest() if blob else None


class Webcam:
    """Camera access for one printer: detection, images and wake-up."""

    def __init__(self, client: MoonrakerClient) -> None:
        self.client = client
        self.mode = "unknown"
        self.stream_url: str | None = None
        self.snapshot_url: str | None = None
        self.checked_at: float | None = None  # time.time() of the last detection
        self.next_check = 0.0  # monotonic: earliest next detection
        self._stream_retry_at = 0.0
        self._last_wake = 0.0
        self._image: bytes | None = None
        self._image_at = 0.0
        self._fails = 0
        self._lock = asyncio.Lock()
        self._detecting = False

    # ── Detection ──────────────────────────────────────────────────────────
    def reset(self) -> None:
        """Printer went offline: detect again when it is back."""
        self.mode = "unknown"
        self.next_check = 0.0
        self._image = None

    def due(self) -> bool:
        return not self._detecting and (self.mode == "unknown" or time.monotonic() >= self.next_check)

    async def detect(self) -> str:
        """Find out how to get an image; sets and returns ``mode``."""
        if self._detecting:
            return self.mode
        self._detecting = True
        try:
            mode, stream, snap = await self._probe()
        except MoonrakerError as err:
            _LOGGER.debug("Camera detection failed: %s", err)
            mode, stream, snap = "unknown", None, None
        finally:
            self._detecting = False
        if mode != self.mode:
            _LOGGER.info("Camera: %s (stream %s, snapshot %s)", mode, stream, snap)
        self.mode, self.stream_url, self.snapshot_url = mode, stream, snap
        self.checked_at = time.time()
        self._fails = 0
        self._image = None
        now = time.monotonic()
        # Live and still keep their mode until images fail; wake/none are re-checked
        # now and then (firmware changes, camera service restarted).
        self.next_check = now + (NONE_RETRY_S if mode in ("none", "unknown", "wake") else 24 * 3600)
        return mode

    async def _probe(self) -> tuple[str, str | None, str | None]:
        cams = await self.client.webcams()
        candidates: list[tuple[str | None, str | None]] = [
            (self.client.resolve_url(c.get("stream_url")), self.client.resolve_url(c.get("snapshot_url")))
            for c in cams
        ]
        default = (self.client.resolve_url(DEFAULT_STREAM), self.client.resolve_url(DEFAULT_SNAPSHOT))
        if default not in candidates:
            candidates.append(default)
        still: tuple[str | None, str | None] | None = None
        stream_ok = time.monotonic() >= self._stream_retry_at
        for stream, snap in candidates:
            if stream and stream_ok and await self.client.first_mjpeg_frame(stream):
                return "live", stream, snap
            if still is None and snap and await self.client.fetch_image(snap):
                still = (stream, snap)
        if still:
            return "still", still[0], still[1]
        if await self._monitor_changes():
            return "wake", None, None
        return "none", None, None

    async def _monitor_changes(self) -> bool:
        """Stock firmware: does monitor.jpg change after camera.start_monitor?"""
        first = await self._monitor()
        await self.wake(force=True)
        await asyncio.sleep(WAKE_SETTLE_S)
        second = await self._monitor()
        if first is None and second is None:
            return False
        if first is None or second is None:
            return second is not None  # the wake call created the image
        if _digest(first) != _digest(second):
            return True
        # Same bytes: one more try, the service may have needed longer
        await self.wake(force=True)
        await asyncio.sleep(WAKE_SETTLE_S)
        third = await self._monitor()
        return third is not None and _digest(third) != _digest(second)

    async def _monitor(self) -> bytes | None:
        try:
            blob = await self.client.download(MONITOR, root="camera")
        except MoonrakerError:
            return None
        return blob if blob[:2] == b"\xff\xd8" else None

    # ── Images ─────────────────────────────────────────────────────────────
    async def wake(self, force: bool = False) -> None:
        """camera.start_monitor, at most every WAKE_GAP_S seconds."""
        now = time.monotonic()
        if not force and now - self._last_wake < WAKE_GAP_S:
            return
        self._last_wake = now
        try:
            await self.client.camera_wake()
        except MoonrakerError as err:
            _LOGGER.debug("camera.start_monitor failed: %s", err)

    async def image(self) -> bytes | None:
        """Current image for the mode; cached for CACHE_S."""
        async with self._lock:
            now = time.monotonic()
            if self._image is not None and now - self._image_at < CACHE_S:
                return self._image
            blob = await self._fetch()
            if blob:
                self._image, self._image_at, self._fails = blob, now, 0
            else:
                self._fails += 1
                if self._fails >= FAIL_LIMIT:
                    self.next_check = 0.0  # detect again on the next poll
            return blob or self._image

    async def _fetch(self) -> bytes | None:
        if self.mode == "live":
            if self.snapshot_url:
                blob = await self.client.fetch_image(self.snapshot_url)
                if blob:
                    return blob
            return await self.client.first_mjpeg_frame(self.stream_url) if self.stream_url else None
        if self.mode == "still" and self.snapshot_url:
            return await self.client.fetch_image(self.snapshot_url)
        if self.mode == "wake":
            await self.wake()
            return await self._monitor()
        return None

    def stream_failed(self) -> None:
        """The live stream broke: still images for now, stream again after STREAM_RETRY_S."""
        self._stream_retry_at = time.monotonic() + STREAM_RETRY_S
        if self.mode == "live":
            self.mode = "still" if self.snapshot_url else "unknown"
            self.next_check = self._stream_retry_at if self.mode == "still" else 0.0
            _LOGGER.info("Camera stream failed, using still images for %s s", STREAM_RETRY_S)

    def as_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "stream_url": self.stream_url, "snapshot_url": self.snapshot_url,
                "checked_at": self.checked_at}
