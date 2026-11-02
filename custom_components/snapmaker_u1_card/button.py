"""2.0: pause, resume, cancel, emergency stop and homing as own buttons."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .machine_entities import MachineButton
from .sensor import add_when


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the buttons once the printer has answered."""
    coordinator = entry.runtime_data
    add_when(entry, lambda d: bool(d.machine), lambda: async_add_entities(
        [MachineButton(coordinator, a) for a in ("pause", "resume", "cancel", "emergency_stop", "home")]))
