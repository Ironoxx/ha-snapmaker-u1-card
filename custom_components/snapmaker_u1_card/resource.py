"""Karte zusaetzlich als Dashboard-Ressource unter /local eintragen.

Warum zwei Ladewege: ``add_extra_js_url`` landet in der Startseite von Home
Assistant. Der Webserver liefert die Startseite aber schon aus, sobald das
Frontend laeuft - lange bevor eigene Integrationen eingerichtet sind. Wer in
diesem Fenster laedt (Browser-Tab, App nach Neustart), bekommt die Seite ohne
Karte ("Custom element doesn't exist"), bis er neu laedt. Das Frontend laedt
spaeter angemeldete Skripte nicht nach.

Dashboard-Ressourcen dagegen holt das Dashboard selbst aus seinem Speicher,
und ``/local`` (= /config/www) bedient das Frontend vom ersten Moment an.
Damit ist die Karte unabhaengig davon da, wann die Integration startet.
``add_extra_js_url`` bleibt fuer Dashboards im YAML-Modus.
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
    """Karte nach /config/www kopieren. True, wenn www vorher schon existierte."""
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
    """Ressourcen-Sammlung im Speicher-Modus, sonst None (YAML-Modus/kein Lovelace)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        data = hass.data.get(LOVELACE_DATA)
    except ImportError:  # aeltere HA-Versionen
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
    """Datei kopieren und Ressource anlegen bzw. auf die aktuelle Version heben."""
    try:
        www_existed = await hass.async_add_executor_job(_copy_card, hass)
    except OSError as err:
        _LOGGER.warning("Karte nicht nach /config/www kopiert: %s", err)
        return
    if not www_existed:
        # /local wird nur bedient, wenn www beim Start schon existierte.
        _LOGGER.info("/config/www neu angelegt; der zusaetzliche Ladeweg greift ab dem naechsten Neustart")

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
            _LOGGER.info("Dashboard-Ressource angelegt: %s", wanted)
            return
        first, *dupes = mine
        if first.get("url") != wanted or first.get("type") != "module":
            await resources.async_update_item(first["id"], {"res_type": "module", "url": wanted})
        for item in dupes:
            await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001 - Ressource ist Komfort, nie Startblocker
        _LOGGER.warning("Dashboard-Ressource nicht eingetragen: %s", err)


async def async_uninstall(hass: HomeAssistant) -> None:
    """Beim Entfernen der letzten Integration: Ressource und Datei entfernen."""
    resources = _resources(hass)
    if resources is not None:
        try:
            await _loaded(resources)
            for item in list(resources.async_items()):
                if str(item.get("url", "")).split("?")[0] == LOCAL_URL:
                    await resources.async_delete_item(item["id"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Dashboard-Ressource nicht entfernt: %s", err)

    def _remove() -> None:
        shutil.rmtree(Path(hass.config.path("www")) / LOCAL_DIR, ignore_errors=True)

    await hass.async_add_executor_job(_remove)
