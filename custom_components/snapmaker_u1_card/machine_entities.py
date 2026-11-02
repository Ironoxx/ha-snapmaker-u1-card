"""2.0: own entities for the values and controls that used to need the Moonraker integration.

Created per key once the printer reports it (``add_when``), named by
translation keys; one placeholder entity per heater/LED/fan type keeps the
translations small (``translation_placeholders``).
"""

from __future__ import annotations

from typing import Any, ClassVar

from homeassistant.components.button import ButtonEntity
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .coordinator import U1Coordinator
from .machine_status import HEATERS
from .sensor import U1Entity

PRINT_STATES = ["standby", "printing", "paused", "complete", "cancelled", "error"]
HEAD_SUFFIX = {"extruder": 1, "extruder1": 2, "extruder2": 3, "extruder3": 4}


def heater_keys(machine: dict[str, Any]) -> list[str]:
    """Heaters present: "bed" and "extruder…" (key prefix of the machine values)."""
    return [("bed" if h == "heater_bed" else h) for h in HEATERS
            if f"{'bed' if h == 'heater_bed' else h}_temperature" in machine]


class MachineSensor(U1Entity, SensorEntity):
    """All machine values in one entity: the card's data source (replaces ~55 Moonraker entities)."""

    _attr_translation_key = "machine"
    _attr_icon = "mdi:printer-3d"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _unrecorded_attributes = frozenset({"values", "attrs", "entry_id"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "machine")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.machine.get("printer_state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {"values": d.machine, "attrs": d.machine_attrs,
                "entry_id": self.coordinator.config_entry.entry_id}


class TemperatureSensor(U1Entity, SensorEntity):
    """Bed, nozzle or chamber air temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator, f"temp_{key}")
        self._key = key
        if key == "bed":
            self._attr_translation_key = "bed_temperature"
        elif key == "cavity":
            self._attr_translation_key = "cavity_temperature"
        else:
            self._attr_translation_key = "nozzle_temperature"
            self._attr_translation_placeholders = {"head": str(HEAD_SUFFIX[key])}

    @property
    def native_value(self) -> float | None:
        m = self.coordinator.data.machine
        return m.get("cavity_temp") if self._key == "cavity" else m.get(f"{self._key}_temperature")


class ProgressSensor(U1Entity, SensorEntity):
    """Print progress in percent (file position)."""

    _attr_translation_key = "progress"
    _attr_icon = "mdi:progress-clock"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "progress")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.machine.get("progress")


class PrintStateSensor(U1Entity, SensorEntity):
    """Klipper print state: standby, printing, paused, complete, cancelled, error."""

    _attr_translation_key = "print_state"
    _attr_icon = "mdi:printer-3d-nozzle"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PRINT_STATES

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "print_state")

    @property
    def native_value(self) -> str | None:
        state = self.coordinator.data.machine.get("current_print_state")
        return state if state in PRINT_STATES else None


class LayerSensor(U1Entity, SensorEntity):
    """Current layer; total layers as attribute."""

    _attr_translation_key = "current_layer"
    _attr_icon = "mdi:layers-outline"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "current_layer")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.machine.get("current_layer")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"total_layers": self.coordinator.data.machine.get("total_layer")}


class TargetNumber(U1Entity, NumberEntity):
    """Target temperature of the bed or a nozzle (SET_HEATER_TEMPERATURE)."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:thermometer-chevron-up"

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator, f"target_{key}")
        self._key = f"{key}_target"
        attrs = coordinator.data.machine_attrs.get(self._key) or {}
        self._attr_native_max_value = attrs.get("max", 300)
        if key == "bed":
            self._attr_translation_key = "bed_target"
        else:
            self._attr_translation_key = "nozzle_target"
            self._attr_translation_placeholders = {"head": str(HEAD_SUFFIX[key])}

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.machine.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_machine_command("set", self._key, value)


class PercentNumber(U1Entity, NumberEntity):
    """Part cooling fan or speed factor in percent."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator, f"m_{key}")
        self._key = key
        attrs = coordinator.data.machine_attrs.get(key) or {}
        self._attr_native_min_value = attrs.get("min", 0)
        self._attr_native_max_value = attrs.get("max", 100)
        self._attr_translation_key = "part_fan" if key == "fan_speed" else "speed_factor"
        self._attr_icon = "mdi:fan" if key == "fan_speed" else "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.machine.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_machine_command("set", self._key, value)


class MachineButton(U1Entity, ButtonEntity):
    """Pause, resume, cancel, emergency stop, home all axes."""

    ICONS: ClassVar[dict[str, str]] = {"pause": "mdi:pause", "resume": "mdi:play", "cancel": "mdi:stop",
                                       "emergency_stop": "mdi:alert-octagon", "home": "mdi:home"}

    def __init__(self, coordinator: U1Coordinator, action: str) -> None:
        super().__init__(coordinator, f"button_{action}")
        self._action = action
        self._attr_translation_key = f"{action}_print" if action in ("pause", "resume", "cancel") else action
        self._attr_icon = self.ICONS[action]

    async def async_press(self) -> None:
        if self._action == "home":
            await self.coordinator.async_machine_command("home", "all")
        else:
            await self.coordinator.async_machine_command(self._action)


class MachineLight(U1Entity, LightEntity):
    """An LED of the printer (U1: the chamber light), on/off."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}  # noqa: RUF012 - HA reads the set
    _attr_translation_key = "chamber_light"

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        if key != "led_cavity_led":
            self._attr_translation_key = "led"
            self._attr_translation_placeholders = {"name": key[len("led_"):]}

    @property
    def is_on(self) -> bool | None:
        v = self.coordinator.data.machine.get(self._key)
        return None if v is None else v == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_machine_command("switch", self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_machine_command("switch", self._key, False)
