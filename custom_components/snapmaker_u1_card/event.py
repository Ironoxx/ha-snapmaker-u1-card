"""2.4: print events as an event entity, for own automations.

Fires on every event the notifications know (finished, cancelled, error, paused,
message during a print, first layer, almost done, spool low / runs out, part
removable, maintenance due, chamber warm) – independent of whether
notifications are set up. Trigger: "Event entity … event type is complete".
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .const import NOTIFY_EVENTS
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the print event entity."""
    async_add_entities([PrintEvent(entry.runtime_data)])


class PrintEvent(U1Entity, EventEntity):
    """One entity, one event type per notification event."""

    _attr_translation_key = "print_event"
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "print_event")
        self._attr_event_types = list(NOTIFY_EVENTS)

    @property
    def available(self) -> bool:
        return True  # events also come while the printer is off (e.g. part removable, maintenance)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.add_event_listener(self._fire))

    @callback
    def _fire(self, event_type: str, attrs: dict[str, Any]) -> None:
        if event_type not in self._attr_event_types:
            return
        self._trigger_event(event_type, attrs)
        self.async_write_ha_state()
