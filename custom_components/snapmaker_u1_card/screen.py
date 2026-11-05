"""paxx12 display mirror: the printer's touchscreen as picture and touch target.

paxx12's Extended Firmware mirrors the touchscreen at ``/screen/``: the current
picture is ``/screen/snapshot`` (PNG in panel pixels) and ``POST
/screen/touch?a=down|move|up&x=&y=`` injects a touch in those pixels. Moonraker
lists the mirror as a webcam, but it is no camera: ``webcam.py`` skips it and
the card shows it in its own view.

Detection looks at the Moonraker webcams and the default path; the panel size
comes from the PNG header and bounds every touch. Both URLs are built from the
configured printer host, never from a URL Moonraker reports, so touches can
only go to that printer.
"""

from __future__ import annotations

import logging
import struct
import time
from typing import Any
from urllib.parse import urlsplit

from .api import MoonrakerClient, MoonrakerError

_LOGGER = logging.getLogger(__name__)

SNAPSHOT_PATH = "/screen/snapshot"
TOUCH_PATH = "/screen/touch"
ACTIONS = ("down", "move", "up")
RETRY_S = 600  # nothing found: look again after this (firmware changes)
SNAPSHOT_TIMEOUT_S = 3
# Touch rate limit (token bucket): a swipe sends a move every 60 ms at most
TOUCH_BURST = 40
TOUCH_PER_S = 20.0


def is_screen(cam: dict[str, Any]) -> bool:
    """Whether a Moonraker webcam entry is the display mirror (not a camera)."""
    return any(urlsplit(str(cam.get(key) or "").strip()).path.rstrip("/") in ("/screen", SNAPSHOT_PATH)
               for key in ("snapshot_url", "stream_url"))


def png_size(blob: bytes | None) -> tuple[int, int] | None:
    """(width, height) from a PNG header, else None."""
    if not blob or len(blob) < 24 or blob[:8] != b"\x89PNG\r\n\x1a\n" or blob[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", blob[16:24])
    return (width, height) if width and height else None


class ScreenMirror:
    """The display mirror of one printer: detection, picture, touch."""

    def __init__(self, client: MoonrakerClient) -> None:
        self.client = client
        self.size: tuple[int, int] | None = None  # panel pixels; None = no mirror
        self.next_check = 0.0
        self._detecting = False
        self._tokens = float(TOUCH_BURST)
        self._tokens_at = time.monotonic()

    @property
    def snapshot_url(self) -> str:
        return f"http://{self.client.host}{SNAPSHOT_PATH}"

    @property
    def touch_url(self) -> str:
        return f"http://{self.client.host}{TOUCH_PATH}"

    def reset(self) -> None:
        """Printer went offline: detect again when it is back."""
        self.next_check = 0.0

    def due(self) -> bool:
        return not self._detecting and time.monotonic() >= self.next_check

    async def detect(self) -> tuple[int, int] | None:
        """Look for the mirror; sets and returns ``size``."""
        if self._detecting:
            return self.size
        self._detecting = True
        try:
            cams = await self.client.webcams()
            listed = any(is_screen(c) for c in cams)
            # Listed or not: paxx12 serves it at the default path either way
            size = png_size(await self.client.fetch_image(self.snapshot_url, timeout=SNAPSHOT_TIMEOUT_S))
            if size is None and listed:
                _LOGGER.debug("Display mirror listed, but %s gave no PNG", self.snapshot_url)
        except MoonrakerError as err:
            _LOGGER.debug("Display mirror detection failed: %s", err)
            size = self.size
        finally:
            self._detecting = False
        if size != self.size:
            _LOGGER.info("Display mirror: %s", f"{size[0]}x{size[1]}" if size else "none")
        self.size = size
        self.next_check = float("inf") if size else time.monotonic() + RETRY_S
        return size

    async def snapshot(self) -> bytes | None:
        """The current picture, never cached; keeps ``size`` up to date."""
        blob = await self.client.fetch_image(self.snapshot_url, timeout=SNAPSHOT_TIMEOUT_S)
        if (size := png_size(blob)) is not None:
            self.size = size
        return blob

    def clean_touch(self, body: Any) -> tuple[str, int, int] | None:
        """(action, x, y) inside the panel, or None if it is not a valid touch."""
        if self.size is None or not isinstance(body, dict) or body.get("a") not in ACTIONS:
            return None
        x, y = body.get("x"), body.get("y")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (x, y)):
            return None
        width, height = self.size
        return (body["a"], x, y) if 0 <= x < width and 0 <= y < height else None

    def allow_touch(self) -> bool:
        """Token bucket: False when touches come faster than a finger can."""
        now = time.monotonic()
        self._tokens = min(TOUCH_BURST, self._tokens + (now - self._tokens_at) * TOUCH_PER_S)
        self._tokens_at = now
        if self._tokens < 1:
            return False
        self._tokens -= 1
        return True

    async def touch(self, action: str, x: int, y: int) -> None:
        await self.client.screen_touch(self.touch_url, action, x, y)

    def as_dict(self) -> dict[str, Any]:
        """For diagnostics."""
        return {"size": list(self.size) if self.size else None, "snapshot_url": self.snapshot_url}
