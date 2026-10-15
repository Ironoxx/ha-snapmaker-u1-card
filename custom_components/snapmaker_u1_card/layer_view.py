"""HTTP-Endpunkt fuer die Schichtansicht der Karte.

GET /api/snapmaker_u1_card/layers/<entry_id>?layer=N  -> Bahnen der Schicht N
GET /api/snapmaker_u1_card/layers/<entry_id>?position=1 -> aktuelle Dateiposition

Die Bahnen sind fuer eine Sensor-Eigenschaft zu gross (Recorder, Websocket an
alle Clients) und werden deshalb nur auf Anfrage der Karte geliefert.
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

LAYER_URL = f"/api/{DOMAIN}/layers"


class LayerView(HomeAssistantView):
    url = LAYER_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:layers"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message("not found", HTTPStatus.NOT_FOUND)
        coordinator = entry.runtime_data
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
                            "toolhead": ("extruder",)}
                )
            except MoonrakerError:
                return self.json({**base, "position": None})
            info = (status.get("print_stats") or {}).get("info") or {}
            return self.json({
                **base,
                "position": (status.get("virtual_sdcard") or {}).get("file_position"),
                "layer": info.get("current_layer"),
                "active_head": head_index((status.get("toolhead") or {}).get("extruder")),
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


TEMPS_URL = f"/api/{DOMAIN}/temps"
TEMP_SERIES = ("extruder", "extruder1", "extruder2", "extruder3", "heater_bed")


def downsample(store: dict[str, Any], step: int = 5) -> dict[str, Any]:
    """Moonrakers Temperaturspeicher (1 Wert/s) auf Mittelwerte je ``step`` s."""
    out: dict[str, Any] = {}
    for name in TEMP_SERIES:
        series = store.get(name)
        if not isinstance(series, dict):
            continue
        row: dict[str, list[float | None]] = {}
        for key in ("temperatures", "targets"):
            values = [v for v in series.get(key) or [] if isinstance(v, (int, float))]
            row[key] = [round(sum(chunk) / len(chunk), 1)
                        for chunk in (values[i:i + step] for i in range(0, len(values), step)) if chunk]
        out[name] = row
    return {"step": step, "series": out}


class TempsView(HomeAssistantView):
    """Temperaturverlauf der Koepfe und des Betts (Moonraker /server/temperature_store)."""

    url = TEMPS_URL + "/{entry_id}"
    name = f"api:{DOMAIN}:temps"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str) -> web.Response:
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or not hasattr(entry, "runtime_data"):
            return self.json_message("not found", HTTPStatus.NOT_FOUND)
        try:
            store = await entry.runtime_data.client.temperature_store()
        except MoonrakerError:
            return self.json({"step": 5, "series": {}, "offline": True})
        return self.json(downsample(store))
