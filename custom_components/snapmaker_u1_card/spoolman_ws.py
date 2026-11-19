"""Spoolman suggestions for the card's "new spool" form, over the websocket.

``snapmaker_u1_card/spoolman/catalog`` – vendor and material names (own ones first)
``snapmaker_u1_card/spoolman/suggest`` – filaments matching vendor, material and text,
own Spoolman filaments first, then SpoolmanDB
``snapmaker_u1_card/spoolman/archived`` – 2.4: the archived spools, only when the card
shows them (filter "archived"), so the regular poll stays as small as before
``snapmaker_u1_card/spoolman/fields`` – 2.4.0b3: the user's own Spoolman fields (spool and
filament) for the new-spool and edit forms
``snapmaker_u1_card/spoolman/spool`` – 2.4.0b3: one spool for the edit form, with its fields
and how many spools share the filament

Changes go through the services ``create_spool`` and ``update_spool``.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .api import MoonrakerError
from .const import DOMAIN
from .parsing import compact_fields, compact_spool, edit_spool_view
from .settings_ws import _entry


def _manager(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> Any:
    entry = _entry(hass, msg.get("entry_id"))
    mgr = entry.runtime_data.spools if entry is not None else None
    if mgr is None or not mgr.enabled or mgr.client is None:
        connection.send_error(msg["id"], "not_found", "Spoolman is not set up")
        return None
    return mgr


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/spoolman/catalog",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_catalog(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    mgr = _manager(hass, connection, msg)
    if mgr is None:
        return
    try:
        connection.send_result(msg["id"], await mgr.catalog.overview(mgr.client))
    except MoonrakerError as err:
        connection.send_error(msg["id"], "spoolman", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/spoolman/suggest",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): vol.All(str, vol.Length(max=100)),
    vol.Optional("vendor", default=""): vol.All(str, vol.Length(max=64)),
    vol.Optional("material", default=""): vol.All(str, vol.Length(max=32)),
})
@websocket_api.async_response
async def ws_suggest(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    mgr = _manager(hass, connection, msg)
    if mgr is None:
        return
    try:
        items = await mgr.catalog.suggest(mgr.client, msg["query"], msg["vendor"], msg["material"])
        connection.send_result(msg["id"], {"items": items})
    except MoonrakerError as err:
        connection.send_error(msg["id"], "spoolman", str(err))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/spoolman/archived",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_archived(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Archived spools in the card's compact form, newest ID first."""
    mgr = _manager(hass, connection, msg)
    if mgr is None:
        return
    try:
        spools = [compact_spool(s) for s in await mgr.client.archived_spools()]
        connection.send_result(msg["id"], {"spools": sorted(spools, key=lambda s: -(s.get("id") or 0))})
    except MoonrakerError as err:
        connection.send_error(msg["id"], "spoolman", str(err))


async def _fields(mgr: Any) -> dict[str, list[dict[str, Any]]]:
    """Own fields of spools and filaments; an older Spoolman without /field gives none."""
    out = {}
    for entity in ("spool", "filament"):
        try:
            out[entity] = compact_fields(await mgr.client.fields(entity))
        except MoonrakerError:
            out[entity] = []
    return out


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/spoolman/fields",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_fields(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    mgr = _manager(hass, connection, msg)
    if mgr is None:
        return
    connection.send_result(msg["id"], await _fields(mgr))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/spoolman/spool",
    vol.Required("spool_id"): vol.All(int, vol.Range(min=1)),
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_spool(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Everything the edit form needs, in one call when it opens."""
    mgr = _manager(hass, connection, msg)
    if mgr is None:
        return
    try:
        view = edit_spool_view(await mgr.client.spool(msg["spool_id"]))
        fid = view["filament"]["id"]
        shared = await mgr.client.count_spools(fid) if fid else 0
    except MoonrakerError as err:
        connection.send_error(msg["id"], "spoolman", str(err))
        return
    connection.send_result(msg["id"], {"spool": view, "filament_spools": shared, "fields": await _fields(mgr)})


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_catalog)
    websocket_api.async_register_command(hass, ws_suggest)
    websocket_api.async_register_command(hass, ws_archived)
    websocket_api.async_register_command(hass, ws_fields)
    websocket_api.async_register_command(hass, ws_spool)
