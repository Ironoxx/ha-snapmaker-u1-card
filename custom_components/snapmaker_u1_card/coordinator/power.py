"""Power switch: switching on, clean shutdown, auto-off and idle-off."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError

from ..api import (
    MoonrakerConnectionError,
    MoonrakerError,
)
from ..const import (
    CONF_AUTO_OFF,
    CONF_AUTO_OFF_DELAY,
    CONF_AUTO_OFF_TEMP,
    CONF_IDLE_OFF,
    CONF_SHUTDOWN_HOST,
    DEFAULT_AUTO_OFF_DELAY,
    DEFAULT_AUTO_OFF_TEMP,
    DEFAULT_IDLE_OFF,
    DEFAULT_SHUTDOWN_HOST,
    DOMAIN,
    POWER_ON_TIMEOUT_S,
    SHUTDOWN_MAX_S,
    SHUTDOWN_SETTLE_S,
)
from ..i18n import tr
from ..parsing import (
    ACTIVE_PRINT_STATES,
    EXTRUDER_OBJECTS,
)

_LOGGER = logging.getLogger(__name__)
from .data import U1Data
from .helpers import (
    BOOT_POLL_S,
    POLL_S,
)

_LOGGER = logging.getLogger(__name__)


class PowerMixin:
    """Power switch: switching on, clean shutdown, auto-off and idle-off."""

    def _check_idle_off(self, data: U1Data) -> None:
        """Idle shutdown: x hours without a print and without heating -> shut down, power off.

        The firmware only knows idle_timeout (heaters/motors off) but never
        powers off. Any heater with a target > 0 (e.g. preheating on the
        display) and any print resets the clock.
        """
        hours = float(self.options.get(CONF_IDLE_OFF, DEFAULT_IDLE_OFF) or 0)
        now = time.time()
        if hours <= 0 or not self.power_switch or not data.online:
            self._idle_since = None
            return
        busy = (data.print_state in ACTIVE_PRINT_STATES or self._print_state.get("active")
                or any(t > 0 for t in data.targets) or self.shutting_down or self.powering_on)
        if busy or self._idle_since is None:
            self._idle_since = now
            return
        if now - self._idle_since >= hours * 3600:
            self._idle_since = None
            _LOGGER.info("Idle for %.1f h: switching the printer off", hours)
            self.hass.async_create_task(self.async_power_off(reason="idle"), f"{DOMAIN} idle off")

    def _check_auto_off(self, data: U1Data) -> None:
        """Auto-off after a print: wait for the delay and for all heaters to cool down."""
        if self.auto_off_armed is None or self.shutting_down:
            return
        if (
            data.print_state in ACTIVE_PRINT_STATES
            or self._print_state.get("active")
            or not self.options.get(CONF_AUTO_OFF)
        ):
            self.auto_off_armed = None
            return
        # A target > 0 means somebody is heating up (e.g. a start on the display
        # while print_stats still reports the old state).
        if any(t > 0 for t in data.targets):
            return
        delay = float(self.options.get(CONF_AUTO_OFF_DELAY, DEFAULT_AUTO_OFF_DELAY)) * 60
        limit = float(self.options.get(CONF_AUTO_OFF_TEMP, DEFAULT_AUTO_OFF_TEMP))
        if time.time() - self.auto_off_armed < delay:
            return
        if not data.temperatures or max(data.temperatures) >= limit:
            return
        _LOGGER.info("Auto-off: print finished, all heaters below %s °C", limit)
        self.auto_off_armed = None
        self.hass.async_create_task(self.async_power_off(reason="auto"))

    # ── Power ───────────────────────────────────────────────────────────────
    async def async_power_on(self, wait: bool = False) -> None:
        """Switch on; with ``wait`` block until Klipper is ready."""
        if not self.power_switch:
            raise HomeAssistantError(tr(self.hass, "Kein Netzschalter eingerichtet.", "No power switch configured."))
        if self.shutting_down:
            raise HomeAssistantError(tr(self.hass, "Der Drucker fährt gerade herunter.", "The printer is shutting down."))
        await self.hass.services.async_call(
            "homeassistant", "turn_on", {ATTR_ENTITY_ID: self.power_switch}, blocking=True
        )
        self.async_update_listeners()
        if not wait:
            return
        self.powering_on = True
        self.async_update_listeners()
        try:
            async with asyncio.timeout(POWER_ON_TIMEOUT_S):
                while True:
                    try:
                        if await self.client.klippy_ready():
                            break
                    except MoonrakerError:
                        pass
                    await asyncio.sleep(BOOT_POLL_S)
        except TimeoutError as err:
            raise HomeAssistantError(tr(
                self.hass,
                f"Drucker nach {POWER_ON_TIMEOUT_S // 60} min noch nicht bereit.",
                f"Printer still not ready after {POWER_ON_TIMEOUT_S // 60} min.",
            )) from err
        finally:
            self.powering_on = False
        self.request_files_refresh()
        await self.async_refresh()

    def check_power_off(self, force: bool = False) -> None:
        """Refuse to switch off during a print.

        A running print also counts when the printer briefly does not answer
        (WiFi dropout): the last known state is what matters. ``force``
        overrides this for a crashed printer.
        """
        if not self.power_switch:
            raise HomeAssistantError(tr(self.hass, "Kein Netzschalter eingerichtet.", "No power switch configured."))
        if self.powering_on:
            raise HomeAssistantError(tr(self.hass, "Der Drucker startet gerade. Bitte warten.", "The printer is booting. Please wait."))
        if force:
            return
        data = self.data
        printing = (
            (data is not None and data.print_state in ACTIVE_PRINT_STATES)
            or self._last_state in ACTIVE_PRINT_STATES
            or bool(self._print_state.get("active"))
        )
        if printing:
            raise HomeAssistantError(tr(
                self.hass,
                "Der Drucker druckt gerade oder ein Druck wird gestartet. Druck erst beenden "
                "oder abbrechen. Bei einem abgestürzten Drucker: Dienst power_off mit force: true.",
                "The printer is printing or a print is starting. Finish or cancel the print "
                "first. For a crashed printer: service power_off with force: true.",
            ))

    async def async_power_off(self, reason: str = "user", force: bool = False) -> None:
        """Shut down cleanly first, then cut the power. Runs in the background."""
        self.check_power_off(force)
        if self.shutting_down:
            return
        self.shutting_down = True
        self.auto_off_armed = None
        self.async_update_listeners()
        self._power_task = asyncio.current_task()
        try:
            online = bool(self.data and self.data.online)
            # Ask before shutting down: machine.shutdown would otherwise also end a
            # print that was just started (e.g. on the display).
            if not force and online and await self._printing_now():
                self.last_shutdown = "aborted: print started"
                _LOGGER.warning("Switch-off aborted: the printer is printing or heating")
                return
            if online and self.options.get(CONF_SHUTDOWN_HOST, DEFAULT_SHUTDOWN_HOST):
                await self._shutdown_host()
            else:
                self.last_shutdown = "skipped"
            if not force and await self._printing_now():
                self.last_shutdown = "aborted: print started"
                _LOGGER.warning("Switch-off aborted: the printer is printing")
                return
            await self.hass.services.async_call(
                "homeassistant", "turn_off", {ATTR_ENTITY_ID: self.power_switch}, blocking=True
            )
            _LOGGER.info("Printer switched off (%s)", reason)
        finally:
            self.shutting_down = False
            self.async_update_listeners()

    async def _printing_now(self) -> bool:
        """Last safety check before switching off: is the printer printing or heating?"""
        try:
            status = await self.client.query_objects(
                fields={"print_stats": ("state",), "heater_bed": ("target",),
                        **{name: ("target",) for name in EXTRUDER_OBJECTS}},
            )
        except MoonrakerError:
            return False  # shut down or unreachable
        if (status.get("print_stats") or {}).get("state") in ACTIVE_PRINT_STATES:
            return True
        return any(
            isinstance(t, (int, float)) and t > 0
            for t in ((status.get(n) or {}).get("target") for n in (*EXTRUDER_OBJECTS, "heater_bed"))
        )

    async def _shutdown_host(self) -> None:
        """Send machine.shutdown and wait until the printer stops answering."""
        try:
            await self.client.rpc("machine.shutdown", response_timeout=10)
        except MoonrakerConnectionError:
            pass  # Connection dropped during shutdown: counts as accepted.
        except MoonrakerError as err:
            # Stock firmware: Moonraker calls "sudo systemctl poweroff". If that is
            # missing on the device, power is cut as with the rocker switch.
            _LOGGER.warning("machine.shutdown refused (%s), switching off after %s s", err, SHUTDOWN_SETTLE_S)
            self.last_shutdown = f"refused: {err}"[:200]
            await asyncio.sleep(SHUTDOWN_SETTLE_S)
            return
        self.last_shutdown = "clean"
        deadline = time.monotonic() + SHUTDOWN_MAX_S
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_S)
            try:
                await self.client.klippy_ready()
            except MoonrakerError:
                break  # network is gone: the system is shutting down
        # The OS ends after the network; give the file system some time.
        await asyncio.sleep(SHUTDOWN_SETTLE_S)
