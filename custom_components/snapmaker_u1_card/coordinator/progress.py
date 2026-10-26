"""Ongoing progress notification on Android (companion app) with a push budget.

The notification shows a progress bar and a countdown to the expected end.
The countdown runs on the phone (``chronometer`` + ``when``), so the remaining
time needs no pushes. Updates are only sent when something the user would
notice changes:

- the progress crosses a 10 % step,
- the expected end moves by more than max(5 min, 10 % of the remaining time),
- the print is paused or resumed.

Limits keep the companion app's daily push quota (about 500 per device via the
cloud relay) free for the important notifications: at most one update every
``MIN_GAP_S``, at most ``MAX_PER_PRINT`` per print and a daily budget
(option, counted per UTC day like the relay). Pause/resume ignore the gap.
End, error and pause notifications never go through this budget. At the end
the notification is removed (one more push, outside the budget).
"""

from __future__ import annotations

import logging
import math
import time
from datetime import UTC, datetime
from typing import Any

from homeassistant.util import slugify

from ..const import (
    CONF_LIVE_BUDGET,
    CONF_LIVE_IMAGE,
    CONF_NOTIFY,
    DEFAULT_LIVE_BUDGET,
    DEFAULT_LIVE_IMAGE,
    DOMAIN,
    LIVE_IMAGES,
)

_LOGGER = logging.getLogger(__name__)

MIN_GAP_S = 180
MAX_PER_PRINT = 25
STEP_PCT = 10
DRIFT_MIN_S = 300
DRIFT_SHARE = 0.10
CHANNEL = "Snapmaker U1 Fortschritt"


def utc_day() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class ProgressNotifyMixin:
    """Ongoing progress notification with push budget."""

    # ── State (persisted: enabled flag and today's count) ───────────────────
    def _live_image(self) -> str | None:
        """Image of the progress notification: camera (refreshed every update) or the model preview."""
        mode = self.options.get(CONF_LIVE_IMAGE, DEFAULT_LIVE_IMAGE)
        if mode is True:
            mode = "camera"
        elif mode is False or mode not in LIVE_IMAGES:
            mode = "off"
        if mode == "thumbnail":
            thumb = (self._print_state.get("active") or {}).get("thumb")
            if thumb:
                return str(thumb)  # static path of the integration, loads without login
            mode = "camera"  # no preview in the file: camera instead
        if mode == "camera":
            camera = self.camera_entity()
            return f"/api/camera_proxy/{camera}?ts={int(time.time())}" if camera else None
        return None

    def _live_init(self, stored: dict[str, Any] | None) -> None:
        saved = (stored or {}).get("live_notify") or {}
        self.live_notify_on = bool(saved.get("enabled"))
        self._ln_day = saved.get("day") or utc_day()
        self._ln_count = int(saved.get("count") or 0)
        self._ln: dict[str, Any] = {}

    def _live_stored(self) -> dict[str, Any]:
        return {"enabled": self.live_notify_on, "day": self._ln_day, "count": self._ln_count}

    @property
    def live_budget(self) -> int:
        return int(self.options.get(CONF_LIVE_BUDGET, DEFAULT_LIVE_BUDGET) or 0)

    def live_sent_today(self) -> int:
        if self._ln_day != utc_day():
            self._ln_day, self._ln_count = utc_day(), 0
        return self._ln_count

    def live_status(self) -> dict[str, Any]:
        return {
            "sent_today": self.live_sent_today(),
            "budget": self.live_budget,
            "sent_this_print": self._ln.get("sent", 0),
            "targets": [f"notify.{t}" for t in self._live_targets()],
        }

    async def async_set_live_notify(self, on: bool) -> None:
        self.live_notify_on = on
        if not on and self._ln.get("sent"):
            self._live_clear()
        self._save()
        self.async_update_listeners()

    # ── Targets: Android devices among the notification targets ─────────────
    def _live_targets(self) -> list[str]:
        """mobile_app services from the notification targets that belong to Android devices.

        iOS has no chronometer/progress in notifications (it uses Live
        Activities), and other notify services know none of these fields.
        """
        android = {}
        for entry in self.hass.config_entries.async_entries("mobile_app"):
            name = entry.data.get("device_name")
            if name:
                android[f"mobile_app_{slugify(name)}"] = str(entry.data.get("os_name", "")).lower()
        out = []
        for target in self.options.get(CONF_NOTIFY) or []:
            service = str(target).removeprefix("notify.")
            if not service.startswith("mobile_app_"):
                continue
            if android.get(service, "android") != "android":
                continue
            out.append(service)
        return out

    # ── Called on every poll ────────────────────────────────────────────────
    def _live_tick(self, print_state: str | None, active: dict[str, Any] | None,
                   progress: float | None, remaining: float | None,
                   layer: int | None, total_layers: int | None) -> None:
        running = print_state in ("printing", "paused") and active
        key = f"{(active or {}).get('file')}|{(active or {}).get('started')}" if active else None
        if self._ln.get("key") and self._ln.get("key") != key:
            # print over (or a new one started): remove the ongoing notification
            if self._ln.get("sent"):
                self._live_clear()
            self._ln = {}
        if not running or not self.live_notify_on:
            return
        targets = self._live_targets()
        if not targets:
            return
        ln = self._ln
        if not ln:
            ln.update(key=key, sent=0, step=-1, eta=None, state=None, at=0.0)
        # Wait for the start sequence to finish: before that the end time is vague
        if print_state == "printing" and ln["sent"] == 0 and remaining is None:
            return
        if print_state == "printing" and ln["sent"] == 0 and "begin_s" not in (active or {}):
            return
        now = time.monotonic()
        pct = max(0, min(100, int((progress or 0) * 100)))
        step = pct // STEP_PCT
        eta = time.time() + remaining if remaining is not None else None
        state_changed = ln["state"] is not None and ln["state"] != print_state
        reason = None
        if ln["sent"] == 0 or state_changed:
            reason = "state" if state_changed else "start"
        elif print_state == "printing":
            if step > ln["step"]:
                reason = "step"
            elif (eta is not None and ln["eta"] is not None and remaining is not None
                  and abs(eta - ln["eta"]) > max(DRIFT_MIN_S, DRIFT_SHARE * remaining)):
                reason = "drift"
        if reason is None:
            return
        if reason not in ("start", "state") and now - ln["at"] < MIN_GAP_S:
            return
        if ln["sent"] >= MAX_PER_PRINT and reason != "state":
            return
        if self.live_sent_today() >= self.live_budget:
            return
        self._live_send(targets, active or {}, print_state, pct, eta, layer, total_layers)
        ln.update(sent=ln["sent"] + 1, step=step, eta=eta, state=print_state, at=now)
        self._ln_count += 1
        self._save(30)

    # ── Sending ─────────────────────────────────────────────────────────────
    def _live_tag(self) -> str:
        return f"{DOMAIN}_live_{self.config_entry.entry_id}"

    def _live_send(self, targets: list[str], active: dict[str, Any], print_state: str | None,
                   pct: int, eta: float | None, layer: int | None, total_layers: int | None) -> None:
        de = self.hass.config.language.lower().startswith("de")
        name = str(active.get("name") or active.get("file") or "Snapmaker U1")
        parts = [f"{pct} %"]
        if isinstance(layer, int) and isinstance(total_layers, int) and total_layers > 0:
            parts.append(f"{'Schicht' if de else 'Layer'} {layer}/{total_layers}")
        paused = print_state == "paused"
        if paused:
            parts.append("Pausiert" if de else "Paused")
        elif eta is not None:
            local = datetime.fromtimestamp(eta).astimezone()
            parts.append(f"{'fertig ~' if de else 'done ~'}{local:%H:%M}")
        data: dict[str, Any] = {
            "tag": self._live_tag(),
            "channel": CHANNEL,
            "importance": "low",
            "alert_once": True,
            "sticky": True,
            "notification_icon": "mdi:printer-3d-nozzle",
            "progress": pct,
            "progress_max": 100,
            "live_update": True,
            "critical_text": f"{pct}%",
        }
        # Larger view: camera image when the notification is expanded (refreshed
        # with every update, no extra push); tap opens the configured dashboard.
        image = self._live_image()
        if image:
            data["image"] = image
        data.update(self._click_data())
        if eta is not None and not paused:
            data["chronometer"] = True
            data["when"] = math.ceil(eta)
            data["when_relative"] = False
        for service in targets:
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service, {"title": name, "message": " · ".join(parts), "data": data},
                    blocking=False,
                ),
                f"{DOMAIN} progress {service}",
            )

    def _live_clear(self) -> None:
        for service in self._live_targets():
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "notify", service, {"message": "clear_notification", "data": {"tag": self._live_tag()}},
                    blocking=False,
                ),
                f"{DOMAIN} progress clear {service}",
            )
