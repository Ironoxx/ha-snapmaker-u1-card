"""Statistics, maintenance, self test, firmware check and config backup."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import aiohttp
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from ..api import (
    MoonrakerError,
)
from ..backup import backup_config, list_snapshots
from ..const import (
    BACKUP_DIR,
    CONF_BACKUP,
    CONF_ENERGY_SENSOR,
    CONF_MAINTENANCE,
    CONF_NOTIFY,
    CONF_POWER_SWITCH,
    DEFAULT_BACKUP,
    DOMAIN,
    FIRMWARE_CHECK_S,
    FIRMWARE_REPOS,
)
from ..i18n import tr
from ..stats import MAINTENANCE_ITEMS, build_stats

_LOGGER = logging.getLogger(__name__)
from .helpers import (
    latest_release,
    version_tuple,
)

_LOGGER = logging.getLogger(__name__)


class UpkeepMixin:
    """Statistics, maintenance, self test, firmware check and config backup."""

    # ── Statistics and maintenance ─────────────────────────────────────────
    async def _update_stats(self) -> None:
        """Rebuild statistics and print hours from Moonraker's history."""
        self._stats_at = time.monotonic()
        self._force_stats = False
        try:
            jobs = await self.client.history()
            totals = await self.client.history_totals()
        except MoonrakerError as err:
            _LOGGER.debug("Print history not readable: %s", err)
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
        """Maintenance items plus the firmware's tool changer counter."""
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
        """Service: mark a maintenance item as done now."""
        if key not in MAINTENANCE_ITEMS:
            raise HomeAssistantError(tr(self.hass, f"Unbekannter Wartungspunkt: {key}", f"Unknown maintenance item: {key}"))
        self.maintenance.mark_done(key, self._print_hours, time.time())
        self._save()
        if self.data is not None:
            self.data.maintenance = self._maintenance_status(self.data.tool_changes)
            self.async_update_listeners()


    # ── Self test ──────────────────────────────────────────────────────────
    async def async_self_test(self, language: str | None = None) -> dict[str, Any]:
        """Check everything the integration needs; returns a list of results.

        ok: True = fine, False = error, None = note (optional/missing).
        """
        de = (language or self.hass.config.language).lower().startswith("de")
        t = (lambda a, b: a) if de else (lambda a, b: b)
        checks: list[dict[str, Any]] = []

        def add(key: str, ok: bool | None, detail: str) -> None:
            checks.append({"key": key, "ok": ok, "detail": detail})

        # printer and Klipper
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
        # Moonraker integration (temperatures, camera, light in the card)
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(self.hass)
        mr = [e for e in reg.entities.values() if e.platform == "moonraker"]
        add("moonraker_integration", bool(mr),
            t(f"{len(mr)} Entitäten der Moonraker-Integration", f"{len(mr)} Moonraker integration entities") if mr
            else t("Moonraker-Integration fehlt: Temperaturen, Licht und Kamera fehlen in der Karte",
                   "Moonraker integration missing: no temperatures, light or camera in the card"))
        # camera: detection of the own camera entity, then an image from the camera in use
        mode = self.webcam.mode
        mode_text = {
            "live": t("Livestream", "live stream"),
            "still": t("Standbilder (Snapshot)", "still images (snapshot)"),
            "wake": t("Standbilder, Stock-Firmware (wird geweckt)", "still images, stock firmware (woken up)"),
            "none": t("keine Kamera gefunden", "no camera found"),
        }.get(mode, t("noch nicht erkannt", "not detected yet"))
        why = f" – Stream: {self.webcam.stream_error}" if mode != "live" and self.webcam.stream_error else ""
        add("camera_detect", mode in ("live", "still", "wake") or (None if mode == "unknown" else False),
            t(f"Kamera erkannt: {mode_text}{why}", f"Camera detected: {mode_text}{why}"))
        camera = self.camera_entity()
        if not camera:
            add("camera", None, t("Keine Kamera (Bild in Push und Ergebnisfoto fehlen)",
                                  "No camera (no image in push and no result photo)"))
        else:
            try:
                from homeassistant.components.camera import async_get_image

                img = await async_get_image(self.hass, camera, timeout=10)
                add("camera", True, t(f"{camera}: Bild {len(img.content) // 1024} kB", f"{camera}: image {len(img.content) // 1024} kB"))
            except (HomeAssistantError, ImportError) as err:
                add("camera", False, f"{camera}: {err}")
        # power
        for key, conf, label in (("power_switch", CONF_POWER_SWITCH, t("Netzschalter", "Power switch")),
                                 ("energy", CONF_ENERGY_SENSOR, t("Energiezähler", "Energy meter"))):
            entity = self.options.get(conf)
            if not entity:
                add(key, None, t(f"{label}: nicht eingerichtet", f"{label}: not set up"))
                continue
            st = self.hass.states.get(entity)
            good = st is not None and st.state not in ("unavailable", "unknown")
            add(key, good, f"{label}: {entity} = {st.state if st else t('fehlt', 'missing')}")
        price, source = self.energy_price_source
        label = t("Strompreis", "Energy price")
        if source is None:
            add("price", None, t(f"{label}: nicht eingerichtet (Entität, fester Preis oder Energie-Dashboard)",
                                 f"{label}: not set up (entity, fixed price or energy dashboard)"))
        else:
            fixed = t("fester Preis", "fixed price")
            if source.startswith("energy:"):
                inner = source.removeprefix("energy:")
                where = t("Energie-Dashboard", "energy dashboard") + f" ({fixed if inner == 'fixed' else inner})"
            else:
                where = fixed if source == "fixed" else source
            value = f"{price:.4f}".rstrip("0").rstrip(".") + "/kWh" if price is not None else t("fehlt", "missing")
            add("price", price is not None, f"{label}: {where} = {value}")
        # notifications
        targets = self.options.get(CONF_NOTIFY) or []
        if not targets:
            add("notify", None, t("Keine Benachrichtigung eingerichtet", "No notifications set up"))
        for target in targets:
            name = str(target).removeprefix("notify.")
            add("notify", self.hass.services.has_service("notify", name),
                f"notify.{name}" + ("" if self.hass.services.has_service("notify", name) else t(" fehlt", " missing")))
        # Spoolman
        if self.spools.enabled:
            await self.spools.async_refresh()
            okay = self.spools.online  # async_refresh returns "state changed", not reachability
            add("spoolman", okay, t(f"Spoolman: {len(self.spools.spools)} Spulen", f"Spoolman: {len(self.spools.spools)} spools")
                if okay else t(f"Spoolman nicht erreichbar ({self.spools.client.url}): {self.spools.error or '?'}",
                               f"Spoolman unreachable ({self.spools.client.url}): {self.spools.error or '?'}"))
        # Assist
        sentences = Path(self.hass.config.path("custom_sentences", "de", f"{DOMAIN}.yaml"))
        exists = await self.hass.async_add_executor_job(sentences.exists)
        add("assist", True if exists else None, t("Sätze für Assist vorhanden", "Assist sentences present") if exists
            else t("Keine Sätze für Assist (wird beim nächsten Start angelegt)", "No Assist sentences (created on next start)"))
        # timelapse backup
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

    # ── Firmware check ─────────────────────────────────────────────────────
    def _start_firmware_check(self) -> None:
        """Check for new firmware in the background, at most once a day."""
        latest = self.firmware.get("latest") or {}
        if self._fw_task and not self._fw_task.done():
            return
        if time.time() - float(latest.get("checked") or 0) < FIRMWARE_CHECK_S:
            return
        self._fw_task = self.hass.async_create_background_task(
            self.async_check_firmware(), f"{DOMAIN} firmware check"
        )

    async def async_check_firmware(self) -> dict[str, Any] | None:
        """Latest firmware from Snapmaker's release commits (GitHub, no login)."""
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
            except Exception as err:  # noqa: BLE001 - the check is an extra
                _LOGGER.debug("Firmware check %s: %s", repo, err)
                continue
            found = latest_release(commits)
            if found and (best is None or version_tuple(found["version"]) > version_tuple(best["version"])):
                best = found
        prev = self.firmware.get("latest") or {}
        # Without a result (offline, rate limit) retry in an hour
        checked = time.time() if best else time.time() - FIRMWARE_CHECK_S + 3600
        self.firmware["latest"] = {**(best or {k: prev.get(k) for k in ("version", "url", "date")}),
                                   "checked": checked}
        self._save()
        self.async_update_listeners()
        return best

    # ── Config backup (backup.py) ──────────────────────────────────────────
    @property
    def backup_folder(self) -> Path:
        return Path(self.hass.config.path(BACKUP_DIR)) / self.client.host.replace(":", "_")

    def _backup_data(self) -> dict[str, Any] | None:
        """Config backup status for the card (None if never enabled)."""
        if not self.options.get(CONF_BACKUP, DEFAULT_BACKUP) and not self._backup:
            return None
        return {"enabled": bool(self.options.get(CONF_BACKUP, DEFAULT_BACKUP)),
                **{k: self._backup.get(k) for k in ("snapshot", "saved_at", "checked_at", "status", "files")},
                "folder": f"{BACKUP_DIR}/{self.backup_folder.name}"}

    def _start_backup(self) -> None:
        """Start the daily config backup in the background when due."""
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
        """Service: back up the printer configuration now."""
        try:
            result = await backup_config(self.hass, self.client, self.backup_folder, self._backup.get("digest"))
        except MoonrakerError as err:
            _LOGGER.debug("Config backup failed: %s", err)
            self._backup = {**self._backup, "checked_at": time.time() - 86400 + 3600, "status": "error"}
            raise HomeAssistantError(tr(self.hass, f"Konfig-Sicherung fehlgeschlagen: {err}", f"Config backup failed: {err}")) from err
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
