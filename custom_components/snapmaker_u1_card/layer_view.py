"""HTTP endpoints for the card's layer view and temperature chart.

GET /api/snapmaker_u1_card/layers/<entry_id>?layer=N  -> paths of layer N
GET /api/snapmaker_u1_card/layers/<entry_id>?position=1 -> current file position

The paths are too large for a sensor attribute (recorder, WebSocket to all
clients), so they are only delivered when the card asks for them.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView

from .api import MoonrakerError
from .const import DOMAIN
from .coordinator import head_index
from .layers import layer_payload
from .parsing import exclude_state

LAYER_URL = f"/api/{DOMAIN}/layers"


class LayerView(HomeAssistantView):
    """Layer paths and live position for the card's layer view."""
    url = LAYER_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:layers"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return one layer (``layer=N``) or the live position (``position=1``)."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message("not found", HTTPStatus.NOT_FOUND)
        coordinator = entry.runtime_data
        if request.query.get("file"):
            return await self._preview(hass, request, coordinator, request.query["file"])
        coordinator.request_layers()
        view = coordinator.layer_view
        base = {"status": view.get("status"), "file": view.get("file"), "error": view.get("error")}

        if request.query.get("position"):
            live = coordinator.live_position()
            if live is not None and live.get("position") is not None:
                return self.json({**base, **live, "live": True})
            try:
                status = await coordinator.client.query_objects(
                    fields={"virtual_sdcard": ("file_position", "progress"), "print_stats": ("info",),
                            "toolhead": ("extruder",),
                            "exclude_object": ("objects", "excluded_objects", "current_object")}
                )
            except MoonrakerError:
                return self.json({**base, "position": None})
            info = (status.get("print_stats") or {}).get("info") or {}
            return self.json({
                **base,
                "position": (status.get("virtual_sdcard") or {}).get("file_position"),
                "layer": info.get("current_layer"),
                "active_head": head_index((status.get("toolhead") or {}).get("extruder")),
                "exclude": exclude_state(status.get("exclude_object")),
            })

        if view.get("status") != "ready":
            return self.json(base)
        try:
            number = int(request.query.get("layer", "1"))
        except ValueError:
            return self.json_message("layer", HTTPStatus.BAD_REQUEST)
        payload = await hass.async_add_executor_job(
            layer_payload, view["meta"], coordinator.layer_store, number
        )
        if payload is None:
            return self.json({**base, "layer": number, "missing": True, "total": view["meta"]["total"]})
        return self.json({**base, **payload, "colors": coordinator.layer_colors()})

    async def _preview(self, hass: Any, request: web.Request, coordinator: Any, filename: str) -> web.Response:
        """2.1: one layer of any file (``file=…&layer=N``) for the preview in the print dialog."""
        state = coordinator.request_preview(filename)
        base = {"status": state["status"], "file": filename, "error": state.get("error"), "preview": True}
        if state["status"] != "ready":
            return self.json(base)
        try:
            number = int(request.query.get("layer", "1"))
        except ValueError:
            return self.json_message("layer", HTTPStatus.BAD_REQUEST)
        payload = await hass.async_add_executor_job(layer_payload, state["meta"], state["store"], number)
        if payload is None:
            return self.json({**base, "layer": number, "missing": True, "total": state["meta"]["total"]})
        return self.json({**base, **payload, "colors": coordinator.preview_colors(filename)})


TEMPS_URL = f"/api/{DOMAIN}/temps"
TEMP_SERIES = ("extruder", "extruder1", "extruder2", "extruder3", "heater_bed")
# 2.0: chamber air and the X/Y stepper drivers as extra lines (shown name -> store keys)
EXTRA_SERIES = {"cavity": ("temperature_sensor cavity",),
                # chamber heater (paxx12: Panda Breath / DragonBreath), with its target
                "chamber_heater": ("heater_generic panda_breath", "heater_generic dragonbreath"),
                "stepper_x": ("tmc2240 stepper_x", "tmc2209 stepper_x", "tmc5160 stepper_x"),
                "stepper_y": ("tmc2240 stepper_y", "tmc2209 stepper_y", "tmc5160 stepper_y")}


def _avg(values: list[Any], step: int) -> list[float | None]:
    """Mean per ``step`` values; None where a chunk has no number (driver off) – keeps the time axis."""
    out: list[float | None] = []
    for i in range(0, len(values), step):
        nums = [v for v in values[i:i + step] if isinstance(v, (int, float)) and not isinstance(v, bool)]
        out.append(round(sum(nums) / len(nums), 1) if nums else None)
    return out


def downsample(store: dict[str, Any], step: int = 5, cpu: list[float | None] | None = None) -> dict[str, Any]:
    """Average Moonraker's temperature store (1 value/s) over ``step`` seconds.

    ``cpu``: CPU temperature history from the live connection (1/s), aligned to the store's end.
    """
    out: dict[str, Any] = {}
    for name in TEMP_SERIES:
        series = store.get(name)
        if not isinstance(series, dict):
            continue
        out[name] = {key: _avg(series.get(key) or [], step) for key in ("temperatures", "targets")}
    extra = dict(EXTRA_SERIES)
    # any further sensor the printer config has (e.g. MCU or board sensors added by a mod)
    for key in store:
        kind, _, sensor = key.partition(" ")
        if kind in ("temperature_sensor", "temperature_fan") and sensor and sensor != "cavity":
            extra.setdefault(sensor, (key,))
    for name, keys in extra.items():
        series = next((store[k] for k in keys if isinstance(store.get(k), dict)), None)
        if series is None:
            continue
        temps = _avg(series.get("temperatures") or [], step)
        if any(v is not None for v in temps):
            out[name] = {"temperatures": temps, "targets": _avg(series.get("targets") or [], step)}
    if cpu and any(v is not None for v in cpu):
        length = max((len(s.get("temperatures") or []) for s in store.values() if isinstance(s, dict)), default=0)
        values = list(cpu)[-length:] if length else list(cpu)
        values = [None] * (length - len(values)) + values
        out["cpu"] = {"temperatures": _avg(values, step), "targets": []}
    return {"step": step, "series": out}


class TempsView(HomeAssistantView):
    """Temperature history of the heads and the bed (Moonraker /server/temperature_store)."""

    url = TEMPS_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:temps"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        """Return the downsampled temperature history."""
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message("not found", HTTPStatus.NOT_FOUND)
        try:
            store = await entry.runtime_data.client.temperature_store()
        except MoonrakerError:
            return self.json({"step": 5, "series": {}, "offline": True})
        return self.json(downsample(store, cpu=list(entry.runtime_data.live.cpu_hist)))
