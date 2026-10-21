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
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_aiohttp_proxy_stream
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .api import MoonrakerError
from .coordinator import U1Coordinator
from .sensor import U1Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([U1Camera(entry.runtime_data)])


class U1Camera(U1Entity, Camera):
    """Printer camera: live stream, still images or woken stock camera."""

    _attr_translation_key = "camera"

    def __init__(self, coordinator: U1Coordinator) -> None:
        U1Entity.__init__(self, coordinator, "camera")
        Camera.__init__(self)
        self.content_type = "image/jpeg"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.webcam.mode != "none"

    @property
    def frame_interval(self) -> float:
        # still images: HA's MJPEG loop asks this often; the webcam caches 1 s
        return 1.5 if self.coordinator.webcam.mode == "wake" else 1.0

    @property
    def is_streaming(self) -> bool:
        return self.coordinator.webcam.mode == "live"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cam = self.coordinator.webcam
        attrs = {"mode": cam.mode, "live_stream": cam.mode == "live"}
        if cam.mode != "live" and cam.stream_error:
            attrs["stream_error"] = cam.stream_error
        return attrs

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return await self.coordinator.webcam.image()

    async def handle_async_mjpeg_stream(self, request: web.Request) -> web.StreamResponse | None:
        """Live: pass the printer's MJPEG through; otherwise HA's still-image stream."""
        cam = self.coordinator.webcam
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
