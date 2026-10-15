"""The coordinator: one instance per printer (config entry)."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from ..api import (
    MoonrakerClient,
    MoonrakerError,
    SpoolmanClient,
)
from ..archive import ARCHIVE_DIR, TimelapseArchive, list_archive, media_root
from ..const import (
    CONF_ARCHIVE,
    CONF_ENERGY_PRICE,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_PRICES,
    CONF_POWER_SWITCH,
    CONF_SPOOLMAN_DEDUCT,
    CONF_SPOOLMAN_URL,
    DEFAULT_ARCHIVE,
    DEFAULT_SPOOLMAN_DEDUCT,
    DOMAIN,
    EVENT_NOTIFY_ACTION,
    FILES_INTERVAL,
    STATS_INTERVAL_S,
    TIMELAPSE_INTERVAL_S,
    UPDATE_INTERVAL,
)
from ..errors import collect_errors
from ..jobs import (
    JobQueue,
)
from ..live import LiveListener
from ..parsing import (
    ACTIVE_PRINT_STATES,
    EXTRUDER_OBJECTS,
    SWITCH_FIELDS,
    energy_kwh,
    migrate_print_state,
    parse_preferences,
    parse_slots,
    parse_tool_changes,
    price_per_kwh,
    print_progress,
    track_print,
)
from ..spools import SpoolManager
from ..stats import Maintenance

_LOGGER = logging.getLogger(__name__)
from .data import U1Data
from .helpers import (
    FILES_PRINTING_S,
    STORE_VERSION,
    head_index,
)
from .jobs import PrintJobMixin
from .media import MediaMixin
from .monitor import PrintMonitorMixin
from .notify import NotifyMixin
from .power import PowerMixin
from .spools import SpoolMixin
from .upkeep import UpkeepMixin

_LOGGER = logging.getLogger(__name__)




class U1Coordinator(SpoolMixin, PrintMonitorMixin, PrintJobMixin, UpkeepMixin, MediaMixin, NotifyMixin, PowerMixin, DataUpdateCoordinator[U1Data]):
    """Central data hub: polls the printer, tracks prints, power, files and media.

    Polling runs every 10 s (30 s while the live subscription is up), the file
    list every 60 s and timelapses every 5 min. Feature logic lives in the
    mixins; this class owns the state, persistence and the poll loop.
    """

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MoonrakerClient,
        thumb_dir: Path,
        files_limit: int,
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry,
            name=f"{DOMAIN} {client.host}", update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.thumb_dir = thumb_dir
        self.files_limit = files_limit
        # (path, modified) -> prepared file entry; metadata and thumbnail
        # are fetched only once per file version.
        self._file_cache: dict[tuple[str, float], dict[str, Any]] = {}
        self._files: list[dict[str, Any]] = []
        self._all_files: list[dict[str, Any]] = []
        self._pinned: set[str] = set()
        self._files_at = 0.0
        self._force_files = True
        self._timelapses: list[dict[str, Any]] = []
        self._timelapses_at = 0.0
        self._force_timelapses = True
        self._store: Store[dict[str, Any]] = Store(
            hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}.print_switches"
        )
        self._print_state: dict[str, Any] = migrate_print_state(None)
        self._counters: dict[str, float | None] = {"switches": None, "energy": None}
        self._prev: U1Data = U1Data()
        self._last_state: str | None = None
        # Auto-off: time of the print end from which switching off is allowed.
        self.auto_off_armed: float | None = None
        self.shutting_down = False
        self.powering_on = False
        self.spools = SpoolManager(None, None, DEFAULT_SPOOLMAN_DEDUCT)
        # Result of the last shutdown: clean | refused: <reason> | skipped
        self.last_shutdown: str | None = None
        self._power_task: asyncio.Task | None = None
        self.queue = JobQueue(None)
        self.maintenance = Maintenance(None)
        self.archive: TimelapseArchive | None = None
        self._archive_task: asyncio.Task | None = None
        self._archive_list: list[dict[str, Any]] = []
        self._archive_running = False
        self._stats: dict[str, Any] | None = None
        self._stats_at = 0.0
        self._force_stats = True
        self._print_hours: float | None = None
        self._errors: list[dict[str, Any]] = []
        self._error_keys: set[str] = set()
        self._starting = False
        self._cpu_count: int | None = None
        self._cpu_tried = False
        # Firmware: installed (from the printer), latest (GitHub, daily)
        self.firmware: dict[str, Any] = {"installed": None, "latest": None}
        self._fw_task: asyncio.Task | None = None
        # Layer view of the running file (layers.py)
        self.layer_view: dict[str, Any] = {"key": None, "status": "none"}
        self._layer_task: asyncio.Task | None = None
        # Live subscription (live.py) and once-per-print events (first layer, almost done)
        self.live = LiveListener(client, self._on_live, self._on_live_state, self.power_is_off)
        self._event_key: Any = None
        self._events_sent: set[str] = set()
        self._last_layer: int | None = None
        self._backup: dict[str, Any] = {}
        self._early_photo: dict[str, Any] | None = None  # photo after the last extrusion
        self._cool_watch: float | None = None  # print ended "complete": watch the bed temperature
        self._idle_since: float | None = None  # idle shutdown
        self._unsub_action = None
        self._backup_task: asyncio.Task | None = None

    # ── Options ─────────────────────────────────────────────────────────────
    @property
    def options(self) -> dict[str, Any]:
        return dict(self.config_entry.options)

    @property
    def power_switch(self) -> str | None:
        return self.options.get(CONF_POWER_SWITCH) or None

    @property
    def energy_price(self) -> float | None:
        """Current energy price per kWh from the price entity."""
        entity = self.options.get(CONF_ENERGY_PRICE)
        st = self.hass.states.get(entity) if isinstance(entity, str) and entity else None
        if st is None:
            return None
        return price_per_kwh(st.state, st.attributes.get(ATTR_UNIT_OF_MEASUREMENT))

    @property
    def filament_prices(self) -> dict[str, float | None]:
        return dict(self.options.get(CONF_FILAMENT_PRICES) or {})

    def power_is_off(self) -> bool:
        if not self.power_switch:
            return False
        state = self.hass.states.get(self.power_switch)
        return state is not None and state.state != STATE_ON and state.state not in ("unavailable", "unknown")

    # ── Lifecycle ───────────────────────────────────────────────────────────
    async def _async_setup(self) -> None:
        """Load persisted state and set up Spoolman, queue, maintenance and archive."""
        stored = await self._store.async_load()
        self._print_state = migrate_print_state(stored)
        url = self.options.get(CONF_SPOOLMAN_URL)
        self.spools = SpoolManager(
            SpoolmanClient(async_get_clientsession(self.hass), url) if url else None,
            stored if isinstance(stored, dict) else None,
            bool(self.options.get(CONF_SPOOLMAN_DEDUCT, DEFAULT_SPOOLMAN_DEDUCT)),
        )
        if self.spools.enabled:
            await self.spools.async_refresh()
        extra = stored if isinstance(stored, dict) else {}
        self.queue = JobQueue(extra.get("queue"))
        self.maintenance = Maintenance(extra.get("maintenance"))
        self._print_hours = extra.get("print_hours")
        self._backup = dict(extra.get("backup") or {})
        self.firmware["latest"] = extra.get("firmware_latest")
        if self.options.get(CONF_ARCHIVE, DEFAULT_ARCHIVE):
            folder = media_root(dict(self.hass.config.media_dirs), self.hass.config.config_dir) / ARCHIVE_DIR
            self.archive = TimelapseArchive(self.client, folder, extra.get("archive"))
            self._archive_list = await self.hass.async_add_executor_job(list_archive, folder)
        # Last file list: show something even with the printer switched off.
        self._files = list(self._print_state.get("files") or [])
        self._timelapses = list(self._print_state.get("timelapses") or [])
        self._prev = self._offline()
        self._unsub_action = self.hass.bus.async_listen(EVENT_NOTIFY_ACTION, self._on_notify_action)

    async def async_shutdown(self) -> None:
        """Cancel background tasks, stop the live subscription and save state."""
        # Flush the delayed save now; otherwise reloading the integration
        # in the middle of a print would lose the baseline.
        await super().async_shutdown()
        if self._power_task and not self._power_task.done():
            self._power_task.cancel()
        if self._archive_task and not self._archive_task.done():
            self._archive_task.cancel()
        if self._layer_task and not self._layer_task.done():
            self._layer_task.cancel()
        if self._fw_task and not self._fw_task.done():
            self._fw_task.cancel()
        if self._backup_task and not self._backup_task.done():
            self._backup_task.cancel()
        await self.live.stop()
        if self._unsub_action:
            self._unsub_action()
            self._unsub_action = None
        await self._store.async_save(self._stored())

    def _save(self, delay: float = 1) -> None:
        self._saved_at = time.monotonic()
        self._store.async_delay_save(self._stored, delay)

    def _stored(self) -> dict[str, Any]:
        """Everything that is persisted in the entry's store."""
        return {
            **self._print_state, **self.spools.as_stored(),
            "queue": self.queue.as_stored(),
            "maintenance": self.maintenance.as_stored(),
            "print_hours": self._print_hours,
            "backup": self._backup,
            "firmware_latest": self.firmware.get("latest"),
            **({"archive": self.archive.as_stored()} if self.archive else {}),
        }

    def _save_periodic(self) -> None:
        """Save running cost/duration roughly once a minute.

        async_delay_save debounces: calling it every 10 s with a 60 s delay
        postpones writing until the print ends. So only trigger it when the
        last save is long enough ago.
        """
        if time.monotonic() - getattr(self, "_saved_at", 0.0) >= 60:
            self._save()

    def request_files_refresh(self) -> None:
        self._force_files = True
        self._force_timelapses = True

    def note_print_started(self, filename: str) -> None:
        """Set the baseline right when we start a print, not at the next poll.

        Counters do not change while idle, so the last values are current.
        """
        self.auto_off_armed = None
        self._print_state, finished, changed = track_print(
            self._print_state, None, filename, self._read_counters(), time.time(),
            pending=True, price=self.energy_price,
        )
        if finished:
            self._finished(finished)
        if changed:
            self._save()

    # ── Polling ─────────────────────────────────────────────────────────────
    def _read_counters(self, switches: int | None = None) -> dict[str, float | None]:
        """Current tool change and energy meter readings."""
        counters = dict(self._counters)
        if switches is not None:
            counters["switches"] = switches
        sensor = self.options.get(CONF_ENERGY_SENSOR)
        st = self.hass.states.get(sensor) if sensor else None
        counters["energy"] = (
            energy_kwh(st.state, st.attributes.get(ATTR_UNIT_OF_MEASUREMENT)) if st else None
        )
        return counters

    def _offline(self) -> U1Data:
        """Data snapshot while the printer is off: keep the last known values."""
        # Re-read firmware/cores after switching on (update on the printer)
        self._cpu_tried = False
        self._cpu_count = None
        prev = self._prev
        return U1Data(
            online=False, slots=prev.slots, preferences=prev.preferences,
            map_table=prev.map_table, files=prev.files or self._files,
            files_updated=prev.files_updated, tool_changes=None, print_state=None,
            prints=self._prints(), history=self._history(),
            timelapses=prev.timelapses or self._timelapses,
            spoolman=self._spoolman_data(prev.slots),
            queue=list(self.queue.jobs), stats=self._stats,
            maintenance=self._maintenance_status(None), print_hours=self._print_hours,
            archive=self._archive_data(), backup=self._backup_data(),
        )

    def _history(self) -> list[dict[str, Any]]:
        return list(self._print_state.get("history") or [])

    def _prints(self) -> dict[str, Any]:
        """Running, active and last print for entities and the card."""
        return {
            "current": print_progress(self._print_state, self._counters),
            "active": self._print_state.get("active"),
            "last": self._print_state.get("last"),
        }

    async def _async_update_data(self) -> U1Data:
        """One poll: printer status, print tracking and all periodic side tasks.

        Order matters: the print is tracked before files, timelapses and
        statistics are refreshed, so a print end is booked with the counters
        of this very poll.
        """
        # Switched off: do not even ask, otherwise every round hangs in a timeout.
        if self.power_is_off():
            self.auto_off_armed = None
            self._prev = self._offline()
            return self._prev
        try:
            status = await self.client.query_objects(
                "print_task_config",
                fields={
                    "print_stats": ("state", "filename", "print_duration", "filament_used", "exception", "info"),
                    "exception_manager": ("exceptions",),
                    "toolhead": ("extruder",),
                    "virtual_sdcard": ("progress", "file_position"),
                    "heater_bed": ("temperature", "target"),
                    **{name: (*SWITCH_FIELDS, "temperature", "target") for name in EXTRUDER_OBJECTS},
                },
            )
        except MoonrakerError as err:
            # Offline is not an integration error: the power switch must remain
            # usable while the printer is off.
            _LOGGER.debug("Printer not reachable: %s", err)
            self._prev = self._offline()
            return self._prev

        ptc = status.get("print_task_config") or {}
        stats = status.get("print_stats") or {}
        print_state = stats.get("state")
        if self.live.connected and print_state:
            # Consistency check: do not leave a missed live update standing
            self.live.status.setdefault("print_stats", {})["state"] = print_state
        tool_changes = parse_tool_changes(status)
        self._counters = self._read_counters(tool_changes["total"] if tool_changes else None)

        self._print_state, finished, changed = track_print(
            self._print_state, print_state, stats.get("filename") or None,
            self._counters, time.time(), price=self.energy_price, stats=stats,
        )
        active = self._print_state.get("active")
        if active and not active.get("meta_done"):
            await self._enrich_active(active)
            self._check_spools(active, list(ptc.get("extruder_map_table") or []))
            changed = True
        if finished:
            self._finished(finished)
        if changed or finished:
            self._save()
        elif active:
            self._save_periodic()
        errors = collect_errors(status)
        self._update_errors(errors)
        paused = self._notify_transition(print_state, stats.get("filename"))
        self._alert_new(errors, print_state, skip=paused)
        vsd = status.get("virtual_sdcard") or {}
        self._print_events(stats, vsd)
        if print_state in ACTIVE_PRINT_STATES:
            # Time profile for remaining time and filament demand: once per print
            self.request_layers(print_state)

        temps = [
            float(t) for t in (
                (status.get(name) or {}).get("temperature")
                for name in (*EXTRUDER_OBJECTS, "heater_bed")
            ) if isinstance(t, (int, float))
        ]

        targets = [
            float(t) for t in (
                (status.get(name) or {}).get("target")
                for name in (*EXTRUDER_OBJECTS, "heater_bed")
            ) if isinstance(t, (int, float))
        ]

        data = U1Data(
            online=True,
            targets=targets,
            slots=parse_slots(ptc),
            preferences=parse_preferences(ptc),
            map_table=list(ptc.get("extruder_map_table") or [])[:8],
            tool_changes=tool_changes,
            print_state=print_state,
            temperatures=temps,
            prints=self._prints(),
            history=self._history(),
            errors=self._errors,
            queue=list(self.queue.jobs),
            active_head=head_index((status.get("toolhead") or {}).get("extruder")),
            progress=(status.get("virtual_sdcard") or {}).get("progress"),
            print_duration=stats.get("print_duration"),
            layer=(stats.get("info") or {}).get("current_layer") if isinstance(stats.get("info"), dict) else None,
            total_layers=(stats.get("info") or {}).get("total_layer") if isinstance(stats.get("info"), dict) else None,
        )
        if print_state in ACTIVE_PRINT_STATES:
            data.remaining = self._remaining(stats, vsd)
            if data.remaining is not None:
                data.eta = time.time() + data.remaining
            if print_state == "printing":
                data.runout = self._check_runout(vsd, data.remaining, ptc)
        self._check_bed_cool((status.get("heater_bed") or {}).get("temperature"), print_state)

        now = time.monotonic()
        # During a print nothing changes in timelapses and history
        # (both arrive with the print end, which triggers a poll anyway),
        # and new files usually come through the card (which reloads right away).
        # So ask rarely: the printer has more important things to do meanwhile.
        printing = print_state in ACTIVE_PRINT_STATES
        files_every = FILES_PRINTING_S if printing else FILES_INTERVAL.total_seconds()
        if self._force_files or now - self._files_at >= files_every:
            try:
                files = await self._load_files()
                if files != self._files:
                    self._print_state["files"] = files
                    self._save(30)
                self._files = files
                self._files_at = now
                self._force_files = False
            except MoonrakerError as err:
                # The file list is secondary: keep the old state.
                _LOGGER.debug("File list not updated: %s", err)
        if self._force_timelapses or (not printing and now - self._timelapses_at >= TIMELAPSE_INTERVAL_S):
            try:
                timelapses = await self._load_timelapses()
                if timelapses != self._timelapses:
                    self._print_state["timelapses"] = timelapses
                    self._save(30)
                self._timelapses = timelapses
                self._timelapses_at = now
                self._force_timelapses = False
                self._start_archive(print_state)
            except MoonrakerError as err:
                _LOGGER.debug("Timelapses not updated: %s", err)
        await self._update_spools(data, ptc)
        data.files = self._files
        data.all_files = self._all_files
        data.files_updated = time.time() if self._files_at else None
        data.timelapses = self._timelapses
        if self._force_stats or (not printing and now - self._stats_at >= STATS_INTERVAL_S):
            await self._update_stats()
        if self._cpu_count is None and not self._cpu_tried:
            self._cpu_tried = True
            try:
                self.firmware["installed"] = await self.client.firmware_version()
            except MoonrakerError:
                pass
            try:
                self._cpu_count = await self.client.cpu_count()
            except MoonrakerError:
                pass
        data.cpu_count = self._cpu_count
        data.stats = self._stats
        data.print_hours = self._print_hours
        data.maintenance = self._maintenance_status(data.tool_changes)
        data.archive = self._archive_data()
        if not printing:
            self._start_backup()
            self._start_firmware_check()
        data.backup = self._backup_data()
        self._prev = data
        self._check_auto_off(data)
        self._check_idle_off(data)
        return data

