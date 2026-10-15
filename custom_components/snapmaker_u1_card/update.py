"""Firmware-Stand des U1 als Update-Entitaet (nur Anzeige und Hinweis).

Installiert: ``/machine/system_info`` -> ``product_info.firmware_version``.
Neueste: Snapmakers Release-Commits der Firmware-Quellen auf GitHub, einmal
am Tag. Installiert wird weiter am Drucker (Display oder Snapmaker-App);
die Entitaet bietet deshalb keine Installation an.
"""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .coordinator import version_tuple
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FirmwareUpdate(entry.runtime_data)])


class FirmwareUpdate(U1Entity, UpdateEntity):
    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_title = "Snapmaker U1 Firmware"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "firmware")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None and bool(self.coordinator.firmware.get("installed"))

    @property
    def installed_version(self) -> str | None:
        ver = self.coordinator.firmware.get("installed")
        tup = version_tuple(ver)
        return ".".join(map(str, tup)) if tup else ver

    @property
    def latest_version(self) -> str | None:
        latest = (self.coordinator.firmware.get("latest") or {}).get("version")
        installed = self.installed_version
        if not latest:
            return installed
        # Aelter als installiert (z. B. Beta am Drucker): kein Update anzeigen
        if installed and version_tuple(latest) <= version_tuple(installed):
            return installed
        return latest

    @property
    def release_url(self) -> str | None:
        return (self.coordinator.firmware.get("latest") or {}).get("url")

    @property
    def release_summary(self) -> str | None:
        de = self.hass.config.language.lower().startswith("de")
        return ("Installation am Drucker: Display → Einstellungen → Firmware, oder in der Snapmaker-App."
                if de else "Install on the printer: display → settings → firmware, or in the Snapmaker app.")
