"""Spoolman spools: sync, assignment, consumption and run-out warnings."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..api import (
    MoonrakerError,
)
from ..const import (
    CONF_SPOOL_RESTORE,
    CONF_SPOOLMAN_LOW,
    DEFAULT_SPOOL_RESTORE,
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
    spool_filament,
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
        ids = ptc.get("filament_spool_id")
        mgr.printer_ids = [int(x) if isinstance(x, (int, float)) else 0 for x in ids] if isinstance(ids, list) else None
        mgr.keep_last = self._restore_mode() != "off"
        if mgr.enabled:
            if mgr.due(SPOOLMAN_INTERVAL_S):
                changed = await mgr.async_refresh()
                if changed:
                    self._mark_booked()
                if mgr.online and self._fill_spool_after(data.print_state):
                    changed = True
                if changed:
                    self._save()
            if mgr.assign(data.slots):
                self._save()
            if mgr.to_push and data.print_state not in ACTIVE_PRINT_STATES:
                await self._push_spoollink()
            if mgr.online and self._restore_mode() == "auto" and data.print_state not in ACTIVE_PRINT_STATES:
                await self._restore_spools(data.slots)
        # What the running print needs to book usage per head later:
        # map table logical->head and the spool per head.
        active = self._print_state.get("active")
        if active and not active.get("pending") and data.print_state in ACTIVE_PRINT_STATES:
            active["map_table"] = list(ptc.get("extruder_map_table") or [])
            if mgr.enabled:
                active["spool_ids"] = {str(k): v for k, v in mgr.assigned().items()}
                # Remaining weight per head at the start, for "550 g -> 460 g" in the history
                start = active.setdefault("spool_start", {})
                for key, sid in active["spool_ids"].items():
                    if key not in start and sid:
                        start[key] = mgr.remaining(sid)
        data.spoolman = self._spoolman_data(data.slots)

    def _restore_mode(self) -> str:
        return str(self.options.get(CONF_SPOOL_RESTORE, DEFAULT_SPOOL_RESTORE))

    async def _restore_spools(self, slots: list[dict[str, Any]]) -> None:
        """Option "auto": a head loaded again gets its last spool without asking."""
        for idx, spool in self.spools.restorable(slots).items():
            try:
                await self.async_set_spool(idx, spool["id"], False)
                _LOGGER.info("Spool %s restored on head %s after reloading", spool["id"], idx + 1)
            except HomeAssistantError as err:
                _LOGGER.warning("Spool %s for head %s not restored: %s", spool["id"], idx + 1, err)
                self.spools.forget_last(idx)

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
        self._set_history(history)

    def _set_history(self, history: list[dict[str, Any]]) -> None:
        self._print_state = {**self._print_state, "history": history,
                             "last": history[0] if history else self._print_state.get("last")}

    def _fill_spool_after(self, print_state: str | None) -> bool:
        """Real remaining weight after the latest print, read back from Spoolman once.

        Only for the newest print and only while no other print runs, otherwise the
        value would already include the next print. Our own booking must be done;
        Moonraker (SpoolLink) books while printing, so its value is final at the end.
        """
        history = self._history()
        if not history or print_state in ACTIVE_PRINT_STATES:
            return False
        rec = history[0]
        spools = rec.get("spools") or []
        if not spools or rec.get("spools_final"):
            return False
        if any(sp.get("booked") is False for sp in spools):
            return False  # still queued
        filled = []
        for sp in spools:
            rest = self.spools.remaining(sp.get("spool_id"))
            filled.append({**sp, "after": rest} if rest is not None and sp.get("booked") is not None else sp)
        self._set_history([{**rec, "spools": filled, "spools_final": True}, *history[1:]])
        return True

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
            # who books usage and who keeps the spool per head
            "books": mgr.books,
            "external_booking": mgr.external_booking,
            "spoollink": mgr.spoollink,
            "pending": [dict(q) for q in mgr.queue],
            "slots": {str(s["index"]): mgr.slot_info(s["index"]) for s in slots},
            # head loaded again without a spool: offer the one it had before (option spool_restore)
            "restore": {} if self._restore_mode() == "off" else {
                str(k): {"id": v["id"], "name": v.get("name"), "vendor": v.get("vendor"), "material": v.get("material"),
                         "color": v.get("color")}
                for k, v in mgr.restorable(slots).items()},
            "spools": mgr.spools,
        }

    async def async_set_spool(self, slot_index: int, spool_id: int | None, automatic: bool) -> None:
        """Service: assign a spool to a head manually or go back to automatic."""
        if not self.spools.enabled:
            raise HomeAssistantError(tr(self.hass, "Spoolman ist nicht eingerichtet.", "Spoolman is not set up."))
        if self.spools.spoollink:
            await self._set_spool_spoollink(slot_index, spool_id, automatic)
            self.spools.forget_last(slot_index)
            return
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
        if spool_id and not automatic:
            await self._load_spool_filament(slot, self.spools.spool(spool_id))

    async def _push_spoollink(self) -> None:
        """Hand spools chosen before SpoolLink was enabled to the printer, once each."""
        mgr = self.spools
        for idx, sid in sorted(mgr.to_push.items()):
            try:
                await self.client.gcode(f"SET_SPOOL_ID CHANNEL={int(idx)} SPOOL_ID={int(sid)}")
                _LOGGER.info("SpoolLink: spool %s handed to head %s", sid, idx + 1)
                # show it right away; the printer confirms with filament_spool_id
                mgr.mapping[str(idx)] = {**(mgr.mapping.get(str(idx)) or {}), "spool_id": sid, "manual": True,
                                         "source": "printer"}
                mgr.hold(idx)
            except MoonrakerError as err:
                _LOGGER.warning("SpoolLink: spool %s for head %s refused: %s", sid, idx + 1, err)
                mgr.mapping[str(idx)] = {"spool_id": None, "manual": True, "source": "printer"}
        mgr.to_push.clear()
        self._save()

    async def _set_spool_spoollink(self, slot_index: int, spool_id: int | None, automatic: bool) -> None:
        """paxx12 SpoolLink: the printer keeps the spool per head and applies its filament itself."""
        if automatic:
            raise HomeAssistantError(tr(
                self.hass, "Mit SpoolLink legt der Drucker die Spule fest – bitte eine Spule wählen oder „Keine Spule“.",
                "With SpoolLink the printer keeps the spool – choose a spool or \"No spool\"."))
        if spool_id and self.current_print_state() in ACTIVE_PRINT_STATES:
            raise HomeAssistantError(tr(
                self.hass, "Spule kann während eines Drucks nicht gewechselt werden.",
                "The spool cannot be changed during a print."))
        await self._run_gcode(f"SET_SPOOL_ID CHANNEL={int(slot_index)} SPOOL_ID={int(spool_id or 0)}")
        # Show the choice right away; SpoolLink confirms it with filament_spool_id a moment later
        self.spools.mapping[str(slot_index)] = {**(self.spools.mapping.get(str(slot_index)) or {}),
                                                "spool_id": spool_id or None, "manual": True, "source": "printer"}
        self.spools.hold(slot_index)
        if self.data is not None:
            self.data.spoolman = self._spoolman_data(self.data.slots)
            self.async_update_listeners()

    async def async_weigh_spool(self, slot_index: int | None, spool_id: int | None,
                                weight: float, gross: bool = True) -> dict[str, Any]:
        """Set a spool's remaining weight in Spoolman from the scale.

        ``gross``: weighed with the empty spool; its weight comes from Spoolman.
        Either the spool of a head or a spool ID.
        """
        mgr = self.spools
        if not mgr.enabled or mgr.client is None:
            raise HomeAssistantError(tr(self.hass, "Spoolman ist nicht eingerichtet.", "Spoolman is not set up."))
        if spool_id is None and slot_index is not None:
            spool_id = (mgr.assigned() or {}).get(slot_index)
        if not spool_id:
            raise HomeAssistantError(tr(self.hass, "Diesem Kopf ist keine Spule zugeordnet.",
                                        "No spool is assigned to this head."))
        if mgr.spool(spool_id) is None:
            await mgr.async_refresh()
        if mgr.spool(spool_id) is None:
            raise HomeAssistantError(tr(self.hass, f"Spule {spool_id} gibt es in Spoolman nicht.",
                                        f"Spool {spool_id} does not exist in Spoolman."))
        try:
            rest = mgr.gross_to_remaining(spool_id, weight) if gross else max(0.0, round(float(weight), 1))
        except ValueError as err:
            raise HomeAssistantError(tr(
                self.hass, f"Spule {spool_id}: Leergewicht der Spule fehlt in Spoolman – Nettogewicht eingeben oder dort ergänzen.",
                f"Spool {spool_id}: empty spool weight missing in Spoolman – enter the net weight or add it there.")) from err
        before = mgr.remaining(spool_id)
        try:
            await mgr.client.set_remaining(spool_id, rest)
        except MoonrakerError as err:
            raise HomeAssistantError(tr(self.hass, f"Spoolman lehnt ab: {err}", f"Spoolman refused: {err}")) from err
        mgr.force()
        await mgr.async_refresh()
        if self.data is not None:
            self.data.spoolman = self._spoolman_data(self.data.slots)
            self.async_update_listeners()
        _LOGGER.info("Spool %s weighed: %s g left (was %s g)", spool_id, rest, before)
        return {"spool_id": spool_id, "remaining_weight": rest, "before": before}

    async def _load_spool_filament(self, slot: dict[str, Any], spool: dict[str, Any] | None) -> None:
        """Write material, vendor and colour of a chosen Spoolman spool into the printer's slot.

        Without this the head keeps showing what the firmware has (stock: PLA for
        every slot without RFID tag). Skipped for official RFID spools (the tag is
        the truth), during a print (the firmware refuses) and when nothing changes.
        """
        fil = spool_filament(spool)
        if fil is None or slot.get("official"):
            return
        if self.current_print_state() in ACTIVE_PRINT_STATES:
            _LOGGER.info("Spool chosen during a print: filament of head %s left as is", slot["index"] + 1)
            return
        same = ((slot.get("type") or "").upper() == fil["type"]
                and (slot.get("sub_type") or "").upper() == fil["sub_type"].upper()
                and (slot.get("vendor") or "").upper() == fil["vendor"].upper()
                and (not fil["color"] or (slot.get("color") or "").upper() == fil["color"].upper())
                and (not fil["colors"] or [c.upper() for c in slot.get("colors") or []] == [c.upper() for c in fil["colors"]]))
        if same:
            return
        self.spools.expect_filament_change(slot["index"])
        self._save()
        await self.async_set_filament(slot["index"], fil["type"], fil["sub_type"], fil["vendor"], fil["color"],
                                      colors=fil["colors"] or None)

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
