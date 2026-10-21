"""Diagnostics download (device/integration page -> "Download diagnostics").

Contains everything needed for troubleshooting: options, state of the live
subscription, raw printer status, current print, errors and the queue.
API keys, the Spoolman address and notification targets are redacted.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import MoonrakerError
from .const import CONF_NOTIFY, CONF_SPOOLMAN_URL, VERSION

# "url" covers the Spoolman address inside the spoolman block (diagnostics are
# often posted publicly, e.g. on Reddit)
TO_REDACT = {"api_key", CONF_SPOOLMAN_URL, CONF_NOTIFY, "host", "access_token", "token", "url",
             "stream_url", "snapshot_url"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Collect redacted diagnostics for one config entry."""
    coord = entry.runtime_data
    data = coord.data or coord._prev
    try:
        raw = await coord.client.query_objects(
            "print_task_config", "print_stats", "toolhead", "virtual_sdcard", "exception_manager", "webhooks",
        )
    except MoonrakerError as err:
        raw = {"error": str(err)}
    view = {k: v for k, v in coord.layer_view.items() if k != "meta"}
    if "meta" in coord.layer_view:
        meta = coord.layer_view["meta"]
        view["meta"] = {"total": meta.get("total"), "bbox": meta.get("bbox"), "tools": meta.get("tools"),
                        "size": meta.get("size")}
    return async_redact_data({
        "version": VERSION,
        "firmware": {"installed": coord.firmware.get("installed"),
                     "latest": (coord.firmware.get("latest") or {}).get("version")},
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "camera": coord.webcam.as_dict(),
        "live": {"connected": coord.live.connected, "messages": coord.live.messages,
                 "interval_s": coord.update_interval.total_seconds() if coord.update_interval else None},
        "online": data.online,
        "print_state": data.print_state,
        "active_head": data.active_head,
        "map_table": data.map_table,
        "slots": data.slots,
        "errors": data.errors,
        "queue": data.queue,
        "tool_changes": data.tool_changes,
        "maintenance": data.maintenance,
        "prints": data.prints,
        "history": data.history[:5],
        "files": len(data.files),
        "timelapses": len(data.timelapses),
        "archive": data.archive,
        "layer_view": view,
        "spoolman": data.spoolman,
        "cpu_count": data.cpu_count,
        "printer": raw,
    }, TO_REDACT)
