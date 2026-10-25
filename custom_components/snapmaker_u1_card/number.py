"""Number entities: flow (extrusion factor) and the top cover fans.

Flow is Klipper's M221 and may change during a print. The top cover fans only
exist while a cover is plugged in; their entities are added the first time the
firmware reports one (purifier.power_detected), so printers without a cover get
no dead entities.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .coordinator import U1Coordinator
from .machine import FLOW_MAX, FLOW_MIN
from .sensor import U1Entity, add_when_top_cover


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the flow number; the top cover fans once a cover is detected."""
    coordinator = entry.runtime_data
    async_add_entities([FlowNumber(coordinator)])
    add_when_top_cover(entry, lambda: async_add_entities(
        [TopCoverFanNumber(coordinator, "exhaust"), TopCoverFanNumber(coordinator, "inner")]))


class FlowNumber(U1Entity, NumberEntity):
    """Flow in percent (M221); 100 % = as sliced."""

    _attr_translation_key = "flow_factor"
    _attr_icon = "mdi:water-percent"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = FLOW_MIN
    _attr_native_max_value = FLOW_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "flow_factor")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.flow is not None

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.flow

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_flow(value)


class TopCoverFanNumber(U1Entity, NumberEntity):
    """Exhaust or circulation fan of the top cover in percent."""

    _attr_icon = "mdi:fan"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: U1Coordinator, fan: str) -> None:
        super().__init__(coordinator, f"top_cover_{fan}")
        self._fan = fan
        self._attr_translation_key = f"top_cover_{fan}"

    @property
    def available(self) -> bool:
        p = self.coordinator.data.purifier if self.coordinator.data else None
        return super().available and bool(p and p.get("present"))

    @property
    def native_value(self) -> float | None:
        p = self.coordinator.data.purifier or {}
        return p.get(self._fan)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_purifier_fan(self._fan, value)



