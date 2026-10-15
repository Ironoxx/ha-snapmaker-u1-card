"""Spulenverwaltung mit Spoolman: Zuordnung je Kopf und Abbuchung je Druck.

Ohne eingetragene Spoolman-URL ist das Modul inaktiv; Karte und Sensoren
zeigen dann nichts davon.

Zustand (der Coordinator speichert ihn mit, siehe ``as_stored``):
  spool_map:   {"<kopf>": {"spool_id": int|None, "manual": bool, "fp": str|None}}
  spool_queue: [{"key", "spool_id", "grams", "file", "slot"}]  noch nicht gebucht
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
        self.just_booked: list[dict[str, Any]] = []  # fuer die Historie, vom Coordinator abgeholt

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
        """Spulen holen und offene Buchungen nachholen. True = Zustand geaendert."""
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

    def assign(self, slots: list[dict[str, Any]]) -> bool:
        """Zuordnung je Kopf fortschreiben. True = geaendert (speichern)."""
        if not self.enabled or not self.online:
            return False
        known = {s["id"] for s in self.spools}
        fixed: dict[int, int | None] = {}
        changed = False
        for slot in slots:
            key = str(slot["index"])
            entry = self.mapping.get(key)
            fp = slot_fingerprint(slot)
            if entry is None:
                continue
            # Anderes Filament eingelegt oder Spule archiviert/geloescht:
            # Zuordnung neu bestimmen, auch eine manuelle.
            if entry.get("fp") != fp or (entry.get("spool_id") and entry["spool_id"] not in known):
                del self.mapping[key]
                changed = True
                continue
            # Manuelle und gefundene Zuordnungen bleiben stabil, solange das
            # Filament gleich ist. Automatisch leere werden neu gesucht (z. B.
            # wenn inzwischen eine passende Spule in Spoolman angelegt wurde).
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
        key = str(slot["index"])
        if automatic:
            self.mapping.pop(key, None)
            return
        self.mapping[key] = {"spool_id": spool_id, "manual": True, "fp": slot_fingerprint(slot)}

    def assigned(self) -> dict[int, int | None]:
        return {int(k): v.get("spool_id") for k, v in self.mapping.items()}

    def spool(self, spool_id: int | None) -> dict[str, Any] | None:
        return next((s for s in self.spools if s["id"] == spool_id), None) if spool_id else None

    def slot_info(self, index: int) -> dict[str, Any] | None:
        entry = self.mapping.get(str(index)) or {}
        spool = self.spool(entry.get("spool_id"))
        if spool is None:
            return None
        return {**spool, "manual": bool(entry.get("manual"))}

    def book(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Verbrauch eines beendeten Drucks einplanen; Rueckgabe fuer die Historie."""
        if not self.enabled:
            return []
        spool_ids: dict[str, Any] = record.get("spool_ids") or {}
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
            booked.append({"slot": slot, "spool_id": spool_id, "grams": item["grams"],
                           "booked": False if self.deduct else None})
            if self.deduct and not any(q["key"] == item["key"] for q in self.queue):
                self.queue.append(item)
        return booked

    async def _flush_queue(self) -> bool:
        if not self.queue or self.client is None:
            return False
        done = []
        for item in list(self.queue):
            try:
                await self.client.use_weight(item["spool_id"], item["grams"])
            except MoonrakerError as err:
                if "404" in str(err):  # Spule geloescht: nicht ewig wiederholen
                    _LOGGER.warning("Spoolman: Spule %s existiert nicht mehr, %s g verworfen",
                                    item["spool_id"], item["grams"])
                    done.append(item)
                    continue
                _LOGGER.debug("Spoolman-Buchung verschoben: %s", err)
                break
            _LOGGER.info("Spoolman: %s g von Spule %s abgebucht (%s, Kopf %s)",
                         item["grams"], item["spool_id"], item.get("file"), item["slot"] + 1)
            done.append(item)
        for item in done:
            self.queue.remove(item)
        self.just_booked.extend(done)
        if done:
            # Restgewichte sofort aktualisieren
            with contextlib.suppress(MoonrakerError):
                self.spools = [compact_spool(s) for s in await self.client.spools()]
        return bool(done)
