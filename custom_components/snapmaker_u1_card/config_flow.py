"""Setup through the UI (config flow and options flow)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import SectionConfig, section
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    MoonrakerClient,
    MoonrakerConnectionError,
    MoonrakerError,
    SpoolmanClient,
)
from .const import (
    CAMERA_WAKE_MODES,
    CONF_ALMOST_DONE,
    CONF_API_KEY,
    CONF_ARCHIVE,
    CONF_ARCHIVE_DAYS,
    CONF_ARCHIVE_KEEP,
    CONF_ARCHIVE_MAX,
    CONF_AUTO_OFF,
    CONF_AUTO_OFF_DELAY,
    CONF_AUTO_OFF_TEMP,
    CONF_AUTO_ON,
    CONF_BACKUP,
    CONF_BED_COOL,
    CONF_CAMERA,
    CONF_CAMERA_WAKE,
    CONF_ENERGY_PRICE,
    CONF_ENERGY_PRICE_FIXED,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_PRICES,
    CONF_FILES_LIMIT,
    CONF_IDLE_OFF,
    CONF_LIVE_BUDGET,
    CONF_LIVE_IMAGE,
    CONF_MAINTENANCE,
    CONF_MAINTENANCE_MONTHS,
    CONF_NOTIFY,
    CONF_NOTIFY_EVENTS,
    CONF_NOTIFY_URL,
    CONF_POWER_SENSOR,
    CONF_POWER_SWITCH,
    CONF_SHUTDOWN_HOST,
    CONF_SPOOLMAN_DEDUCT,
    CONF_SPOOLMAN_LOW,
    CONF_SPOOLMAN_URL,
    DEFAULT_ALMOST_DONE,
    DEFAULT_ARCHIVE,
    DEFAULT_ARCHIVE_DAYS,
    DEFAULT_ARCHIVE_KEEP,
    DEFAULT_ARCHIVE_MAX,
    DEFAULT_AUTO_OFF,
    DEFAULT_AUTO_OFF_DELAY,
    DEFAULT_AUTO_OFF_TEMP,
    DEFAULT_AUTO_ON,
    DEFAULT_BACKUP,
    DEFAULT_BED_COOL,
    DEFAULT_CAMERA_WAKE,
    DEFAULT_FILES_LIMIT,
    DEFAULT_IDLE_OFF,
    DEFAULT_LIVE_BUDGET,
    DEFAULT_LIVE_IMAGE,
    DEFAULT_NOTIFY_EVENTS,
    DEFAULT_PORT,
    DEFAULT_SHUTDOWN_HOST,
    DEFAULT_SPOOLMAN_DEDUCT,
    DEFAULT_SPOOLMAN_LOW,
    DOMAIN,
    LIVE_IMAGES,
    NOTIFY_EVENTS,
)
from .parsing import FILAMENT_PRICE_KEYS
from .stats import MAINTENANCE_ITEMS, MAINTENANCE_MONTHS

SEC_POWER, SEC_NOTIFY, SEC_FILAMENT, SEC_FILES = "power", "notify", "filament", "files"
SEC_SPOOLMAN = "spoolman"
SEC_TIMELAPSE, SEC_MAINT = "timelapse", "maintenance"
PRICE_FIELDS = [f"price_{k.lower()}" for k in (*FILAMENT_PRICE_KEYS, "OTHER")]
MAINT_FIELDS = [f"maint_{k}" for k in MAINTENANCE_ITEMS]
MAINT_MONTH_FIELDS = [f"maint_m_{k}" for k in MAINTENANCE_ITEMS]
INT_FIELDS = (CONF_FILES_LIMIT, CONF_AUTO_OFF_TEMP, CONF_AUTO_OFF_DELAY, CONF_SPOOLMAN_LOW, CONF_ARCHIVE_KEEP, CONF_ARCHIVE_MAX, CONF_ARCHIVE_DAYS,
              CONF_ALMOST_DONE, CONF_BED_COOL, CONF_IDLE_OFF)


def _box(minimum: float, maximum: float, step: float, unit: str | None = None) -> selector.NumberSelector:
    """Number selector shown as an input box."""
    config = selector.NumberSelectorConfig(
        min=minimum, max=maximum, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _options_schema(notify_services: list[str]) -> vol.Schema:
    """Options form, grouped into collapsible sections."""
    power = vol.Schema(
        {
            # The printer's power switch: Shelly, KNX, Zigbee plug ... anything
            # that can be switched on and off.
            vol.Optional(CONF_POWER_SWITCH): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "light", "input_boolean"])
            ),
            vol.Optional(CONF_POWER_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            vol.Optional(CONF_ENERGY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Optional(CONF_ENERGY_PRICE): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
            ),
            vol.Optional(CONF_ENERGY_PRICE_FIXED): _box(0, 5, 0.001, "€/kWh"),
            vol.Required(CONF_SHUTDOWN_HOST, default=DEFAULT_SHUTDOWN_HOST): selector.BooleanSelector(),
            vol.Required(CONF_AUTO_ON, default=DEFAULT_AUTO_ON): selector.BooleanSelector(),
            vol.Required(CONF_AUTO_OFF, default=DEFAULT_AUTO_OFF): selector.BooleanSelector(),
            vol.Required(CONF_AUTO_OFF_TEMP, default=DEFAULT_AUTO_OFF_TEMP): _box(30, 100, 1, "°C"),
            vol.Required(CONF_AUTO_OFF_DELAY, default=DEFAULT_AUTO_OFF_DELAY): _box(0, 240, 1, "min"),
            vol.Required(CONF_IDLE_OFF, default=DEFAULT_IDLE_OFF): _box(0, 72, 1, "h"),
        }
    )
    notify = vol.Schema(
        {
            vol.Optional(CONF_NOTIFY): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=notify_services, multiple=True, custom_value=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_NOTIFY_EVENTS, default=DEFAULT_NOTIFY_EVENTS): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(NOTIFY_EVENTS), multiple=True,
                    translation_key="notify_events",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_ALMOST_DONE, default=DEFAULT_ALMOST_DONE): _box(1, 120, 1, "min"),
            vol.Required(CONF_LIVE_BUDGET, default=DEFAULT_LIVE_BUDGET): _box(10, 400, 1),
            vol.Required(CONF_LIVE_IMAGE, default=DEFAULT_LIVE_IMAGE): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(LIVE_IMAGES), translation_key=CONF_LIVE_IMAGE,
                                              mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Optional(CONF_NOTIFY_URL): selector.TextSelector(),
            vol.Required(CONF_BED_COOL, default=DEFAULT_BED_COOL): _box(20, 60, 1, "°C"),
            vol.Optional(CONF_CAMERA): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="camera")
            ),
            vol.Required(CONF_CAMERA_WAKE, default=DEFAULT_CAMERA_WAKE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=list(CAMERA_WAKE_MODES), translation_key="camera_wake",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )
    filament = vol.Schema({vol.Optional(key): _box(0, 500, 0.01, "€/kg") for key in PRICE_FIELDS})
    spoolman = vol.Schema(
        {
            # Empty = spool management off; none of it shows up in the card/integration.
            # Text instead of a URL field: an address without http:// is allowed (api.py adds it)
            vol.Optional(CONF_SPOOLMAN_URL): selector.TextSelector(),
            vol.Required(CONF_SPOOLMAN_DEDUCT, default=DEFAULT_SPOOLMAN_DEDUCT): selector.BooleanSelector(),
            vol.Required(CONF_SPOOLMAN_LOW, default=DEFAULT_SPOOLMAN_LOW): _box(0, 1000, 10, "g"),
        }
    )
    files = vol.Schema(
        {
            vol.Required(CONF_FILES_LIMIT, default=DEFAULT_FILES_LIMIT): _box(1, 100, 1),
            vol.Required(CONF_BACKUP, default=DEFAULT_BACKUP): selector.BooleanSelector(),
        }
    )
    timelapse = vol.Schema(
        {
            vol.Required(CONF_ARCHIVE, default=DEFAULT_ARCHIVE): selector.BooleanSelector(),
            vol.Required(CONF_ARCHIVE_KEEP, default=DEFAULT_ARCHIVE_KEEP): _box(0, 100, 1),
            vol.Required(CONF_ARCHIVE_MAX, default=DEFAULT_ARCHIVE_MAX): _box(0, 1000, 1),
            vol.Required(CONF_ARCHIVE_DAYS, default=DEFAULT_ARCHIVE_DAYS): _box(0, 3650, 1, "d"),
        }
    )
    maint_fields: dict[Any, Any] = {}
    for k, v in MAINTENANCE_ITEMS.items():
        maint_fields[vol.Required(f"maint_{k}", default=v)] = _box(0, 5000, 1, "h")
        maint_fields[vol.Required(f"maint_m_{k}", default=MAINTENANCE_MONTHS.get(k, 0))] = _box(0, 36, 1, "mo")
    maintenance = vol.Schema(maint_fields)
    return vol.Schema(
        {
            vol.Required(SEC_POWER): section(power, SectionConfig(collapsed=False)),
            vol.Required(SEC_NOTIFY): section(notify, SectionConfig(collapsed=True)),
            vol.Required(SEC_FILAMENT): section(filament, SectionConfig(collapsed=True)),
            # Sections are always Required and without a default: a default ({}) on
            # the section replaces the pre-filled values of its fields in the frontend
            # (compute-initial-ha-form-data takes "default" before the children).
            # The result would be "Not all required fields are filled in" until you
            # expand the section and touch every field once.
            vol.Required(SEC_SPOOLMAN): section(spoolman, SectionConfig(collapsed=True)),
            vol.Required(SEC_FILES): section(files, SectionConfig(collapsed=True)),
            vol.Required(SEC_TIMELAPSE): section(timelapse, SectionConfig(collapsed=True)),
            vol.Required(SEC_MAINT): section(maintenance, SectionConfig(collapsed=True)),
        }
    )


def flatten_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Form sections -> flat options; filament prices as a dict."""
    flat: dict[str, Any] = {}
    for value in user_input.values():
        if isinstance(value, dict):
            flat.update(value)
    prices = {}
    for key in PRICE_FIELDS:
        value = flat.pop(key, None)
        if value not in (None, ""):
            prices[key.removeprefix("price_").upper()] = float(value)
    flat[CONF_FILAMENT_PRICES] = prices
    months = {}
    for key in MAINT_MONTH_FIELDS:
        value = flat.pop(key, None)
        if value not in (None, ""):
            months[key.removeprefix("maint_m_")] = int(value)
    if months:
        flat[CONF_MAINTENANCE_MONTHS] = months
    maint = {}
    for key in MAINT_FIELDS:
        value = flat.pop(key, None)
        if value not in (None, ""):
            maint[key.removeprefix("maint_")] = int(value)
    if maint:
        flat[CONF_MAINTENANCE] = maint
    for key in INT_FIELDS:
        if key in flat:
            flat[key] = int(flat[key])
    # Store with the "notify." prefix so the selector recognises it.
    flat[CONF_NOTIFY] = [t if t.startswith("notify.") else f"notify.{t}" for t in flat.get(CONF_NOTIFY) or []]
    return flat


def nest_options(options: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Stored options -> suggested values per section."""
    opts = dict(options)
    if isinstance(opts.get(CONF_LIVE_IMAGE), bool):  # before 1.6.0: on/off
        opts[CONF_LIVE_IMAGE] = "camera" if opts[CONF_LIVE_IMAGE] else "off"
    prices = opts.pop(CONF_FILAMENT_PRICES, {}) or {}
    for key, value in prices.items():
        opts[f"price_{key.lower()}"] = value
    for key, value in (opts.pop(CONF_MAINTENANCE, {}) or {}).items():
        opts[f"maint_{key}"] = value
    for key, value in (opts.pop(CONF_MAINTENANCE_MONTHS, {}) or {}).items():
        opts[f"maint_m_{key}"] = value
    groups = {
        SEC_POWER: (CONF_POWER_SWITCH, CONF_POWER_SENSOR, CONF_ENERGY_SENSOR, CONF_ENERGY_PRICE, CONF_ENERGY_PRICE_FIXED,
                    CONF_SHUTDOWN_HOST, CONF_AUTO_ON, CONF_AUTO_OFF, CONF_AUTO_OFF_TEMP,
                    CONF_AUTO_OFF_DELAY, CONF_IDLE_OFF),
        SEC_NOTIFY: (CONF_NOTIFY, CONF_NOTIFY_EVENTS, CONF_ALMOST_DONE, CONF_LIVE_BUDGET, CONF_LIVE_IMAGE, CONF_NOTIFY_URL, CONF_BED_COOL, CONF_CAMERA, CONF_CAMERA_WAKE),
        SEC_FILAMENT: tuple(PRICE_FIELDS),
        SEC_SPOOLMAN: (CONF_SPOOLMAN_URL, CONF_SPOOLMAN_DEDUCT, CONF_SPOOLMAN_LOW),
        SEC_FILES: (CONF_FILES_LIMIT, CONF_BACKUP),
        SEC_TIMELAPSE: (CONF_ARCHIVE, CONF_ARCHIVE_KEEP, CONF_ARCHIVE_MAX, CONF_ARCHIVE_DAYS),
        SEC_MAINT: tuple(f for k in MAINTENANCE_ITEMS for f in (f"maint_{k}", f"maint_m_{k}")),
    }
    return {sec: {k: opts[k] for k in keys if k in opts} for sec, keys in groups.items()}


def _notify_services(hass: Any) -> list[str]:
    return sorted(f"notify.{name}" for name in hass.services.async_services_for_domain("notify")
                  if name not in ("notify", "send_message", "persistent_notification"))


async def _validate_options(hass: Any, flat: dict[str, Any]) -> str | None:
    """Validation shared by initial setup and options; returns an error key or None."""
    if (flat.get(CONF_AUTO_OFF) or flat.get(CONF_AUTO_ON)) and not flat.get(CONF_POWER_SWITCH):
        return "auto_needs_switch"
    if flat.get(CONF_NOTIFY) and not all(
        hass.services.has_service("notify", t.removeprefix("notify.")) for t in flat[CONF_NOTIFY]
    ):
        return "unknown_notify"
    if flat.get(CONF_SPOOLMAN_URL):
        try:
            info = await SpoolmanClient(async_get_clientsession(hass), flat[CONF_SPOOLMAN_URL]).info()
        except MoonrakerError:
            return "spoolman_unreachable"
        if not info.get("version"):
            return "spoolman_unreachable"
    else:
        flat.pop(CONF_SPOOLMAN_URL, None)
    return None


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Connection form (host, port, API key)."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Optional(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): str,
        }
    )


class U1ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: connect to the printer, then all options in a second step."""
    VERSION = 1

    async def _probe(self, data: dict[str, Any]) -> str | None:
        """Check that Moonraker answers; returns an error key or None."""
        client = MoonrakerClient(
            async_get_clientsession(self.hass), data[CONF_HOST], data[CONF_PORT],
            data.get(CONF_API_KEY) or None,
        )
        try:
            status = await client.query_objects("print_task_config")
        except MoonrakerConnectionError:
            return "cannot_connect"
        except MoonrakerError:
            return "not_u1"
        return None if "print_task_config" in status else "not_u1"

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First step: printer address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().removeprefix("http://").rstrip("/")
            await self.async_set_unique_id(user_input[CONF_HOST].lower())
            self._abort_if_unique_id_configured()
            error = await self._probe(user_input)
            if error is None:
                self._data = user_input
                return await self.async_step_settings()
            errors["base"] = error
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}), errors=errors
        )

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Second setup step: all settings right away (later under "Configure")."""
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = flatten_options(user_input)
            error = await _validate_options(self.hass, flat)
            if error is None:
                return self.async_create_entry(
                    title=f"Snapmaker U1 ({self._data[CONF_HOST]})", data=self._data, options=flat
                )
            errors["base"] = error
        schema = _options_schema(_notify_services(self.hass))
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="settings", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the printer address of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip().removeprefix("http://").rstrip("/")
            error = await self._probe(user_input)
            if error is None:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure", data_schema=_schema(user_input or dict(entry.data)), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return U1OptionsFlow()


class U1OptionsFlow(OptionsFlow):
    """Everything else in one place: power, notifications, prices, Spoolman, files."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show and store the options form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = flatten_options(user_input)
            error = await _validate_options(self.hass, flat)
            if error is None:
                return self.async_create_entry(data=flat)
            errors["base"] = error
        services = _notify_services(self.hass)
        values = user_input if user_input is not None else nest_options(self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            # Suggested values instead of defaults: this way an entity
            # can also be removed again.
            data_schema=self.add_suggested_values_to_schema(_options_schema(services), values),
            errors=errors,
        )
