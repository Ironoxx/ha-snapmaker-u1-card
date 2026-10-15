"""Druckdateien aus der Karte hochladen.

Der Browser schickt die Datei an Home Assistant (angemeldet, auch ueber
Nabu Casa), die Integration reicht sie an Moonraker weiter. So braucht der
Browser keinen direkten Zugang zum Drucker.

Ablauf: Multipart-Strom -> temporaere Datei -> POST /server/files/upload.
``request.multipart()`` liest streamend und unterliegt nicht der
16-MB-Grenze fuer Anfragekoerper von Home Assistant.
"""

from __future__ import annotations

import logging
import posixpath
import re
import tempfile
from http import HTTPStatus
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN, UPLOAD_MAX_BYTES, UPLOAD_URL
from .parsing import PRINTABLE_SUFFIXES

_LOGGER = logging.getLogger(__name__)
_SAFE = re.compile(r"[^\w.\- ()+\[\]]", re.UNICODE)


def safe_name(name: str) -> str | None:
    """Dateiname ohne Pfadanteile und Steuerzeichen; nur druckbare Endungen."""
    base = posixpath.basename(str(name).replace("\\", "/")).strip()
    base = _SAFE.sub("_", base).lstrip(".")
    if not base or not base.lower().endswith(PRINTABLE_SUFFIXES):
        return None
    return base[:200]


def safe_folder(folder: str | None) -> str:
    parts = [
        _SAFE.sub("_", p).lstrip(".") for p in str(folder or "").replace("\\", "/").split("/")
        if p and p not in (".", "..")
    ]
    return "/".join(p for p in parts if p)


def _t(hass: Any, de: str, en: str) -> str:
    return de if str(hass.config.language).lower().startswith("de") else en


class UploadView(HomeAssistantView):
    url = UPLOAD_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:upload"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message(_t(hass, "Drucker nicht gefunden", "Printer not found"), HTTPStatus.NOT_FOUND)
        coordinator = entry.runtime_data
        if coordinator.power_is_off():
            return self.json_message(_t(hass, "Der Drucker ist ausgeschaltet.", "The printer is switched off."), HTTPStatus.SERVICE_UNAVAILABLE)

        reader = await request.multipart()
        folder = ""
        result: dict[str, Any] | None = None
        with tempfile.TemporaryDirectory(prefix="u1upload") as tmp:
            while (part := await reader.next()) is not None:
                if part.name == "path":
                    folder = safe_folder(await part.text())
                    continue
                if part.name != "file":
                    continue
                name = safe_name(part.filename or "")
                if name is None:
                    return self.json_message(_t(hass, "Nur .gcode- und .3mf-Dateien.", "Only .gcode and .3mf files."), HTTPStatus.BAD_REQUEST)
                local = Path(tmp) / "upload"
                size = await _receive(hass, part, local)
                if size is None:
                    return self.json_message(_t(hass, "Datei zu gross.", "File too large."), HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                target = f"{folder}/{name}" if folder else name
                try:
                    await coordinator.client.upload(local, target)
                except MoonrakerError as err:
                    _LOGGER.warning("Upload %s abgelehnt: %s", target, err)
                    return self.json_message(_t(hass, f"Drucker lehnt ab: {err}", f"Printer refused: {err}"),
                                             HTTPStatus.BAD_GATEWAY)
                result = {"file": target, "size": size}
                _LOGGER.info("Hochgeladen: %s (%s Bytes)", target, size)
        if result is None:
            return self.json_message(_t(hass, "Keine Datei gesendet.", "No file sent."), HTTPStatus.BAD_REQUEST)
        coordinator.request_files_refresh()
        await coordinator.async_request_refresh()
        return self.json(result)


async def _receive(hass: Any, part: Any, target: Path) -> int | None:
    """Teil streamend in eine Datei schreiben; None bei Ueberschreitung der Grenze."""
    fh = await hass.async_add_executor_job(target.open, "wb")
    size = 0
    buf = bytearray()
    try:
        while chunk := await part.read_chunk(256 * 1024):
            size += len(chunk)
            if size > UPLOAD_MAX_BYTES:
                return None
            buf += chunk
            if len(buf) >= 4 * 1024 * 1024:
                await hass.async_add_executor_job(fh.write, bytes(buf))
                buf.clear()
        if buf:
            await hass.async_add_executor_job(fh.write, bytes(buf))
    finally:
        await hass.async_add_executor_job(fh.close)
    return size
