"""2.0: the printer's LEDs (U1: chamber light) as own lights."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .machine_entities import MachineLight
from .sensor import add_machine


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add one light per reported LED."""
    coordinator = entry.runtime_data
    add_machine(entry, lambda m: {k: (lambda k=k: MachineLight(coordinator, k)) for k in m if k.startswith("led_")},
                async_add_entities)
