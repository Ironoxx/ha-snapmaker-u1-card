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

from .. import resource
from ..api import (
    MoonrakerError,
)
from ..backup import backup_config, list_snapshots
from ..const import (
    BACKUP_DIR,
    CONF_BACKUP,
    CONF_ENERGY_SENSOR,
    CONF_MAINTENANCE,
    CONF_MAINTENANCE_MONTHS,
    CONF_NOTIFY,
    CONF_NOTIFY2,
    CONF_POWER_SENSOR,
    CONF_POWER_SWITCH,
    DEFAULT_BACKUP,
    DOMAIN,
    FIRMWARE_CHECK_S,
    FIRMWARE_REPOS,
    PAXX_REPO,
)
from ..i18n import tr
from ..stats import MAINTENANCE_ITEMS, build_stats, maintenance_label

_LOGGER = logging.getLogger(__name__)
from .helpers import (
    latest_release,
    parse_firmware_config,
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
            self._job_totals = totals
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

    def _maintenance_status(self, tool_changes: dict[str, Any] | None,
                            cover: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Maintenance items plus the firmware's tool changer counter.

        The air filter item only appears once a top cover was seen (it has the filter).
        """
        filter_hours = None
        if cover and cover.get("present"):
            self._cover_seen = True
            filter_hours = cover.get("filter_hours")
            if self.maintenance.baseline(None, time.time(), filter_hours):
                self._save()
        items = self.maintenance.status(self._print_hours, self.options.get(CONF_MAINTENANCE) or {},
                                        self.options.get(CONF_MAINTENANCE_MONTHS) or {}, time.time(),
                                        has_filter=getattr(self, "_cover_seen", False), filter_hours=filter_hours)
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

    def _check_maintenance_due(self, items: list[dict[str, Any]], printing: bool) -> None:
        """Push once when maintenance items become due; not in the middle of a print.

        Remembered across restarts (``maint_notified``); an item that is done
        again (not due any more) can notify again next time.
        """
        due = {m["key"] for m in items if m.get("due")}
        notified = set(self._maint_notified)
        if notified - due:
            self._maint_notified = sorted(notified & due)
            self._save(30)
        new = sorted(due - notified)
        if not new or printing:
            return
        de = self.hass.config.language.lower().startswith("de")
        labels = [maintenance_label(k, de) for k in new]
        self._notify("maintenance", {"name": "Snapmaker U1", "text": "\n".join(labels), "no_image": True})
        self._maint_notified = sorted(notified | set(new))
        self._save(30)

    def mark_maintenance(self, key: str) -> None:
        """Service: mark a maintenance item as done now."""
        if key not in MAINTENANCE_ITEMS:
            raise HomeAssistantError(tr(self.hass, f"Unbekannter Wartungspunkt: {key}", f"Unknown maintenance item: {key}"))
        cover = (self.data or self._prev).purifier or {}
        self.maintenance.mark_done(key, self._print_hours, time.time(),
                                   cover.get("filter_hours") if cover.get("present") else None)
        self._save()
        if self.data is not None:
            self.data.maintenance = self._maintenance_status(self.data.tool_changes, self.data.purifier)
            self.async_update_listeners()


    # ── Self test ──────────────────────────────────────────────────────────
    async def async_self_test(self, language: str | None = None) -> dict[str, Any]:
        """Check everything the integration needs; returns a list of results.

        ok: True = fine, False = error, None = note (optional/missing).
        """
        de = (language or self.hass.config.language).lower().startswith("de")
        t = (lambda a, b: a) if de else (lambda a, b: b)
        paxx = self.firmware.get("variant") == "paxx12"
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
        # 2.2: which firmware (paxx12 Extended Firmware or stock)
        if self.firmware.get("variant") == "paxx12":
            paxx = self.firmware.get("paxx") or {}
            note = {"login": t("Version unbekannt: Firmware-Config braucht eine Anmeldung (Fluidd)",
                               "Version unknown: Firmware Config needs a login (Fluidd)"),
                    "service_off": t("Version unbekannt: Firmware-Config-Dienst aus (Advanced Mode einschalten)",
                                     "Version unknown: Firmware Config service off (enable Advanced Mode)")}.get(paxx.get("note"))
            add("paxx12", True, t("paxx12 Extended Firmware erkannt", "paxx12 Extended Firmware detected")
                + (f": {paxx['version']}" if paxx.get("version") else "")
                + (f" ({t('Basis', 'base')} {paxx['base']})" if paxx.get("base") else "")
                + (f" – {note}" if note else ""))
        elif self.firmware.get("variant") == "stock":
            add("paxx12", None, t("Snapmaker-Firmware (Stock), keine paxx12 Extended Firmware",
                                  "Snapmaker firmware (stock), no paxx12 Extended Firmware"))
        try:
            space = await self.client.rpc("server.files.get_userdata_space", response_timeout=10)
            free = (space or {}).get("free_space")
            if isinstance(free, (int, float)):
                add("storage", free >= 500, t(f"{free:.0f} MiB frei", f"{free:.0f} MiB free"))
        except MoonrakerError:
            pass
        # Printer values for the card: own (2.0), else the Moonraker integration
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(self.hass)
        mr = [e for e in reg.entities.values() if e.platform == "moonraker" and e.disabled_by is None]
        own = bool(self.data and self.data.machine)
        add("moonraker_integration", bool(mr) or own,
            t("Werte direkt vom Drucker – Moonraker-Integration nicht nötig"
              + (f" ({len(mr)} Entitäten vorhanden, nur Rückfall)" if mr else ""),
              "Values straight from the printer – Moonraker integration not needed"
              + (f" ({len(mr)} entities present, fallback only)" if mr else "")) if own
            else t(f"{len(mr)} Entitäten der Moonraker-Integration", f"{len(mr)} Moonraker integration entities") if mr
            else t("Keine Druckerwerte: Drucker nicht erreichbar", "No printer values: printer not reachable"))
        # 2.4: other cards called "snapmaker-u1-card" (kbaker827's integration, sergey08's card)
        foreign = await resource.async_check_conflict(self.hass)
        if foreign:
            names = ", ".join(foreign)
            add("card_conflict", False, t(
                f"Kartennamen kollidieren mit {names}: beide heißen custom:snapmaker-u1-card. "
                f"Für diese Karte type: {resource.OWN_CARD_TYPE} verwenden.",
                f"Card names collide with {names}: both are called custom:snapmaker-u1-card. "
                f"Use type: {resource.OWN_CARD_TYPE} for this card."))
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
        rtsp = self.webcam.rtsp_url
        add("camera_rtsp", True if rtsp else None,
            t(f"RTSP: {rtsp} (Home Assistant streamt H.264 selbst)", f"RTSP: {rtsp} (Home Assistant streams H.264 itself)")
            if rtsp else (t("RTSP aus (in /firmware-config/ einschaltbar)", "RTSP off (can be enabled in /firmware-config/)")
                          if paxx else t("RTSP aus (gibt es mit der paxx12 Extended Firmware)",
                                         "RTSP off (available with the paxx12 Extended Firmware)")))
        if self.webcam2.mode in ("live", "still"):
            add("camera2", True, t("Zweite Kamera (USB) gefunden", "Second camera (USB) found")
                + (f", RTSP {self.webcam2.rtsp_url}" if self.webcam2.rtsp_url else ""))
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
        targets = list(self.options.get(CONF_NOTIFY) or [])
        targets += [x for x in self.options.get(CONF_NOTIFY2) or [] if x not in targets]
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
            mgr = self.spools
            if mgr.external_booking and not mgr.spoollink:
                detail = t("Moonraker hat Spoolman, aber ohne SpoolLink: Moonraker bucht nur seine aktive Spule ab, "
                           "die übrigen Spulen bucht die Integration nach dem Druck"
                           + ("" if mgr.deduct else " (Abbuchen ist in den Einstellungen aus)")
                           + (". Für Live-Abbuchung aller Köpfe SpoolLink in /firmware-config/ einschalten" if paxx
                              else ". Live-Abbuchung aller Köpfe gibt es mit SpoolLink der paxx12 Extended Firmware"),
                           "Moonraker has Spoolman but no SpoolLink: it only books its active spool, the integration "
                           "books the other spools after the print"
                           + ("" if mgr.deduct else " (booking is off in the settings)")
                           + (". For live booking of all heads enable SpoolLink in /firmware-config/" if paxx
                              else ". Live booking of all heads comes with SpoolLink of the paxx12 Extended Firmware"))
            elif mgr.external_booking:
                detail = t("Verbrauch bucht Moonraker (Spoolman im Drucker aktiv), die Integration bucht nicht doppelt",
                           "Moonraker books usage (Spoolman on the printer), the integration does not book twice")
            elif mgr.deduct:
                detail = t("Verbrauch bucht die Integration nach jedem Druck",
                           "The integration books usage after every print")
            else:
                detail = t("Verbrauch wird nicht abgebucht", "Usage is not booked")
            if mgr.spoollink:
                detail += t("; Spule je Kopf vom Drucker (SpoolLink)", "; spool per head from the printer (SpoolLink)")
            add("spoolman_booking", True if (mgr.external_booking or mgr.deduct) else None, detail)
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
        await self._self_test_more(add, t, paxx)
        ok = all(c["ok"] is not False for c in checks)
        return {"ok": ok, "time": dt_util.now().isoformat(), "checks": checks}

    async def _self_test_more(self, add: Any, t: Any, paxx: bool) -> None:
        """2.4: power switch and meter, Spoolman per head, paxx12 health, printer clock,
        maintenance due, status light blueprint."""
        # power switch and power meter
        switch = self.options.get(CONF_POWER_SWITCH)
        if switch:
            st = self.hass.states.get(switch)
            usable = st is not None and st.state not in ("unavailable", "unknown")
            add("power_switch", usable, t(f"Netzschalter {switch}: {st.state if st else 'fehlt'}",
                                          f"Power switch {switch}: {st.state if st else 'missing'}"))
        meter = self.options.get(CONF_POWER_SENSOR)
        if meter:
            st = self.hass.states.get(meter)
            try:
                value = float(st.state) if st else None
            except ValueError:
                value = None
            add("power_meter", True if value is not None else None,
                t(f"Leistungsmesser {meter}: {st.state} {st.attributes.get('unit_of_measurement', '')}".strip()
                  if st else f"Leistungsmesser {meter} fehlt",
                  f"Power meter {meter}: {st.state} {st.attributes.get('unit_of_measurement', '')}".strip()
                  if st else f"Power meter {meter} missing") if value is not None or st is None
                else t(f"Leistungsmesser {meter} liefert keinen Wert ({st.state})",
                       f"Power meter {meter} has no value ({st.state})"))
        # Spoolman per head: a spool on every loaded head, material matching
        if self.spools.enabled and self.spools.online and self.data:
            missing, wrong = [], []
            for slot in self.data.slots or []:
                if not slot.get("loaded"):
                    continue
                info = self.spools.slot_info(slot["index"])
                if not info:
                    missing.append(str(slot["index"] + 1))
                    continue
                mat = str(info.get("material") or "").upper()
                typ = str(slot.get("type") or "").upper()
                if mat and typ and not (mat.startswith(typ) or typ.startswith(mat)):
                    wrong.append(f"{slot['index'] + 1} ({typ} ≠ {mat})")
            if missing or wrong:
                add("spoolman_heads", None, t(
                    (f"Ohne Spule: Kopf {', '.join(missing)}. " if missing else "")
                    + (f"Material passt nicht: Kopf {', '.join(wrong)}" if wrong else ""),
                    (f"No spool: head {', '.join(missing)}. " if missing else "")
                    + (f"Material differs: head {', '.join(wrong)}" if wrong else "")).strip())
            else:
                add("spoolman_heads", True, t("Jeder geladene Kopf hat eine passende Spule",
                                              "Every loaded head has a matching spool"))
        # paxx12: WLAN signal and eMMC wear
        if paxx and self.data:
            m = self.data.machine or {}
            wifi, wear, eol = m.get("wifi_signal"), m.get("emmc_life_used"), m.get("emmc_pre_eol")
            if wifi is not None or wear is not None:
                weak = isinstance(wifi, (int, float)) and wifi < -75
                worn = eol in ("warning", "urgent") or (isinstance(wear, (int, float)) and wear >= 80)
                parts = []
                if wifi is not None:
                    parts.append(t(f"WLAN {wifi} dBm" + (" (schwach)" if weak else ""), f"WLAN {wifi} dBm" + (" (weak)" if weak else "")))
                if wear is not None:
                    parts.append(t(f"eMMC {wear} % verbraucht" + (" – Speicher altert" if worn else ""),
                                   f"eMMC {wear} % used" + (" – storage is wearing out" if worn else "")))
                add("paxx12_health", False if eol == "urgent" else (None if weak or worn else True), " · ".join(parts))
        # printer clock against Home Assistant (end times, history)
        try:
            when = await self.client.server_time()
        except MoonrakerError:
            when = None
        if when is not None:
            diff = abs((dt_util.utcnow() - when).total_seconds())
            add("clock", True if diff < 120 else None,
                t(f"Uhr des Druckers weicht {round(diff)} s von Home Assistant ab", f"Printer clock differs by {round(diff)} s from Home Assistant")
                if diff >= 120 else t("Uhr des Druckers stimmt mit Home Assistant überein", "Printer clock matches Home Assistant"))
        # maintenance due
        due = [i for i in (self.data.maintenance if self.data else None) or [] if i.get("due")]
        if due:
            add("maintenance", None, t(f"Wartung fällig: {', '.join(str(i.get('label') or i.get('key')) for i in due)}",
                                       f"Maintenance due: {', '.join(str(i.get('label') or i.get('key')) for i in due)}"))
        # status light blueprint: installed, used?
        from homeassistant.components.automation import automations_with_blueprint

        path = f"{DOMAIN}/status_light.yaml"
        installed = await self.hass.async_add_executor_job(
            Path(self.hass.config.path("blueprints", "automation", path)).exists)
        used = automations_with_blueprint(self.hass, path) if installed else []
        add("blueprint", True if used else None,
            t(f"Status-Licht-Blueprint in {len(used)} Automation(en) genutzt", f"Status light blueprint used in {len(used)} automation(s)")
            if used else t("Status-Licht-Blueprint installiert, noch keine Automation daraus", "Status light blueprint installed, no automation from it yet")
            if installed else t("Status-Licht-Blueprint nicht installiert", "Status light blueprint not installed"))

    # ── paxx12 Extended Firmware (2.2) ─────────────────────────────────────
    async def _detect_paxx(self) -> None:
        """Which firmware runs: paxx12 Extended Firmware (its /firmware-config/) or stock.

        Stores ``firmware["variant"]`` (paxx12 | stock) and, with paxx12, its version,
        Snapmaker base, profile and active slot. Runs once per connection.
        """
        try:
            code, status = await self.client.firmware_config()
        except MoonrakerError as err:
            _LOGGER.debug("paxx12 check: %s", err)
            return
        if code == 200 and isinstance(status, dict):
            info = parse_firmware_config(status)
        elif code in (401, 403, 502):
            # the page exists, but needs a login or its service is off (advanced mode)
            info = {"variant": "paxx12", "note": "login" if code in (401, 403) else "service_off"}
        else:
            info = {"variant": "stock"}
        changed = info.get("variant") != self.firmware.get("variant") or info.get("version") != self.firmware.get("paxx", {}).get("version")
        self.firmware["variant"] = info.pop("variant")
        self.firmware["paxx"] = info if self.firmware["variant"] == "paxx12" else {}
        if changed:
            _LOGGER.info("Firmware: %s %s", self.firmware["variant"], self.firmware["paxx"].get("version") or "")
            # a different firmware: look up its latest release right away
            self.firmware.setdefault("latest", {})
            if isinstance(self.firmware.get("latest"), dict):
                self.firmware["latest"]["checked"] = 0

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
        """Latest firmware from Snapmaker's release commits (GitHub, no login).

        2.2: with paxx12 also its latest release (GitHub releases of the extended firmware).
        """
        session = async_get_clientsession(self.hass)
        if self.firmware.get("variant") == "paxx12":
            try:
                async with session.get(
                    f"https://api.github.com/repos/{PAXX_REPO}/releases/latest",
                    headers={"Accept": "application/vnd.github+json"}, timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    rel = await resp.json() if resp.status == 200 else None
                if isinstance(rel, dict) and rel.get("tag_name"):
                    self.firmware["paxx_latest"] = {
                        "version": str(rel["tag_name"]).lstrip("v"), "url": rel.get("html_url"),
                        "date": rel.get("published_at")}
            except Exception as err:  # noqa: BLE001 - the check is an extra
                _LOGGER.debug("paxx12 release check: %s", err)
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
