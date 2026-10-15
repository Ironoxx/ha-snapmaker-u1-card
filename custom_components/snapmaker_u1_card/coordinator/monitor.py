"""Watching a running print: layer view, printer messages, print events and the live subscription."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from ..const import (
    CONF_ALMOST_DONE,
    CONF_BED_COOL,
    DEFAULT_ALMOST_DONE,
    DEFAULT_BED_COOL,
    DOMAIN,
    LIVE_INTERVAL,
    RUNOUT_WARN_MIN,
    UPDATE_INTERVAL,
)
from ..errors import error_text
from ..layers import estimate_remaining, parse_layers, timeline_at
from ..parsing import (
    ACTIVE_PRINT_STATES,
    grams_per_slot,
    parse_slots,
)

_LOGGER = logging.getLogger(__name__)
from .helpers import (
    _position,
    _takeover,
    head_index,
    remaining_seconds,
)

_LOGGER = logging.getLogger(__name__)


class PrintMonitorMixin:
    """Watching a running print: layer view, printer messages, print events and the live subscription."""

    # ── Layer view ─────────────────────────────────────────────────────────
    @property
    def layer_store(self) -> Path:
        return self.thumb_dir.parent / "layers" / f"{self.config_entry.entry_id}.jsonl"

    def request_layers(self, print_state: str | None = None) -> None:
        """Download and split the print file once per print (layer view, time profile)."""
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
        """Download the print file and build the layer index (background task)."""
        store = self.layer_store
        # Create and clean up the temp folder in the executor (it would block the event loop)
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
        except Exception as err:  # noqa: BLE001 - the view is an extra and must never interfere
            _LOGGER.info("Layer view for %s not possible: %s", filename, err)
            if self.layer_view.get("key") == key:
                self.layer_view = {"key": key, "status": "error", "file": filename, "error": str(err)}
            return
        finally:
            await self.hass.async_add_executor_job(shutil.rmtree, tmp, True)
        if self.layer_view.get("key") == key:
            self.layer_view = {"key": key, "status": "ready", "file": filename, "meta": meta}
            _LOGGER.debug("Layer view %s: %s layers", filename, meta["total"])

    def layer_colors(self) -> dict[str, Any]:
        """Colours per logical filament (from the file) and mapping to the heads."""
        active = self._print_state.get("active") or {}
        fils = {str(f["index"]): f.get("color") for f in active.get("filaments") or [] if "index" in f}
        data = self.data or self._prev
        return {"file": fils, "map_table": list(active.get("map_table") or data.map_table or [])}

    # ── Printer messages in plain language ─────────────────────────────────
    def _update_errors(self, errors: list[dict[str, Any]]) -> None:
        """Translate open firmware exceptions and remember them for the card."""
        keys = {e["key"] for e in errors}
        self._new_errors = [e for e in errors if e["key"] not in self._error_keys]
        for err in self._new_errors:
            _LOGGER.info("Printer reports: %s (%s, %s)", err["text"]["de"], err["key"], err["message"])
        self._errors, self._error_keys = errors, keys

    def _alert_new(self, errors: list[dict[str, Any]], print_state: str | None, skip: bool) -> None:
        """Push new firmware messages during a print (a pause reports itself)."""
        new = getattr(self, "_new_errors", [])
        if not new or skip or print_state not in ACTIVE_PRINT_STATES:
            return
        active = self._print_state.get("active") or {}
        lang = self.hass.config.language
        self._notify("alert", {"name": active.get("name"), "file": active.get("file"),
                               "text": "\n".join(error_text(e, lang) for e in new)})

    # ── Events during a print ──────────────────────────────────────────────
    def _print_events(self, stats: dict[str, Any], vsd: dict[str, Any]) -> None:
        """First layer done and "almost done", once per print."""
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
            # Only report the change 1 -> 2, not joining in the middle of a print.
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
        """Remaining time: file time profile (calibrated), else duration x rest/progress."""
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
        """Will a spool run out during the print? Time from the profile and Spoolman remainder.

        With auto-replenish (print_task_config.auto_replenish_filament) the
        firmware continues from a head with the same material; if there is
        one, it is named in the message.
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
        """After "complete": notify as soon as the bed is cool enough to remove the part."""
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
        """At print start: is the spool per head (Spoolman remainder) enough for the file?"""
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

    # ── Live subscription ──────────────────────────────────────────────────
    def start_live(self) -> None:
        self.live.start(self.hass)

    def _on_live_state(self, connected: bool) -> None:
        self.update_interval = LIVE_INTERVAL if connected else UPDATE_INTERVAL
        _LOGGER.debug("Live subscription %s", "steht" if connected else "getrennt")
        if self.data is not None:
            self.async_update_listeners()

    def _on_live(self, diff: dict[str, Any]) -> None:
        """Change from the printer: important things now, the rest at the next poll."""
        ps = diff.get("print_stats") or {}
        refresh = "state" in ps or "filename" in ps or "exception_manager" in diff
        if self.data is None or self._starting:
            return
        if "state" in ps and ps["state"] != self.data.print_state:
            # Visible right away (card, voice commands); the poll follows debounced.
            self.data.print_state = ps["state"]
        head = diff.get("toolhead", {}).get("extruder") if isinstance(diff.get("toolhead"), dict) else None
        if head is not None and head_index(head) != self.data.active_head:
            self.data.active_head = head_index(head)
            if not refresh:
                self.async_update_listeners()
        status = self.live.status
        if "print_stats" in diff or "virtual_sdcard" in diff:
            # Keep current for voice answers etc. (without redrawing)
            ps_all = status.get("print_stats") or {}
            info = ps_all.get("info") if isinstance(ps_all.get("info"), dict) else {}
            self.data.progress = (status.get("virtual_sdcard") or {}).get("progress", self.data.progress)
            self.data.print_duration = ps_all.get("print_duration", self.data.print_duration)
            self.data.layer = info.get("current_layer", self.data.layer)
            self._print_events(status.get("print_stats") or {}, status.get("virtual_sdcard") or {})
        if refresh:
            self.hass.async_create_task(self.async_request_refresh(), f"{DOMAIN} live refresh")

    def current_print_state(self) -> str | None:
        """Print state, as fresh as possible (live subscription before the last poll)."""
        if self.live.connected:
            state = (self.live.status.get("print_stats") or {}).get("state")
            if state:
                return state
        return (self.data or self._prev).print_state

    def live_position(self) -> dict[str, Any] | None:
        """File position, layer and head from the live subscription (None = not connected)."""
        if not self.live.connected:
            return None
        st = self.live.status
        info = (st.get("print_stats") or {}).get("info") or {}
        return {
            "position": (st.get("virtual_sdcard") or {}).get("file_position"),
            "layer": info.get("current_layer") if isinstance(info, dict) else None,
            "active_head": head_index((st.get("toolhead") or {}).get("extruder")),
        }
