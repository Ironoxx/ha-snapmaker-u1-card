"""Diagnostic entity: is the live subscription to Moonraker up (live.py)?"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the live connection diagnostic entity."""
    async_add_entities([LiveConnection(entry.runtime_data)])


class LiveConnection(U1Entity, BinarySensorEntity):
    """On = Moonraker pushes changes immediately; off = polling every 10 s only."""

    _attr_translation_key = "live"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "live")

    @property
    def available(self) -> bool:
        # Also when the printer is switched off: then simply "disconnected".
        return self.coordinator.data is not None

    @property
    def is_on(self) -> bool:
        return self.coordinator.live.connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        since = self.coordinator.live.connected_since
        interval = self.coordinator.update_interval
        return {
            "connected_since": datetime.fromtimestamp(since, UTC).isoformat() if since else None,
            "poll_interval_s": interval.total_seconds() if interval else None,
            "entry_id": self.coordinator.config_entry.entry_id,
        }
