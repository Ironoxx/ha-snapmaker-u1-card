"""Datenabgleich mit dem Drucker, Druckerfassung, Strom und Auto-Aus."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import posixpath
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import (
    MoonrakerClient,
    MoonrakerConnectionError,
    MoonrakerError,
    SpoolmanClient,
)
from .archive import ARCHIVE_DIR, TimelapseArchive, list_archive, media_root
from .backup import backup_config, list_snapshots
from .const import (
    BACKUP_DIR,
    CONF_ALMOST_DONE,
    CONF_ARCHIVE,
    CONF_ARCHIVE_KEEP,
    CONF_AUTO_OFF,
    CONF_AUTO_OFF_DELAY,
    CONF_AUTO_OFF_TEMP,
    CONF_BACKUP,
    CONF_BED_COOL,
    CONF_CAMERA,
    CONF_ENERGY_PRICE,
    CONF_ENERGY_SENSOR,
    CONF_FILAMENT_PRICES,
    CONF_IDLE_OFF,
    CONF_MAINTENANCE,
    CONF_NOTIFY,
    CONF_NOTIFY_EVENTS,
    CONF_POWER_SWITCH,
    CONF_SHUTDOWN_HOST,
    CONF_SPOOLMAN_DEDUCT,
    CONF_SPOOLMAN_LOW,
    CONF_SPOOLMAN_URL,
    DEFAULT_ALMOST_DONE,
    DEFAULT_ARCHIVE,
    DEFAULT_ARCHIVE_KEEP,
    DEFAULT_AUTO_OFF_DELAY,
    DEFAULT_AUTO_OFF_TEMP,
    DEFAULT_BACKUP,
    DEFAULT_BED_COOL,
    DEFAULT_IDLE_OFF,
    DEFAULT_NOTIFY_EVENTS,
    DEFAULT_SHUTDOWN_HOST,
    DEFAULT_SPOOLMAN_DEDUCT,
    DEFAULT_SPOOLMAN_LOW,
    DOMAIN,
    EVENT_NOTIFY_ACTION,
    EVENT_PRINT_FINISHED,
    FILES_INTERVAL,
    FIRMWARE_CHECK_S,
    FIRMWARE_REPOS,
    HISTORY_SIZE,
    LIVE_INTERVAL,
    POWER_ON_TIMEOUT_S,
    RUNOUT_WARN_MIN,
    SHUTDOWN_MAX_S,
    SHUTDOWN_SETTLE_S,
    SPOOLMAN_INTERVAL_S,
    STATS_INTERVAL_S,
    THUMB_URL,
    TIMELAPSE_INTERVAL_S,
    UPDATE_INTERVAL,
)
from .errors import collect_errors, error_text
from .jobs import (
    JobQueue,
    add_layer_pauses,
    is_pause_copy,
    original_file,
    pause_file_name,
)
from .layers import estimate_remaining, parse_layers, timeline_at
from .live import LiveListener
from .parsing import (
    ACTIVE_PRINT_STATES,
    EXTRUDER_OBJECTS,
    PRINTABLE_SUFFIXES,
    SWITCH_FIELDS,
    TIMELAPSE_SKIP_ROOTS,
    describe_file,
    energy_kwh,
    grams_per_slot,
    map_table_option,
    migrate_print_state,
    parse_file_filaments,
    parse_preferences,
    parse_slots,
    parse_tool_changes,
    pick_thumbnail,
    pick_timelapses,
    price_per_kwh,
    print_progress,
    suggest_mapping,
    summarize_print,
    thumbnail_source,
    track_print,
)
from .spools import SpoolManager
from .stats import MAINTENANCE_ITEMS, Maintenance, build_stats

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
POLL_S = 3  # Abfragetakt beim Herunterfahren
EARLY_PHOTO_DELAY_S = 2  # Ergebnisfoto: Vorlauf der Dateiposition vor der Bewegung
FILES_PRINTING_S = 600  # Dateiliste waehrend eines Drucks
BOOT_POLL_S = 5  # Abfragetakt beim Hochfahren
AUTO_OFF_RESULTS = ("complete", "cancelled")

RESULT_TEXT = {
    "complete": "Druck fertig",
    "cancelled": "Druck abgebrochen",
    "error": "Druckfehler",
    "paused": "Druck pausiert",
    "queue": "Nächster Auftrag wartet",
    "alert": "Meldung vom Drucker",
    "first_layer": "Erste Schicht fertig",
    "almost_done": "Gleich fertig",
    "spool_low": "Filament reicht nicht",
    "spool_runout": "Spule läuft gleich leer",
    "bed_cool": "Teil entnehmbar",
    "cancel_confirm": "Druck abbrechen?",
}
RESULT_TEXT_EN = {
    "complete": "Print finished",
    "cancelled": "Print cancelled",
    "error": "Print error",
    "paused": "Print paused",
    "queue": "Next job waiting",
    "alert": "Printer message",
    "first_layer": "First layer done",
    "almost_done": "Almost done",
    "spool_low": "Not enough filament",
    "spool_runout": "Spool about to run out",
    "bed_cool": "Part ready to remove",
    "cancel_confirm": "Cancel print?",
}


@dataclass
class U1Data:
    online: bool = False
    slots: list[dict[str, Any]] = field(default_factory=list)
    preferences: dict[str, bool] = field(default_factory=dict)
    map_table: list[int] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)
    files_updated: float | None = None
    # Werkzeugwechsel: None, wenn die Firmware keine Zaehler liefert.
    tool_changes: dict[str, Any] | None = None
    print_state: str | None = None
    temperatures: list[float] = field(default_factory=list)
    targets: list[float] = field(default_factory=list)
    # {"current": {switches, energy, energy_cost}, "active": {...} | None, "last": {...} | None}
    prints: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    timelapses: list[dict[str, Any]] = field(default_factory=list)
    # Spoolman: None, wenn nicht eingerichtet
    spoolman: dict[str, Any] | None = None
    # Offene Firmware-Ausnahmen im Klartext (errors.py)
    errors: list[dict[str, Any]] = field(default_factory=list)
    queue: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] | None = None
    maintenance: list[dict[str, Any]] = field(default_factory=list)
    print_hours: float | None = None
    archive: dict[str, Any] | None = None
    # Aktiver Kopf laut Firmware (toolhead.extruder), 0-3; None = unbekannt
    active_head: int | None = None
    cpu_count: int | None = None
    all_files: list[dict[str, Any]] = field(default_factory=list)
    backup: dict[str, Any] | None = None
    # Laufender Druck: Dateifortschritt 0-1, Dauer s, Schicht (fuer Sprachausgabe)
    progress: float | None = None
    # Restzeit in s (Zeitprofil der Datei, sonst Dateifortschritt) und Fertig-Zeitpunkt
    remaining: float | None = None
    eta: float | None = None
    # Spule laeuft im Druck leer: {kopf: {"minutes", "takeover"}}
    runout: dict[int, dict[str, Any]] = field(default_factory=dict)
    print_duration: float | None = None
    layer: int | None = None
    total_layers: int | None = None


class U1Coordinator(DataUpdateCoordinator[U1Data]):
    """Drucker alle 10 s, Dateiliste alle 60 s, Zeitraffer alle 5 min."""

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
        # (path, modified) -> aufbereiteter Dateieintrag; Metadaten und
        # Vorschaubild werden je Dateiversion nur einmal geholt.
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
        # Auto-Aus: Zeitpunkt des Druckendes, ab dem abgeschaltet werden darf.
        self.auto_off_armed: float | None = None
        self.shutting_down = False
        self.powering_on = False
        self.spools = SpoolManager(None, None, DEFAULT_SPOOLMAN_DEDUCT)
        # Ergebnis des letzten Herunterfahrens: clean | refused: <grund> | skipped
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
        # Firmware: installiert (vom Drucker), neueste (GitHub, taeglich)
        self.firmware: dict[str, Any] = {"installed": None, "latest": None}
        self._fw_task: asyncio.Task | None = None
        # Schichtansicht der laufenden Datei (layers.py)
        self.layer_view: dict[str, Any] = {"key": None, "status": "none"}
        self._layer_task: asyncio.Task | None = None
        # Live-Abo (live.py) und Ereignisse je Druck (erste Schicht, gleich fertig)
        self.live = LiveListener(client, self._on_live, self._on_live_state, self.power_is_off)
        self._event_key: Any = None
        self._events_sent: set[str] = set()
        self._last_layer: int | None = None
        self._backup: dict[str, Any] = {}
        self._early_photo: dict[str, Any] | None = None  # Foto nach der letzten Bahn
        self._cool_watch: float | None = None  # Druckende "fertig": Bett beobachten
        self._idle_since: float | None = None  # Leerlauf-Abschaltung
        self._unsub_action = None
        self._backup_task: asyncio.Task | None = None

    # ── Optionen ────────────────────────────────────────────────────────────
    @property
    def options(self) -> dict[str, Any]:
        return dict(self.config_entry.options)

    @property
    def power_switch(self) -> str | None:
        return self.options.get(CONF_POWER_SWITCH) or None

    @property
    def energy_price(self) -> float | None:
        """Aktueller Strompreis je kWh aus der Preis-Entitaet."""
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

    # ── Lebenszyklus ────────────────────────────────────────────────────────
    async def _async_setup(self) -> None:
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
        # Letzte Dateiliste: auch bei ausgeschaltetem Drucker etwas anzeigen.
        self._files = list(self._print_state.get("files") or [])
        self._timelapses = list(self._print_state.get("timelapses") or [])
        self._prev = self._offline()
        self._unsub_action = self.hass.bus.async_listen(EVENT_NOTIFY_ACTION, self._on_notify_action)

    async def async_shutdown(self) -> None:
        # Verzoegertes Speichern sofort erledigen, sonst ginge beim Neuladen
        # der Integration mitten im Druck die Basis verloren.
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
        """Laufende Kosten/Dauer etwa minuetlich sichern.

        async_delay_save entprellt: wer es alle 10 s mit 60 s Verzoegerung
        ruft, verschiebt das Schreiben bis zum Druckende. Deshalb nur
        ausloesen, wenn die letzte Sicherung laenger her ist.
        """
        if time.monotonic() - getattr(self, "_saved_at", 0.0) >= 60:
            self._save()

    def request_files_refresh(self) -> None:
        self._force_files = True
        self._force_timelapses = True

    def note_print_started(self, filename: str) -> None:
        """Basis sofort beim eigenen Druckstart setzen, nicht erst beim naechsten Abruf.

        Im Leerlauf aendern sich die Zaehler nicht, die letzten Werte sind also aktuell.
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

    # ── Abfrage ─────────────────────────────────────────────────────────────
    def _read_counters(self, switches: int | None = None) -> dict[str, float | None]:
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
        # Nach dem Einschalten Firmware/Kerne neu lesen (Update am Drucker)
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
        return {
            "current": print_progress(self._print_state, self._counters),
            "active": self._print_state.get("active"),
            "last": self._print_state.get("last"),
        }

    async def _async_update_data(self) -> U1Data:
        # Ausgeschaltet: gar nicht erst fragen, sonst haengt jede Runde im Timeout.
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
            # Offline ist kein Fehler der Integration: der Netzschalter muss
            # auch bei ausgeschaltetem Drucker bedienbar bleiben.
            _LOGGER.debug("Drucker nicht erreichbar: %s", err)
            self._prev = self._offline()
            return self._prev

        ptc = status.get("print_task_config") or {}
        stats = status.get("print_stats") or {}
        print_state = stats.get("state")
        if self.live.connected and print_state:
            # Abgleich: verpasste Aenderung im Live-Abo nicht stehen lassen
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
            # Zeitprofil fuer Restzeit und Filamentbedarf: einmal je Druck
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
        # Waehrend eines Drucks aendert sich an Zeitraffern und Historie nichts
        # (beides kommt erst mit dem Druckende, das die Abfrage ohnehin anstoesst),
        # und neue Dateien kommen meist ueber die Karte (die sofort neu laedt).
        # Also nur selten fragen: der Drucker hat waehrenddessen Wichtigeres zu tun.
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
                # Dateiliste ist Nebensache: alter Stand bleibt stehen.
                _LOGGER.debug("Dateiliste nicht aktualisiert: %s", err)
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
                _LOGGER.debug("Zeitraffer nicht aktualisiert: %s", err)
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

    # ── Spoolman ────────────────────────────────────────────────────────────
    async def _update_spools(self, data: U1Data, ptc: dict[str, Any]) -> None:
        mgr = self.spools
        if mgr.enabled:
            if mgr.due(SPOOLMAN_INTERVAL_S) and await mgr.async_refresh():
                self._mark_booked()
                self._save()
            if mgr.assign(data.slots):
                self._save()
        # Was der laufende Druck braucht, um ihn spaeter je Kopf abzubuchen:
        # Zuordnungstabelle logisch->Kopf und die Spule je Kopf.
        active = self._print_state.get("active")
        if active and not active.get("pending") and data.print_state in ACTIVE_PRINT_STATES:
            active["map_table"] = list(ptc.get("extruder_map_table") or [])
            if mgr.enabled:
                active["spool_ids"] = {str(k): v for k, v in mgr.assigned().items()}
        data.spoolman = self._spoolman_data(data.slots)

    def _mark_booked(self) -> None:
        """Gebuchte Mengen in der Historie als gebucht markieren."""
        done = {(str(i["key"]).split("|")[0], i["slot"]) for i in self.spools.just_booked}
        self.spools.just_booked.clear()
        if not done:
            return
        history = []
        for rec in self._history():
            if rec.get("spools"):
                rec = {**rec, "spools": [
                    {**sp, "booked": True} if (str(rec.get("started")), sp.get("slot")) in done else sp
                    for sp in rec["spools"]
                ]}
            history.append(rec)
        self._print_state = {**self._print_state, "history": history,
                             "last": history[0] if history else self._print_state.get("last")}

    def _spoolman_data(self, slots: list[dict[str, Any]]) -> dict[str, Any] | None:
        mgr = self.spools
        if not mgr.enabled or mgr.client is None:
            return None
        return {
            "online": mgr.online,
            "error": mgr.error,
            "url": mgr.client.url,
            "low": float(self.options.get(CONF_SPOOLMAN_LOW, DEFAULT_SPOOLMAN_LOW)),
            "deduct": mgr.deduct,
            "pending": [dict(q) for q in mgr.queue],
            "slots": {str(s["index"]): mgr.slot_info(s["index"]) for s in slots},
            "spools": mgr.spools,
        }

    async def async_set_spool(self, slot_index: int, spool_id: int | None, automatic: bool) -> None:
        if not self.spools.enabled:
            raise HomeAssistantError("Spoolman ist nicht eingerichtet.")
        slots = (self.data or self._prev).slots
        slot = next((s for s in slots if s["index"] == slot_index), None)
        if slot is None:
            raise HomeAssistantError(f"Kopf {slot_index + 1} unbekannt.")
        if spool_id and self.spools.spool(spool_id) is None:
            await self.spools.async_refresh()
            if self.spools.spool(spool_id) is None:
                raise HomeAssistantError(f"Spule {spool_id} gibt es in Spoolman nicht (oder sie ist archiviert).")
        if spool_id and not automatic:
            # Eine Spule steckt nur in einem Kopf: anderswo gesetzt -> dort loesen
            for key, entry in list(self.spools.mapping.items()):
                if key != str(slot_index) and entry.get("spool_id") == spool_id:
                    self.spools.mapping[key] = {**entry, "spool_id": None, "manual": True}
        self.spools.set_manual(slot, spool_id, automatic)
        self.spools.assign(slots)
        self._save()
        if self.data is not None:
            self.data.spoolman = self._spoolman_data(slots)
            self.async_update_listeners()

    async def _enrich_active(self, active: dict[str, Any]) -> None:
        """Slicer-Daten der laufenden Datei merken (Filamente, Gewicht, Bild)."""
        path = active.get("file")
        active["meta_done"] = True
        if not path:
            return
        # Pause-Kopie: Name und Vorschaubild der Originaldatei
        info = next((f for f in self._files if f.get("path") == original_file(path)), None)
        try:
            meta = await self.client.file_metadata(path)
        except MoonrakerError:
            meta = {}
        fils = parse_file_filaments(meta)
        active["filaments"] = [
            {"index": f["index"], "type": f["type"], "color": f["color"], "weight": f["weight"]}
            for f in fils if f.get("used") and f.get("weight")
        ]
        total = meta.get("filament_total")
        if isinstance(total, (int, float)):
            active["filament_total"] = total
        if isinstance(meta.get("estimated_time"), (int, float)):
            active["estimated_time"] = meta["estimated_time"]
        active["name"] = (info or {}).get("name") or describe_file(original_file(path), {}, meta)["name"]
        if info and info.get("thumb"):
            active["thumb"] = info["thumb"]

    # ── Schichtansicht ─────────────────────────────────────────────────────
    @property
    def layer_store(self) -> Path:
        return self.thumb_dir.parent / "layers" / f"{self.config_entry.entry_id}.jsonl"

    def request_layers(self, print_state: str | None = None) -> None:
        """Druckdatei einmal je Druck laden und zerlegen (Schichtansicht, Zeitprofil)."""
        data = self.data or self._prev
        active = self._print_state.get("active") or {}
        print_state, filename = print_state or data.print_state, active.get("file")
        if print_state not in ACTIVE_PRINT_STATES or not filename:
            return
        key = f"{filename}|{active.get('started')}"
        if self.layer_view.get("key") == key or (self._layer_task and not self._layer_task.done()):
            return
        self.layer_view = {"key": key, "status": "parsing", "file": filename}
        self._layer_task = self.hass.async_create_background_task(
            self._parse_layers(key, filename), f"{DOMAIN} layers"
        )

    async def _parse_layers(self, key: str, filename: str) -> None:
        store = self.layer_store
        # Temporaerordner im Executor anlegen und aufraeumen (blockiert sonst die Ereignisschleife)
        tmp = Path(await self.hass.async_add_executor_job(tempfile.mkdtemp, None, "u1layers"))
        try:
            src = tmp / "print.gcode"
            await self.client.download_to("gcodes", filename, src, self.hass)
            part = tmp / "layers.jsonl"
            meta = await self.hass.async_add_executor_job(parse_layers, src, part)

            def _move() -> None:
                store.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(part), str(store))

            await self.hass.async_add_executor_job(_move)
        except Exception as err:  # noqa: BLE001 - Ansicht ist Beiwerk, darf nie stoeren
            _LOGGER.info("Schichtansicht fuer %s nicht moeglich: %s", filename, err)
            if self.layer_view.get("key") == key:
                self.layer_view = {"key": key, "status": "error", "file": filename, "error": str(err)}
            return
        finally:
            await self.hass.async_add_executor_job(shutil.rmtree, tmp, True)
        if self.layer_view.get("key") == key:
            self.layer_view = {"key": key, "status": "ready", "file": filename, "meta": meta}
            _LOGGER.debug("Schichtansicht %s: %s Schichten", filename, meta["total"])

    def layer_colors(self) -> dict[str, Any]:
        """Farben je logischem Filament (aus der Datei) und Zuordnung zu den Koepfen."""
        active = self._print_state.get("active") or {}
        fils = {str(f["index"]): f.get("color") for f in active.get("filaments") or [] if "index" in f}
        data = self.data or self._prev
        return {"file": fils, "map_table": list(active.get("map_table") or data.map_table or [])}

    # ── Fehler im Klartext ─────────────────────────────────────────────────
    def _update_errors(self, errors: list[dict[str, Any]]) -> None:
        keys = {e["key"] for e in errors}
        self._new_errors = [e for e in errors if e["key"] not in self._error_keys]
        for err in self._new_errors:
            _LOGGER.info("Drucker meldet: %s (%s, %s)", err["text"]["de"], err["key"], err["message"])
        self._errors, self._error_keys = errors, keys

    def _alert_new(self, errors: list[dict[str, Any]], print_state: str | None, skip: bool) -> None:
        """Neue Firmware-Meldung waehrend eines Drucks pushen (Pause meldet sich selbst)."""
        new = getattr(self, "_new_errors", [])
        if not new or skip or print_state not in ACTIVE_PRINT_STATES:
            return
        active = self._print_state.get("active") or {}
        lang = self.hass.config.language
        self._notify("alert", {"name": active.get("name"), "file": active.get("file"),
                               "text": "\n".join(error_text(e, lang) for e in new)})

    # ── Ereignisse im Druck ────────────────────────────────────────────────
    def _print_events(self, stats: dict[str, Any], vsd: dict[str, Any]) -> None:
        """Erste Schicht fertig und "gleich fertig", je Druck einmal."""
        active = self._print_state.get("active")
        if not active:
            self._event_key, self._last_layer = None, None
            return
        key = (active.get("file"), active.get("started"))
        if key != self._event_key:
            self._event_key, self._events_sent, self._last_layer = key, set(), None
        if stats.get("state") != "printing":
            return
        self._maybe_early_photo(active, stats, vsd)
        info = stats.get("info") if isinstance(stats.get("info"), dict) else {}
        layer = info.get("current_layer")
        if isinstance(layer, int):
            # Nur den Wechsel 1 -> 2 melden, nicht das Einsteigen mitten im Druck.
            if self._last_layer == 1 and layer >= 2 and "first_layer" not in self._events_sent:
                self._events_sent.add("first_layer")
                self._notify("first_layer", {"name": active.get("name"), "file": active.get("file")})
            self._last_layer = layer
        left = self._remaining(stats, vsd)
        minutes = float(self.options.get(CONF_ALMOST_DONE, DEFAULT_ALMOST_DONE) or 0)
        if left is not None and minutes > 0 and left <= minutes * 60 and "almost_done" not in self._events_sent:
            self._events_sent.add("almost_done")
            self._notify("almost_done", {"name": active.get("name"), "file": active.get("file"),
                                         "left_min": max(1, round(left / 60))})

    def _remaining(self, stats: dict[str, Any], vsd: dict[str, Any]) -> float | None:
        """Restzeit: Zeitprofil der Datei (geeicht), sonst Dauer x Rest/Fortschritt."""
        active = self._print_state.get("active") or {}
        meta = self._profile(active)
        left = estimate_remaining(meta, _position(vsd, meta), stats.get("print_duration"),
                                  active.get("estimated_time"))
        if left is None:
            left = remaining_seconds(stats.get("print_duration"), vsd.get("progress"))
        return left

    def _profile(self, active: dict[str, Any]) -> dict[str, Any] | None:
        view = self.layer_view
        if view.get("status") == "ready" and active.get("file") and view.get("file") == active.get("file"):
            return view.get("meta")
        return None

    def _check_runout(self, vsd: dict[str, Any], remaining: float | None, ptc: dict[str, Any]) -> dict[int, dict[str, Any]]:
        """Laeuft eine Spule im Druck leer? Zeitpunkt aus Zeitprofil und Spoolman-Rest.

        Die Firmware fuellt mit Auto-Nachfuellen (print_task_config.
        auto_replenish_filament) von einem Kopf mit gleichem Material nach;
        gibt es den, steht er in der Meldung.
        """
        active = self._print_state.get("active") or {}
        meta = self._profile(active)
        if not self.spools.enabled or meta is None:
            return {}
        at = timeline_at(meta, _position(vsd, meta))
        if at is None or not at["t_total"]:
            return {}
        rows = meta["timeline"]
        table = list(active.get("map_table") or ptc.get("extruder_map_table") or [0, 1, 2, 3])
        gpmm: dict[int, float] = {}
        for fil in active.get("filaments") or []:
            idx = fil.get("index")
            if isinstance(idx, int) and 0 <= idx < 8 and at["e_total"][idx] > 0 and fil.get("weight"):
                gpmm[idx] = fil["weight"] / at["e_total"][idx]
        heads: dict[int, list[int]] = {}
        for logical in gpmm:
            head = table[logical] if logical < len(table) else logical
            if isinstance(head, int) and 0 <= head < 4:
                heads.setdefault(head, []).append(logical)
        left = at["t_total"] - at["t"]
        factor = (remaining / left) if remaining and left > 0 else 1.0
        slots = parse_slots(ptc)
        out: dict[int, dict[str, Any]] = {}
        for head, logicals in heads.items():
            info = self.spools.slot_info(head) or {}
            rest = info.get("remaining_weight")
            if not isinstance(rest, (int, float)):
                continue
            total = sum(at["e_total"][t] * gpmm[t] for t in logicals)
            if total <= rest:
                continue
            t_run = next((row[1] for row in rows if sum(row[2 + t] * gpmm[t] for t in logicals) >= rest), None)
            if t_run is None:
                continue
            minutes = max(0.0, (t_run - at["t"]) * factor / 60)
            out[head] = {"minutes": round(minutes), "takeover": _takeover(slots, head, ptc)}
            key = f"runout{head}"
            if minutes <= RUNOUT_WARN_MIN and key not in self._events_sent:
                self._events_sent.add(key)
                self._notify("spool_runout", {
                    "name": active.get("name"), "file": active.get("file"),
                    "runout": {"head": head + 1, "minutes": max(1, round(minutes)),
                               "takeover": (out[head]["takeover"] + 1) if out[head]["takeover"] is not None else None},
                })
        return out

    def _check_bed_cool(self, bed: Any, print_state: str | None) -> None:
        """Nach "fertig": melden, sobald das Bett kalt genug zum Entnehmen ist."""
        if self._cool_watch is None:
            return
        if print_state in ACTIVE_PRINT_STATES or time.time() - self._cool_watch > 3 * 3600:
            self._cool_watch = None
            return
        limit = float(self.options.get(CONF_BED_COOL, DEFAULT_BED_COOL) or DEFAULT_BED_COOL)
        if isinstance(bed, (int, float)) and bed <= limit:
            self._cool_watch = None
            last = self._print_state.get("last") or {}
            self._notify("bed_cool", {"name": last.get("name"), "file": last.get("file"),
                                      "bed": round(bed)})

    def _check_spools(self, active: dict[str, Any], table: list[int]) -> None:
        """Beim Druckstart: reicht die Spule je Kopf (Spoolman-Rest) fuer die Datei?"""
        if not self.spools.enabled:
            return
        need = grams_per_slot({**active, "result": "complete",
                               "map_table": active.get("map_table") or table})
        short = []
        for slot, grams in sorted(need.items()):
            info = self.spools.slot_info(slot)
            rest = (info or {}).get("remaining_weight")
            if isinstance(rest, (int, float)) and rest < grams:
                short.append({"head": slot + 1, "need": round(grams), "rest": round(rest),
                              "name": (info or {}).get("name")})
        active["spool_short"] = short
        if short:
            self._notify("spool_low", {"name": active.get("name"), "file": active.get("file"), "short": short})

    # ── Live-Abo ───────────────────────────────────────────────────────────
    def start_live(self) -> None:
        self.live.start(self.hass)

    def _on_live_state(self, connected: bool) -> None:
        self.update_interval = LIVE_INTERVAL if connected else UPDATE_INTERVAL
        _LOGGER.debug("Live-Abo %s", "steht" if connected else "getrennt")
        if self.data is not None:
            self.async_update_listeners()

    def _on_live(self, diff: dict[str, Any]) -> None:
        """Aenderung vom Drucker: Wichtiges sofort, Rest beim naechsten Abgleich."""
        ps = diff.get("print_stats") or {}
        refresh = "state" in ps or "filename" in ps or "exception_manager" in diff
        if self.data is None or self._starting:
            return
        if "state" in ps and ps["state"] != self.data.print_state:
            # Sofort sichtbar (Karte, Sprachbefehle); der Abgleich folgt entprellt.
            self.data.print_state = ps["state"]
        head = diff.get("toolhead", {}).get("extruder") if isinstance(diff.get("toolhead"), dict) else None
        if head is not None and head_index(head) != self.data.active_head:
            self.data.active_head = head_index(head)
            if not refresh:
                self.async_update_listeners()
        status = self.live.status
        if "print_stats" in diff or "virtual_sdcard" in diff:
            # Fuer Sprachausgabe & Co. aktuell halten (ohne Neuzeichnen)
            ps_all = status.get("print_stats") or {}
            info = ps_all.get("info") if isinstance(ps_all.get("info"), dict) else {}
            self.data.progress = (status.get("virtual_sdcard") or {}).get("progress", self.data.progress)
            self.data.print_duration = ps_all.get("print_duration", self.data.print_duration)
            self.data.layer = info.get("current_layer", self.data.layer)
            self._print_events(status.get("print_stats") or {}, status.get("virtual_sdcard") or {})
        if refresh:
            self.hass.async_create_task(self.async_request_refresh(), f"{DOMAIN} live refresh")

    def current_print_state(self) -> str | None:
        """Druckstatus, so frisch wie moeglich (Live-Abo vor letztem Abgleich)."""
        if self.live.connected:
            state = (self.live.status.get("print_stats") or {}).get("state")
            if state:
                return state
        return (self.data or self._prev).print_state

    def live_position(self) -> dict[str, Any] | None:
        """Dateiposition, Schicht und Kopf aus dem Live-Abo (None = nicht verbunden)."""
        if not self.live.connected:
            return None
        st = self.live.status
        info = (st.get("print_stats") or {}).get("info") or {}
        return {
            "position": (st.get("virtual_sdcard") or {}).get("file_position"),
            "layer": info.get("current_layer") if isinstance(info, dict) else None,
            "active_head": head_index((st.get("toolhead") or {}).get("extruder")),
        }

    # ── Druckstart und Warteschlange ───────────────────────────────────────
    async def async_start_print(
        self,
        filename: str,
        mapping: dict[int, int] | None = None,
        *,
        bed_leveling: bool | None = None,
        flow_calibration: bool | None = None,
        timelapse: bool | None = None,
        plate: int = 1,
        pause_layers: list[int] | None = None,
        auto_on: bool = False,
    ) -> dict[str, Any]:
        """Druck starten: Einschalten, Zuordnung, Pause-Kopie, Druckstart."""
        filename = filename.lstrip("/")
        if self.shutting_down:
            raise HomeAssistantError("Der Drucker faehrt gerade herunter. Bitte danach erneut starten.")
        if self._starting:
            raise HomeAssistantError("Ein Druckstart laeuft bereits.")
        self._starting = True
        try:
            if self.power_is_off():
                if not auto_on:
                    raise HomeAssistantError("Der Drucker ist ausgeschaltet.")
                _LOGGER.info("Drucker aus: schalte fuer %s ein", filename)
                await self.async_power_on(wait=True)
            if self.data is not None and self.data.print_state in ACTIVE_PRINT_STATES:
                raise HomeAssistantError("Der Drucker druckt bereits.")

            if mapping is None:
                # Ohne Vorgabe dieselbe Logik wie der Dialog in der Karte.
                try:
                    meta = await self.client.file_metadata(filename)
                except MoonrakerError:
                    meta = {}
                slots = self.data.slots if self.data else []
                mapping = suggest_mapping(parse_file_filaments(meta), slots)
            table = map_table_option(mapping) if mapping else None

            target = filename
            if pause_layers:
                target = await self._prepare_pause_copy(filename, pause_layers)

            _LOGGER.info("Druckstart %s, Zuordnung %s, Pause %s", target, table, pause_layers or "-")
            try:
                result = await self.client.start_print(
                    target, map_table=table, bed_leveling=bed_leveling,
                    flow_calibration=flow_calibration, timelapse=timelapse, plate=plate,
                )
            except MoonrakerError as err:
                if target != filename:
                    await self._delete_copy(target)
                raise HomeAssistantError(f"Druckstart abgelehnt: {err}") from err
            self.note_print_started(target)
            active = self._print_state.get("active")
            if active is not None:
                active["source"] = filename
                active["mapping"] = {str(k): v for k, v in (mapping or {}).items()}
                active["options"] = {
                    k: v for k, v in (("bed_leveling", bed_leveling), ("flow_calibration", flow_calibration),
                                      ("timelapse", timelapse)) if v is not None
                }
                if pause_layers:
                    active["pause_layers"] = sorted(set(pause_layers))
                self._save()
        finally:
            self._starting = False
        await self.async_request_refresh()
        return {"state": result.get("state", "success"), "map_table": table, "file": target}

    async def _prepare_pause_copy(self, filename: str, layers: list[int]) -> str:
        """Kopie mit PAUSE vor den Schichten anlegen und hochladen."""
        target = pause_file_name(filename, layers)
        with tempfile.TemporaryDirectory(prefix="u1pause") as tmp:
            src, dst = Path(tmp) / "src.gcode", Path(tmp) / "dst.gcode"
            try:
                await self.client.download_to("gcodes", filename, src, self.hass)
            except MoonrakerError as err:
                raise HomeAssistantError(f"Datei nicht lesbar: {err}") from err
            try:
                result = await self.hass.async_add_executor_job(add_layer_pauses, src, dst, layers)
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err
            if result["missing"]:
                raise HomeAssistantError(
                    f"Schicht {', '.join(map(str, result['missing']))} gibt es nicht "
                    f"(Datei hat {result['total']} Schichten)."
                )
            try:
                await self.client.upload(dst, target)
            except MoonrakerError as err:
                raise HomeAssistantError(f"Kopie mit Pause nicht hochgeladen: {err}") from err
        return target

    async def _delete_copy(self, path: str) -> None:
        if not is_pause_copy(path):
            return
        try:
            await self.client.delete_file(path)
        except MoonrakerError as err:
            _LOGGER.debug("Pause-Kopie %s nicht geloescht: %s", path, err)

    def queue_add(self, job: dict[str, Any]) -> dict[str, Any]:
        info = next((f for f in self._files if f.get("path") == job["file"]), None)
        entry = self.queue.add({**job, "name": (info or {}).get("name") or posixpath.basename(job["file"]),
                                "thumb": (info or {}).get("thumb")})
        self._queue_changed()
        return entry

    def queue_remove(self, job_id: str) -> None:
        if not self.queue.remove(job_id):
            raise HomeAssistantError("Auftrag nicht gefunden.")
        self._queue_changed()

    def queue_move(self, job_id: str, position: int) -> None:
        if not self.queue.move(job_id, position):
            raise HomeAssistantError("Auftrag nicht gefunden.")
        self._queue_changed()

    def queue_clear(self) -> None:
        self.queue.clear()
        self._queue_changed()

    async def queue_start(self, job_id: str | None) -> dict[str, Any]:
        job = self.queue.get(job_id)
        if job is None:
            raise HomeAssistantError("Die Warteschlange ist leer." if job_id is None else "Auftrag nicht gefunden.")
        mapping = {int(k): int(v) for k, v in (job.get("mapping") or {}).items()} or None
        result = await self.async_start_print(
            job["file"], mapping,
            bed_leveling=job.get("bed_leveling"), flow_calibration=job.get("flow_calibration"),
            timelapse=job.get("timelapse"), plate=int(job.get("plate") or 1),
            pause_layers=job.get("pause_layers"), auto_on=bool(self.options.get("auto_on")),
        )
        self.queue.remove(job["id"])
        self._queue_changed()
        return result

    def _queue_changed(self) -> None:
        self._save()
        if self.data is not None:
            self.data.queue = list(self.queue.jobs)
            self.async_update_listeners()

    # ── Statistik und Wartung ──────────────────────────────────────────────
    async def _update_stats(self) -> None:
        self._stats_at = time.monotonic()
        self._force_stats = False
        try:
            jobs = await self.client.history()
            totals = await self.client.history_totals()
        except MoonrakerError as err:
            _LOGGER.debug("Druckhistorie nicht lesbar: %s", err)
            return
        hist = [{**h, "ended": h.get("ended")} for h in self._history()]
        self._stats = build_stats(jobs, hist, time.time(), dt_util.get_default_time_zone(),
                                  prices=self.filament_prices)
        seconds = totals.get("total_print_time")
        if isinstance(seconds, (int, float)):
            self._print_hours = round(float(seconds) / 3600, 2)
            self._stats["totals"]["hours_total"] = self._print_hours
            if self.maintenance.baseline(self._print_hours, time.time()):
                self._save()

    def _maintenance_status(self, tool_changes: dict[str, Any] | None) -> list[dict[str, Any]]:
        items = self.maintenance.status(self._print_hours, self.options.get(CONF_MAINTENANCE) or {})
        if tool_changes:
            worst = max((h.get("since_maintenance") or 0 for h in tool_changes.get("heads") or []), default=0)
            limit = tool_changes.get("maintenance_threshold") or 0
            if limit:
                items.append({
                    "key": "tool_changer", "interval": limit, "used": worst,
                    "remaining": limit - worst, "progress": round(min(worst / limit, 9.99) * 100),
                    "due": worst >= limit, "firmware": True,
                })
        return items

    def mark_maintenance(self, key: str) -> None:
        if key not in MAINTENANCE_ITEMS:
            raise HomeAssistantError(f"Unbekannter Wartungspunkt: {key}")
        self.maintenance.mark_done(key, self._print_hours, time.time())
        self._save()
        if self.data is not None:
            self.data.maintenance = self._maintenance_status(self.data.tool_changes)
            self.async_update_listeners()

    # ── Zeitraffer sichern ─────────────────────────────────────────────────
    def _archive_data(self) -> dict[str, Any] | None:
        if self.archive is None:
            return None
        entry = self.config_entry.entry_id
        videos = [
            {**v, "poster_url": f"{THUMB_URL}/{entry}/archive/{Path(v['file']).stem}.jpg"} if v.get("poster") else v
            for v in self._archive_list[:30]
        ]
        return {
            "videos": videos,
            "count": len(self._archive_list),
            "folder": str(self.archive.folder),
            "last_backup": self.archive.last_backup,
            "cleanup": self.archive.cleanup,
            "keep": int(self.options.get(CONF_ARCHIVE_KEEP, DEFAULT_ARCHIVE_KEEP)),
            "busy": self._archive_running,
            "errors": self.archive.errors,
        }

    def _start_archive(self, print_state: str | None, force: bool = False) -> None:
        if self.archive is None or (self._archive_task and not self._archive_task.done()):
            return
        # Waehrend eines Drucks nicht: der Drucker zeichnet gerade auf, und WLAN
        # braucht er fuer die Kamera.
        if print_state in ACTIVE_PRINT_STATES and not force:
            return
        videos = list(self._timelapses)
        if not videos:
            return
        self._archive_task = self.hass.async_create_background_task(
            self._run_archive(videos), f"{DOMAIN} timelapse archive"
        )

    async def async_backup_timelapses(self) -> None:
        if self.archive is None:
            raise HomeAssistantError("Zeitraffer-Sicherung ist in den Optionen nicht eingeschaltet.")
        if self._archive_task and not self._archive_task.done():
            await self._archive_task
            return
        self._start_archive(self.data.print_state if self.data else None)
        if self._archive_task:
            await self._archive_task

    async def _run_archive(self, videos: list[dict[str, Any]]) -> None:
        assert self.archive is not None
        self._archive_running = True
        if self.data is not None:
            self.data.archive = self._archive_data()
        self.async_update_listeners()
        try:
            await self.archive.backup(self.hass, videos, self._own_dir / "tl", self._own_dir / "archive")
            keep = int(self.options.get(CONF_ARCHIVE_KEEP, DEFAULT_ARCHIVE_KEEP))
            if keep > 0 and not (self.data and self.data.print_state in ACTIVE_PRINT_STATES):
                deleted = await self.archive.cleanup_printer(self.hass, videos, keep)
                if deleted:
                    _LOGGER.info("Auf dem Drucker geloescht (gesichert): %s", ", ".join(deleted))
                    self._force_timelapses = True
            self._archive_list = await self.hass.async_add_executor_job(list_archive, self.archive.folder)
            self._save()
        finally:
            self._archive_running = False
            if self.data is not None:
                self.data.archive = self._archive_data()
            self.async_update_listeners()

    # ── Selbsttest ─────────────────────────────────────────────────────────
    async def async_self_test(self, language: str | None = None) -> dict[str, Any]:
        """Alles pruefen, was die Integration braucht; Ergebnis als Liste.

        ok: True = in Ordnung, False = Fehler, None = Hinweis (optional/fehlt).
        """
        de = (language or self.hass.config.language).lower().startswith("de")
        t = (lambda a, b: a) if de else (lambda a, b: b)
        checks: list[dict[str, Any]] = []

        def add(key: str, ok: bool | None, detail: str) -> None:
            checks.append({"key": key, "ok": ok, "detail": detail})

        # Drucker und Klipper
        try:
            ready = await self.client.klippy_ready()
            add("printer", ready, t("Moonraker erreichbar, Klipper bereit", "Moonraker reachable, Klipper ready")
                if ready else t("Moonraker erreichbar, Klipper nicht bereit", "Moonraker reachable, Klipper not ready"))
        except MoonrakerError as err:
            off = self.power_is_off()
            add("printer", None if off else False,
                t("Drucker ist ausgeschaltet", "Printer is switched off") if off else str(err))
        add("live", True if self.live.connected else None,
            t("Live-Verbindung steht", "Live connection up") if self.live.connected
            else t("Live-Verbindung getrennt, Abfrage alle 10 s", "Live connection down, polling every 10 s"))
        ver = self.firmware.get("installed")
        latest = (self.firmware.get("latest") or {}).get("version")
        add("firmware", None if latest and ver and version_tuple(latest) > version_tuple(ver) else (True if ver else None),
            f"{t('Installiert', 'Installed')} {ver or '?'}"
            + (f", {t('neueste', 'latest')} {latest}" if latest else ""))
        try:
            space = await self.client.rpc("server.files.get_userdata_space", response_timeout=10)
            free = (space or {}).get("free_space")
            if isinstance(free, (int, float)):
                add("storage", free >= 500, t(f"{free:.0f} MiB frei", f"{free:.0f} MiB free"))
        except MoonrakerError:
            pass
        # Moonraker-Integration (Temperaturen, Kamera, Licht in der Karte)
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(self.hass)
        mr = [e for e in reg.entities.values() if e.platform == "moonraker"]
        add("moonraker_integration", bool(mr),
            t(f"{len(mr)} Entitäten der Moonraker-Integration", f"{len(mr)} Moonraker integration entities") if mr
            else t("Moonraker-Integration fehlt: Temperaturen, Licht und Kamera fehlen in der Karte",
                   "Moonraker integration missing: no temperatures, light or camera in the card"))
        # Kamera
        camera = self.options.get(CONF_CAMERA)
        if not camera:
            add("camera", None, t("Keine Kamera gewählt (Bild in Push und Ergebnisfoto fehlen)",
                                  "No camera selected (no image in push and no result photo)"))
        else:
            try:
                from homeassistant.components.camera import async_get_image

                img = await async_get_image(self.hass, camera, timeout=10)
                add("camera", True, t(f"{camera}: Bild {len(img.content) // 1024} kB", f"{camera}: image {len(img.content) // 1024} kB"))
            except (HomeAssistantError, ImportError) as err:
                add("camera", False, f"{camera}: {err}")
        # Strom
        for key, conf, label in (("power_switch", CONF_POWER_SWITCH, t("Netzschalter", "Power switch")),
                                 ("energy", CONF_ENERGY_SENSOR, t("Energiezähler", "Energy meter")),
                                 ("price", CONF_ENERGY_PRICE, t("Strompreis", "Energy price"))):
            entity = self.options.get(conf)
            if not entity:
                add(key, None, t(f"{label}: nicht eingerichtet", f"{label}: not set up"))
                continue
            st = self.hass.states.get(entity)
            good = st is not None and st.state not in ("unavailable", "unknown")
            add(key, good, f"{label}: {entity} = {st.state if st else t('fehlt', 'missing')}")
        # Benachrichtigung
        targets = self.options.get(CONF_NOTIFY) or []
        if not targets:
            add("notify", None, t("Keine Benachrichtigung eingerichtet", "No notifications set up"))
        for target in targets:
            name = str(target).removeprefix("notify.")
            add("notify", self.hass.services.has_service("notify", name),
                f"notify.{name}" + ("" if self.hass.services.has_service("notify", name) else t(" fehlt", " missing")))
        # Spoolman
        if self.spools.enabled:
            okay = await self.spools.async_refresh()
            add("spoolman", okay, t(f"Spoolman: {len(self.spools.spools)} Spulen", f"Spoolman: {len(self.spools.spools)} spools")
                if okay else t("Spoolman nicht erreichbar", "Spoolman unreachable"))
        # Assist
        sentences = Path(self.hass.config.path("custom_sentences", "de", f"{DOMAIN}.yaml"))
        exists = await self.hass.async_add_executor_job(sentences.exists)
        add("assist", True if exists else None, t("Sätze für Assist vorhanden", "Assist sentences present") if exists
            else t("Keine Sätze für Assist (wird beim nächsten Start angelegt)", "No Assist sentences (created on next start)"))
        # Zeitraffer-Sicherung
        if self.archive is not None:
            folder = self.archive.folder

            def _writable() -> bool:
                folder.mkdir(parents=True, exist_ok=True)
                probe = folder / ".su1_probe"
                probe.write_text("ok")
                probe.unlink()
                return True

            try:
                await self.hass.async_add_executor_job(_writable)
                add("media", True, t(f"Medienordner beschreibbar: {folder}", f"Media folder writable: {folder}"))
            except OSError as err:
                add("media", False, f"{folder}: {err}")
        ok = all(c["ok"] is not False for c in checks)
        return {"ok": ok, "time": dt_util.now().isoformat(), "checks": checks}

    # ── Firmware-Pruefung ──────────────────────────────────────────────────
    def _start_firmware_check(self) -> None:
        latest = self.firmware.get("latest") or {}
        if self._fw_task and not self._fw_task.done():
            return
        if time.time() - float(latest.get("checked") or 0) < FIRMWARE_CHECK_S:
            return
        self._fw_task = self.hass.async_create_background_task(
            self.async_check_firmware(), f"{DOMAIN} firmware check"
        )

    async def async_check_firmware(self) -> dict[str, Any] | None:
        """Neueste Firmware aus Snapmakers Release-Commits (GitHub, ohne Anmeldung)."""
        session = async_get_clientsession(self.hass)
        best: dict[str, Any] | None = None
        for repo in FIRMWARE_REPOS:
            try:
                async with session.get(
                    f"https://api.github.com/repos/{repo}/commits", params={"per_page": "50"},
                    headers={"Accept": "application/vnd.github+json"}, timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        continue
                    commits = await resp.json()
            except Exception as err:  # noqa: BLE001 - Pruefung ist Beiwerk
                _LOGGER.debug("Firmware-Pruefung %s: %s", repo, err)
                continue
            found = latest_release(commits)
            if found and (best is None or version_tuple(found["version"]) > version_tuple(best["version"])):
                best = found
        prev = self.firmware.get("latest") or {}
        # Ohne Ergebnis (offline, Rate-Limit) in einer Stunde erneut
        checked = time.time() if best else time.time() - FIRMWARE_CHECK_S + 3600
        self.firmware["latest"] = {**(best or {k: prev.get(k) for k in ("version", "url", "date")}),
                                   "checked": checked}
        self._save()
        self.async_update_listeners()
        return best

    # ── Konfig-Sicherung (backup.py) ───────────────────────────────────────
    @property
    def backup_folder(self) -> Path:
        return Path(self.hass.config.path(BACKUP_DIR)) / self.client.host.replace(":", "_")

    def _backup_data(self) -> dict[str, Any] | None:
        if not self.options.get(CONF_BACKUP, DEFAULT_BACKUP) and not self._backup:
            return None
        return {"enabled": bool(self.options.get(CONF_BACKUP, DEFAULT_BACKUP)),
                **{k: self._backup.get(k) for k in ("snapshot", "saved_at", "checked_at", "status", "files")},
                "folder": f"{BACKUP_DIR}/{self.backup_folder.name}"}

    def _start_backup(self) -> None:
        if not self.options.get(CONF_BACKUP, DEFAULT_BACKUP):
            return
        if self._backup_task and not self._backup_task.done():
            return
        if time.time() - float(self._backup.get("checked_at") or 0) < 86400:
            return
        self._backup_task = self.hass.async_create_background_task(
            self.async_backup_config(), f"{DOMAIN} config backup"
        )

    async def async_backup_config(self) -> dict[str, Any]:
        try:
            result = await backup_config(self.hass, self.client, self.backup_folder, self._backup.get("digest"))
        except MoonrakerError as err:
            _LOGGER.debug("Konfig-Sicherung fehlgeschlagen: %s", err)
            self._backup = {**self._backup, "checked_at": time.time() - 86400 + 3600, "status": "error"}
            raise HomeAssistantError(f"Konfig-Sicherung fehlgeschlagen: {err}") from err
        now = time.time()
        self._backup = {**self._backup, "digest": result.get("digest"), "checked_at": now,
                        "status": result["status"], "files": result.get("files")}
        if result["status"] == "saved":
            self._backup.update(snapshot=result["snapshot"], saved_at=now)
        self._save()
        if self.data is not None:
            self.data.backup = self._backup_data()
            self.async_update_listeners()
        snaps = await self.hass.async_add_executor_job(list_snapshots, self.backup_folder)
        return {**{k: v for k, v in result.items() if k != "digest"}, "snapshots": snaps}

    # ── Druckende und Benachrichtigung ──────────────────────────────────────
    def _finished(self, record: dict[str, Any]) -> None:
        if is_pause_copy(record.get("file")):
            copy = record["file"]
            record = {**record, "file": record.get("source") or original_file(copy)}
            self.hass.async_create_task(self._delete_copy(copy), f"{DOMAIN} delete pause copy")
        if record.get("result") == "error" and self._errors:
            record = {**record, "error": error_text(self._errors[0], self.hass.config.language)}
        summary = summarize_print(record, self.filament_prices)
        booked = self.spools.book(record)
        if booked:
            summary["spools"] = booked
            self.spools.force()  # beim naechsten Abruf buchen
        history = [summary, *self._history()][:HISTORY_SIZE]
        self._print_state = {**self._print_state, "last": summary, "history": history}
        self._force_timelapses = True
        self.hass.bus.async_fire(
            EVENT_PRINT_FINISHED,
            {
                "config_entry_id": self.config_entry.entry_id,
                "file": summary.get("file"),
                "name": summary.get("name"),
                "result": summary.get("result"),
                "duration_s": summary.get("duration"),
                "tool_changes": summary.get("switches"),
                "energy_kwh": summary.get("energy"),
                "energy_cost": summary.get("energy_cost"),
                "filament_g": summary.get("filament_g"),
                "filament_cost": summary.get("filament_cost"),
                "total_cost": summary.get("total_cost"),
            },
        )
        if summary.get("result") == "complete":
            self._cool_watch = time.time()
        photo = self._result_photo_url(summary)
        if photo:
            summary["photo"] = photo
        if summary.get("result") in RESULT_TEXT:
            self._notify(summary["result"], summary)
        self._force_stats = True
        if self.queue.jobs and summary.get("result") in ("complete", "cancelled", "error"):
            nxt = self.queue.jobs[0]
            self._notify("queue", {"name": nxt.get("name") or nxt.get("file"), "queue": len(self.queue.jobs)})
        if (
            self.options.get(CONF_AUTO_OFF)
            and self.power_switch
            and summary.get("result") in AUTO_OFF_RESULTS
        ):
            self.auto_off_armed = time.time()
            _LOGGER.info("Auto-Aus vorgemerkt nach %s", summary.get("file"))

    def _notify_transition(self, state: str | None, filename: str | None) -> bool:
        """Pause melden (z. B. Filament leer). Ende/Fehler laufen ueber _finished."""
        prev, self._last_state = self._last_state, state
        if state == "paused" and prev == "printing":
            active = self._print_state.get("active") or {}
            self._notify("paused", {"file": filename, "name": active.get("name")})
            return True
        return False

    def _notify(self, event: str, info: dict[str, Any]) -> None:
        targets = self.options.get(CONF_NOTIFY) or []
        events = self.options.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
        if not targets or (event not in events and event not in ("queue", "cancel_confirm")):
            return
        de = self.hass.config.language.lower().startswith("de")
        title = f"Snapmaker U1: {(RESULT_TEXT if de else RESULT_TEXT_EN).get(event, event)}"
        message = notify_message(info, de)
        data: dict[str, Any] = {"tag": f"{DOMAIN}_{self.config_entry.entry_id}", "group": DOMAIN}
        camera = self.options.get(CONF_CAMERA)
        if camera:
            # Companion-App laedt das Bild mit eigener Anmeldung.
            data["image"] = f"/api/camera_proxy/{camera}"
        actions = self._actions(event, de)
        if actions:
            data["actions"] = actions
        if event in ("error", "paused") and self._errors:
            message = f"{error_text(self._errors[0], self.hass.config.language)}\n{message}"
        if event in ("error", "paused", "alert", "spool_low", "spool_runout", "cancel_confirm"):
            data["push"] = {"interruption-level": "time-sensitive"}
            data["priority"] = "high"
            data["ttl"] = 0
        for target in targets:
            service = str(target).removeprefix("notify.")
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service, {"title": title, "message": message, "data": data},
                    blocking=False,
                ),
                f"{DOMAIN} notify {service}",
            )

    # ── Aktionen in der Benachrichtigung (Companion-App) ───────────────────
    def _action_id(self, name: str) -> str:
        return f"SU1_{name}_{self.config_entry.entry_id}"

    def _actions(self, event: str, de: bool) -> list[dict[str, str]]:
        t = (lambda a, b: a) if de else (lambda a, b: b)
        if event in ("first_layer", "almost_done", "alert", "spool_low", "spool_runout"):
            return [{"action": self._action_id("PAUSE"), "title": t("Pausieren", "Pause")},
                    {"action": self._action_id("LIGHT"), "title": t("Licht", "Light")}]
        if event == "paused":
            return [{"action": self._action_id("RESUME"), "title": t("Fortsetzen", "Resume")},
                    {"action": self._action_id("CANCEL"), "title": t("Abbrechen …", "Cancel …")}]
        if event == "cancel_confirm":
            return [{"action": self._action_id("CANCEL_CONFIRM"), "title": t("Ja, abbrechen", "Yes, cancel"),
                     "destructive": "true"}]
        return []

    async def _on_notify_action(self, event: Any) -> None:
        action = str((event.data or {}).get("action") or "")
        suffix = f"_{self.config_entry.entry_id}"
        if not action.startswith("SU1_") or not action.endswith(suffix):
            return
        name = action[4:-len(suffix)]
        state = self.current_print_state()
        try:
            if name == "PAUSE" and state == "printing":
                await self.client.print_action("pause")
            elif name == "RESUME" and state == "paused":
                await self.client.print_action("resume")
            elif name == "CANCEL" and state in ACTIVE_PRINT_STATES:
                # Zweistufig: erst nachfragen
                active = self._print_state.get("active") or {}
                self._notify("cancel_confirm", {"name": active.get("name"), "file": active.get("file")})
                return
            elif name == "CANCEL_CONFIRM" and state in ACTIVE_PRINT_STATES:
                await self.client.print_action("cancel")
            elif name == "LIGHT":
                light = self._light_entity()
                if light:
                    await self.hass.services.async_call("light", "toggle", {ATTR_ENTITY_ID: light}, blocking=True)
            else:
                return
        except MoonrakerError as err:
            _LOGGER.warning("Aktion %s aus der Benachrichtigung fehlgeschlagen: %s", name, err)
            return
        _LOGGER.info("Aktion aus der Benachrichtigung: %s", name)
        await self.async_request_refresh()

    def _light_entity(self) -> str | None:
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(self.hass)
        hits = [e.entity_id for e in reg.entities.values()
                if e.domain == "light" and e.platform == "moonraker" and "cavity_led" in e.entity_id]
        return hits[0] if hits else None

    # ── Foto vom Ergebnis ──────────────────────────────────────────────────
    def _maybe_early_photo(self, active: dict[str, Any], stats: dict[str, Any], vsd: dict[str, Any]) -> None:
        """Ergebnisfoto direkt nach der letzten Bahn, bevor der End-G-Code das Bett absenkt.

        Mit Zeitprofil: sobald die Dateiposition die letzte Extrusion erreicht
        (Live-Abo, 250 ms). Ohne Profil: in der letzten Schicht ab 99,5 %.
        """
        camera = self.options.get(CONF_CAMERA)
        started = active.get("started")
        if not camera or (self._early_photo or {}).get("started") == started:
            return
        meta = self._profile(active)
        pos = _position(vsd, meta)
        if meta and meta.get("last_extrude"):
            due = pos is not None and pos >= meta["last_extrude"]
        else:
            info = stats.get("info") if isinstance(stats.get("info"), dict) else {}
            total, layer = info.get("total_layer"), info.get("current_layer")
            progress = vsd.get("progress")
            due = (isinstance(total, int) and total > 0 and layer == total
                   and isinstance(progress, (int, float)) and progress >= 0.995)
        if not due:
            return
        url, target = self._photo_target()
        self._early_photo = {"started": started, "url": url}
        _LOGGER.debug("Ergebnisfoto nach der letzten Bahn: %s", target.name)
        # Klipper liest die Datei der Bewegung ~1-2 s voraus: kurz warten
        self.hass.async_create_background_task(self._save_photo(camera, target, EARLY_PHOTO_DELAY_S),
                                               f"{DOMAIN} result photo")

    def _photo_target(self) -> tuple[str, Path]:
        stamp = dt_util.now().strftime("%Y%m%d_%H%M%S")
        return (f"{THUMB_URL}/{self.config_entry.entry_id}/results/{stamp}.jpg",
                self._own_dir / "results" / f"{stamp}.jpg")

    def _result_photo_url(self, summary: dict[str, Any]) -> str | None:
        """Ergebnisfoto: das nach der letzten Bahn, sonst jetzt (Abbruch, Fehler)."""
        camera = self.options.get(CONF_CAMERA)
        early, self._early_photo = self._early_photo, None
        if early and early.get("started") == summary.get("started") and summary.get("result") == "complete":
            return early["url"]
        if not camera or summary.get("result") not in ("complete", "cancelled", "error"):
            return None
        url, target = self._photo_target()
        self.hass.async_create_background_task(self._save_photo(camera, target), f"{DOMAIN} result photo")
        return url

    async def _save_photo(self, camera: str, target: Path, delay: float = 0) -> None:
        if delay:
            await asyncio.sleep(delay)
        try:
            from homeassistant.components.camera import async_get_image

            image = await async_get_image(self.hass, camera, timeout=15)
        except (HomeAssistantError, ImportError) as err:
            _LOGGER.info("Ergebnisfoto nicht moeglich: %s", err)
            return
        keep = {Path(str(h.get("photo"))).name for h in self._history() if h.get("photo")} | {target.name}

        def _store() -> None:
            _write(target, image.content)
            _prune_dir(target.parent, keep)

        await self.hass.async_add_executor_job(_store)

    def _check_idle_off(self, data: U1Data) -> None:
        """Leerlauf-Abschaltung: x Stunden ohne Druck und ohne Heizung -> herunterfahren, aus.

        Die Firmware kennt nur idle_timeout (Heizung/Motoren aus), schaltet
        aber nie ab. Jede Heizung mit Sollwert > 0 (z. B. Vorheizen am
        Display) und jeder Druck setzt die Uhr zurueck.
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
            _LOGGER.info("Leerlauf seit %.1f h: Drucker wird ausgeschaltet", hours)
            self.hass.async_create_task(self.async_power_off(reason="idle"), f"{DOMAIN} idle off")

    def _check_auto_off(self, data: U1Data) -> None:
        if self.auto_off_armed is None or self.shutting_down:
            return
        if (
            data.print_state in ACTIVE_PRINT_STATES
            or self._print_state.get("active")
            or not self.options.get(CONF_AUTO_OFF)
        ):
            self.auto_off_armed = None
            return
        # Ein Sollwert > 0 heisst: es heizt jemand auf (z. B. Start am Display,
        # waehrend print_stats noch den alten Zustand meldet).
        if any(t > 0 for t in data.targets):
            return
        delay = float(self.options.get(CONF_AUTO_OFF_DELAY, DEFAULT_AUTO_OFF_DELAY)) * 60
        limit = float(self.options.get(CONF_AUTO_OFF_TEMP, DEFAULT_AUTO_OFF_TEMP))
        if time.time() - self.auto_off_armed < delay:
            return
        if not data.temperatures or max(data.temperatures) >= limit:
            return
        _LOGGER.info("Auto-Aus: Druck beendet, alle Heizungen unter %s °C", limit)
        self.auto_off_armed = None
        self.hass.async_create_task(self.async_power_off(reason="auto"))

    # ── Strom ───────────────────────────────────────────────────────────────
    async def async_power_on(self, wait: bool = False) -> None:
        """Einschalten; mit ``wait`` blockieren, bis Klipper bereit ist."""
        if not self.power_switch:
            raise HomeAssistantError("Kein Netzschalter eingerichtet.")
        if self.shutting_down:
            raise HomeAssistantError("Der Drucker faehrt gerade herunter.")
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
            raise HomeAssistantError(
                f"Drucker nach {POWER_ON_TIMEOUT_S // 60} min noch nicht bereit."
            ) from err
        finally:
            self.powering_on = False
        self.request_files_refresh()
        await self.async_refresh()

    def check_power_off(self, force: bool = False) -> None:
        """Ausschalten waehrend eines Drucks ablehnen.

        Ein laufender Druck zaehlt auch dann, wenn der Drucker gerade kurz
        nicht antwortet (WLAN-Aussetzer): massgeblich ist der zuletzt bekannte
        Zustand. ``force`` uebergeht das fuer einen abgestuerzten Drucker.
        """
        if not self.power_switch:
            raise HomeAssistantError("Kein Netzschalter eingerichtet.")
        if self.powering_on:
            raise HomeAssistantError("Der Drucker startet gerade. Bitte warten.")
        if force:
            return
        data = self.data
        printing = (
            (data is not None and data.print_state in ACTIVE_PRINT_STATES)
            or self._last_state in ACTIVE_PRINT_STATES
            or bool(self._print_state.get("active"))
        )
        if printing:
            raise HomeAssistantError(
                "Der Drucker druckt gerade oder ein Druck wird gestartet. Druck erst beenden "
                "oder abbrechen. Bei einem abgestuerzten Drucker: Dienst power_off mit force: true."
            )

    async def async_power_off(self, reason: str = "user", force: bool = False) -> None:
        """Erst sauber herunterfahren, dann Strom weg. Laeuft im Hintergrund."""
        self.check_power_off(force)
        if self.shutting_down:
            return
        self.shutting_down = True
        self.auto_off_armed = None
        self.async_update_listeners()
        self._power_task = asyncio.current_task()
        try:
            online = bool(self.data and self.data.online)
            # Vor dem Herunterfahren fragen: machine.shutdown wuerde einen eben
            # (z. B. am Display) gestarteten Druck sonst genauso beenden.
            if not force and online and await self._printing_now():
                self.last_shutdown = "aborted: print started"
                _LOGGER.warning("Ausschalten abgebrochen: am Drucker laeuft ein Druck oder es heizt")
                return
            if online and self.options.get(CONF_SHUTDOWN_HOST, DEFAULT_SHUTDOWN_HOST):
                await self._shutdown_host()
            else:
                self.last_shutdown = "skipped"
            if not force and await self._printing_now():
                self.last_shutdown = "aborted: print started"
                _LOGGER.warning("Ausschalten abgebrochen: am Drucker laeuft ein Druck")
                return
            await self.hass.services.async_call(
                "homeassistant", "turn_off", {ATTR_ENTITY_ID: self.power_switch}, blocking=True
            )
            _LOGGER.info("Drucker ausgeschaltet (%s)", reason)
        finally:
            self.shutting_down = False
            self.async_update_listeners()

    async def _printing_now(self) -> bool:
        """Letzte Sicherung vor dem Abschalten: druckt oder heizt der Drucker?"""
        try:
            status = await self.client.query_objects(
                fields={"print_stats": ("state",), "heater_bed": ("target",),
                        **{name: ("target",) for name in EXTRUDER_OBJECTS}},
            )
        except MoonrakerError:
            return False  # heruntergefahren oder nicht erreichbar
        if (status.get("print_stats") or {}).get("state") in ACTIVE_PRINT_STATES:
            return True
        return any(
            isinstance(t, (int, float)) and t > 0
            for t in ((status.get(n) or {}).get("target") for n in (*EXTRUDER_OBJECTS, "heater_bed"))
        )

    async def _shutdown_host(self) -> None:
        """machine.shutdown senden und warten, bis der Drucker nicht mehr antwortet."""
        try:
            await self.client.rpc("machine.shutdown", response_timeout=10)
        except MoonrakerConnectionError:
            pass  # Verbindung riss beim Herunterfahren ab: gilt als angenommen.
        except MoonrakerError as err:
            # Stock-Firmware: Moonraker ruft "sudo systemctl poweroff" auf. Fehlt
            # das auf dem Geraet, wird wie mit dem Kippschalter abgeschaltet.
            _LOGGER.warning("machine.shutdown abgelehnt (%s), schalte nach %s s aus", err, SHUTDOWN_SETTLE_S)
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
                break  # Netzwerk ist weg: System faehrt herunter
        # Nach dem Netzwerk endet das Betriebssystem; Dateisystem Zeit lassen.
        await asyncio.sleep(SHUTDOWN_SETTLE_S)

    # ── Zeitraffer ──────────────────────────────────────────────────────────
    async def _load_timelapses(self) -> list[dict[str, Any]]:
        roots = [r for r in await self.client.list_roots() if r not in TIMELAPSE_SKIP_ROOTS]
        # "camera" (Stock-Firmware) und "timelapse" (Fluidd) zuerst.
        roots.sort(key=lambda r: (r not in ("camera", "timelapse"), r))
        found: list[dict[str, Any]] = []
        for root in roots:
            try:
                found += pick_timelapses(root, await self.client.list_files(root))
            except MoonrakerError as err:
                _LOGGER.debug("Ordner %s nicht lesbar: %s", root, err)
        found.sort(key=lambda v: v.get("modified") or 0, reverse=True)
        found = found[:20]
        await self._cache_timelapse_images(found)
        return found

    async def _cache_timelapse_images(self, videos: list[dict[str, Any]]) -> None:
        """Vorschaubilder der Zeitraffer lokal ablegen.

        Sie liefert dann HA selbst als statische Dateien aus, sofort und auch
        bei ausgeschaltetem Drucker. Ueber den Proxy wuerde jede Anfrage bei
        abgeschaltetem Drucker haengen und eine der nur 6 Browser-Verbindungen
        zu HA blockieren (HTTP/1.1, auch ueber Nabu Casa) - genug davon und
        das Frontend kann nichts mehr nachladen.
        """
        folder = self._own_dir / "tl"
        sem = asyncio.Semaphore(3)
        keep: set[str] = set()

        async def one(video: dict[str, Any], key: str) -> None:
            source = video.get(key)
            if not source:
                return
            digest = hashlib.sha1(
                f"{video['root']}|{source}|{video.get('modified')}".encode()
            ).hexdigest()[:20]
            name = f"{digest}{Path(source).suffix.lower() or '.jpg'}"
            keep.add(name)
            target = folder / name
            if not await self.hass.async_add_executor_job(target.exists):
                async with sem:
                    try:
                        blob = await self.client.download(source, root=video["root"])
                    except MoonrakerError as err:
                        _LOGGER.debug("Zeitraffer-Bild %s fehlt: %s", source, err)
                        return
                await self.hass.async_add_executor_job(_write, target, blob)
            video[f"{key}_url"] = f"{THUMB_URL}/{self.config_entry.entry_id}/tl/{name}"

        await asyncio.gather(*(one(v, k) for v in videos for k in ("thumb", "poster")))
        await self.hass.async_add_executor_job(_prune_dir, folder, keep)

    async def _load_files(self) -> list[dict[str, Any]]:
        entries = [
            e for e in await self.client.list_files()
            if str(e.get("path", "")).lower().endswith(PRINTABLE_SUFFIXES)
            and not posixpath.basename(str(e.get("path", ""))).startswith(".")
            and not is_pause_copy(e.get("path"))
        ]
        entries.sort(key=lambda e: e.get("modified") or 0, reverse=True)
        # Alle Namen (ohne Metadaten) fuer Suche und Ordner in der Karte
        self._all_files = [
            {"path": e["path"], "modified": e.get("modified"), "size": e.get("size")} for e in entries
        ]
        entries = entries[: self.files_limit]
        # Per Suche geoeffnete aeltere Dateien behalten Metadaten und Vorschaubild
        by_path = {e["path"]: e for e in self._all_files}
        extra = [by_path[p] for p in self._pinned if p in by_path and p not in {e["path"] for e in entries}]
        self._pinned = {e["path"] for e in extra}

        sem = asyncio.Semaphore(3)
        files = await asyncio.gather(*(self._file_info(e, sem) for e in entries))
        pinned = await asyncio.gather(*(self._file_info(e, sem) for e in extra))

        keep = {(e["path"], float(e.get("modified") or 0)) for e in [*entries, *extra]}
        for stale in [k for k in self._file_cache if k not in keep]:
            del self._file_cache[stale]
        await self.hass.async_add_executor_job(
            self._prune_thumbs, {Path(f["thumb"]).name for f in [*files, *pinned] if f["thumb"]}
        )
        return list(files)

    async def _file_info(self, entry: dict[str, Any], sem: asyncio.Semaphore) -> dict[str, Any]:
        key = (entry["path"], float(entry.get("modified") or 0))
        if key in self._file_cache:
            return self._file_cache[key]
        async with sem:
            try:
                meta = await self.client.file_metadata(entry["path"])
            except MoonrakerError as err:
                _LOGGER.debug("Keine Metadaten fuer %s: %s", entry["path"], err)
                meta = {}
            info = describe_file(entry["path"], entry, meta)
            info["thumb"] = await self._cache_thumbnail(entry["path"], key, meta)
        self._file_cache[key] = info
        return info

    # ── Dateiverwaltung ────────────────────────────────────────────────────
    async def async_file_details(self, path: str) -> dict[str, Any]:
        """Metadaten einer (auch aelteren) Datei, z. B. aus der Suche der Karte."""
        entry = next((e for e in self._all_files if e["path"] == path), None)
        if entry is None:
            raise HomeAssistantError(f"Datei {path} gibt es auf dem Drucker nicht.")
        info = await self._file_info(entry, asyncio.Semaphore(1))
        self._pinned.add(path)
        return info

    def _check_file_change(self, path: str) -> None:
        active = self._print_state.get("active") or {}
        if self.current_print_state() in ACTIVE_PRINT_STATES and path in (active.get("file"), active.get("source")):
            raise HomeAssistantError("Die Datei wird gerade gedruckt.")
        if any(j.get("file") == path for j in self.queue.jobs):
            raise HomeAssistantError("Die Datei steht in der Warteschlange.")

    async def async_delete_file(self, path: str) -> None:
        self._check_file_change(path)
        try:
            await self.client.delete_file(path)
        except MoonrakerError as err:
            raise HomeAssistantError(str(err)) from err
        self._pinned.discard(path)
        self._force_files = True
        await self.async_request_refresh()

    async def async_move_file(self, source: str, dest: str) -> None:
        self._check_file_change(source)
        dest = dest.strip().lstrip("/")
        if not dest or ".." in dest.split("/"):
            raise HomeAssistantError("Ungültiges Ziel.")
        if not dest.lower().endswith(PRINTABLE_SUFFIXES):
            dest += posixpath.splitext(source)[1]
        try:
            await self.client.move_file(source, dest)
        except MoonrakerError as err:
            raise HomeAssistantError(str(err)) from err
        self._force_files = True
        await self.async_request_refresh()

    @property
    def _own_dir(self) -> Path:
        # Eigenes Unterverzeichnis je Drucker: Aufraeumen trifft nie fremde Bilder.
        return self.thumb_dir / self.config_entry.entry_id

    async def _cache_thumbnail(
        self, path: str, key: tuple[str, float], meta: dict[str, Any]
    ) -> str | None:
        relative = pick_thumbnail(meta)
        if not relative:
            return None
        # Name aus Hash von Pfad und Aenderungszeit: nicht erratbar, und eine
        # neue Dateiversion bekommt automatisch eine neue URL (kein Browser-Cache).
        digest = hashlib.sha1(f"{key[0]}|{key[1]}".encode()).hexdigest()[:20]
        name = f"{digest}{Path(relative).suffix or '.png'}"
        target = self._own_dir / name
        if not await self.hass.async_add_executor_job(target.exists):
            try:
                blob = await self.client.download(thumbnail_source(path, relative))
            except MoonrakerError as err:
                _LOGGER.debug("Vorschaubild fuer %s fehlt: %s", path, err)
                return None
            await self.hass.async_add_executor_job(_write, target, blob)
        return f"{THUMB_URL}/{self.config_entry.entry_id}/{name}"

    def _prune_thumbs(self, keep: set[str]) -> None:
        folder = self._own_dir
        if not folder.is_dir():
            return
        for item in folder.iterdir():
            if item.is_file() and item.name not in keep:
                item.unlink(missing_ok=True)


def _write(target: Path, blob: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(blob)
    tmp.replace(target)



def head_index(name: Any) -> int | None:
    """'extruder' -> 0, 'extruder2' -> 2; sonst None."""
    if not isinstance(name, str) or not name.startswith("extruder"):
        return None
    rest = name[len("extruder"):]
    if rest == "":
        return 0
    return int(rest) if rest.isdigit() else None


def _position(vsd: dict[str, Any], meta: dict[str, Any] | None) -> int | None:
    """Dateiposition; passt sie nicht zur Datei (anderer Stand), ueber den Fortschritt."""
    pos, progress = vsd.get("file_position"), vsd.get("progress")
    size = (meta or {}).get("size")
    if isinstance(pos, (int, float)) and (not size or 0 <= pos <= size):
        return int(pos)
    if isinstance(progress, (int, float)) and size:
        return int(progress * size)
    return None


_RELEASE = re.compile(r"Release firmware version v?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)


def version_tuple(text: str | None) -> tuple[int, ...]:
    m = re.search(r"(\d+(?:\.\d+)+)", text or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def latest_release(commits: Any) -> dict[str, Any] | None:
    """Neuester "Release firmware version x.y.z"-Commit einer GitHub-Commitliste."""
    best = None
    for c in commits if isinstance(commits, list) else []:
        msg = ((c.get("commit") or {}).get("message") or "").splitlines()[0] if isinstance(c, dict) else ""
        m = _RELEASE.search(msg)
        if not m:
            continue
        item = {"version": m.group(1), "url": c.get("html_url"),
                "date": ((c.get("commit") or {}).get("committer") or {}).get("date")}
        if best is None or version_tuple(item["version"]) > version_tuple(best["version"]):
            best = item
    return best


def _takeover(slots: list[dict[str, Any]], head: int, ptc: dict[str, Any]) -> int | None:
    """Kopf, von dem die Firmware bei leerer Spule automatisch nachfuellt (oder None)."""
    if not ptc.get("auto_replenish_filament", True):
        return None
    me = next((s for s in slots if s.get("index") == head), None)
    if not me or not me.get("type"):
        return None
    ignore_color = bool(ptc.get("replenish_ignore_color"))
    for slot in slots:
        if slot.get("index") == head or not slot.get("loaded"):
            continue
        if slot.get("type") != me.get("type"):
            continue
        if not ignore_color and (slot.get("color") or "").upper() != (me.get("color") or "").upper():
            continue
        return slot["index"]
    return None


def remaining_seconds(duration: Any, progress: Any) -> float | None:
    """Restzeit aus bisheriger Druckdauer und Dateifortschritt (grob, ab 5 %)."""
    if not isinstance(duration, (int, float)) or not isinstance(progress, (int, float)):
        return None
    if not 0.05 <= progress < 1 or duration <= 0:
        return None
    return duration * (1 - progress) / progress


def notify_message(info: dict[str, Any], de: bool = True) -> str:
    """Kurzer Text fuer die Benachrichtigung."""
    name = str(info.get("name") or info.get("file") or ("Druck" if de else "Print"))
    if info.get("text"):
        return f"{info['text']}\n{name}"
    if info.get("runout"):
        r = info["runout"]
        if de:
            text = f"Kopf {r['head']}: Spule in etwa {r['minutes']} min leer."
            text += (f" Kopf {r['takeover']} (gleiches Filament) übernimmt automatisch." if r.get("takeover")
                     else " Ohne gleiches Filament auf einem anderen Kopf pausiert der Druck.")
        else:
            text = f"Head {r['head']}: spool empty in about {r['minutes']} min."
            text += (f" Head {r['takeover']} (same filament) takes over automatically." if r.get("takeover")
                     else " Without the same filament on another head the print will pause.")
        return f"{text}\n{name}"
    if info.get("bed") is not None:
        return (f"{name} – Bett {info['bed']} °C, Teil kann runter." if de
                else f"{name} – bed {info['bed']} °C, part can be removed.")
    if info.get("left_min"):
        return f"{name} – {'noch etwa' if de else 'about'} {info['left_min']} min"
    if info.get("short"):
        rows = [
            (f"Kopf {s['head']}: braucht {s['need']} g, Spule hat {s['rest']} g" if de
             else f"Head {s['head']}: needs {s['need']} g, spool has {s['rest']} g")
            for s in info["short"]
        ]
        return f"{name}\n" + "\n".join(rows)
    if info.get("queue"):
        n = info["queue"]
        if de:
            return f"{info.get('name')} – Druckbett räumen und in der Karte starten ({n} in der Warteschlange)."
        return f"{info.get('name')} – clear the bed and start it from the card ({n} queued)."
    parts = [str(info.get("name") or info.get("file") or ("Druck" if de else "Print"))]
    duration = info.get("duration")
    if duration:
        hours, rest = divmod(int(duration), 3600)
        parts.append(f"{hours} h {rest // 60} min" if hours else f"{rest // 60} min")
    if info.get("filament_g") is not None:
        parts.append(f"{info['filament_g']:.0f} g")
    if info.get("energy") is not None:
        parts.append(f"{info['energy']:.2f} kWh")
    if info.get("total_cost") is not None:
        parts.append(f"{info['total_cost']:.2f} €".replace(".", ","))
    if info.get("switches"):
        parts.append(f"{info['switches']} {'Wechsel' if de else 'changes'}")
    return " · ".join(parts)


def _prune_dir(folder: Path, keep: set[str]) -> None:
    if not folder.is_dir():
        return
    for item in folder.iterdir():
        if item.is_file() and item.name not in keep:
            item.unlink(missing_ok=True)
