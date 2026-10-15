"""Zeitraffer-Videos und -Vorschaubilder ueber Home Assistant ausliefern.

Der Browser spricht nie direkt mit dem Drucker: das funktioniert auch ueber
Nabu Casa/VPN und ohne Mixed-Content-Probleme. Der Videoplayer braucht
Range-Anfragen zum Spulen; Range und die passenden Antwort-Header werden
1:1 durchgereicht. Die Karte holt sich per ``auth/sign_path`` eine signierte
URL, weil ein <video>-Element keinen Authorization-Header mitschicken kann.

Ausgeliefert wird nur, was in der aktuellen Zeitraffer-Liste steht.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN, VIDEO_URL

if TYPE_CHECKING:
    from .coordinator import U1Coordinator

_LOGGER = logging.getLogger(__name__)

PASS_REQUEST = ("Range", "If-Range")
PASS_RESPONSE = ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges",
                 "Last-Modified", "ETag")


def allowed(coordinator: U1Coordinator, root: str, path: str) -> bool:
    data = coordinator.data
    for item in (data.timelapses if data else []):
        if item.get("root") == root and path in (item.get("path"), item.get("poster")):
            return True
    return False


def reachable(coordinator: U1Coordinator) -> bool:
    """Bei ausgeschaltetem/nicht erreichbarem Drucker gar nicht erst verbinden.

    Eine haengende Anfrage blockiert eine der wenigen Browser-Verbindungen.
    """
    data = coordinator.data
    return not coordinator.power_is_off() and data is not None and data.online


class TimelapseView(HomeAssistantView):
    url = VIDEO_URL + "/{entry_id}/{root}/{path:.+}"
    name = f"api:{DOMAIN}:video"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, root: str, path: str) -> web.StreamResponse:
        hass = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return web.Response(status=404)
        coordinator: U1Coordinator = entry.runtime_data
        if not allowed(coordinator, root, path):
            return web.Response(status=404)
        if not reachable(coordinator):
            return web.Response(status=503, text="Drucker ist aus oder nicht erreichbar")

        headers = {k: request.headers[k] for k in PASS_REQUEST if k in request.headers}
        try:
            upstream = await coordinator.client.open_file(root, path, headers)
        except MoonrakerError as err:
            _LOGGER.debug("Zeitraffer %s/%s nicht abrufbar: %s", root, path, err)
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
            # Player hat abgebrochen (Spulen, Dialog zu): normal.
            return response if response is not None else web.Response(status=499)
        finally:
            upstream.release()
