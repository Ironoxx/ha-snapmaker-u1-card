"""Live-Abo (live.py) gegen einen echten WebSocket-Server und neue Push-Ereignisse."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant

from custom_components.snapmaker_u1_card import live as live_mod
from custom_components.snapmaker_u1_card.api import MoonrakerClient
from custom_components.snapmaker_u1_card.coordinator import remaining_seconds
from tests.test_init import API, mock_client  # noqa: F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: F401


class _Hass:
    def async_create_background_task(self, coro, name):
        return asyncio.get_running_loop().create_task(coro)


@pytest.mark.live
async def test_listener_subscribe_diff_resubscribe(socket_enabled) -> None:
    subs: list[dict] = []
    done = asyncio.Event()

    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            req = json.loads(msg.data)
            subs.append(req)
            if len(subs) == 1:
                await ws.send_json({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "eventtime": 1, "status": {"print_stats": {"state": "printing", "info": {"current_layer": 1}},
                                               "toolhead": {"extruder": "extruder"}}}})
                await ws.send_json({"jsonrpc": "2.0", "method": "notify_status_update",
                                    "params": [{"toolhead": {"extruder": "extruder2"}}, 2]})
                await ws.send_json({"jsonrpc": "2.0", "method": "notify_klippy_ready"})
            else:
                # Zweites Abo nach Klipper-Neustart: abgelehnt, dann Ende
                await ws.send_json({"jsonrpc": "2.0", "id": req["id"], "error": {"code": 503, "message": "x"}})
                done.set()
                await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/websocket", handler)
    server = TestServer(app)
    await server.start_server()
    updates, states = [], []
    async with aiohttp.ClientSession() as session:
        client = MoonrakerClient(session, "127.0.0.1", server.port)
        listener = live_mod.LiveListener(client, updates.append, states.append, lambda: False)
        listener.start(_Hass())
        await asyncio.wait_for(done.wait(), 5)
        await asyncio.sleep(0.05)
        await listener.stop()
    await server.close()

    assert subs[0]["method"] == "printer.objects.subscribe"
    assert set(subs[0]["params"]["objects"]) == set(live_mod.SUBSCRIBE)
    assert len(subs) == 2, "nach notify_klippy_ready neu abonniert"
    assert updates[1] == {"toolhead": {"extruder": "extruder2"}}
    assert listener.status["toolhead"]["extruder"] == "extruder2"
    assert listener.status["print_stats"]["info"] == {"current_layer": 1}
    assert states[0] is True and states[-1] is False


@pytest.mark.live
async def test_listener_skips_when_off() -> None:
    client = AsyncMock()
    listener = live_mod.LiveListener(client, lambda d: None, lambda c: None, lambda: True)
    with patch.object(live_mod.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)):
        listener.start(_Hass())
        with pytest.raises(asyncio.CancelledError):
            await listener._task
    client.websocket.assert_not_called()


def test_remaining_seconds() -> None:
    assert remaining_seconds(3600, 0.5) == 3600
    assert remaining_seconds(100, 0.01) is None  # zu frueh fuer eine Schaetzung
    assert remaining_seconds(100, 1.0) is None
    assert remaining_seconds(None, 0.5) is None


def _sent(calls, title):
    return [c for c in calls if title in c.data["title"]]


async def test_live_diff_updates_head_and_refreshes(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    seen = []
    coord.async_add_listener(lambda: seen.append(coord.data.active_head))
    coord._on_live({"toolhead": {"extruder": "extruder3"}})
    assert coord.data.active_head == 3 and seen == [3]
    mock_client["query"].reset_mock()
    coord._on_live({"print_stats": {"state": "paused"}})
    await hass.async_block_till_done()
    mock_client["query"].assert_awaited()  # Statuswechsel: sofort abgleichen
    coord._on_live_state(True)
    assert coord.update_interval.total_seconds() == 30
    coord._on_live_state(False)
    assert coord.update_interval.total_seconds() == 10


async def test_first_layer_and_almost_done(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"],
                         notify_events=["first_layer", "almost_done"], almost_done_minutes=10)
    hass.config.language = "de"
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=600, info={"current_layer": 1})
    st["virtual_sdcard"] = {"progress": 0.1}
    await _refresh(hass, entry)
    assert notifications == []
    st["print_stats"]["info"] = {"current_layer": 2}
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert len(_sent(notifications, "Erste Schicht")) == 1
    # Restzeit 600*(1-0.95)/0.95 ~ 32 s -> gleich fertig, nur einmal
    st["print_stats"]["print_duration"] = 6000
    st["virtual_sdcard"] = {"progress": 0.95}
    await _refresh(hass, entry)
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    msgs = _sent(notifications, "Gleich fertig")
    assert len(msgs) == 1 and "min" in msgs[0].data["message"]
    # Ueber das Live-Abo kein zweites Mal
    coord = entry.runtime_data
    coord.live.status = {"print_stats": st["print_stats"], "virtual_sdcard": {"progress": 0.97}}
    coord._on_live({"virtual_sdcard": {"progress": 0.97}})
    await hass.async_block_till_done()
    assert len(_sent(notifications, "Gleich fertig")) == 1


async def test_join_mid_print_no_first_layer(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["first_layer"])
    st = _status(mock_client, "printing", "sub/new.gcode", info={"current_layer": 40})
    await _refresh(hass, entry)
    st["print_stats"]["info"] = {"current_layer": 41}
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert notifications == []


async def test_alert_on_new_error_while_printing(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["alert", "paused"])
    hass.config.language = "de"
    st = _status(mock_client, "printing", "sub/new.gcode")
    await _refresh(hass, entry)
    st["exception_manager"] = {"exceptions": [{"id": 523, "index": 0, "code": 1, "level": 2, "message": "x"}]}
    await _refresh(hass, entry)
    await _refresh(hass, entry)  # gleiche Meldung: nicht nochmal
    await hass.async_block_till_done()
    alerts = _sent(notifications, "Meldung vom Drucker")
    assert len(alerts) == 1
    assert alerts[0].data["data"]["priority"] == "high"
    # Neue Meldung zusammen mit Pause: nur die Pausenmeldung (enthaelt den Text)
    st["exception_manager"] = {"exceptions": [{"id": 524, "index": 1, "code": 2, "level": 2, "message": "y"}]}
    st["print_stats"]["state"] = "paused"
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert len(_sent(notifications, "Meldung vom Drucker")) == 1
    assert len(_sent(notifications, "pausiert")) == 1


async def test_spool_low_at_start(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["spool_low"])
    hass.config.language = "de"
    coord = entry.runtime_data
    with patch.object(type(coord.spools), "enabled", property(lambda self: True)), \
         patch.object(type(coord.spools), "slot_info",
                      lambda self, i: {"name": "Rot", "remaining_weight": 1.0} if i == 0 else None):
        _status(mock_client, "printing", "sub/new.gcode")
        await _refresh(hass, entry)
        await hass.async_block_till_done()
    msgs = _sent(notifications, "Filament reicht nicht")
    active = coord._print_state["active"]
    if not any(f.get("weight") for f in active.get("filaments") or []):
        pytest.skip("Testdatei ohne Gewichte")
    assert len(msgs) == 1 and "Kopf 1" in msgs[0].data["message"]
    assert active["spool_short"][0]["head"] == 1


async def test_live_binary_sensor(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    from homeassistant.helpers import entity_registry as er

    ent = next(e for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
               if e.domain == "binary_sensor")
    assert ent.translation_key == "live" and ent.entity_category == "diagnostic"
    assert hass.states.get(ent.entity_id).state == "off"
    coord.live._set(True)
    await hass.async_block_till_done()
    st = hass.states.get(ent.entity_id)
    assert st.state == "on" and st.attributes["poll_interval_s"] == 30 and st.attributes["connected_since"]
    coord.live._set(False)
    await hass.async_block_till_done()
    st = hass.states.get(ent.entity_id)
    assert st.state == "off" and st.attributes["poll_interval_s"] == 10 and st.attributes["connected_since"] is None
