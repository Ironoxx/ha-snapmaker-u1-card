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
    filament_gcode,
    flow_gcode,
    park_gcode,
    pick_gcode,
    purifier_gcode,
    purifier_mode_gcode,
)
from ..machine_status import (
    HOME_AXES,
    CommandError,
    feeders,
    filament_check,
    set_gcode,
    switch_gcode,
)
from ..parsing import ACTIVE_PRINT_STATES

_LOGGER = logging.getLogger(__name__)

# Head changes and console commands may home X/Y or heat first: give them time.
LONG_GCODE_S = 180

# 2.2: why loading/unloading is not possible right now (machine_status.filament_check)
FILAMENT_REASONS = {
    "no_feeder": ("Kein Einzug für diesen Kopf erkannt.", "No feeder found for this head."),
    "feeder_error": ("Der Einzug meldet eine Störung.", "The feeder reports a fault."),
    "auto_off": ("Automatisches Laden ist für diesen Kopf ausgeschaltet.", "Automatic loading is switched off for this head."),
    "loaded": ("Im Kopf ist schon Filament.", "There is already filament in the head."),
    "no_filament": ("Am Einzug steckt kein Filament.", "There is no filament at the feeder."),
    "empty": ("Im Kopf ist kein Filament.", "There is no filament in the head."),
}
FILAMENT_GCODE_S = 420


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

    async def async_set_purifier_mode(self, mode: str, target: float | None = None) -> None:
        """Top cover mode (idle, cool, preheat, hot); ``target`` = chamber temperature.

        Without ``target`` the current chamber target is kept, so switching
        between preheat and hot does not lose it.
        """
        purifier = (self.data or self._prev).purifier
        if not purifier or not purifier.get("present"):
            raise HomeAssistantError(tr(self.hass, "Keine Top Cover erkannt.", "No top cover detected."))
        if target is None and mode != "idle":
            target = purifier.get("desired_temp")
        try:
            script = purifier_mode_gcode(mode, target)
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
        # 2.2: check that it happened (the command returns when the firmware is done)
        want = "active" if action == "pick" else "parked"
        state = await self._head_state(head)
        if state is not None and state != want:
            raise HomeAssistantError(tr(
                self.hass, f"Kopf {head + 1} wurde nicht {'aufgenommen' if action == 'pick' else 'abgelegt'}.",
                f"Head {head + 1} was not {'picked' if action == 'pick' else 'parked'}."))

    async def _head_state(self, head: int) -> str | None:
        """active / parked / unknown of physical head 0-3, straight from the printer; None if unknown."""
        name = "extruder" if head == 0 else f"extruder{head}"
        try:
            status = await self.client.query_objects(fields={name: ("state",)})
        except MoonrakerError:
            return None
        state = str((status.get(name) or {}).get("state") or "").upper()
        return {"ACTIVATE": "active", "PARKED": "parked"}.get(state)

    async def _feed_now(self, head: int) -> dict[str, Any] | None:
        """Feeder and head sensor of head 0-3, straight from the printer."""
        side = "left" if head < 2 else "right"
        try:
            status = await self.client.query_objects(f"filament_feed {side}", fields={
                f"filament_motion_sensor e{head}_filament": ("filament_detected", "enabled")})
        except MoonrakerError:
            return None
        return feeders(status).get(head)

    async def async_filament(self, head: int, action: str) -> None:
        """Load or unload the filament of head 0-3 (machine.filament_gcode).

        Locked during a print: the firmware moves the head to the discard position.
        """
        if self.current_print_state() in ACTIVE_PRINT_STATES:
            raise HomeAssistantError(tr(
                self.hass, "Filament laden/entladen ist während eines Drucks gesperrt.",
                "Loading/unloading filament is locked during a print."))
        try:
            steps = filament_gcode(head, action)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        # 2.2: only when it can work (filament waiting at the feeder / in the head)
        machine_feed = ((self.data.machine if self.data else {}) or {}).get("filament_feed") or {}
        reason = filament_check(machine_feed.get(str(head)), action)
        if reason:
            de, en = FILAMENT_REASONS[reason]
            raise ServiceValidationError(tr(self.hass, f"Kopf {head + 1}: {de}", f"Head {head + 1}: {en}"))
        _LOGGER.info("Head %s: filament %s", head + 1, action)
        for script in steps:
            # heating to the filament temperature alone can take minutes
            await self._run_gcode(script, timeout=FILAMENT_GCODE_S)
        # check the result: filament out of / in the head
        feed = await self._feed_now(head)
        inside = feed.get("in_head") if feed else None
        if action == "unload" and inside is True:
            raise HomeAssistantError(tr(self.hass, f"Kopf {head + 1}: Entladen hat nicht geklappt, Filament steckt noch im Kopf.",
                                        f"Head {head + 1}: unloading did not work, the filament is still in the head."))
        if action == "load" and inside is False:
            raise HomeAssistantError(tr(self.hass, f"Kopf {head + 1}: Laden hat nicht geklappt, kein Filament im Kopf.",
                                        f"Head {head + 1}: loading did not work, no filament in the head."))

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

    # ── 2.0: controls without the Moonraker integration ─────────────────────
    async def async_machine_command(self, action: str, target: str | None = None, value: Any = None) -> None:
        """Pause, resume, cancel, emergency stop, homing, setpoints and switches.

        ``set``: target = machine value key (bed_target, extruder1_target, fan_speed,
        speed_factor, <fan>_speed), value = number. ``switch``: target = output_pin_X
        or led_X, value = on/off. ``home``: target = all | x | y | z.
        Only objects the printer reported are accepted.
        """
        objects = list(self._objects or [])
        try:
            if action in ("pause", "resume", "cancel"):
                if self.power_is_off():
                    raise HomeAssistantError(tr(self.hass, "Der Drucker ist ausgeschaltet.", "The printer is switched off."))
                await self.client.print_action(action)
                await self.async_request_refresh()
                return
            if action == "emergency_stop":
                await self.client.emergency_stop()
                await self.async_request_refresh()
                return
            if action == "home":
                axis = str(target or "all").lower()
                if axis not in HOME_AXES:
                    raise CommandError(f"Unknown axis {target!r}")
                if self.current_print_state() in ACTIVE_PRINT_STATES:
                    raise HomeAssistantError(tr(self.hass, "Referenzfahrt ist während des Drucks gesperrt.",
                                                "Homing is locked during a print."))
                await self._run_gcode(HOME_AXES[axis], timeout=LONG_GCODE_S)
                return
            if action == "set":
                script = set_gcode(str(target or ""), value, objects)
            elif action == "switch":
                on = bool(value) if isinstance(value, (bool, int, float)) else str(value).lower() in ("1", "on", "true")
                script = switch_gcode(str(target or ""), on, objects)
            else:
                raise CommandError(f"Unknown action {action!r}")
        except CommandError as err:
            raise ServiceValidationError(str(err)) from err
        except MoonrakerError as err:
            raise HomeAssistantError(tr(self.hass, f"Drucker lehnt ab: {err}", f"Printer refused: {err}")) from err
        await self._run_gcode(script)
