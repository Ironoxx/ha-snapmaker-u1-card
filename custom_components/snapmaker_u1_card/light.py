"""2.0: the printer's LEDs (U1: chamber light) as own lights."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .machine_entities import MachineLight
from .sensor import add_when


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add one light per reported LED."""
    coordinator = entry.runtime_data
    add_when(entry, lambda d: any(k.startswith("led_") for k in d.machine), lambda: async_add_entities(
        [MachineLight(coordinator, k) for k in coordinator.data.machine if k.startswith("led_")]))
