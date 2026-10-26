"""Sensors: loaded filaments, individual slots, print files, statistics."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_HOST,
    EntityCategory,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import U1ConfigEntry
from .const import (
    CONF_ENERGY_PRICE,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_PRICES,
    DOMAIN,
    VERSION,
    VIDEO_URL,
)
from .coordinator import U1Coordinator
from .machine import PURIFIER_MODES
from .parsing import average_kw, estimate_cost


async def async_setup_entry(
    hass: HomeAssistant, entry: U1ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add all sensors of one printer."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [FilamentsSensor(coordinator), FilesSensor(coordinator)]
    entities += [SlotSensor(coordinator, i) for i in range(4)]
    entities += [ToolChangesSensor(coordinator), PrintToolChangesSensor(coordinator)]
    entities += [HistorySensor(coordinator), TimelapsesSensor(coordinator)]
    entities += [QueueSensor(coordinator), StatisticsSensor(coordinator), MaintenanceSensor(coordinator),
                 ErrorsSensor(coordinator), RemainingSensor(coordinator), FinishSensor(coordinator),
                 BedMeshSensor(coordinator)]
    if entry.options.get(CONF_ENERGY_SENSOR):
        entities.append(PrintEnergySensor(coordinator))
    if entry.options.get(CONF_ENERGY_PRICE) or entry.options.get(CONF_FILAMENT_PRICES):
        entities.append(PrintCostSensor(coordinator))
    async_add_entities(entities)
    add_when_top_cover(entry, lambda: async_add_entities([TopCoverSensor(coordinator)]))
    add_when_chamber(entry, lambda: async_add_entities([ChamberSensor(coordinator)]))


def add_when_top_cover(entry: U1ConfigEntry, add: Callable[[], None]) -> None:
    """Call ``add`` once the firmware reports a plugged-in top cover (now or later).

    Printers without a cover get no entities that would only ever be unavailable.
    Once added, the entities stay (unavailable while the cover is unplugged).
    """
    add_when(entry, lambda d: bool(d.purifier and d.purifier.get("present")), add)


def add_when_chamber(entry: U1ConfigEntry, add: Callable[[], None]) -> None:
    """Call ``add`` once a chamber heater (Panda Breath / DragonBreath) shows up."""
    add_when(entry, lambda d: d.chamber is not None, add)


def add_when(entry: U1ConfigEntry, test: Callable[[Any], bool], add: Callable[[], None]) -> None:
    """Call ``add`` once ``test(data)`` is true, now or on a later update."""
    coordinator = entry.runtime_data
    done = False

    def present() -> bool:
        data = coordinator.data
        return bool(data and test(data))

    @callback
    def check() -> None:
        nonlocal done
        if done or not present():
            return
        done = True
        add()

    if present():
        check()
        return
    entry.async_on_unload(coordinator.async_add_listener(check))


class U1Entity(CoordinatorEntity[U1Coordinator]):
    """Base class: device info and availability for all entities of a printer."""
    _attr_has_entity_name = True

    def __init__(self, coordinator: U1Coordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Snapmaker U1 Card",
            manufacturer="Snapmaker",
            model="U1",
            sw_version=VERSION,
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def available(self) -> bool:
        # Printer values only while it is reachable.
        data = self.coordinator.data
        return super().available and data is not None and data.online


class PrintRecordEntity(U1Entity):
    """Values of the running or last print; available even with the printer off."""

    _key = ""

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    def _value(self) -> float | None:
        """Value of the running print, else of the last one."""
        prints = self.coordinator.data.prints
        current = (prints.get("current") or {}).get(self._key)
        if current is not None:
            return current
        last = prints.get("last") or {}
        return last.get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        prints = self.coordinator.data.prints
        active, last = prints.get("active"), prints.get("last")
        attrs: dict[str, Any] = {"in_progress": bool(active and not active.get("pending"))}
        if attrs["in_progress"]:
            attrs.update(file=active.get("file"), started=_iso(active.get("started")))
        elif last:
            attrs.update(
                file=last.get("file"), result=last.get("result"),
                started=_iso(last.get("started")), ended=_iso(last.get("ended")),
            )
        if last:
            attrs[f"last_{self._key}"] = last.get(self._key)
        return attrs


class FilamentsSensor(U1Entity, SensorEntity):
    """All four slots in one attribute; the card's main data source."""

    _attr_translation_key = "filaments"
    _attr_icon = "mdi:printer-3d-nozzle"
    _unrecorded_attributes = frozenset({"slots", "map_table", "preferences", "entry_id", "live", "spoolman",
                                        "active_head", "cpu_count", "runout", "head_states"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "filaments")

    @property
    def available(self) -> bool:
        # The last known state stays visible for the print dialog (auto-on).
        data = self.coordinator.data
        return super(U1Entity, self).available and data is not None and bool(data.slots)

    @property
    def native_value(self) -> int:
        return sum(1 for s in self.coordinator.data.slots if s["loaded"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self.coordinator.data
        return {
            "slots": d.slots,
            "map_table": d.map_table,
            "preferences": d.preferences,
            "live": d.online,
            # active head according to the firmware (toolhead.extruder), 0-3
            "active_head": d.active_head,
            # printer CPU cores: puts the system load (load average) into context
            "cpu_count": d.cpu_count,
            # spool runs out during the print: {head: {minutes, takeover}}
            "runout": {str(k): v for k, v in d.runout.items()},
            # per head: parked | active | unknown (park detector); [] = not reported
            "head_states": d.head_states,
            # only with Spoolman configured: spool per head + spool list
            **({"spoolman": d.spoolman} if d.spoolman is not None else {}),
            "entry_id": self.coordinator.config_entry.entry_id,
        }


class SlotSensor(U1Entity, SensorEntity):
    """One slot for automations ('slot 2 empty', 'PLA loaded')."""

    _attr_translation_key = "slot"
    _attr_icon = "mdi:printer-3d-nozzle-outline"

    def __init__(self, coordinator: U1Coordinator, index: int) -> None:
        super().__init__(coordinator, f"slot_{index + 1}")
        self._index = index
        self._attr_translation_placeholders = {"slot": str(index + 1)}

    @property
    def _slot(self) -> dict[str, Any]:
        return self.coordinator.data.slots[self._index]

    @property
    def native_value(self) -> str:
        slot = self._slot
        if not slot["loaded"]:
            return "leer"
        return " ".join(p for p in (slot["type"], slot["sub_type"]) if p) or "unbekannt"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = dict(self._slot)
        sm = self.coordinator.data.spoolman
        if sm is not None:
            spool = (sm.get("slots") or {}).get(str(self._index))
            attrs["spool"] = spool
            attrs["spool_remaining"] = spool.get("remaining_weight") if spool else None
        return attrs


class FilesSensor(U1Entity, SensorEntity):
    """Newest print files including filaments and thumbnail."""

    _attr_translation_key = "files"
    _attr_icon = "mdi:file-document-multiple-outline"
    _unrecorded_attributes = frozenset({"files", "entry_id", "updated", "all", "cost_basis", "version", "stream_url"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "files")

    @property
    def available(self) -> bool:
        # Last known list even with the printer switched off (auto-on).
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.files)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        coord = self.coordinator
        prices, kwh, kw = coord.filament_prices, coord.energy_price, average_kw(coord.data.history)
        files = [
            {**f, "cost": cost} if (cost := estimate_cost(f, prices, kwh, kw)) else f
            for f in coord.data.files
        ]
        return {
            "files": files,
            "cost_basis": {"kwh_price": kwh, "avg_kw": kw},
            # all printable files (name, date, size only): search and folders
            "all": coord.data.all_files,
            "updated": self.coordinator.data.files_updated,
            "entry_id": self.coordinator.config_entry.entry_id,
            # the card compares it with its own version (outdated browser cache)
            "version": VERSION,
            # direct MJPEG stream in the LAN (card option camera_direct)
            "stream_url": f"http://{self.coordinator.config_entry.data[CONF_HOST]}/webcam/?action=stream",
        }


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, UTC).isoformat() if ts else None


class ToolChangesSensor(U1Entity, SensorEntity):
    """Tool changes since delivery or counter reset, per head as attributes."""

    _attr_translation_key = "tool_changes"
    _attr_icon = "mdi:swap-horizontal-circle-outline"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _unrecorded_attributes = frozenset({"heads", "maintenance_threshold"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "tool_changes")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.tool_changes is not None

    @property
    def native_value(self) -> int | None:
        tc = self.coordinator.data.tool_changes
        return tc["total"] if tc else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tc = self.coordinator.data.tool_changes or {}
        return {
            "heads": tc.get("heads", []),
            "maintenance_threshold": tc.get("maintenance_threshold"),
        }


class PrintToolChangesSensor(PrintRecordEntity, SensorEntity):
    """Changes in the running print, otherwise in the last recorded print."""

    _attr_translation_key = "tool_changes_print"
    _attr_icon = "mdi:swap-horizontal"
    _key = "switches"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "tool_changes_print")

    @property
    def native_value(self) -> int | None:
        return self._value()


class PrintEnergySensor(PrintRecordEntity, SensorEntity):
    """Energy of the running or last print from the energy meter."""

    _attr_translation_key = "print_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3
    _key = "energy"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "print_energy")

    @property
    def native_value(self) -> float | None:
        return self._value()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        attrs["price"] = self.coordinator.energy_price
        return attrs


class PrintCostSensor(PrintRecordEntity, SensorEntity):
    """Cost of the running print (energy so far) or the last one (energy + filament)."""

    _attr_translation_key = "print_cost"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash"
    _key = "total_cost"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "print_cost")
        self._attr_native_unit_of_measurement = coordinator.hass.config.currency

    @property
    def native_value(self) -> float | None:
        prints = self.coordinator.data.prints
        active = prints.get("active")
        if active and not active.get("pending"):
            cost = (prints.get("current") or {}).get("energy_cost")
            return None if cost is None else round(cost, 2)
        return (prints.get("last") or {}).get("total_cost")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        last = self.coordinator.data.prints.get("last") or {}
        attrs.update(
            energy_cost=last.get("energy_cost"),
            filament_cost=last.get("filament_cost"),
            filament_g=last.get("filament_g"),
        )
        return attrs


class HistorySensor(U1Entity, SensorEntity):
    """Recent prints with duration, result, consumption and cost."""

    _attr_translation_key = "history"
    _attr_icon = "mdi:history"
    _unrecorded_attributes = frozenset({"prints", "entry_id"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "history")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.history)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        prints = []
        for item in self.coordinator.data.history:
            entry = dict(item)
            for key in ("started", "ended"):
                entry[key] = _iso(entry.get(key))
            prints.append(entry)
        return {"prints": prints, "entry_id": self.coordinator.config_entry.entry_id}


class TimelapsesSensor(U1Entity, SensorEntity):
    """Timelapses on the printer; playback goes through the integration's proxy."""

    _attr_translation_key = "timelapses"
    _attr_icon = "mdi:filmstrip-box-multiple"
    _unrecorded_attributes = frozenset({"videos", "entry_id", "url", "archive", "playable"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "timelapses")

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.timelapses)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        entry_id = self.coordinator.config_entry.entry_id
        return {
            "videos": self.coordinator.data.timelapses,
            "url": f"{VIDEO_URL}/{entry_id}",
            # Playback only while the printer is reachable (the proxy fetches from it)
            "playable": bool(self.coordinator.data.online and not self.coordinator.power_is_off()),
            "entry_id": entry_id,
            # backup in the media folder (None = off)
            "archive": self.coordinator.data.archive,
        }


class OfflineEntity(U1Entity):
    """Values owned by the integration itself: present even with the printer off."""

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


class QueueSensor(OfflineEntity, SensorEntity):
    """Planned print jobs (always started by hand, after clearing the bed)."""

    _attr_translation_key = "queue"
    _attr_icon = "mdi:tray-full"
    _unrecorded_attributes = frozenset({"jobs", "entry_id"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "queue")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.queue)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        jobs = [{**j, "added": _iso(j.get("added"))} for j in self.coordinator.data.queue]
        return {"jobs": jobs, "entry_id": self.coordinator.config_entry.entry_id}


class StatisticsSensor(OfflineEntity, SensorEntity):
    """Total print hours; monthly values as attributes (from Moonraker's history)."""

    _attr_translation_key = "statistics"
    _attr_icon = "mdi:chart-bar"
    _attr_native_unit_of_measurement = "h"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _unrecorded_attributes = frozenset({"months", "totals", "top_files", "materials", "colors", "entry_id"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "statistics")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.print_hours

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = self.coordinator.data.stats or {}
        return {
            "months": stats.get("months") or [],
            "totals": stats.get("totals") or {},
            "top_files": stats.get("top_files") or [],
            "materials": stats.get("materials") or [],
            "colors": stats.get("colors") or [],
            "entry_id": self.coordinator.config_entry.entry_id,
        }


class MaintenanceSensor(OfflineEntity, SensorEntity):
    """Number of maintenance items due; details as attributes."""

    _attr_translation_key = "maintenance"
    _attr_icon = "mdi:wrench-clock"
    _unrecorded_attributes = frozenset({"items", "entry_id"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "maintenance")

    @property
    def native_value(self) -> int:
        return sum(1 for i in self.coordinator.data.maintenance if i.get("due"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = [{**i, "done_at": _iso(i.get("done_at"))} if "done_at" in i else i
                 for i in self.coordinator.data.maintenance]
        backup = self.coordinator.data.backup
        if backup:
            backup = {**backup, "saved_at": _iso(backup.get("saved_at")), "checked_at": _iso(backup.get("checked_at"))}
        return {"items": items, "config_backup": backup, "entry_id": self.coordinator.config_entry.entry_id}


class ErrorsSensor(U1Entity, SensorEntity):
    """Open firmware messages (count); plain text per message as attributes."""

    _attr_translation_key = "errors"
    _attr_icon = "mdi:alert-circle-outline"
    _unrecorded_attributes = frozenset({"errors"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "errors")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.errors)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"errors": self.coordinator.data.errors}


class RemainingSensor(U1Entity, SensorEntity):
    """Remaining time: the file's time profile, calibrated with the real print duration."""

    _attr_translation_key = "remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "remaining")

    @property
    def native_value(self) -> float | None:
        r = self.coordinator.data.remaining
        return round(r / 60, 1) if r is not None and self.coordinator.data.print_state in ("printing", "paused") else None


class FinishSensor(U1Entity, SensorEntity):
    """Expected end of the print."""

    _attr_translation_key = "finish"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:flag-checkered"

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "finish")

    @property
    def native_value(self) -> datetime | None:
        d = self.coordinator.data
        if d.eta is None or d.print_state not in ("printing", "paused"):
            return None
        # rounded to the minute: otherwise a new state on every poll
        return datetime.fromtimestamp(round(d.eta / 60) * 60, UTC)


class BedMeshSensor(U1Entity, SensorEntity):
    """Spread of the loaded bed mesh (max - min); the probed points are in the attributes."""

    _attr_translation_key = "bed_mesh"
    _attr_icon = "mdi:grid"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_suggested_display_precision = 3
    _unrecorded_attributes = frozenset({"matrix", "mesh_min", "mesh_max", "rows", "cols"})

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "bed_mesh")

    @property
    def native_value(self) -> float | None:
        mesh = self.coordinator.data.bed_mesh
        return mesh["range"] if mesh else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        mesh = self.coordinator.data.bed_mesh
        if not mesh:
            return {}
        return {k: v for k, v in mesh.items() if k != "range"}


class TopCoverSensor(U1Entity, SensorEntity):
    """Top cover (purifier): chamber mode; fans, filter hours and target in the attributes."""

    _attr_translation_key = "top_cover"
    _attr_icon = "mdi:air-filter"
    _attr_device_class = SensorDeviceClass.ENUM
    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "top_cover")
        self._attr_options = [*PURIFIER_MODES.values(), "unknown"]

    @property
    def available(self) -> bool:
        p = self.coordinator.data.purifier if self.coordinator.data else None
        return super().available and bool(p and p.get("present"))

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data.purifier or {}).get("mode")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        p = self.coordinator.data.purifier or {}
        return {k: p.get(k) for k in ("exhaust", "inner", "inner_rpm", "filter_hours", "desired_temp")}


class ChamberSensor(U1Entity, SensorEntity):
    """Chamber temperature of the chamber heater; target, power and device in the attributes."""

    _attr_translation_key = "chamber_heater"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "°C"
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: U1Coordinator) -> None:
        super().__init__(coordinator, "chamber_heater")

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.chamber is not None

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data.chamber or {}).get("temperature")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.coordinator.data.chamber or {}
        return {k: c.get(k) for k in ("target", "power", "filter", "label", "min", "max")}

