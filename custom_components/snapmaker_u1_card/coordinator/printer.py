"""Printer settings: firmware preferences, filament of a slot and camera wake-up."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from ..api import MoonrakerError
from ..const import CAMERA_WAKE_S, CONF_CAMERA_WAKE, DEFAULT_CAMERA_WAKE
from ..i18n import tr
from ..parsing import ACTIVE_PRINT_STATES, filament_gcode, preference_gcode

_LOGGER = logging.getLogger(__name__)


class PrinterSettingsMixin:
    """Printer settings: firmware preferences, filament of a slot and camera wake-up."""

    async def async_set_preference(self, key: str, value: Any) -> None:
        """Change a firmware preference (auto-replenish, entangle detection, LED ...).

        These are stored by the firmware itself and may change during a print.
        """
        try:
            script = preference_gcode(key, value)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self._run_gcode(script)

    async def async_set_filament(self, slot: int, ftype: str, sub_type: str | None, vendor: str | None,
                                 color: str | None = None, force: bool = False) -> None:
        """Set material, vendor and colour of a slot (0-3) by hand, e.g. for spools without RFID."""
        if self.current_print_state() in ACTIVE_PRINT_STATES:
            raise HomeAssistantError(tr(
                self.hass, "Filament kann während eines Drucks nicht geändert werden.",
                "The filament cannot be changed during a print."))
        slots = (self.data or self._prev).slots
        if 0 <= slot < len(slots) and slots[slot].get("official") and not force:
            raise HomeAssistantError(tr(
                self.hass, "Offizielle Snapmaker-Spule (RFID): nur mit force überschreibbar.",
                "Official Snapmaker spool (RFID): can only be overwritten with force."))
        try:
            script = filament_gcode(slot, ftype, sub_type or "", vendor or "", color, force)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self._run_gcode(script)

    async def _run_gcode(self, script: str) -> None:
        if self.power_is_off():
            raise HomeAssistantError(tr(self.hass, "Der Drucker ist ausgeschaltet.", "The printer is switched off."))
        try:
            await self.client.gcode(script)
        except MoonrakerError as err:
            raise HomeAssistantError(tr(self.hass, f"Drucker lehnt ab: {err}", f"Printer refused: {err}")) from err
        await self.async_request_refresh()

    # ── Camera wake-up ─────────────────────────────────────────────────────
    def _start_camera_wake(self) -> None:
        """Start the periodic camera.start_monitor call if enabled in the options."""
        if self.options.get(CONF_CAMERA_WAKE, DEFAULT_CAMERA_WAKE) == "off":
            return
        self._unsub_wake = async_track_time_interval(
            self.hass, self._camera_wake_tick, timedelta(seconds=CAMERA_WAKE_S),
            name="snapmaker_u1_card camera wake",
        )

    @callback
    def _camera_wake_tick(self, _now: Any) -> None:
        mode = self.options.get(CONF_CAMERA_WAKE, DEFAULT_CAMERA_WAKE)
        data = self.data
        if mode == "off" or data is None or not data.online or self.power_is_off():
            return
        if mode == "printing" and self.current_print_state() not in ACTIVE_PRINT_STATES:
            return
        if self._wake_busy:
            return
        self._wake_busy = True
        self.hass.async_create_background_task(self._camera_wake(), "snapmaker_u1_card camera wake")

    async def async_camera_wake_once(self) -> None:
        """One-off camera.start_monitor on request of the card (image stale or stream missing).

        Ignored while the printer is off/offline or a wake call is still running;
        at most one call every 5 s, no matter how many cards ask.
        """
        data = self.data
        if data is None or not data.online or self.power_is_off() or self._wake_busy:
            return
        now = time.monotonic()
        if now - self._wake_last < 5:
            return
        self._wake_last = now
        self._wake_busy = True
        await self._camera_wake()

    async def _camera_wake(self) -> None:
        try:
            await self.client.camera_wake()
        except MoonrakerError as err:
            _LOGGER.debug("camera.start_monitor failed: %s", err)
        finally:
            self._wake_busy = False
