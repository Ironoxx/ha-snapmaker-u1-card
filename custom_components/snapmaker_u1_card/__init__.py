"""Snapmaker U1 Card – Filamente, Dateien und Druckstart mit Zuordnung.

Die Integration liefert die Lovelace-Karte selbst aus und registriert sie im
Frontend. Eine manuelle Ressource unter Dashboards ist nicht noetig.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from . import resource
from .api import MoonrakerClient
from .const import (
    CARD_FILENAME,
    CARD_URL,
    CONF_API_KEY,
    CONF_AUTO_ON,
    CONF_FILES_LIMIT,
    DEFAULT_FILES_LIMIT,
    DEFAULT_PORT,
    DOMAIN,
    SERVICE_BACKUP_CONFIG,
    SERVICE_BACKUP_TIMELAPSES,
    SERVICE_MAINTENANCE_DONE,
    SERVICE_POWER_OFF,
    SERVICE_POWER_ON,
    SERVICE_QUEUE_ADD,
    SERVICE_QUEUE_CLEAR,
    SERVICE_QUEUE_MOVE,
    SERVICE_QUEUE_REMOVE,
    SERVICE_QUEUE_START,
    SERVICE_REFRESH,
    SERVICE_SET_SPOOL,
    SERVICE_START_PRINT,
    THUMB_URL,
    VERSION,
)
from .coordinator import U1Coordinator
from .layer_view import LayerView, TempsView
from .stats import MAINTENANCE_ITEMS
from .upload import UploadView
from .video import TimelapseView
from .voice import async_setup_voice

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.UPDATE]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type U1ConfigEntry = ConfigEntry[U1Coordinator]

ATTR_ENTRY = "config_entry_id"

PRINT_FIELDS = {
    vol.Required("filename"): cv.string,
    vol.Optional("mapping"): vol.Schema(
        {vol.Coerce(int): vol.All(vol.Coerce(int), vol.Range(min=0, max=3))}
    ),
    vol.Optional("bed_leveling"): cv.boolean,
    vol.Optional("flow_calibration"): cv.boolean,
    vol.Optional("timelapse"): cv.boolean,
    vol.Optional("plate", default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
    # Vor diesen Schichten (1 = erste) anhalten, z. B. fuer Magnete oder Muttern
    vol.Optional("pause_layers"): vol.All(
        cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=1, max=100000))]
    ),
}
START_PRINT_SCHEMA = vol.Schema({**PRINT_FIELDS, vol.Optional(ATTR_ENTRY): cv.string})
QUEUE_ADD_SCHEMA = START_PRINT_SCHEMA
JOB_SCHEMA = vol.Schema({vol.Required("job_id"): cv.string, vol.Optional(ATTR_ENTRY): cv.string})
QUEUE_MOVE_SCHEMA = vol.Schema({
    vol.Required("job_id"): cv.string,
    vol.Required("position"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional(ATTR_ENTRY): cv.string,
})
QUEUE_START_SCHEMA = vol.Schema({vol.Optional("job_id"): cv.string, vol.Optional(ATTR_ENTRY): cv.string})
MAINTENANCE_SCHEMA = vol.Schema({
    vol.Required("item"): vol.In(list(MAINTENANCE_ITEMS)), vol.Optional(ATTR_ENTRY): cv.string,
})
REFRESH_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): cv.string})
SELF_TEST_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTRY): cv.string, vol.Optional("language"): cv.string})
PATH_SCHEMA = vol.Schema({vol.Required("path"): cv.string, vol.Optional(ATTR_ENTRY): cv.string})
MOVE_SCHEMA = vol.Schema({vol.Required("source"): cv.string, vol.Required("dest"): cv.string,
                          vol.Optional(ATTR_ENTRY): cv.string})
SET_SPOOL_SCHEMA = vol.Schema(
    {
        vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=1, max=4)),
        # Spulen-ID aus Spoolman; 0 = bewusst keine Spule. Weglassen = automatisch.
        vol.Optional("spool_id"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(ATTR_ENTRY): cv.string,
    }
)
POWER_OFF_SCHEMA = vol.Schema(
    {vol.Optional("force", default=False): cv.boolean, vol.Optional(ATTR_ENTRY): cv.string}
)
POWER_ON_SCHEMA = vol.Schema(
    {vol.Optional("wait", default=False): cv.boolean, vol.Optional(ATTR_ENTRY): cv.string}
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Karte ausliefern und Dienste anmelden – einmal pro HA-Start."""
    frontend_dir = Path(__file__).parent / "frontend"
    thumb_dir = Path(hass.config.path(".storage", DOMAIN, "thumbs"))
    await hass.async_add_executor_job(lambda: thumb_dir.mkdir(parents=True, exist_ok=True))

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, str(frontend_dir), cache_headers=False),
            StaticPathConfig(THUMB_URL, str(thumb_dir), cache_headers=True),
        ]
    )
    hass.http.register_view(TimelapseView())
    hass.http.register_view(UploadView())
    hass.http.register_view(LayerView())
    hass.http.register_view(TempsView())
    # Versionsparameter erzwingt nach Updates das Neuladen im Browser.
    add_extra_js_url(hass, f"{CARD_URL}/{CARD_FILENAME}?v={VERSION}")
    # Zweiter Ladeweg, unabhaengig vom Startzeitpunkt der Integration (siehe resource.py).
    await resource.async_install(hass)
    hass.data[DOMAIN] = {"thumb_dir": thumb_dir}
    await async_setup_voice(hass)

    async def start_print(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        try:
            return await coordinator.async_start_print(
                call.data["filename"], call.data.get("mapping"),
                bed_leveling=call.data.get("bed_leveling"),
                flow_calibration=call.data.get("flow_calibration"),
                timelapse=call.data.get("timelapse"),
                plate=call.data["plate"],
                pause_layers=call.data.get("pause_layers"),
                auto_on=bool(coordinator.options.get(CONF_AUTO_ON)),
            )
        except ValueError as err:  # ungueltige Zuordnung
            raise ServiceValidationError(str(err)) from err

    async def refresh(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        coordinator.request_files_refresh()
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_START_PRINT, start_print,
        schema=START_PRINT_SCHEMA, supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, refresh, schema=REFRESH_SCHEMA)

    async def set_spool(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        automatic = "spool_id" not in call.data
        spool_id = call.data.get("spool_id") or None
        await coordinator.async_set_spool(call.data["slot"] - 1, spool_id, automatic)

    hass.services.async_register(DOMAIN, SERVICE_SET_SPOOL, set_spool, schema=SET_SPOOL_SCHEMA)

    async def power_on(call: ServiceCall) -> None:
        await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_power_on(wait=call.data["wait"])

    async def power_off(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        # Pruefung sofort (Fehlermeldung beim Aufrufer), Herunterfahren im Hintergrund.
        force = call.data["force"]
        coordinator.check_power_off(force)
        hass.async_create_task(coordinator.async_power_off(force=force), f"{DOMAIN} power off")

    hass.services.async_register(DOMAIN, SERVICE_POWER_ON, power_on, schema=POWER_ON_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_POWER_OFF, power_off, schema=POWER_OFF_SCHEMA)

    async def queue_add(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        job = {k: v for k, v in call.data.items() if k not in (ATTR_ENTRY, "filename")}
        job["file"] = call.data["filename"].lstrip("/")
        if "mapping" in job:
            job["mapping"] = {str(k): v for k, v in job["mapping"].items()}
        return {"job": coordinator.queue_add(job)}

    async def queue_remove(call: ServiceCall) -> None:
        _coordinator(hass, call.data.get(ATTR_ENTRY)).queue_remove(call.data["job_id"])

    async def queue_move(call: ServiceCall) -> None:
        _coordinator(hass, call.data.get(ATTR_ENTRY)).queue_move(call.data["job_id"], call.data["position"])

    async def queue_start(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator(hass, call.data.get(ATTR_ENTRY))
        try:
            return await coordinator.queue_start(call.data.get("job_id"))
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def queue_clear(call: ServiceCall) -> None:
        _coordinator(hass, call.data.get(ATTR_ENTRY)).queue_clear()

    async def maintenance_done(call: ServiceCall) -> None:
        _coordinator(hass, call.data.get(ATTR_ENTRY)).mark_maintenance(call.data["item"])

    async def backup_timelapses(call: ServiceCall) -> None:
        await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_backup_timelapses()

    hass.services.async_register(DOMAIN, SERVICE_QUEUE_ADD, queue_add, schema=QUEUE_ADD_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_QUEUE_REMOVE, queue_remove, schema=JOB_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_QUEUE_MOVE, queue_move, schema=QUEUE_MOVE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_QUEUE_START, queue_start, schema=QUEUE_START_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, SERVICE_QUEUE_CLEAR, queue_clear, schema=REFRESH_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_MAINTENANCE_DONE, maintenance_done, schema=MAINTENANCE_SCHEMA)
    async def backup_config_service(call: ServiceCall) -> ServiceResponse:
        return await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_backup_config()

    hass.services.async_register(DOMAIN, SERVICE_BACKUP_CONFIG, backup_config_service, schema=REFRESH_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
    async def file_details(call: ServiceCall) -> ServiceResponse:
        return {"file": await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_file_details(call.data["path"])}

    async def delete_file(call: ServiceCall) -> None:
        await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_delete_file(call.data["path"])

    async def move_file(call: ServiceCall) -> None:
        await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_move_file(call.data["source"], call.data["dest"])

    async def self_test(call: ServiceCall) -> ServiceResponse:
        return await _coordinator(hass, call.data.get(ATTR_ENTRY)).async_self_test(call.data.get("language"))

    hass.services.async_register(DOMAIN, "file_details", file_details, schema=PATH_SCHEMA,
                                 supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "delete_file", delete_file, schema=PATH_SCHEMA)
    hass.services.async_register(DOMAIN, "move_file", move_file, schema=MOVE_SCHEMA)
    hass.services.async_register(DOMAIN, "self_test", self_test, schema=SELF_TEST_SCHEMA,
                                 supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_BACKUP_TIMELAPSES, backup_timelapses, schema=REFRESH_SCHEMA)
    return True


def _coordinator(hass: HomeAssistant, entry_id: str | None) -> U1Coordinator:
    entries = [
        e for e in hass.config_entries.async_loaded_entries(DOMAIN)
        if entry_id in (None, e.entry_id)
    ]
    if not entries:
        raise ServiceValidationError("Kein eingerichteter Snapmaker U1 gefunden.")
    if entry_id is None and len(entries) > 1:
        raise ServiceValidationError(
            "Mehrere Drucker eingerichtet – bitte config_entry_id angeben."
        )
    return entries[0].runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: U1ConfigEntry) -> bool:
    client = MoonrakerClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        entry.data.get(CONF_API_KEY) or None,
    )
    coordinator = U1Coordinator(
        hass, entry, client, hass.data[DOMAIN]["thumb_dir"],
        entry.options.get(CONF_FILES_LIMIT, DEFAULT_FILES_LIMIT),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.start_live()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: U1ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: U1ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: U1ConfigEntry) -> None:
    """Letzter Drucker entfernt: Dashboard-Ressource und Kopie unter /local aufraeumen."""
    if not [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]:
        await resource.async_uninstall(hass)
