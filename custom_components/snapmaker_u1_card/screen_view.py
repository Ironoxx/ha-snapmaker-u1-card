"""HTTP endpoints for the card's display view (paxx12 display mirror, see screen.py).

GET  /api/snapmaker_u1_card/screen/<entry_id>/snapshot  -> current picture, never cached
POST /api/snapmaker_u1_card/screen/<entry_id>/touch     -> {"a": "down", "x": 120, "y": 80}

The browser cannot reach the printer from an https page, so Home Assistant
relays both. A touch can change any printer setting: admin only, validated
against the panel size and rate limited.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN

SCREEN_URL = f"/api/{DOMAIN}/screen"


def _coordinator(request: web.Request, entry_id: str) -> Any | None:
    """Coordinator of the entry if it has a display mirror, else None."""
    entry = request.app[KEY_HASS].config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
        return None
    coord = entry.runtime_data
    return coord if coord.screen.size else None


class ScreenSnapshotView(HomeAssistantView):
    """GET: the display picture, fetched for every request."""

    url = SCREEN_URL + "/{entry_id}/snapshot"
    name = f"api:{DOMAIN}:screen_snapshot"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        coord = _coordinator(request, entry_id)
        if coord is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        if coord.power_is_off():
            return web.Response(status=HTTPStatus.SERVICE_UNAVAILABLE)
        blob = await coord.screen.snapshot()
        if blob is None:
            return web.Response(status=HTTPStatus.BAD_GATEWAY)
        ctype = "image/png" if blob[:4] == b"\x89PNG" else "image/jpeg"
        return web.Response(body=blob, content_type=ctype, headers={"Cache-Control": "no-store"})


class ScreenTouchView(HomeAssistantView):
    """POST: one touch event (down, move or up) on the display."""

    url = SCREEN_URL + "/{entry_id}/touch"
    name = f"api:{DOMAIN}:screen_touch"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        user = request.get(KEY_HASS_USER)
        if user is None or not user.is_admin:
            return self.json_message("admin only", HTTPStatus.FORBIDDEN)
        coord = _coordinator(request, entry_id)
        if coord is None:
            return self.json_message("no display mirror", HTTPStatus.NOT_FOUND)
        try:
            touch = coord.screen.clean_touch(json.loads(await request.text()))
        except ValueError:
            touch = None
        if touch is None:
            return self.json_message("invalid touch", HTTPStatus.BAD_REQUEST)
        if not coord.screen.allow_touch():
            return self.json_message("too many touches", HTTPStatus.TOO_MANY_REQUESTS)
        try:
            await coord.screen.touch(*touch)
        except MoonrakerError as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)
        return self.json({"ok": True})
