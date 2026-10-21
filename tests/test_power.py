"""Power switch, energy and cost per print, history, notifications,
auto-on/-off and the timelapse proxy."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant, ServiceCall  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.exceptions import HomeAssistantError  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
    async_capture_events,
)

from tests.test_init import API, DOMAIN, PTC, mock_client  # noqa: E402,F401

COORD = "custom_components.snapmaker_u1_card.coordinator.power"
SWITCH = "input_boolean.drucker_steckdose"
ENERGY = "sensor.drucker_energie"
POWER = "sensor.drucker_leistung"
PRICE = "sensor.strompreis"
OWN_SWITCH = "switch.snapmaker_u1_card_power"


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, hass, tmp_path):
    hass.config.components.add("frontend")
    hass.config.config_dir = str(tmp_path)
    yield


@pytest.fixture
def notifications(hass):
    calls: list[ServiceCall] = []

    async def handler(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("notify", "mobile_app_handy", handler)
    return calls


@pytest.fixture
def fast_power():
    with patch(f"{COORD}.POLL_S", 0), patch(f"{COORD}.BOOT_POLL_S", 0), \
         patch(f"{COORD}.SHUTDOWN_SETTLE_S", 0):
        yield


async def _setup(hass: HomeAssistant, switch_on: bool = True, **options) -> MockConfigEntry:
    assert await async_setup_component(hass, "http", {})
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": {"drucker_steckdose": {"initial": switch_on}}}
    )
    hass.states.async_set(ENERGY, "10.0", {"unit_of_measurement": "kWh", "device_class": "energy"})
    hass.states.async_set(POWER, "85", {"unit_of_measurement": "W", "device_class": "power"})
    hass.states.async_set(PRICE, "30", {"unit_of_measurement": "ct/kWh"})
    opts = {
        "power_switch": SWITCH, "power_sensor": POWER, "energy_sensor": ENERGY,
        "energy_price": PRICE, "shutdown_host": True, "auto_on": False, "auto_off": False,
        "auto_off_temp": 50, "auto_off_delay": 0, "files_limit": 24,
        "filament_prices": {"PLA": 20.0, "PETG": 25.0},
        "notify_targets": [], "notify_events": ["complete", "error", "paused"], **options,
    }
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.10", "port": 80},
                            options=opts, unique_id="192.0.2.10")
    entry.add_to_hass(hass)
    with patch("custom_components.snapmaker_u1_card.add_extra_js_url"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _status(mock_client, state="standby", filename="", temps=20.0, **stats):
    st = mock_client["query"].return_value
    st["print_stats"] = {"state": state, "filename": filename, **stats}
    for name in ("extruder", "extruder1", "extruder2", "extruder3"):
        st[name]["temperature"] = temps
    st["heater_bed"] = {"temperature": temps}
    return st


async def _refresh(hass, entry):
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


# ── Options ─────────────────────────────────────────────────────────────────
async def test_options_flow_sections(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    schema = result["data_schema"].schema
    assert {str(k) for k in schema} == {"power", "notify", "filament", "spoolman", "files", "timelapse", "maintenance"}

    base = {
        "power": {"shutdown_host": True, "auto_on": True, "auto_off": False,
                  "auto_off_temp": 50, "auto_off_delay": 5},
        "notify": {"notify_events": ["complete"]},
        "filament": {},
        "files": {"files_limit": 10},
        "spoolman": {"spoolman_deduct": True, "spoolman_low": 100}, "timelapse": {"timelapse_archive": False, "timelapse_keep": 5}, "maintenance": {"maint_plate": 30, "maint_nozzle": 100, "maint_rails": 300, "maint_belts": 500, "maint_filter": 0},
    }
    # auto-on without a switch is refused
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["errors"] == {"base": "auto_needs_switch"}
    # unknown notification service
    base["power"]["power_switch"] = SWITCH
    base["notify"]["notify_targets"] = ["notify.gibt_es_nicht"]
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["errors"] == {"base": "unknown_notify"}

    base["notify"]["notify_targets"] = ["notify.mobile_app_handy"]
    base["power"]["energy_price"] = PRICE
    base["filament"] = {"price_pla": 19.99, "price_other": 30}
    result = await hass.config_entries.options.async_configure(result["flow_id"], base)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    opts = entry.options
    assert opts["files_limit"] == 10 and isinstance(opts["auto_off_temp"], int)
    assert opts["filament_prices"] == {"PLA": 19.99, "OTHER": 30.0}
    assert opts["notify_targets"] == ["notify.mobile_app_handy"]
    assert opts["energy_price"] == PRICE
    assert "energy_sensor" not in opts  # removed

    # reopening shows the stored values in the right section
    from custom_components.snapmaker_u1_card.config_flow import nest_options

    nested = nest_options(opts)
    assert nested["filament"] == {"price_pla": 19.99, "price_other": 30.0}
    assert nested["power"]["power_switch"] == SWITCH


# ── On/off ──────────────────────────────────────────────────────────────────
async def test_setup_while_printer_off(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    mock_client["query"].side_effect = MoonrakerConnectionError("aus")
    entry = await _setup(hass, switch_on=False)
    assert entry.state.name == "LOADED"
    sw = hass.states.get(OWN_SWITCH)
    assert sw.state == "off"
    assert sw.attributes["power_sensor"] == POWER
    assert hass.states.get("sensor.snapmaker_u1_card_filaments").state == "unavailable"
    # With the switch off the printer is not even asked
    calls = mock_client["query"].await_count
    await _refresh(hass, entry)
    assert mock_client["query"].await_count == calls

    mock_client["query"].side_effect = None
    await hass.services.async_call("switch", "turn_on", {"entity_id": OWN_SWITCH}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "on"
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_filaments").state == "2"


async def test_files_survive_restart_while_off(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    entry = await _setup(hass)
    assert hass.states.get("sensor.snapmaker_u1_card_print_files").state == "2"
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    # Printer off, HA restarts: the last file list stays available for the card
    mock_client["query"].side_effect = MoonrakerConnectionError("aus")
    await hass.services.async_call("input_boolean", "turn_off", {"entity_id": SWITCH}, blocking=True)
    with patch("custom_components.snapmaker_u1_card.add_extra_js_url"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    files = hass.states.get("sensor.snapmaker_u1_card_print_files")
    assert files.state == "2" and files.attributes["files"][0]["path"] == "sub/new.gcode"


async def test_power_off_blocked_while_printing(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    with pytest.raises(HomeAssistantError, match="is printing"):
        await hass.services.async_call("switch", "turn_off", {"entity_id": OWN_SWITCH}, blocking=True)
    with pytest.raises(HomeAssistantError, match="is printing"):
        await hass.services.async_call(DOMAIN, "power_off", {}, blocking=True)
    assert hass.states.get(SWITCH).state == "on"


async def test_power_off_waits_until_printer_is_gone(hass: HomeAssistant, mock_client, fast_power) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    await _setup(hass)
    seen: list[str] = []
    # The printer answers twice more, then the network is gone.
    mock_client["ready"].side_effect = [True, True, MoonrakerConnectionError("weg")]

    async def turn_off_check(*a, **k):
        seen.append(a[0])

    with patch(f"{API}.rpc", AsyncMock(side_effect=turn_off_check)) as rpc:
        await hass.services.async_call(DOMAIN, "power_off", {}, blocking=True)
        await hass.async_block_till_done()
    assert seen == ["machine.shutdown"]
    rpc.assert_awaited_once()
    assert mock_client["ready"].await_count == 3
    assert hass.states.get(SWITCH).state == "off"
    assert hass.states.get(OWN_SWITCH).attributes["shutting_down"] is False
    assert hass.states.get(OWN_SWITCH).attributes["last_shutdown"] == "clean"


async def test_power_off_when_shutdown_refused(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerError

    await _setup(hass)
    # Refused shutdown: switch off right away without waiting (otherwise a timeout here).
    with patch(f"{API}.rpc", AsyncMock(side_effect=MoonrakerError("sudo: a password is required"))), \
         patch(f"{COORD}.SHUTDOWN_SETTLE_S", 0.01):
        await hass.services.async_call("switch", "turn_off", {"entity_id": OWN_SWITCH}, blocking=True)
        await asyncio.wait_for(hass.async_block_till_done(), 5)
    assert hass.states.get(SWITCH).state == "off"
    assert hass.states.get(OWN_SWITCH).attributes["last_shutdown"].startswith("refused: sudo")
    # Without asking the printer (option off): no shutdown



async def test_auto_on_when_starting_print(hass: HomeAssistant, mock_client, fast_power) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    entry = await _setup(hass, switch_on=False, auto_on=True)
    # Without auto-on: a clear refusal
    hass.config_entries.async_update_entry(entry, options={**entry.options, "auto_on": False})
    await hass.async_block_till_done()
    with pytest.raises(HomeAssistantError, match="switched off"):
        await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode", "mapping": {"0": 0}}, blocking=True)
    mock_client["start_print"].assert_not_awaited()

    hass.config_entries.async_update_entry(entry, options={**entry.options, "auto_on": True})
    await hass.async_block_till_done()
    # Booting: twice unreachable, once Klipper not ready yet, then ready
    mock_client["ready"].side_effect = [MoonrakerConnectionError("boot"), MoonrakerConnectionError("boot"), False, True]
    await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode", "mapping": {"0": 0}}, blocking=True)
    assert hass.states.get(SWITCH).state == "on"
    assert mock_client["ready"].await_count == 4
    mock_client["start_print"].assert_awaited_once()


async def test_auto_on_times_out(hass: HomeAssistant, mock_client, fast_power) -> None:
    await _setup(hass, switch_on=False, auto_on=True)
    mock_client["ready"].return_value = False
    with patch(f"{COORD}.POWER_ON_TIMEOUT_S", 0.05), \
         pytest.raises(HomeAssistantError, match="not ready"):
        await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode"}, blocking=True)
    mock_client["start_print"].assert_not_awaited()


# ── Print: energy, cost, history, notification, auto-off ───────────────────
async def test_full_print_cycle(hass: HomeAssistant, mock_client, notifications, fast_power) -> None:
    entry = await _setup(
        hass, auto_off=True, auto_off_delay=0, auto_off_temp=50,
        notify_targets=["notify.mobile_app_handy"], camera="camera.drucker",
    )
    hass.config.language = "de"  # check the notification texts in German
    events = async_capture_events(hass, f"{DOMAIN}_print_finished")
    _status(mock_client, "printing", "sub/new.gcode", temps=220.0, print_duration=10.0, filament_used=0.0)
    await _refresh(hass, entry)
    # running print: 0.75 kWh at 30 ct, then 0.25 kWh at 10 ct
    hass.states.async_set(ENERGY, "10.75", {"unit_of_measurement": "kWh"})
    await _refresh(hass, entry)
    hass.states.async_set(PRICE, "10", {"unit_of_measurement": "ct/kWh"})
    hass.states.async_set(ENERGY, "11.0", {"unit_of_measurement": "kWh"})
    mock_client["query"].return_value["extruder"]["switch_count"] += 30
    _status(mock_client, "printing", "sub/new.gcode", temps=220.0, print_duration=3540.0, filament_used=900.0)
    await _refresh(hass, entry)
    en = hass.states.get("sensor.snapmaker_u1_card_energy_print")
    assert float(en.state) == pytest.approx(1.0) and en.attributes["in_progress"] is True
    assert float(hass.states.get("sensor.snapmaker_u1_card_cost_print").state) == pytest.approx(0.25)

    # a pause (filament runout) is reported
    _status(mock_client, "paused", "sub/new.gcode", temps=220.0)
    await _refresh(hass, entry)
    assert len(notifications) == 1 and "pausiert" in notifications[0].data["title"]
    assert notifications[0].data["data"]["image"] == "/api/camera_proxy/camera.drucker"

    # finished but still hot: event, history, notification; no switch-off yet
    _status(mock_client, "complete", "sub/new.gcode", temps=180.0)
    await _refresh(hass, entry)
    assert len(events) == 1
    ev = events[0].data
    assert ev["result"] == "complete" and ev["tool_changes"] == 30
    assert ev["energy_kwh"] == pytest.approx(1.0) and ev["energy_cost"] == pytest.approx(0.25)
    # META: PETG 4 g x 25 €/kg + PLA 6 g x 20 €/kg = 0.22 €
    assert ev["filament_g"] == 10.0 and ev["filament_cost"] == pytest.approx(0.22)
    assert ev["total_cost"] == pytest.approx(0.47) and ev["duration_s"] == 3540.0

    hist = hass.states.get("sensor.snapmaker_u1_card_print_history")
    assert hist.state == "1"
    rec = hist.attributes["prints"][0]
    assert rec["name"] == "new" and rec["thumb"].startswith("/snapmaker_u1_card/thumbs/")
    assert rec["materials"] == ["PETG", "PLA"] and rec["started"].endswith("+00:00")

    assert len(notifications) == 2
    msg = notifications[1].data
    assert msg["title"] == "Snapmaker U1: Druck fertig"
    assert msg["message"] == "new · 59 min · 10 g · 1.00 kWh · 0,47 € · 30 Wechsel"
    assert hass.states.get(OWN_SWITCH).attributes["auto_off_pending"] is True
    assert hass.states.get(SWITCH).state == "on"

    # cooled down: auto-off (the printer stops answering after the shutdown)
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    mock_client["ready"].side_effect = MoonrakerConnectionError("weg")
    _status(mock_client, "complete", "sub/new.gcode", temps=35.0)
    with patch(f"{API}.rpc", AsyncMock()):
        await _refresh(hass, entry)
        await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "off"
    # values of the last print stay visible
    cost = hass.states.get("sensor.snapmaker_u1_card_cost_print")
    assert float(cost.state) == pytest.approx(0.47) and cost.attributes["result"] == "complete"
    assert hass.states.get("sensor.snapmaker_u1_card_print_history").state == "1"


async def test_notify_events_filter(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["error"])
    hass.config.language = "de"
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    _status(mock_client, "complete", "a.gcode")
    await _refresh(hass, entry)
    assert notifications == []
    _status(mock_client, "printing", "b.gcode")
    await _refresh(hass, entry)
    _status(mock_client, "error", "b.gcode")
    await _refresh(hass, entry)
    assert len(notifications) == 1 and notifications[0].data["title"] == "Snapmaker U1: Druckfehler"
    assert notifications[0].data["data"]["priority"] == "high"


async def test_auto_off_disarmed_by_new_print(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass, auto_off=True, auto_off_delay=0)
    _status(mock_client, "printing", "a.gcode", temps=200.0)
    await _refresh(hass, entry)
    _status(mock_client, "complete", "a.gcode", temps=200.0)
    await _refresh(hass, entry)
    assert entry.runtime_data.auto_off_armed is not None
    _status(mock_client, "printing", "b.gcode", temps=200.0)
    await _refresh(hass, entry)
    assert entry.runtime_data.auto_off_armed is None


async def test_no_auto_off_after_error(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass, auto_off=True, auto_off_delay=0)
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    _status(mock_client, "error", "a.gcode", temps=20.0)
    await _refresh(hass, entry)
    assert entry.runtime_data.auto_off_armed is None
    assert hass.states.get(SWITCH).state == "on"


# ── Timelapses ──────────────────────────────────────────────────────────────
async def test_timelapses_and_proxy(hass: HomeAssistant, hass_client, mock_client) -> None:
    entry = await _setup(hass)
    tl = hass.states.get("sensor.snapmaker_u1_card_timelapses")
    assert tl.state == "1"
    video = tl.attributes["videos"][0]
    assert video["root"] == "camera" and video["name"] == "Nuss 2 PLA 1h17m"
    assert video["poster"].endswith("_cover.jpg")
    base = tl.attributes["url"]
    assert base == f"/api/{DOMAIN}/video/{entry.entry_id}"

    class Upstream:
        status = 206
        headers = {"Content-Type": "video/mp4", "Content-Range": "bytes 0-3/17019965",
                   "Content-Length": "4", "Accept-Ranges": "bytes"}

        def __init__(self):
            self.released = False

            async def chunks(size):
                yield b"\x00\x00\x00\x18"
            self.content = type("C", (), {"iter_chunked": staticmethod(chunks)})()

        def release(self):
            self.released = True

    up = Upstream()
    client = await hass_client()
    with patch(f"{API}.open_file", AsyncMock(return_value=up)) as op:
        resp = await client.get(f"{base}/camera/{video['path']}", headers={"Range": "bytes=0-3"})
        assert resp.status == 206
        assert resp.headers["Content-Range"] == "bytes 0-3/17019965"
        assert await resp.read() == b"\x00\x00\x00\x18"
        assert op.await_args.args == ("camera", video["path"], {"Range": "bytes=0-3"})
        assert up.released
        # only files from the list: everything else 404, without asking the printer
        op.reset_mock()
        for path in ("config/printer.cfg", "camera/../config/printer.cfg", "logs/klippy.log"):
            resp = await client.get(f"{base}/{path}")
            assert resp.status == 404, path
        op.assert_not_awaited()
    # preview images are stored locally and served statically (not via the proxy)
    assert video["poster_url"].startswith(f"/{DOMAIN}/thumbs/{entry.entry_id}/tl/")
    assert video["thumb_url"].startswith(f"/{DOMAIN}/thumbs/{entry.entry_id}/tl/")
    mock_client["download"].assert_any_await(video["poster"], root="camera")
    resp = await client.get(video["poster_url"])
    assert resp.status == 200
    assert tl.attributes["playable"] is True

    # printer off: the proxy answers immediately without asking the printer
    await hass.services.async_call("input_boolean", "turn_off", {"entity_id": SWITCH}, blocking=True)
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_timelapses").attributes["playable"] is False
    with patch(f"{API}.open_file", AsyncMock(return_value=up)) as op:
        resp = await client.get(f"{base}/camera/{video['path']}")
        assert resp.status == 503
        op.assert_not_awaited()
    # images stay available while switched off
    resp = await client.get(video["poster_url"])
    assert resp.status == 200

    # no access without authentication
    from aiohttp import ClientSession

    async with ClientSession() as raw:
        resp = await raw.get(str(client.make_url(f"{base}/camera/{video['path']}")))
        assert resp.status == 401


# ── Safeguards from the review ─────────────────────────────────────────────
async def test_power_off_refused_when_printer_drops_out_mid_print(hass: HomeAssistant, mock_client) -> None:
    """A WiFi dropout in the middle of a print must not allow switching off."""
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    entry = await _setup(hass)
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    mock_client["query"].side_effect = MoonrakerConnectionError("timeout")
    await _refresh(hass, entry)
    assert entry.runtime_data.data.online is False
    with pytest.raises(HomeAssistantError, match="is printing"):
        await hass.services.async_call("switch", "turn_off", {"entity_id": OWN_SWITCH}, blocking=True)
    with pytest.raises(HomeAssistantError, match="is printing"):
        await hass.services.async_call(DOMAIN, "power_off", {}, blocking=True)
    assert hass.states.get(SWITCH).state == "on"
    # crashed printer: forcing deliberately works
    await hass.services.async_call(DOMAIN, "power_off", {"force": True}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "off"


async def test_power_off_aborts_if_print_starts_during_shutdown(hass: HomeAssistant, mock_client, fast_power) -> None:
    """Shutdown refused; while waiting somebody starts a print on the display."""
    from custom_components.snapmaker_u1_card.api import MoonrakerError

    entry = await _setup(hass)

    async def refused(*a, **k):
        _status(mock_client, "printing", "display.gcode")
        raise MoonrakerError("sudo: a password is required")

    with patch(f"{API}.rpc", AsyncMock(side_effect=refused)):
        await hass.services.async_call(DOMAIN, "power_off", {}, blocking=True)
        await hass.async_block_till_done()
    assert hass.states.get(SWITCH).state == "on"
    assert entry.runtime_data.last_shutdown == "aborted: print started"


async def test_power_off_aborts_while_heating(hass: HomeAssistant, mock_client, fast_power) -> None:
    await _setup(hass)
    st = _status(mock_client, "standby")
    st["heater_bed"]["target"] = 60.0
    with patch(f"{API}.rpc", AsyncMock(return_value="ok")) as rpc:
        await hass.services.async_call(DOMAIN, "power_off", {}, blocking=True)
        await hass.async_block_till_done()
    rpc.assert_not_awaited()  # no shutdown
    assert hass.states.get(SWITCH).state == "on"


async def test_start_print_refused_while_shutting_down(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    entry.runtime_data.shutting_down = True
    with pytest.raises(HomeAssistantError, match="shutting down"):
        await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode", "mapping": {"0": 0}}, blocking=True)
    mock_client["start_print"].assert_not_awaited()


async def test_power_off_refused_while_powering_on(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    entry.runtime_data.powering_on = True
    with pytest.raises(HomeAssistantError, match="booting"):
        await hass.services.async_call(DOMAIN, "power_off", {"force": True}, blocking=True)


async def test_no_auto_off_while_heaters_have_targets(hass: HomeAssistant, mock_client) -> None:
    """Print started on the display: print_stats still reports 'complete', but it is heating."""
    entry = await _setup(hass, auto_off=True, auto_off_delay=0)
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    st = _status(mock_client, "complete", "a.gcode", temps=20.0)
    st["extruder1"]["target"] = 220.0
    await _refresh(hass, entry)
    assert entry.runtime_data.auto_off_armed is not None
    assert hass.states.get(SWITCH).state == "on"
    st["extruder1"]["target"] = 0.0
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert entry.runtime_data.auto_off_armed is None


async def test_running_print_is_saved_periodically(hass: HomeAssistant, mock_client) -> None:
    """The debounce must not postpone saving forever during a long print."""
    entry = await _setup(hass)
    coord = entry.runtime_data
    _status(mock_client, "printing", "a.gcode")
    await _refresh(hass, entry)
    with patch.object(coord._store, "async_delay_save") as save:
        for _ in range(5):
            await _refresh(hass, entry)
        assert save.call_count == 0  # nothing within a minute
        coord._saved_at -= 61
        await _refresh(hass, entry)
        assert save.call_count == 1
        assert save.call_args.args[1] == 1


async def test_gcode_download(hass: HomeAssistant, hass_client, mock_client) -> None:
    """Listed print files download as an attachment through HA; anything else is 404."""
    entry = await _setup(hass)

    class Upstream:
        status = 200
        headers = {"Content-Length": "7"}

        def __init__(self):
            self.released = False

            async def chunks(size):
                yield b"G28\nM73"
            self.content = type("C", (), {"iter_chunked": staticmethod(chunks)})()

        def release(self):
            self.released = True

    up = Upstream()
    client = await hass_client()
    base = f"/api/{DOMAIN}/gcode/{entry.entry_id}"
    with patch(f"{API}.open_file", AsyncMock(return_value=up)) as op:
        resp = await client.get(f"{base}/sub/new.gcode")
        assert resp.status == 200
        assert "attachment" in resp.headers["Content-Disposition"]
        assert "new.gcode" in resp.headers["Content-Disposition"]
        assert await resp.read() == b"G28\nM73"
        assert op.await_args.args == ("gcodes", "sub/new.gcode", {})
        assert up.released
        op.reset_mock()
        for path in ("notes.txt", "../config/printer.cfg", "missing.gcode"):
            resp = await client.get(f"{base}/{path}")
            assert resp.status == 404, path
        op.assert_not_awaited()
