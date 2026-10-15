"""Select entity: sensitivity of the filament entangle detection (firmware preference)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .coordinator import U1Coordinator
from .parsing import ENTANGLE_SENSITIVITIES
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the entangle sensitivity select."""
    async_add_entities([EntangleSensitivity(entry.runtime_data)])


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
