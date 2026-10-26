"""Spool management with Spoolman: assignment per head and usage booking per print.

Without a Spoolman URL the module is inactive; card and sensors then show
nothing of it.

State (persisted by the coordinator, see ``as_stored``):
  spool_map:   {"<head>": {"spool_id": int|None, "manual": bool, "fp": str|None}}
  spool_queue: [{"key", "spool_id", "grams", "file", "slot"}]  not booked yet
"""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

from .api import MoonrakerError, SpoolmanClient
from .parsing import compact_spool, grams_per_slot, slot_fingerprint, suggest_spools

_LOGGER = logging.getLogger(__name__)


class SpoolManager:
    """Spoolman state: spool list, assignment per head and pending bookings."""
    def __init__(self, client: SpoolmanClient | None, stored: dict[str, Any] | None, deduct: bool) -> None:
        self.client = client
        stored = stored or {}
        self._map: dict[str, dict[str, Any]] = {
            str(k): dict(v) for k, v in (stored.get("spool_map") or {}).items() if isinstance(v, dict)
        }
        self._queue: list[dict[str, Any]] = [
            dict(q) for q in stored.get("spool_queue") or [] if isinstance(q, dict) and q.get("spool_id")
        ]
        self.deduct = deduct
        self.spools: list[dict[str, Any]] = []
        self.online = False
        self.error: str | None = None
        self._fetched = 0.0
        self.just_booked: list[dict[str, Any]] = []  # for the history, picked up by the coordinator
        # paxx12 SpoolLink: spool per head from print_task_config.filament_spool_id (None = not present)
        self.printer_ids: list[int] | None = None
        # Moonraker's own [spoolman] component books usage while printing (SpoolLink or by hand)
        self.external_booking = False

    @property
    def enabled(self) -> bool:
        return self.client is not None

    @property
    def mapping(self) -> dict[str, dict[str, Any]]:
        return self._map

    @property
    def queue(self) -> list[dict[str, Any]]:
        return self._queue

    def as_stored(self) -> dict[str, Any]:
        return {"spool_map": self._map, "spool_queue": self._queue}

    def due(self, interval: float) -> bool:
        return self.enabled and time.monotonic() - self._fetched >= interval

    def force(self) -> None:
        self._fetched = 0.0

    async def async_refresh(self) -> bool:
        """Fetch spools and retry pending bookings. True = state changed."""
        if self.client is None:
            return False
        self._fetched = time.monotonic()
        try:
            self.spools = [compact_spool(s) for s in await self.client.spools()]
            self.online, self.error = True, None
        except MoonrakerError as err:
            self.online, self.error = False, str(err)
            _LOGGER.debug("Spoolman: %s", err)
            return False
        return await self._flush_queue()

    @property
    def spoollink(self) -> bool:
        """The printer keeps the spool per head itself (paxx12 SpoolLink)."""
        return self.printer_ids is not None

    @property
    def books(self) -> bool:
        """Does this integration book usage? Not if Moonraker already does (no double booking)."""
        return self.deduct and not self.external_booking

    def assign(self, slots: list[dict[str, Any]]) -> bool:
        """Update the assignment per head. True = changed (save)."""
        if not self.enabled or not self.online:
            return False
        if self.printer_ids is not None:
            # SpoolLink: the printer is the source of truth, no own guessing
            changed = False
            for slot in slots:
                idx = slot["index"]
                sid = self.printer_ids[idx] if idx < len(self.printer_ids) else 0
                entry = {"spool_id": sid or None, "manual": True, "fp": slot_fingerprint(slot), "source": "printer"}
                if self.mapping.get(str(idx)) != entry:
                    self.mapping[str(idx)] = entry
                    changed = True
            return changed
        known = {s["id"] for s in self.spools}
        fixed: dict[int, int | None] = {}
        changed = False
        for slot in slots:
            key = str(slot["index"])
            entry = self.mapping.get(key)
            fp = slot_fingerprint(slot)
            if entry is None:
                continue
            # Different filament loaded or spool archived/deleted:
            # determine the assignment again, even a manual one.
            if entry.get("fp") != fp and entry.get("manual") and entry.get("sync_until", 0) > time.time():
                # We just wrote the spool's filament to the printer: the new
                # fingerprint belongs to this assignment.
                entry["fp"] = fp
                entry.pop("sync_until", None)
                changed = True
            if entry.get("fp") != fp or (entry.get("spool_id") and entry["spool_id"] not in known):
                del self.mapping[key]
                changed = True
                continue
            # Manual and found assignments stay stable as long as the
            # filament is the same. Automatic empty ones are searched again (e.g.
            # when a matching spool has been added to Spoolman in the meantime).
            if entry.get("manual") or entry.get("spool_id") is not None:
                fixed[slot["index"]] = entry.get("spool_id")
        proposal = suggest_spools(slots, self.spools, fixed)
        for slot in slots:
            key = str(slot["index"])
            entry = self.mapping.get(key)
            if entry is not None:
                if not entry.get("manual") and entry.get("spool_id") is None and proposal.get(slot["index"]):
                    entry["spool_id"] = proposal[slot["index"]]
                    changed = True
                continue
            self.mapping[key] = {
                "spool_id": proposal.get(slot["index"]),
                "manual": False,
                "fp": slot_fingerprint(slot),
            }
            changed = True
        return changed

    def set_manual(self, slot: dict[str, Any], spool_id: int | None, automatic: bool) -> None:
        """Pin a spool to a head (or release the head with None)."""
        key = str(slot["index"])
        if automatic:
            self.mapping.pop(key, None)
            return
        self.mapping[key] = {"spool_id": spool_id, "manual": True, "fp": slot_fingerprint(slot)}

    def expect_filament_change(self, index: int, seconds: float = 180) -> None:
        """The printer is about to report other filament for this head because we set it."""
        entry = self.mapping.get(str(index))
        if entry is not None:
            entry["sync_until"] = time.time() + seconds

    def assigned(self) -> dict[int, int | None]:
        return {int(k): v.get("spool_id") for k, v in self.mapping.items()}

    def spool(self, spool_id: int | None) -> dict[str, Any] | None:
        return next((s for s in self.spools if s["id"] == spool_id), None) if spool_id else None

    def slot_info(self, index: int) -> dict[str, Any] | None:
        """Assigned spool of a head with the manual flag, or None."""
        entry = self.mapping.get(str(index)) or {}
        spool = self.spool(entry.get("spool_id"))
        if spool is None:
            return None
        return {**spool, "manual": bool(entry.get("manual")), "source": entry.get("source", "integration")}

    def book(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Schedule the usage of a finished print; returns data for the history."""
        if not self.enabled:
            return []
        spool_ids: dict[str, Any] = record.get("spool_ids") or {}
        start: dict[str, Any] = record.get("spool_start") or {}
        booked = []
        for slot, grams in sorted(grams_per_slot(record).items()):
            spool_id = spool_ids.get(str(slot))
            if not spool_id or grams <= 0:
                continue
            item = {
                "key": f"{record.get('started')}|{slot}",
                "spool_id": spool_id, "grams": round(grams, 2),
                "file": record.get("file"), "slot": slot,
            }
            before = start.get(str(slot))
            entry: dict[str, Any] = {
                "slot": slot, "spool_id": spool_id, "grams": item["grams"],
                # True/False = booked by us (done/pending), "moonraker" = Moonraker books, None = off
                "booked": False if self.books else ("moonraker" if self.external_booking else None),
                "before": before,
                # expected; replaced by Spoolman's value after the booking
                "after": round(before - item["grams"], 1) if isinstance(before, (int, float)) else None,
            }
            booked.append(entry)
            if self.books and not any(q["key"] == item["key"] for q in self.queue):
                self.queue.append(item)
        return booked

    def remaining(self, spool_id: Any) -> float | None:
        spool = self.spool(spool_id) if isinstance(spool_id, int) else None
        value = (spool or {}).get("remaining_weight")
        return float(value) if isinstance(value, (int, float)) else None

    def gross_to_remaining(self, spool_id: int, gross: float) -> float:
        """Weighed spool (with the empty spool) -> filament left."""
        spool = self.spool(spool_id) or {}
        empty = spool.get("spool_weight")
        if not isinstance(empty, (int, float)) or empty <= 0:
            raise ValueError("no empty spool weight in Spoolman")
        return max(0.0, round(float(gross) - float(empty), 1))

    async def _flush_queue(self) -> bool:
        """Book pending usage in Spoolman; failures stay queued."""
        if not self.queue or self.client is None:
            return False
        done = []
        for item in list(self.queue):
            try:
                await self.client.use_weight(item["spool_id"], item["grams"])
            except MoonrakerError as err:
                if "404" in str(err):  # spool deleted: do not retry forever
                    _LOGGER.warning("Spoolman: spool %s no longer exists, %s g discarded",
                                    item["spool_id"], item["grams"])
                    done.append(item)
                    continue
                _LOGGER.debug("Spoolman booking postponed: %s", err)
                break
            _LOGGER.info("Spoolman: %s g booked from spool %s (%s, head %s)",
                         item["grams"], item["spool_id"], item.get("file"), item["slot"] + 1)
            done.append(item)
        for item in done:
            self.queue.remove(item)
        self.just_booked.extend(done)
        if done:
            # update remaining weights right away
            with contextlib.suppress(MoonrakerError):
                self.spools = [compact_spool(s) for s in await self.client.spools()]
        return bool(done)
