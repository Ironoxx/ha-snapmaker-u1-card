"""Which camera does the printer have, and how do we get an image?

Detection order (``detect``):

1. ``/server/webcams/list`` (plus the usual default paths): a stream URL that
   answers with ``multipart/x-mixed-replace`` and a first JPEG -> ``live``
   (modified firmware, e.g. paxx12 Extended). Moonraker may announce a WebRTC
   or player page instead (paxx12 2.x: ``service: webrtc-camerastreamer``,
   ``stream_url: /webcam/webrtc``); its camera service (v4l2-mpp
   ``stream-http.py``) serves MJPEG next to it at ``<base>/stream.mjpg``,
   which is tried instead of the page.
2. A snapshot URL that returns a JPEG -> ``still``.
3. Stock firmware: no stream, only ``camera/monitor.jpg``, which the camera
   service only refreshes after ``camera.start_monitor``. The image is fetched
   twice around a wake call; only if it changed does it count as working ->
   ``wake`` (an old file would otherwise look fine).
4. Otherwise ``none``.

A second camera (paxx12: USB camera at ``/webcam2/``) is a second ``Webcam``
with ``second=True``: it only looks at the other Moonraker webcams and never
falls back to the stock camera.

RTSP (paxx12, off by default): if the camera service answers on
``rtsp://<printer>:8554/stream`` (8555 for the second camera), ``rtsp_url``
is set and the camera entity offers it as stream source, so Home Assistant
can play H.264 itself (go2rtc / WebRTC) instead of MJPEG.

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
FIRST_FRAME_S = 8  # a stream may need a few seconds for its first frame (camera starting, busy WiFi)
STREAM_TRIES = 2
NONE_RETRY_S = 300  # nothing found: look again after this
WAKE_GAP_S = 10  # at most one camera.start_monitor per this many seconds
WAKE_SETTLE_S = 3  # stock: time for the camera service to write a new monitor.jpg
CACHE_S = 1.0  # image cache for several viewers / the HA MJPEG loop
FAIL_LIMIT = 3  # images in a row without result -> detect again
MONITOR = "monitor.jpg"
# Moonraker integration's defaults (crowsnest / ustreamer on the printer) and
# paxx12 2.x (v4l2-mpp stream-http.py: /stream.mjpg, /snapshot.jpg)
DEFAULTS = (
    ("/webcam/?action=stream", "/webcam/?action=snapshot"),
    ("/webcam/stream.mjpg", "/webcam/snapshot.jpg"),
)
DEFAULTS_SECOND = (("/webcam2/stream.mjpg", "/webcam2/snapshot.jpg"),)
RTSP_PORTS = (8554, 8555)  # paxx12: internal camera, USB camera
RTSP_TIMEOUT_S = 2


async def rtsp_ok(host: str, port: int, timeout: float = RTSP_TIMEOUT_S) -> bool:
    """Does an RTSP server answer OPTIONS on rtsp://host:port/stream?"""
    url = f"rtsp://{host}:{port}/stream"
    try:
        async with asyncio.timeout(timeout):
            reader, writer = await asyncio.open_connection(host, port)
            try:
                writer.write(f"OPTIONS {url} RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: snapmaker_u1_card\r\n\r\n".encode())
                await writer.drain()
                line = await reader.readline()
            finally:
                writer.close()
    except (OSError, TimeoutError):
        return False
    return line.startswith(b"RTSP/1.0 200")
# Moonraker webcam services whose stream_url is a web page, not MJPEG
PAGE_SERVICES = ("webrtc-camerastreamer", "webrtc-go2rtc", "webrtc-mediamtx", "webrtc-janus", "iframe", "hlsstream")
PAGE_ENDINGS = ("/webrtc", "/player", "/webrtc/", "/player/", ".html")


def mjpeg_candidates(cam: dict[str, Any]) -> list[str]:
    """Stream paths worth trying for one Moonraker webcam entry, best first.

    A WebRTC/iframe page is never MJPEG: try ``stream.mjpg`` in the same folder
    instead (paxx12 2.x). Same for a ``snapshot.jpg`` without stream URL
    (``mjpegstreamer-adaptive``).
    """
    stream = str(cam.get("stream_url") or "").strip()
    snap = str(cam.get("snapshot_url") or "").strip()
    service = str(cam.get("service") or "").lower()
    out: list[str] = []
    page = bool(stream) and (service in PAGE_SERVICES or stream.split("?")[0].endswith(PAGE_ENDINGS))
    if stream and not page:
        out.append(stream)
    if page:
        out.append(stream.split("?")[0].rstrip("/").rsplit("/", 1)[0] + "/stream.mjpg")
    if snap.split("?")[0].endswith("/snapshot.jpg"):
        derived = snap.split("?")[0][: -len("snapshot.jpg")] + "stream.mjpg"
        if derived not in out:
            out.append(derived)
    return out


def webrtc_url(cam: dict[str, Any]) -> str | None:
    """Signalling URL of a camera-streamer WebRTC webcam (paxx12 2.x), else None."""
    stream = str(cam.get("stream_url") or "").strip()
    service = str(cam.get("service") or "").lower()
    if service == "webrtc-camerastreamer" or stream.split("?")[0].rstrip("/").endswith("/webrtc"):
        return stream.split("?")[0] if stream else None
    return None


def _digest(blob: bytes | None) -> str | None:
    return hashlib.sha1(blob).hexdigest() if blob else None


class Webcam:
    """Camera access for one printer: detection, images and wake-up."""

    def __init__(self, client: MoonrakerClient, second: bool = False) -> None:
        self.client = client
        self.second = second
        self.rtsp_url: str | None = None
        self.mode = "unknown"
        self.stream_url: str | None = None
        self.snapshot_url: str | None = None
        # camera-streamer WebRTC signalling (paxx12 ``/webcam/webrtc``), None = not offered
        self.webrtc_url: str | None = None
        self.checked_at: float | None = None  # time.time() of the last detection
        self.next_check = 0.0  # monotonic: earliest next detection
        self._stream_retry_at = 0.0
        self._last_wake = 0.0
        self._image: bytes | None = None
        self._image_at = 0.0
        self._fails = 0
        self._lock = asyncio.Lock()
        self._detecting = False
        self.stream_error: str | None = None  # why the last stream check failed (diagnostics)

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
            port = RTSP_PORTS[1 if self.second else 0]
            self.rtsp_url = (f"rtsp://{self.client.host}:{port}/stream"
                             if mode in ("live", "still") and await rtsp_ok(self.client.host, port) else None)
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
        # live keeps its mode until images fail. still with a stream address: try
        # the stream again regularly (one slow first frame must not mean stills
        # for a day); wake/none: re-check now and then (firmware changes).
        if mode == "live":
            self.next_check = now + 24 * 3600
        elif mode == "still" and stream:
            self.next_check = now + STREAM_RETRY_S
        elif mode == "still":
            self.next_check = now + 24 * 3600
        elif self.second:
            self.next_check = now + 3600  # a second camera is rare: look again hourly
        else:
            self.next_check = now + NONE_RETRY_S
        return mode

    async def _probe(self) -> tuple[str, str | None, str | None]:
        cams = await self.client.webcams()
        if self.second:
            # every webcam but the first one Moonraker lists (that is the main camera)
            cams = cams[1:]
        self.webrtc_url = next((self.client.resolve_url(u) for u in (webrtc_url(c) for c in cams[:1]) if u), None)
        candidates: list[tuple[str | None, str | None]] = []
        for c in cams:
            snap = self.client.resolve_url(c.get("snapshot_url"))
            streams = [self.client.resolve_url(u) for u in mjpeg_candidates(c)] or [None]
            candidates += [(u, snap) for u in streams]
        for stream_path, snap_path in (DEFAULTS_SECOND if self.second else DEFAULTS):
            default = (self.client.resolve_url(stream_path), self.client.resolve_url(snap_path))
            if default[0] not in {s for s, _ in candidates}:
                candidates.append(default)
        still: tuple[str | None, str | None] | None = None
        stream_ok = time.monotonic() >= self._stream_retry_at
        self.stream_error = None
        failed: list[str] = []
        for stream, snap in candidates:
            if stream and stream_ok:
                for _ in range(STREAM_TRIES):
                    if await self.client.first_mjpeg_frame(stream, timeout=FIRST_FRAME_S):
                        return "live", stream, snap
                failed.append(stream)
                self.stream_error = (f"no MJPEG frame within {FIRST_FRAME_S} s ({STREAM_TRIES} tries): "
                                     + ", ".join(failed))
            if still is None and snap and await self.client.fetch_image(snap):
                still = (stream, snap)
        if still:
            return "still", still[0], still[1]
        if self.second:
            return "none", None, None
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
            return (await self.client.first_mjpeg_frame(self.stream_url, timeout=FIRST_FRAME_S)
                    if self.stream_url else None)
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
                "rtsp_url": self.rtsp_url, "webrtc_url": self.webrtc_url, "checked_at": self.checked_at, "stream_error": self.stream_error}
