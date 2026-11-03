"""Settings right in the card (2.0): the options of the integration over the websocket.

The card shows the same options as *Configure* in Home Assistant, grouped and
with context (current entity values, Spoolman prices). The fields are taken
from the options flow's schema, labels from its translations, and saving runs
the same validation, so both ways always agree. Admins only.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

from .config_flow import (
    _notify_services,
    _options_schema,
    _validate_options,
    flatten_options,
    nest_options,
)
from .const import DOMAIN
from .parsing import material_prices

_LOGGER = logging.getLogger(__name__)


def _field(sec: str, marker: Any, sel: Any) -> dict[str, Any]:
    """One form field from a schema key and its selector (type, limits, default)."""
    key = str(marker.schema)
    out: dict[str, Any] = {"key": key, "section": sec, "required": isinstance(marker, vol.Required)}
    default = getattr(marker, "default", vol.UNDEFINED)
    if default is not vol.UNDEFINED:
        out["default"] = default() if callable(default) else default
    cfg = dict(getattr(sel, "config", {}) or {})
    if isinstance(sel, selector.EntitySelector):
        dom = cfg.get("domain")
        out.update(type="entity", domains=[dom] if isinstance(dom, str) else list(dom or []))
        filt = cfg.get("filter") or []
        dc = cfg.get("device_class") or next((f.get("device_class") for f in filt if f.get("device_class")), None)
        if dc:
            out["device_class"] = dc if isinstance(dc, str) else next(iter(dc))
    elif isinstance(sel, selector.NumberSelector):
        out.update(type="number", min=cfg.get("min"), max=cfg.get("max"), step=cfg.get("step"),
                   unit=cfg.get("unit_of_measurement"))
    elif isinstance(sel, selector.BooleanSelector):
        out["type"] = "boolean"
    elif isinstance(sel, selector.SelectSelector):
        opts = [o if isinstance(o, str) else o.get("value") for o in cfg.get("options") or []]
        out.update(type="select", options=opts, multiple=bool(cfg.get("multiple")),
                   custom=bool(cfg.get("custom_value")), translation_key=cfg.get("translation_key"))
    else:
        out["type"] = "text"
    return out


def describe(hass: HomeAssistant) -> list[dict[str, Any]]:
    """All fields of the options form, in order, per section."""
    fields = []
    for marker, sec_obj in _options_schema(_notify_services(hass)).schema.items():
        sec = str(marker.schema)
        for m, sel in sec_obj.schema.schema.items():
            fields.append(_field(sec, m, sel))
    return fields


def _labels(trans: dict[str, str], fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Section names, field labels/descriptions and select option labels from the translations."""
    base = f"component.{DOMAIN}.options.step.init"
    sections: dict[str, dict[str, str]] = {}
    for f in fields:
        sec, key = f["section"], f["key"]
        if sec not in sections:
            sections[sec] = {"name": trans.get(f"{base}.sections.{sec}.name", sec),
                             "description": trans.get(f"{base}.sections.{sec}.description", "")}
        f["label"] = trans.get(f"{base}.sections.{sec}.data.{key}", key)
        f["help"] = trans.get(f"{base}.sections.{sec}.data_description.{key}", "")
        if f.get("translation_key"):
            tk = f["translation_key"]
            f["option_labels"] = {o: trans.get(f"component.{DOMAIN}.selector.{tk}.options.{o}", o)
                                  for o in f.get("options") or []}
    return sections


def _entry(hass: HomeAssistant, entry_id: str | None) -> Any:
    """The printer's config entry: by ID, or the only one if no ID is given."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if entry_id:
        return next((e for e in entries if e.entry_id == entry_id), None)
    return entries[0] if len(entries) == 1 else None


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/settings/get",
    vol.Optional("entry_id"): str,
    vol.Optional("language"): str,
})
@websocket_api.async_response
async def ws_get(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Fields, labels, current values and hints for the settings in the card."""
    entry = _entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "No configured Snapmaker U1 found")
        return
    lang = msg.get("language") or hass.config.language
    fields = describe(hass)
    trans = {**await async_get_translations(hass, lang, "options", [DOMAIN]),
             **await async_get_translations(hass, lang, "selector", [DOMAIN])}
    sections = _labels(trans, fields)
    coord = entry.runtime_data
    sm = coord.spools.spools if coord.spools.enabled else []
    connection.send_result(msg["id"], {
        "fields": fields,
        "sections": sections,
        "values": nest_options(entry.options),
        # Spoolman average per kg and material: shown next to the own prices
        "spoolman_prices": material_prices(sm),
        "spoolman": coord.spools.enabled,
        "title": entry.title,
    })


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/settings/set",
    vol.Optional("entry_id"): str,
    vol.Required("values"): dict,
    vol.Optional("language"): str,
})
@websocket_api.async_response
async def ws_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Validate like the options flow and store; the integration then reloads."""
    entry = _entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], "not_found", "No configured Snapmaker U1 found")
        return
    # The card sends only the sections it changed; the others keep their stored values.
    nested = nest_options(entry.options)
    for sec, vals in msg["values"].items():
        if isinstance(vals, dict):
            nested[sec] = {**nested.get(sec, {}), **vals}
    # Cleared fields (None / "") are dropped, so an entity or a price can be removed again;
    # required fields then get their default from the schema.
    nested = {sec: {k: v for k, v in vals.items() if v not in (None, "")} for sec, vals in nested.items()}
    try:
        validated = _options_schema(_notify_services(hass))(nested)
    except vol.Invalid as err:
        path = ".".join(str(p) for p in err.path)
        connection.send_error(msg["id"], "invalid", f"{path}: {err.msg}" if path else str(err.msg))
        return
    flat = flatten_options(validated)
    error = await _validate_options(hass, flat)
    if error:
        lang = msg.get("language") or hass.config.language
        trans = await async_get_translations(hass, lang, "options", [DOMAIN])
        connection.send_error(msg["id"], error,
                              trans.get(f"component.{DOMAIN}.options.error.{error}", error))
        return
    changed = dict(entry.options) != flat
    if changed:
        _LOGGER.info("Settings changed in the card")
        hass.config_entries.async_update_entry(entry, options=flat)
    connection.send_result(msg["id"], {"changed": changed})


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_get)
    websocket_api.async_register_command(hass, ws_set)
