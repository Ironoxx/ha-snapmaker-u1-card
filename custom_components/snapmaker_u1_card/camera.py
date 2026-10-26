"""Own camera entity: works with stock and modified firmware alike.

How the image is obtained is decided by the integration (``webcam.py``),
attribute ``mode``:

- ``live``: the printer's MJPEG stream is passed through.
- ``still`` / ``wake``: single images; Home Assistant turns them into an MJPEG
  stream at ``frame_interval``. ``wake`` (stock firmware) calls
  ``camera.start_monitor`` as needed, at most every 10 s.
- ``none``: no camera found -> unavailable.

The card always uses this entity's ``camera_proxy_stream``; it does not need
to know which kind of camera is behind it.

With RTSP on the printer (paxx12) the entity also offers ``stream_source``, so
Home Assistant streams H.264 itself (more-info dialog, picture cards, go2rtc).
A second camera (paxx12 USB camera) gets a second entity once it is found.
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_aiohttp_proxy_stream
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .api import MoonrakerError
from .coordinator import U1Coordinator
from .sensor import U1Entity
from .webcam import Webcam

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([U1Camera(coordinator)])
    added = False

    @callback
    def second() -> None:
        # Second camera only once it was found (most printers have one camera)
        nonlocal added
        if not added and coordinator.webcam2.mode in ("live", "still"):
            added = True
            async_add_entities([U1Camera(coordinator, second=True)])

    second()
    entry.async_on_unload(coordinator.async_add_listener(second))


class U1Camera(U1Entity, Camera):
    """Printer camera: live stream, still images or woken stock camera."""

    def __init__(self, coordinator: U1Coordinator, second: bool = False) -> None:
        U1Entity.__init__(self, coordinator, "camera2" if second else "camera")
        Camera.__init__(self)
        self._second = second
        self._attr_translation_key = "camera2" if second else "camera"
        self.content_type = "image/jpeg"

    @property
    def _cam(self) -> Webcam:
        return self.coordinator.webcam2 if self._second else self.coordinator.webcam

    @property
    def available(self) -> bool:
        return super().available and self._cam.mode != "none"

    @property
    def supported_features(self) -> CameraEntityFeature:
        return CameraEntityFeature.STREAM if self._cam.rtsp_url else CameraEntityFeature(0)

    async def stream_source(self) -> str | None:
        return self._cam.rtsp_url

    @property
    def frame_interval(self) -> float:
        # still images: HA's MJPEG loop asks this often; the webcam caches 1 s
        return 1.5 if self._cam.mode == "wake" else 1.0

    @property
    def is_streaming(self) -> bool:
        return self._cam.mode == "live"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cam = self._cam
        attrs: dict[str, Any] = {"mode": cam.mode, "live_stream": cam.mode == "live"}
        if cam.rtsp_url:
            attrs["rtsp_url"] = cam.rtsp_url
        if cam.mode != "live" and cam.stream_error:
            attrs["stream_error"] = cam.stream_error
        return attrs

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return await self._cam.image()

    async def handle_async_mjpeg_stream(self, request: web.Request) -> web.StreamResponse | None:
        """Live: pass the printer's MJPEG through; otherwise HA's still-image stream."""
        cam = self._cam
        if cam.mode == "live" and cam.stream_url:
            try:
                upstream = await self.coordinator.client.open_stream(cam.stream_url)
            except MoonrakerError as err:
                _LOGGER.debug("Camera stream not reachable: %s", err)
                upstream = None
            if upstream is not None and upstream.status < 400 and upstream.headers.get(
                    "Content-Type", "").lower().startswith("multipart/x-mixed-replace"):
                return await async_aiohttp_proxy_stream(
                    self.hass, request, upstream, upstream.headers["Content-Type"])
            if upstream is not None:
                upstream.release()
            cam.stream_failed()
            self.async_write_ha_state()
        return await self.handle_async_still_stream(request, self.frame_interval)
