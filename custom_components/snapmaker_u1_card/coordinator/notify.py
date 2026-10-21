"""Print end, notifications with actions and the result photo."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from ..api import (
    MoonrakerError,
)
from ..const import (
    CONF_AUTO_OFF,
    CONF_CAMERA,
    CONF_NOTIFY,
    CONF_NOTIFY_EVENTS,
    DEFAULT_NOTIFY_EVENTS,
    DOMAIN,
    EVENT_PRINT_FINISHED,
    HISTORY_SIZE,
    THUMB_URL,
)
from ..errors import error_text
from ..jobs import (
    is_pause_copy,
    original_file,
)
from ..parsing import (
    ACTIVE_PRINT_STATES,
    summarize_print,
)

_LOGGER = logging.getLogger(__name__)
from .helpers import (
    AUTO_OFF_RESULTS,
    EARLY_PHOTO_DELAY_S,
    PHOTO_BED_DROP_MM,
    PHOTO_MARGIN_MM,
    PHOTO_WAIT_S,
    RESULT_TEXT,
    RESULT_TEXT_EN,
    _position,
    _prune_dir,
    _write,
    notify_message,
)

_LOGGER = logging.getLogger(__name__)


class NotifyMixin:
    """Print end, notifications with actions and the result photo."""

    # ── Print end and notification ──────────────────────────────────────────
    def _finished(self, record: dict[str, Any]) -> None:
        """A print ended: book it, notify, deduct spools and arm auto-off."""
        if is_pause_copy(record.get("file")):
            copy = record["file"]
            record = {**record, "file": record.get("source") or original_file(copy)}
            self.hass.async_create_task(self._delete_copy(copy), f"{DOMAIN} delete pause copy")
        if record.get("result") == "error" and self._errors:
            record = {**record, "error": error_text(self._errors[0], self.hass.config.language)}
        summary = summarize_print(record, self.filament_prices)
        # Learn for the next remaining-time estimate: start duration and
        # actual / slicer time of the print itself (from the first layer on)
        begin, slicer_s = record.get("begin_s"), record.get("slicer_print_s")
        total = record.get("print_duration")
        if (record.get("result") == "complete" and isinstance(begin, (int, float))
                and isinstance(slicer_s, (int, float)) and slicer_s > 0
                and isinstance(total, (int, float)) and total > begin):
            factor = (total - begin) / slicer_s
            if 0.3 < factor < 3:
                summary["speed_factor"] = round(factor, 3)
                summary["prep_s"] = round(begin)
        booked = self.spools.book(record)
        if booked:
            summary["spools"] = booked
            self.spools.force()  # book at the next poll
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
            _LOGGER.info("Auto-off armed after %s", summary.get("file"))

    def _notify_transition(self, state: str | None, filename: str | None) -> bool:
        """Report a pause (e.g. filament runout). End/error go through _finished."""
        prev, self._last_state = self._last_state, state
        if state == "paused" and prev == "printing":
            active = self._print_state.get("active") or {}
            self._notify("paused", {"file": filename, "name": active.get("name")})
            return True
        return False

    def _notify(self, event: str, info: dict[str, Any]) -> None:
        """Send a notification for ``event`` if it is enabled in the options."""
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
            # The companion app loads the image with its own authentication.
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

    # ── Notification actions (companion app) ───────────────────────────────
    def _action_id(self, name: str) -> str:
        return f"SU1_{name}_{self.config_entry.entry_id}"

    def _actions(self, event: str, de: bool) -> list[dict[str, str]]:
        """Companion app action buttons for an event."""
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
        """Handle a tapped notification button (pause, resume, cancel, light)."""
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
                # Two steps: ask first
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
            _LOGGER.warning("Notification action %s failed: %s", name, err)
            return
        _LOGGER.info("Action from the notification: %s", name)
        await self.async_request_refresh()

    def _light_entity(self) -> str | None:
        """Light entity of the Moonraker integration for this printer, if any."""
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(self.hass)
        hits = [e.entity_id for e in reg.entities.values()
                if e.domain == "light" and e.platform == "moonraker" and "cavity_led" in e.entity_id]
        return hits[0] if hits else None

    # ── Result photo ───────────────────────────────────────────────────────
    def _maybe_early_photo(self, active: dict[str, Any], stats: dict[str, Any], vsd: dict[str, Any]) -> None:
        """Result photo right after the last extrusion, before the end G-code lowers the bed.

        With a time profile: as soon as the file position reaches the last
        extrusion (live subscription, 250 ms). Without a profile: in the last
        layer from 99.5 %.
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
        _LOGGER.debug("Result photo after the last extrusion: %s", target.name)
        box = None
        if meta:
            objs = meta.get("objects") or []
            box = ([min(o[0] for o in objs), min(o[1] for o in objs), max(o[2] for o in objs), max(o[3] for o in objs)]
                   if objs else meta.get("bbox"))
        self.hass.async_create_background_task(self._photo_when_clear(camera, target, box),
                                               f"{DOMAIN} result photo")

    async def _photo_when_clear(self, camera: str, target: Path, box: list[float] | None) -> None:
        """Take the result photo once the head has left the part, before the bed goes down.

        The end sequence (PRINT_END) parks the head and lowers the bed within
        ~10-15 s. The head position is polled (motion_report) for at most
        PHOTO_WAIT_S: the photo is taken as soon as the head is PHOTO_MARGIN_MM
        outside the parts' outline, or the bed has already dropped noticeably.
        Without an outline or position: after EARLY_PHOTO_DELAY_S as before.
        The chamber light is switched on for the photo and back off afterwards.
        """
        light = self._light_entity()
        light_was_off = bool(light and (st := self.hass.states.get(light)) and st.state == "off")
        if light_was_off:
            await self.hass.services.async_call("light", "turn_on", {ATTR_ENTITY_ID: light}, blocking=False)
        await asyncio.sleep(EARLY_PHOTO_DELAY_S)
        if box:
            deadline = time.monotonic() + PHOTO_WAIT_S
            z0 = None
            misses = 0
            while time.monotonic() < deadline and misses < 2:
                try:
                    st = await self.client.query_objects("motion_report", fields={"motion_report": ("live_position",)})
                    pos = (st.get("motion_report") or {}).get("live_position") or []
                except MoonrakerError:
                    pos = []
                if len(pos) < 3:
                    misses += 1  # no motion_report: do not wait for nothing
                else:
                    x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
                    z0 = z if z0 is None else z0
                    outside = (x < box[0] - PHOTO_MARGIN_MM or x > box[2] + PHOTO_MARGIN_MM
                               or y < box[1] - PHOTO_MARGIN_MM or y > box[3] + PHOTO_MARGIN_MM)
                    if outside or z - z0 > PHOTO_BED_DROP_MM:
                        break
                await asyncio.sleep(0.5)
        await self._save_photo(camera, target)
        if light_was_off:
            await self.hass.services.async_call("light", "turn_off", {ATTR_ENTITY_ID: light}, blocking=False)

    def _photo_target(self) -> tuple[str, Path]:
        stamp = dt_util.now().strftime("%Y%m%d_%H%M%S")
        return (f"{THUMB_URL}/{self.config_entry.entry_id}/results/{stamp}.jpg",
                self._own_dir / "results" / f"{stamp}.jpg")

    def _result_photo_url(self, summary: dict[str, Any]) -> str | None:
        """Result photo: the one taken after the last extrusion, else now (cancel, error)."""
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
        """Save a camera snapshot to ``target`` after an optional delay."""
        if delay:
            await asyncio.sleep(delay)
        try:
            from homeassistant.components.camera import async_get_image

            image = await async_get_image(self.hass, camera, timeout=15)
        except (HomeAssistantError, ImportError) as err:
            _LOGGER.info("Result photo not possible: %s", err)
            return
        keep = {Path(str(h.get("photo"))).name for h in self._history() if h.get("photo")} | {target.name}

        def _store() -> None:
            _write(target, image.content)
            _prune_dir(target.parent, keep)

        await self.hass.async_add_executor_job(_store)
