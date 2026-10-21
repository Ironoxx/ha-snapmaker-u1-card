"""Serve timelapse videos and previews through Home Assistant.

The browser never talks to the printer directly: this works via Nabu
Casa/VPN and without mixed-content problems. The video player needs Range
requests for seeking; Range and the matching response headers are passed
through 1:1. The card fetches a signed URL via ``auth/sign_path`` because a
<video> element cannot send an Authorization header.

Only files in the current timelapse list are served.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import quote

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN, GCODE_URL, VIDEO_URL

if TYPE_CHECKING:
    from .coordinator import U1Coordinator

_LOGGER = logging.getLogger(__name__)

PASS_REQUEST = ("Range", "If-Range")
PASS_RESPONSE = ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges",
                 "Last-Modified", "ETag")


def allowed(coordinator: U1Coordinator, root: str, path: str) -> bool:
    """Whether ``root/path`` is a timelapse the integration currently lists."""
    data = coordinator.data
    for item in (data.timelapses if data else []):
        if item.get("root") == root and path in (item.get("path"), item.get("poster")):
            return True
    return False


def reachable(coordinator: U1Coordinator) -> bool:
    """Do not even connect while the printer is off or unreachable.

    A hanging request blocks one of the few browser connections.
    """
    data = coordinator.data
    return not coordinator.power_is_off() and data is not None and data.online


class TimelapseView(HomeAssistantView):
    """Authenticated proxy for timelapse videos and images."""
    url = VIDEO_URL + "/{entry_id}/{root}/{path:.+}"
    name = f"api:{DOMAIN}:video"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, root: str, path: str) -> web.StreamResponse:
        """Stream a timelapse file from the printer, passing Range through."""
        hass = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        coordinator: U1Coordinator = entry.runtime_data
        if not allowed(coordinator, root, path):
            return web.Response(status=404)
        if not reachable(coordinator):
            return web.Response(status=503, text="Printer is off or not reachable")

        headers = {k: request.headers[k] for k in PASS_REQUEST if k in request.headers}
        try:
            upstream = await coordinator.client.open_file(root, path, headers)
        except MoonrakerError as err:
            _LOGGER.debug("Timelapse %s/%s not available: %s", root, path, err)
            return web.Response(status=502)

        response: web.StreamResponse | None = None
        try:
            if upstream.status >= 400:
                return web.Response(status=upstream.status)
            response = web.StreamResponse(status=upstream.status)
            for key in PASS_RESPONSE:
                if key in upstream.headers:
                    response.headers[key] = upstream.headers[key]
            response.headers["Cache-Control"] = "private, max-age=3600"
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(64 * 1024):
                await response.write(chunk)
            await response.write_eof()
            return response
        except (ConnectionResetError, OSError):
            # The player aborted (seeking, dialog closed): normal.
            return response if response is not None else web.Response(status=499)
        finally:
            upstream.release()


def gcode_allowed(coordinator: U1Coordinator, path: str) -> bool:
    """Whether ``path`` is a print file the integration currently lists."""
    data = coordinator.data
    if data is None:
        return False
    return any(f.get("path") == path for f in (data.all_files or [])) or any(
        f.get("path") == path for f in (data.files or []))


class GcodeView(HomeAssistantView):
    """Authenticated download of a print file (card: file dialog -> download)."""
    url = GCODE_URL + "/{entry_id}/{path:.+}"
    name = f"api:{DOMAIN}:gcode"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, path: str) -> web.StreamResponse:
        """Stream the file from the printer as an attachment."""
        hass = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        coordinator: U1Coordinator = entry.runtime_data
        if not gcode_allowed(coordinator, path):
            return web.Response(status=404)
        if not reachable(coordinator):
            return web.Response(status=503, text="Printer is off or not reachable")
        try:
            upstream = await coordinator.client.open_file("gcodes", path, {})
        except MoonrakerError as err:
            _LOGGER.debug("G-code %s not available: %s", path, err)
            return web.Response(status=502)

        response: web.StreamResponse | None = None
        try:
            if upstream.status >= 400:
                return web.Response(status=upstream.status)
            response = web.StreamResponse(status=200)
            for key in ("Content-Length", "Last-Modified"):
                if key in upstream.headers:
                    response.headers[key] = upstream.headers[key]
            name = path.rsplit("/", 1)[-1]
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name)}"
            response.headers["Cache-Control"] = "no-store"
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(64 * 1024):
                await response.write(chunk)
            await response.write_eof()
            return response
        except (ConnectionResetError, OSError):
            return response if response is not None else web.Response(status=499)
        finally:
            upstream.release()
