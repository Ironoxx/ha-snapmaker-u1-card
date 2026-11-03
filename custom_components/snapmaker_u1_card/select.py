"""Select entities: entangle detection sensitivity (firmware preference) and the top cover mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .coordinator import U1Coordinator
from .machine import PURIFIER_MODE_IDS
from .parsing import ENTANGLE_SENSITIVITIES
from .sensor import U1Entity, add_when_top_cover


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the entangle sensitivity select; the top cover mode once a cover is detected."""
    async_add_entities([EntangleSensitivity(entry.runtime_data)])
    add_when_top_cover(entry, lambda: async_add_entities([TopCoverMode(entry.runtime_data)]))


class EntangleSensitivity(U1Entity, SelectEntity):
    """low | medium | high; only effective while entangle detection is on."""

    _attr_translation_key = "entangle_sensitivity"
    _attr_entity_category = EntityCategory.CONFIG
    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "pref_entangle_sensitivity")
        self._attr_options = list(ENTANGLE_SENSITIVITIES)

    @property
    def available(self) -> bool:
        return super().available and self.current_option is not None

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.preferences.get("entangle_sensitivity")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_preference("entangle_sensitivity", option)


class TopCoverMode(U1Entity, SelectEntity):
    """Top cover mode: idle, cool (exhaust), preheat or hot (circulation) the chamber."""

    _attr_translation_key = "top_cover_mode"
    _attr_icon = "mdi:air-filter"
    _attr_options = list(PURIFIER_MODE_IDS)  # noqa: RUF012 - fixed list

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "top_cover_mode")

    @property
    def available(self) -> bool:
        p = self.coordinator.data.purifier if self.coordinator.data else None
        return super().available and bool(p and p.get("present"))

    @property
    def current_option(self) -> str | None:
        mode = (self.coordinator.data.purifier or {}).get("mode")
        return mode if mode in PURIFIER_MODE_IDS else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_purifier_mode(option)
