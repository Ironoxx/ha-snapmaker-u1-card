"""Switches: the printer's power switch and the firmware preferences.

Power: the entity mirrors any switch (Shelly, KNX, Zigbee ...). Switching off
through it is blocked during a print and shuts the printer down cleanly first.
Automations should therefore switch this entity, not the switch behind it.

Preferences: auto-replenish, replenish ignoring colour, entangle detection and
LED off after the print. The firmware stores them itself (print_task_config).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import (
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import U1ConfigEntry
from .const import (
    CONF_AUTO_OFF,
    CONF_AUTO_OFF_DELAY,
    CONF_AUTO_OFF_TEMP,
    CONF_AUTO_ON,
    CONF_ENERGY_SENSOR,
    CONF_POWER_SENSOR,
    CONF_POWER_SWITCH,
    DEFAULT_AUTO_OFF_DELAY,
    DEFAULT_AUTO_OFF_TEMP,
)
from .coordinator import U1Coordinator
from .parsing import PRINTER_PREFERENCES
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the firmware preference switches and the power switch if one is configured."""
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = [PreferenceSwitch(coordinator, key) for key in PRINTER_PREFERENCES]
    if entry.options.get(CONF_POWER_SWITCH):
        entities.append(PowerSwitch(coordinator))
    async_add_entities(entities)


class PreferenceSwitch(U1Entity, SwitchEntity):
    """One firmware preference (stored on the printer, changeable during a print)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator, f"pref_{key}")
        self._key = key
        self._attr_translation_key = key

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.preferences.get(self._key) is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.preferences.get(self._key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_preference(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_preference(self._key, False)


class PowerSwitch(U1Entity, SwitchEntity):
    """Mirrors the configured switch and shuts the printer down before power-off."""
    _attr_translation_key = "power"
    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "power")
        self._source = coordinator.power_switch

    async def async_added_to_hass(self) -> None:
        """Follow state changes of the underlying switch."""
        await super().async_added_to_hass()
        watched = [e for e in (self._source, self.coordinator.options.get(CONF_POWER_SENSOR)) if e]
        self.async_on_remove(
            async_track_state_change_event(self.hass, watched, self._source_changed)
        )

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        """Underlying switch changed: update state and poll the printer."""
        self.async_write_ha_state()
        if event.data["entity_id"] == self._source:
            old, new = event.data["old_state"], event.data["new_state"]
            if (old and old.state) != (new and new.state):
                # On: poll the printer again soon. Off: report offline right away.
                self.hass.async_create_task(self.coordinator.async_request_refresh())

    @property
    def available(self) -> bool:
        st = self.hass.states.get(self._source) if self._source else None
        return st is not None and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    @property
    def is_on(self) -> bool | None:
        st = self.hass.states.get(self._source)
        return None if st is None else st.state == STATE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_power_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Validate right away (error shown in the frontend), shut down in the background.
        self.coordinator.check_power_off()
        self.hass.async_create_task(self.coordinator.async_power_off())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator
        opts = c.options
        return {
            "source": self._source,
            "power_sensor": opts.get(CONF_POWER_SENSOR),
            "energy_sensor": opts.get(CONF_ENERGY_SENSOR),
            "energy_price": c.energy_price,
            "shutting_down": c.shutting_down,
            "powering_on": c.powering_on,
            "last_shutdown": c.last_shutdown,
            "auto_on": bool(opts.get(CONF_AUTO_ON)),
            "auto_off": bool(opts.get(CONF_AUTO_OFF)),
            "auto_off_pending": c.auto_off_armed is not None,
            "auto_off_temp": opts.get(CONF_AUTO_OFF_TEMP, DEFAULT_AUTO_OFF_TEMP),
            "auto_off_delay": opts.get(CONF_AUTO_OFF_DELAY, DEFAULT_AUTO_OFF_DELAY),
            "entry_id": c.config_entry.entry_id,
        }
