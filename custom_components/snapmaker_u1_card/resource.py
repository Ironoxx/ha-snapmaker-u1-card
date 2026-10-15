"""Also register the card as a dashboard resource under /local.

Why two loading paths: ``add_extra_js_url`` ends up in Home Assistant's start
page. The web server serves that page as soon as the frontend runs - long
before custom integrations are set up. Anyone loading in that window (browser
tab, app after a restart) gets the page without the card ("Custom element
doesn't exist") until they reload. The frontend does not load scripts that
are registered later.

Dashboard resources, on the other hand, are loaded by the dashboard from its
own storage, and ``/local`` (= /config/www) is served by the frontend from
the first moment. The card is therefore available no matter when the
integration starts. ``add_extra_js_url`` stays for dashboards in YAML mode.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

LOCAL_DIR = DOMAIN  # /config/www/snapmaker_u1_card/
LOCAL_URL = f"/local/{LOCAL_DIR}/{CARD_FILENAME}"


def _copy_card(hass: HomeAssistant) -> bool:
    """Copy the card to /config/www. True if www already existed before."""
    src = Path(__file__).parent / "frontend" / CARD_FILENAME
    www = Path(hass.config.path("www"))
    existed = www.is_dir()
    dst = www / LOCAL_DIR / CARD_FILENAME
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    if not dst.exists() or dst.read_bytes() != data:
        tmp = dst.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(dst)
    return existed


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


async def async_install(hass: HomeAssistant) -> None:
    """Copy the file and create the resource or bump it to the current version."""
    try:
        www_existed = await hass.async_add_executor_job(_copy_card, hass)
    except OSError as err:
        _LOGGER.warning("Card not copied to /config/www: %s", err)
        return
    if not www_existed:
        # /local is only served if www already existed at startup.
        _LOGGER.info("/config/www was just created; the additional loading path takes effect after the next restart")

    resources = _resources(hass)
    if resources is None:
        return
    try:
        await _loaded(resources)
        wanted = f"{LOCAL_URL}?v={VERSION}"
        mine = [
            item for item in resources.async_items()
            if str(item.get("url", "")).split("?")[0] == LOCAL_URL
        ]
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
    """When the last config entry is removed: remove resource and file."""
    resources = _resources(hass)
    if resources is not None:
        try:
            await _loaded(resources)
            for item in list(resources.async_items()):
                if str(item.get("url", "")).split("?")[0] == LOCAL_URL:
                    await resources.async_delete_item(item["id"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Dashboard resource not removed: %s", err)

    def _remove() -> None:
        shutil.rmtree(Path(hass.config.path("www")) / LOCAL_DIR, ignore_errors=True)

    await hass.async_add_executor_job(_remove)
