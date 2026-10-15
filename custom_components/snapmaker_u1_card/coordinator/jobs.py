"""Starting prints, "pause at layer" copies and the job queue."""

from __future__ import annotations

import logging
import posixpath
import tempfile
from pathlib import Path
from typing import Any

from homeassistant.exceptions import HomeAssistantError

from ..api import (
    MoonrakerError,
)
from ..i18n import tr
from ..jobs import (
    add_layer_pauses,
    is_pause_copy,
    pause_file_name,
)
from ..parsing import (
    ACTIVE_PRINT_STATES,
    map_table_option,
    parse_file_filaments,
    suggest_mapping,
)

_LOGGER = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)


class PrintJobMixin:
    """Starting prints, "pause at layer" copies and the job queue."""

    # ── Print start and queue ──────────────────────────────────────────────
    async def async_start_print(
        self,
        filename: str,
        mapping: dict[int, int] | None = None,
        *,
        bed_leveling: bool | None = None,
        flow_calibration: bool | None = None,
        timelapse: bool | None = None,
        plate: int = 1,
        pause_layers: list[int] | None = None,
        auto_on: bool = False,
    ) -> dict[str, Any]:
        """Start a print: power on, mapping, pause copy, start."""
        filename = filename.lstrip("/")
        if self.shutting_down:
            raise HomeAssistantError(tr(
                self.hass, "Der Drucker fährt gerade herunter. Bitte danach erneut starten.",
                "The printer is shutting down. Please start again afterwards."))
        if self._starting:
            raise HomeAssistantError(tr(self.hass, "Ein Druckstart läuft bereits.", "A print start is already in progress."))
        self._starting = True
        try:
            if self.power_is_off():
                if not auto_on:
                    raise HomeAssistantError(tr(self.hass, "Der Drucker ist ausgeschaltet.", "The printer is switched off."))
                _LOGGER.info("Printer off: switching on for %s", filename)
                await self.async_power_on(wait=True)
            if self.data is not None and self.data.print_state in ACTIVE_PRINT_STATES:
                raise HomeAssistantError(tr(self.hass, "Der Drucker druckt bereits.", "The printer is already printing."))

            if mapping is None:
                # Without an explicit mapping: same logic as the dialog in the card.
                try:
                    meta = await self.client.file_metadata(filename)
                except MoonrakerError:
                    meta = {}
                slots = self.data.slots if self.data else []
                mapping = suggest_mapping(parse_file_filaments(meta), slots)
            table = map_table_option(mapping) if mapping else None

            target = filename
            if pause_layers:
                target = await self._prepare_pause_copy(filename, pause_layers)

            _LOGGER.info("Starting print %s, mapping %s, pauses %s", target, table, pause_layers or "-")
            try:
                result = await self.client.start_print(
                    target, map_table=table, bed_leveling=bed_leveling,
                    flow_calibration=flow_calibration, timelapse=timelapse, plate=plate,
                )
            except MoonrakerError as err:
                if target != filename:
                    await self._delete_copy(target)
                raise HomeAssistantError(tr(self.hass, f"Druckstart abgelehnt: {err}", f"Print start refused: {err}")) from err
            self.note_print_started(target)
            active = self._print_state.get("active")
            if active is not None:
                active["source"] = filename
                active["mapping"] = {str(k): v for k, v in (mapping or {}).items()}
                active["options"] = {
                    k: v for k, v in (("bed_leveling", bed_leveling), ("flow_calibration", flow_calibration),
                                      ("timelapse", timelapse)) if v is not None
                }
                if pause_layers:
                    active["pause_layers"] = sorted(set(pause_layers))
                self._save()
        finally:
            self._starting = False
        await self.async_request_refresh()
        return {"state": result.get("state", "success"), "map_table": table, "file": target}

    async def _prepare_pause_copy(self, filename: str, layers: list[int]) -> str:
        """Create a copy with PAUSE before the layers and upload it."""
        target = pause_file_name(filename, layers)
        with tempfile.TemporaryDirectory(prefix="u1pause") as tmp:
            src, dst = Path(tmp) / "src.gcode", Path(tmp) / "dst.gcode"
            try:
                await self.client.download_to("gcodes", filename, src, self.hass)
            except MoonrakerError as err:
                raise HomeAssistantError(tr(self.hass, f"Datei nicht lesbar: {err}", f"File not readable: {err}")) from err
            try:
                result = await self.hass.async_add_executor_job(add_layer_pauses, src, dst, layers)
            except ValueError as err:
                raise HomeAssistantError(tr(
                    self.hass, f"Pause vor Schicht nicht möglich: {err}", f"Pause at layer not possible: {err}"
                )) from err
            if result["missing"]:
                raise HomeAssistantError(tr(
                    self.hass,
                    f"Schicht {', '.join(map(str, result['missing']))} gibt es nicht "
                    f"(Datei hat {result['total']} Schichten).",
                    f"Layer {', '.join(map(str, result['missing']))} does not exist "
                    f"(file has {result['total']} layers).",
                ))
            try:
                await self.client.upload(dst, target)
            except MoonrakerError as err:
                raise HomeAssistantError(tr(
                    self.hass, f"Kopie mit Pause nicht hochgeladen: {err}", f"Pause copy not uploaded: {err}")) from err
        return target

    async def _delete_copy(self, path: str) -> None:
        """Remove a pause copy from the printer after the print."""
        if not is_pause_copy(path):
            return
        try:
            await self.client.delete_file(path)
        except MoonrakerError as err:
            _LOGGER.debug("Pause copy %s not deleted: %s", path, err)

    def queue_add(self, job: dict[str, Any]) -> dict[str, Any]:
        """Add a job to the queue and return it."""
        info = next((f for f in self._files if f.get("path") == job["file"]), None)
        entry = self.queue.add({**job, "name": (info or {}).get("name") or posixpath.basename(job["file"]),
                                "thumb": (info or {}).get("thumb")})
        self._queue_changed()
        return entry

    def queue_remove(self, job_id: str) -> None:
        if not self.queue.remove(job_id):
            raise HomeAssistantError(tr(self.hass, "Auftrag nicht gefunden.", "Job not found."))
        self._queue_changed()

    def queue_move(self, job_id: str, position: int) -> None:
        if not self.queue.move(job_id, position):
            raise HomeAssistantError(tr(self.hass, "Auftrag nicht gefunden.", "Job not found."))
        self._queue_changed()

    def queue_clear(self) -> None:
        self.queue.clear()
        self._queue_changed()

    async def queue_start(self, job_id: str | None) -> dict[str, Any]:
        """Start the given (or first) queued job and remove it from the queue."""
        job = self.queue.get(job_id)
        if job is None:
            raise HomeAssistantError(
                tr(self.hass, "Die Warteschlange ist leer.", "The queue is empty.") if job_id is None
                else tr(self.hass, "Auftrag nicht gefunden.", "Job not found."))
        mapping = {int(k): int(v) for k, v in (job.get("mapping") or {}).items()} or None
        result = await self.async_start_print(
            job["file"], mapping,
            bed_leveling=job.get("bed_leveling"), flow_calibration=job.get("flow_calibration"),
            timelapse=job.get("timelapse"), plate=int(job.get("plate") or 1),
            pause_layers=job.get("pause_layers"), auto_on=bool(self.options.get("auto_on")),
        )
        self.queue.remove(job["id"])
        self._queue_changed()
        return result

    def _queue_changed(self) -> None:
        self._save()
        if self.data is not None:
            self.data.queue = list(self.queue.jobs)
            self.async_update_listeners()
