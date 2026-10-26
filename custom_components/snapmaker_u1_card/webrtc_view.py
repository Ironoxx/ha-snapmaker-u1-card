"""Relay for the WebRTC signalling between the card and the printer's camera.

paxx12's camera (v4l2-mpp, camera-streamer protocol) takes three kinds of
small JSON messages on ``POST /webcam/webrtc``: ``request`` (returns the
offer), ``answer`` and ``remote_candidate``. The printer sends no CORS headers,
so the browser cannot post them itself; this view forwards them. Only these
message types and only to the camera Moonraker reports.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN

WEBRTC_URL = f"/api/{DOMAIN}/webrtc"
_TYPES = {"request", "answer", "remote_candidate"}
_MAX_BODY = 64 * 1024


def clean_message(body: Any) -> dict[str, Any] | None:
    """The message as the printer expects it, or None if it is not a signalling message."""
    if not isinstance(body, dict) or body.get("type") not in _TYPES:
        return None
    kind = body["type"]
    if kind == "request":
        out: dict[str, Any] = {"type": "request", "keepAlive": True}
        if isinstance(body.get("res"), str):
            out["res"] = body["res"][:20]
        if isinstance(body.get("iceServers"), list):
            out["iceServers"] = body["iceServers"][:4]
        return out
    if not isinstance(body.get("id"), (str, int)):
        return None
    if kind == "answer":
        return {"type": "answer", "id": body["id"], "sdp": str(body.get("sdp") or "")} if body.get("sdp") else None
    cands = body.get("candidates")
    return {"type": "remote_candidate", "id": body["id"], "candidates": cands[:20]} if isinstance(cands, list) else None


class WebrtcView(HomeAssistantView):
    """POST /api/snapmaker_u1_card/webrtc/<entry_id>: one signalling step."""

    url = WEBRTC_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:webrtc"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message("not found", HTTPStatus.NOT_FOUND)
        coord = entry.runtime_data
        target = coord.webcam.webrtc_url
        if not target:
            return self.json_message("no WebRTC camera", HTTPStatus.NOT_FOUND)
        if (request.content_length or 0) > _MAX_BODY:
            return self.json_message("too large", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            msg = clean_message(json.loads(await request.text()))
        except ValueError:
            msg = None
        if msg is None:
            return self.json_message("invalid message", HTTPStatus.BAD_REQUEST)
        try:
            return self.json(await coord.client.webrtc_signal(target, msg))
        except MoonrakerError as err:
            return self.json_message(str(err), HTTPStatus.BAD_GATEWAY)
