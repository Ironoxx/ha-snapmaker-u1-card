"""Register the card as a dashboard resource, served from the integration.

``add_extra_js_url`` ends up in Home Assistant's start page, which the
frontend serves as soon as it runs, so a dashboard in storage mode also gets
the card as a regular dashboard resource. Both point to the integration's own
static path (``/snapmaker_u1_card/card/…``) with the same version parameter,
so the browser loads the module once and fetches it again after an update.

Up to 2.1.1 the card was copied to ``/config/www`` and registered under
``/local``. On setup the old resource is moved to the static path and the
copy that the integration itself put there is removed (only that file, the
folder only if it is empty then); nothing else in ``/config/www`` is touched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

CARD_RESOURCE = f"{CARD_URL}/{CARD_FILENAME}"
# Before 2.1.2: copy under /config/www/snapmaker_u1_card/, resource /local/…
LEGACY_URL = f"/local/{DOMAIN}/{CARD_FILENAME}"
OURS = (CARD_RESOURCE, LEGACY_URL)


def _remove_legacy_copy(hass: HomeAssistant) -> bool:
    """Delete the card file earlier versions copied to /config/www (blocking)."""
    folder = Path(hass.config.path("www")) / DOMAIN
    removed = False
    for name in (CARD_FILENAME, f"{Path(CARD_FILENAME).stem}.tmp"):
        path = folder / name
        if path.is_file():
            path.unlink()
            removed = True
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    return removed


def _resources(hass: HomeAssistant) -> Any | None:
    """Resource collection in storage mode, else None (YAML mode / no Lovelace)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        data = hass.data.get(LOVELACE_DATA)
    except ImportError:  # older Home Assistant versions
        data = hass.data.get("lovelace")
    if data is None:
        return None
    mode = getattr(data, "resource_mode", None) or (data.get("resource_mode") if isinstance(data, dict) else None)
    resources = getattr(data, "resources", None) or (data.get("resources") if isinstance(data, dict) else None)
    if mode != "storage" or resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


async def _loaded(resources: Any) -> None:
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True


def _is_ours(item: dict[str, Any]) -> bool:
    return str(item.get("url", "")).split("?")[0] in OURS


async def async_install(hass: HomeAssistant) -> None:
    """Create the resource or bring it to the current version and path."""
    try:
        if await hass.async_add_executor_job(_remove_legacy_copy, hass):
            _LOGGER.info("Removed the old copy of the card from /config/www/%s", DOMAIN)
    except OSError as err:
        _LOGGER.debug("Old card copy not removed: %s", err)

    resources = _resources(hass)
    if resources is None:
        return
    try:
        await _loaded(resources)
        wanted = f"{CARD_RESOURCE}?v={VERSION}"
        mine = [item for item in resources.async_items() if _is_ours(item)]
        if not mine:
            await resources.async_create_item({"res_type": "module", "url": wanted})
            _LOGGER.info("Dashboard resource created: %s", wanted)
            return
        first, *dupes = mine
        if first.get("url") != wanted or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"res_type": "module", "url": wanted})
        for item in dupes:
            await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001 - the resource is a convenience, never a startup blocker
        _LOGGER.warning("Dashboard resource not registered: %s", err)


async def async_uninstall(hass: HomeAssistant) -> None:
    """When the last config entry is removed: remove the dashboard resource."""
    resources = _resources(hass)
    if resources is None:
        return
    try:
        await _loaded(resources)
        for item in list(resources.async_items()):
            if _is_ours(item):
                await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Dashboard resource not removed: %s", err)
