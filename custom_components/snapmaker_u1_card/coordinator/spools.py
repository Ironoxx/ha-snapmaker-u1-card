"""Spoolman spools: sync, assignment, consumption and run-out warnings."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..api import (
    MoonrakerError,
)
from ..const import (
    CONF_SPOOLMAN_LOW,
    DEFAULT_SPOOLMAN_LOW,
    SPOOLMAN_INTERVAL_S,
)
from ..i18n import tr
from ..jobs import (
    original_file,
)
from ..parsing import (
    ACTIVE_PRINT_STATES,
    describe_file,
    parse_file_filaments,
)
from .data import U1Data

_LOGGER = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)


class SpoolMixin:
    """Spoolman spools: sync, assignment, consumption and run-out warnings."""

    # ── Spoolman ────────────────────────────────────────────────────────────
    async def _update_spools(self, data: U1Data, ptc: dict[str, Any]) -> None:
        """Refresh Spoolman and keep the spool-per-head assignment current."""
        mgr = self.spools
        if mgr.enabled:
            if mgr.due(SPOOLMAN_INTERVAL_S) and await mgr.async_refresh():
                self._mark_booked()
                self._save()
            if mgr.assign(data.slots):
                self._save()
        # What the running print needs to book usage per head later:
        # map table logical->head and the spool per head.
        active = self._print_state.get("active")
        if active and not active.get("pending") and data.print_state in ACTIVE_PRINT_STATES:
            active["map_table"] = list(ptc.get("extruder_map_table") or [])
            if mgr.enabled:
                active["spool_ids"] = {str(k): v for k, v in mgr.assigned().items()}
        data.spoolman = self._spoolman_data(data.slots)

    def _mark_booked(self) -> None:
        """Mark booked amounts in the history as booked."""
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
        """Spoolman status for the card (None if not configured)."""
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
        """Service: assign a spool to a head manually or go back to automatic."""
        if not self.spools.enabled:
            raise HomeAssistantError(tr(self.hass, "Spoolman ist nicht eingerichtet.", "Spoolman is not set up."))
        slots = (self.data or self._prev).slots
        slot = next((s for s in slots if s["index"] == slot_index), None)
        if slot is None:
            raise HomeAssistantError(tr(self.hass, f"Kopf {slot_index + 1} unbekannt.", f"Unknown head {slot_index + 1}."))
        if spool_id and self.spools.spool(spool_id) is None:
            await self.spools.async_refresh()
            if self.spools.spool(spool_id) is None:
                raise HomeAssistantError(tr(
                    self.hass, f"Spule {spool_id} gibt es in Spoolman nicht (oder sie ist archiviert).",
                    f"Spool {spool_id} does not exist in Spoolman (or is archived)."))
        if spool_id and not automatic:
            # A spool sits in only one head: set elsewhere -> release it there
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
        """Remember the slicer data of the running file (filaments, weight, image)."""
        path = active.get("file")
        active["meta_done"] = True
        if not path:
            return
        # Pause copy: name and thumbnail of the original file
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
