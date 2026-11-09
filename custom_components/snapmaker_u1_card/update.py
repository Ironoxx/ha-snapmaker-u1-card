"""U1 firmware version as an update entity (display and hint only).

Installed: ``/machine/system_info`` -> ``product_info.firmware_version``.
Latest: Snapmaker's release commits of the firmware sources on GitHub, once a
day. Updating still happens on the printer (display or Snapmaker app), so the
entity does not offer an install action.
"""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import U1ConfigEntry
from .coordinator import paxx_version_tuple, version_tuple
from .sensor import U1Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the firmware update entity."""
    async_add_entities([FirmwareUpdate(entry.runtime_data)])


class FirmwareUpdate(U1Entity, UpdateEntity):
    """Installed vs. latest firmware; display only, no install action."""
    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "firmware")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None and bool(self.coordinator.firmware.get("installed"))

    def _paxx(self) -> dict | None:
        """paxx12 Extended Firmware with a known version (2.2), else None."""
        fw = self.coordinator.firmware
        paxx = fw.get("paxx") or {}
        return paxx if fw.get("variant") == "paxx12" and paxx.get("version") else None

    @property
    def title(self) -> str:
        return "paxx12 Extended Firmware" if self.coordinator.firmware.get("variant") == "paxx12" else "Snapmaker U1 Firmware"

    @property
    def installed_version(self) -> str | None:
        paxx = self._paxx()
        if paxx:
            return paxx["version"]
        ver = self.coordinator.firmware.get("installed")
        tup = version_tuple(ver)
        return ".".join(map(str, tup)) if tup else ver

    @property
    def latest_version(self) -> str | None:
        installed = self.installed_version
        if self._paxx():
            latest = (self.coordinator.firmware.get("paxx_latest") or {}).get("version")
            if not latest or paxx_version_tuple(latest) <= paxx_version_tuple(installed):
                return installed
            return latest
        latest = (self.coordinator.firmware.get("latest") or {}).get("version")
        if not latest:
            return installed
        # Older than installed (e.g. a beta on the printer): do not show an update
        if installed and version_tuple(latest) <= version_tuple(installed):
            return installed
        return latest

    @property
    def release_url(self) -> str | None:
        if self._paxx():
            return (self.coordinator.firmware.get("paxx_latest") or {}).get("url")
        return (self.coordinator.firmware.get("latest") or {}).get("url")

    @property
    def release_summary(self) -> str | None:
        de = self.hass.config.language.lower().startswith("de")
        if self.coordinator.firmware.get("variant") == "paxx12":
            return ("paxx12 Extended Firmware: Update über die paxx12-Anleitung bzw. /firmware-config/, nicht über das Stock-Update (das würde paxx12 ersetzen)."
                    if de else "paxx12 Extended Firmware: update through paxx12's instructions or /firmware-config/, not the stock update (that would replace paxx12).")
        return ("Installation am Drucker: Display → Einstellungen → Firmware, oder in der Snapmaker-App."
                if de else "Install on the printer: display → settings → firmware, or in the Snapmaker app.")

    @property
    def extra_state_attributes(self) -> dict:
        fw = self.coordinator.firmware
        paxx = fw.get("paxx") or {}
        return {"variant": fw.get("variant"), "base": paxx.get("base") or fw.get("installed"),
                "paxx_version": paxx.get("version"), "profile": paxx.get("profile"),
                "active_slot": paxx.get("slot"), "note": paxx.get("note")}
