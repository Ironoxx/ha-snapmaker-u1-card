"""Live-Abo bei Moonraker statt reiner Abfrage.

Moonraker schickt nach ``printer.objects.subscribe`` nur Aenderungen
(``notify_status_update``), hoechstens alle 250 ms. Damit sieht die
Integration Statuswechsel, Schichtwechsel, Kopfwechsel und Fehler sofort,
ohne den Drucker im Sekundentakt zu fragen. Die regelmaessige Abfrage laeuft
weiter, solange das Abo steht aber nur alle 30 s (Rueckfall: 10 s).

Nach einem Neustart von Klipper (``notify_klippy_ready``) muss neu abonniert
werden. Ist der Drucker aus, wird gar nicht erst verbunden.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import aiohttp

from .api import MoonrakerClient

_LOGGER = logging.getLogger(__name__)

SUBSCRIBE: dict[str, list[str]] = {
    "print_stats": ["state", "filename", "info", "print_duration"],
    "toolhead": ["extruder"],
    "virtual_sdcard": ["file_position", "progress"],
    "exception_manager": ["exceptions"],
}
BACKOFF = (5, 10, 30, 60)


def merge(status: dict[str, Any], diff: dict[str, Any]) -> None:
    """Aenderung in den Gesamtstand uebernehmen (eine Ebene tief, wie Moonraker sie schickt)."""
    for obj, fields in diff.items():
        if isinstance(fields, dict):
            status.setdefault(obj, {}).update(fields)


class LiveListener:
    def __init__(
        self,
        client: MoonrakerClient,
        on_update: Callable[[dict[str, Any]], None],
        on_state: Callable[[bool], None],
        is_off: Callable[[], bool],
    ) -> None:
        self.client = client
        self._on_update = on_update
        self._on_state = on_state
        self._is_off = is_off
        self.status: dict[str, Any] = {}
        self.connected = False
        self.connected_since: float | None = None
        self.messages = 0
        self._task: asyncio.Task | None = None
        self._ids = 1000

    def start(self, hass: Any) -> None:
        if self._task is None:
            self._task = hass.async_create_background_task(self._run(), "snapmaker_u1_card live")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        self._set(False)

    def _set(self, connected: bool) -> None:
        if connected != self.connected:
            self.connected = connected
            self.connected_since = time.time() if connected else None
            self._on_state(connected)

    async def _run(self) -> None:
        attempt = 0
        while True:
            if self._is_off():
                self._set(False)
                await asyncio.sleep(10)
                continue
            try:
                await self._session()
                attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - jede Stoerung: neu verbinden
                _LOGGER.debug("Live-Abo getrennt: %s", err)
            self._set(False)
            await asyncio.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
            attempt += 1

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> int:
        self._ids += 1
        await ws.send_json({
            "jsonrpc": "2.0", "method": "printer.objects.subscribe",
            "params": {"objects": SUBSCRIBE}, "id": self._ids,
        })
        return self._ids

    async def _session(self) -> None:
        async with self.client.websocket() as ws:
            pending = await self._subscribe(ws)
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break
                    continue
                data = json.loads(msg.data)
                if data.get("id") == pending:
                    if "error" in data:
                        # Klipper noch nicht bereit: auf notify_klippy_ready warten
                        _LOGGER.debug("Abo abgelehnt: %s", data["error"])
                        continue
                    status = (data.get("result") or {}).get("status") or {}
                    self.status = {}
                    merge(self.status, status)
                    self._set(True)
                    self.messages += 1
                    self._on_update(status)
                    continue
                method = data.get("method")
                if method == "notify_status_update":
                    params = data.get("params") or []
                    diff = params[0] if params and isinstance(params[0], dict) else {}
                    merge(self.status, diff)
                    self.messages += 1
                    self._on_update(diff)
                elif method == "notify_klippy_ready":
                    pending = await self._subscribe(ws)
                elif method in ("notify_klippy_disconnected", "notify_klippy_shutdown"):
                    self._set(False)
