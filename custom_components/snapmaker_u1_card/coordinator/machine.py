"""Machine controls: flow, top cover fans, picking/parking heads and the G-code console."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from ..api import MoonrakerError
from ..i18n import tr
from ..machine import (
    blocked_while_printing,
    chamber_filter_gcode,
    chamber_gcode,
    console_lines,
    console_responses,
    flow_gcode,
    park_gcode,
    pick_gcode,
    purifier_gcode,
)
from ..parsing import ACTIVE_PRINT_STATES

_LOGGER = logging.getLogger(__name__)

# Head changes and console commands may home X/Y or heat first: give them time.
LONG_GCODE_S = 180


class MachineMixin:
    """Machine controls: flow, top cover fans, picking/parking heads and the G-code console."""

    async def async_set_flow(self, percent: float) -> None:
        """Flow (extrusion factor) in percent; allowed during a print, that is its purpose."""
        try:
            script = flow_gcode(percent)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._run_gcode(script)

    async def async_set_purifier_fan(self, fan: str, percent: float) -> None:
        """Exhaust or inner fan of the top cover; only with a detected cover."""
        purifier = (self.data or self._prev).purifier
        if not purifier or not purifier.get("present"):
            raise HomeAssistantError(tr(
                self.hass, "Keine Top Cover erkannt.", "No top cover detected."))
        try:
            script = purifier_gcode(fan, percent)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._run_gcode(script)

    async def async_set_chamber(self, target: float) -> None:
        """Chamber heater target (0 = off); allowed during a print."""
        if not self.chamber_heater:
            raise HomeAssistantError(tr(self.hass, "Keine Kammerheizung gefunden.", "No chamber heater found."))
        try:
            script = chamber_gcode(self.chamber_heater, target)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._run_gcode(script)

    async def async_set_chamber_filter(self, on: bool) -> None:
        if not self.chamber_heater:
            raise HomeAssistantError(tr(self.hass, "Keine Kammerheizung gefunden.", "No chamber heater found."))
        try:
            script = chamber_filter_gcode(self.chamber_heater, on)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        await self._run_gcode(script)

    async def async_tool_change(self, head: int, action: str) -> None:
        """Take head 0-3 (``pick``) or put the head on the carriage back (``park``).

        Locked during a print: the firmware would move the head out of the part.
        """
        if self.current_print_state() in ACTIVE_PRINT_STATES:
            raise HomeAssistantError(tr(
                self.hass, "Kopfwechsel ist während eines Drucks gesperrt.",
                "Changing heads is locked during a print."))
        data = self.data or self._prev
        states = data.head_states or []
        if action == "park":
            active = [i for i, st in enumerate(states) if st == "active"]
            if not active and states and all(st == "parked" for st in states):
                return  # nothing on the carriage
            head = active[0] if active else (data.active_head if data.active_head is not None else head)
            script = park_gcode(head)
        elif action == "pick":
            if not 0 <= head <= 3:
                raise ServiceValidationError(f"head: 1-4 ({head + 1})")
            script = pick_gcode(head)
        else:
            raise ServiceValidationError("action: pick | park")
        _LOGGER.info("Head %s: %s", action, script)
        await self._run_gcode(script, timeout=LONG_GCODE_S)

    async def async_console(self, script: str) -> dict[str, Any]:
        """Run console G-code and return the printer's responses.

        During a print only tuning commands are allowed (machine.PRINT_SAFE_COMMANDS).
        A refusal by the firmware is part of the answer, not an exception, so the
        console can show it like a response.
        """
        try:
            lines = console_lines(script)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        if self.current_print_state() in ACTIVE_PRINT_STATES:
            blocked = blocked_while_printing(lines)
            if blocked:
                raise ServiceValidationError(tr(
                    self.hass, f"Während des Drucks gesperrt: {', '.join(blocked)}",
                    f"Locked during a print: {', '.join(blocked)}"))
        if self.power_is_off():
            raise HomeAssistantError(tr(self.hass, "Der Drucker ist ausgeschaltet.", "The printer is switched off."))
        text = "\n".join(lines)
        error: str | None = None
        try:
            await self.client.gcode(text, timeout=LONG_GCODE_S)
        except MoonrakerError as err:
            error = str(err)
        try:
            responses = console_responses(await self.client.gcode_store(100), text)
        except MoonrakerError as err:
            _LOGGER.debug("gcode store not readable: %s", err)
            responses = []
        _LOGGER.info("Console: %s -> %s", text.replace("\n", " | "), error or "ok")
        await self.async_request_refresh()
        return {"script": text, "ok": error is None, "error": error, "responses": responses}
