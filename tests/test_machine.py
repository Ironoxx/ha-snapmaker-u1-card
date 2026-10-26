"""Machine controls: flow, bed mesh, top cover, picking/parking heads and the G-code console."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.snapmaker_u1_card.machine import (
    blocked_while_printing,
    command_word,
    console_lines,
    console_responses,
    flow_gcode,
    park_gcode,
    parse_bed_mesh,
    parse_flow,
    parse_head_states,
    parse_purifier,
    pick_gcode,
    purifier_gcode,
)

# Shapes as reported by u1-klipper (bed_mesh.get_status, purifier.get_status, extruder park detector)
MESH = {"profile_name": "default", "mesh_min": [5.0, 5.0], "mesh_max": [265.0, 265.0],
        "probed_matrix": [[0.1, 0.05, -0.02], [0.0, -0.04, -0.1], [0.08, 0.02, -0.06]]}
PURIFIER = {"power_detected": True, "power_det_value": 1.2, "mode": 1, "desired_chamber_temp": 42.0,
            "critical_chamber_temp": 43.0, "inner_fan_work_time": 7200.0, "inner_fan_rpm": 2410.7,
            "exhaust_fan": {"speed": 0.6, "delay": 180, "speed_threshold": 0},
            "inner_fan": {"speed": 0.0, "delay": 180, "speed_threshold": 0}}


# ── Pure helpers ────────────────────────────────────────────────────────────
def test_flow() -> None:
    assert parse_flow({"extrude_factor": 0.95}) == 95.0
    assert parse_flow({"extrude_factor": True}) is None
    assert parse_flow(None) is None
    assert flow_gcode(97.4) == "M221 S97"
    for bad in (49, 151, "x", float("nan")):
        with pytest.raises(ValueError):
            flow_gcode(bad)


def test_bed_mesh() -> None:
    mesh = parse_bed_mesh(MESH)
    assert mesh["rows"] == 3 and mesh["cols"] == 3
    assert mesh["min"] == -0.1 and mesh["max"] == 0.1 and mesh["range"] == 0.2
    assert mesh["profile"] == "default" and mesh["mesh_min"] == [5.0, 5.0]
    # No mesh loaded: Klipper reports [[]]
    assert parse_bed_mesh({"profile_name": "", "probed_matrix": [[]]}) is None
    assert parse_bed_mesh({"probed_matrix": [[0.1, 0.2], [0.1]]}) is None  # not rectangular
    assert parse_bed_mesh({"probed_matrix": [[0.1, None], [0.1, 0.2]]}) is None
    assert parse_bed_mesh(None) is None


def test_purifier() -> None:
    p = parse_purifier(PURIFIER)
    assert p == {"present": True, "mode": "cool", "exhaust": 60, "inner": 0, "inner_rpm": 2411,
                 "filter_hours": 2.0, "desired_temp": 42.0}
    absent = parse_purifier({"power_detected": False, "mode": 0, "desired_chamber_temp": 0})
    assert absent["present"] is False and absent["mode"] == "idle" and absent["desired_temp"] is None
    assert parse_purifier(None) is None and parse_purifier({}) is None
    assert purifier_gcode("exhaust", 60) == "SET_PURIFIER FAN=exhaust SPEED=0.60"
    with pytest.raises(ValueError):
        purifier_gcode("cavity", 50)
    with pytest.raises(ValueError):
        purifier_gcode("inner", 101)


def test_heads() -> None:
    status = {"extruder": {"state": "PARKED"}, "extruder1": {"state": "ACTIVATE"},
              "extruder2": {"state": "UNKNOWN"}, "extruder3": {}}
    assert parse_head_states(status) == ["parked", "active", "unknown", None]
    assert pick_gcode(2) == "T2 A0"  # A0: physical head, no filament mapping; classic command, no "="
    assert park_gcode(0) == "PARK_EXTRUDER" and park_gcode(3) == "PARK_EXTRUDER3"
    with pytest.raises(ValueError):
        pick_gcode(4)


def test_console_rules() -> None:
    assert console_lines("  M221 S95 \n; comment\n\nSET_FAN_SPEED FAN=cavity_fan SPEED=0.5") == [
        "M221 S95", "SET_FAN_SPEED FAN=cavity_fan SPEED=0.5"]
    for bad in ("", "  \n; only a comment", "G1 X1\n" * 21, "M117 " + "x" * 2000):
        with pytest.raises(ValueError):
            console_lines(bad)
    assert command_word("set_fan_speed FAN=x") == "SET_FAN_SPEED"
    assert command_word("M104 T1 S200") == "M104"
    # During a print: tuning and queries yes, motion/homing/heads no
    ok = ["M104 T0 S215", "M221 S98", "SET_GCODE_OFFSET Z_ADJUST=-0.02", "GET_POSITION", "QUERY_PARK_STA NAME=e0"]
    assert blocked_while_printing(ok) == []
    assert blocked_while_printing(["G28", "G1 X10", "T1 A0", "PARK_EXTRUDER", "G28"]) == [
        "G28", "G1", "T1", "PARK_EXTRUDER"]


def test_console_responses() -> None:
    store = [
        {"type": "command", "message": "M115", "time": 1},
        {"type": "response", "message": "old", "time": 1},
        {"type": "command", "message": "M105\nM114", "time": 2},
        {"type": "command", "message": "M105\nM114", "time": 2},
        {"type": "response", "message": "ok T:21.0", "time": 2},
        {"type": "response", "message": "X:0 Y:0", "time": 2},
        {"type": "command", "message": "G28", "time": 3},  # someone else
        {"type": "response", "message": "not ours", "time": 3},
    ]
    assert console_responses(store, "M105\nM114") == ["ok T:21.0", "X:0 Y:0"]
    assert console_responses(store, "M999") == []
    assert console_responses(None, "M105") == []


# ── In Home Assistant ───────────────────────────────────────────────────────
pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError  # noqa: E402

from tests.test_init import API, DOMAIN, mock_client  # noqa: E402, F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: E402, F401


def _machine(mock_client, purifier=None) -> dict:
    st = mock_client["query"].return_value
    st["gcode_move"] = {"extrude_factor": 1.0}
    st["bed_mesh"] = MESH
    st["extruder"]["state"] = "ACTIVATE"
    for n in ("extruder1", "extruder2", "extruder3"):
        st[n]["state"] = "PARKED"
    if purifier is not None:
        st["purifier"] = purifier
    return st


async def test_flow_and_mesh_entities(hass: HomeAssistant, mock_client, notifications) -> None:
    _machine(mock_client)
    entry = await _setup(hass)
    flow = hass.states.get("number.snapmaker_u1_card_flow")
    assert flow.state == "100.0"
    mesh = hass.states.get("sensor.snapmaker_u1_card_bed_mesh_spread")
    assert float(mesh.state) == 0.2 and mesh.attributes["cols"] == 3
    fil = hass.states.get("sensor.snapmaker_u1_card_filaments")
    assert fil.attributes["head_states"] == ["active", "parked", "parked", "parked"]
    # No cover plugged in: no top cover entities at all
    assert hass.states.get("sensor.snapmaker_u1_card_top_cover") is None

    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        _status(mock_client, "printing", "a.gcode")  # flow is meant for running prints
        await _refresh(hass, entry)
        await hass.services.async_call("number", "set_value",
                                       {"entity_id": "number.snapmaker_u1_card_flow", "value": 95}, blocking=True)
        gcode.assert_awaited_with("M221 S95")


async def test_top_cover_added_when_detected(hass: HomeAssistant, mock_client, notifications) -> None:
    st = _machine(mock_client, {**PURIFIER, "power_detected": False})
    entry = await _setup(hass)
    assert hass.states.get("sensor.snapmaker_u1_card_top_cover") is None
    st["purifier"] = PURIFIER
    await _refresh(hass, entry)
    cover = hass.states.get("sensor.snapmaker_u1_card_top_cover")
    assert cover.state == "cool" and cover.attributes["filter_hours"] == 2.0
    assert hass.states.get("number.snapmaker_u1_card_top_cover_exhaust_fan").state == "60"
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        await hass.services.async_call("number", "set_value",
                                       {"entity_id": "number.snapmaker_u1_card_top_cover_circulation_fan",
                                        "value": 40}, blocking=True)
        gcode.assert_awaited_with("SET_PURIFIER FAN=inner SPEED=0.40")
    # Cover unplugged: entities stay, but unavailable
    st["purifier"] = {**PURIFIER, "power_detected": False}
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_top_cover").state == "unavailable"


async def test_tool_change(hass: HomeAssistant, mock_client, notifications) -> None:
    _machine(mock_client)
    entry = await _setup(hass)
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        await hass.services.async_call(DOMAIN, "tool_change", {"head": 3}, blocking=True)
        assert gcode.await_args.args[0] == "T2 A0"
        assert gcode.await_args.kwargs["timeout"] >= 120
        await hass.services.async_call(DOMAIN, "tool_change", {"head": 1, "action": "park"}, blocking=True)
        assert gcode.await_args.args[0] == "PARK_EXTRUDER"  # head 1 is on the carriage
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        calls = gcode.await_count
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(DOMAIN, "tool_change", {"head": 2}, blocking=True)
        assert gcode.await_count == calls


async def test_send_gcode(hass: HomeAssistant, mock_client, notifications) -> None:
    _machine(mock_client)
    entry = await _setup(hass)
    store = [{"type": "command", "message": "M105", "time": 1},
             {"type": "response", "message": "ok T0:21.0 /0.0", "time": 1}]
    with patch(f"{API}.gcode", AsyncMock()) as gcode, patch(f"{API}.gcode_store", AsyncMock(return_value=store)):
        result = await hass.services.async_call(DOMAIN, "send_gcode", {"script": "M105"},
                                                blocking=True, return_response=True)
        assert result == {"script": "M105", "ok": True, "error": None, "responses": ["ok T0:21.0 /0.0"]}
        # Firmware refusal is part of the answer
        from custom_components.snapmaker_u1_card.api import MoonrakerError
        gcode.side_effect = MoonrakerError("Unknown command:\"FOO\"")
        result = await hass.services.async_call(DOMAIN, "send_gcode", {"script": "FOO"},
                                                blocking=True, return_response=True)
        assert result["ok"] is False and "FOO" in result["error"]
        gcode.side_effect = None
        # During a print only tuning commands
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        with pytest.raises(ServiceValidationError, match="G28"):
            await hass.services.async_call(DOMAIN, "send_gcode", {"script": "M221 S95\nG28"},
                                           blocking=True, return_response=True)
        await hass.services.async_call(DOMAIN, "send_gcode", {"script": "M221 S95"},
                                       blocking=True, return_response=True)
        gcode.assert_awaited_with("M221 S95", timeout=180)


# ── Nozzles (1.6.0b4) ───────────────────────────────────────────────────────
def test_nozzles() -> None:
    from custom_components.snapmaker_u1_card.machine import nozzle_mismatches, parse_nozzles
    status = {"extruder": {"nozzle_diameter": 0.4, "nozzle_volume_type": "standard"},
              "extruder1": {"nozzle_diameter": 0.6, "nozzle_volume_type": "high_flow"},
              "extruder2": {"nozzle_diameter": 0.0}, "extruder3": {}}
    heads = parse_nozzles(status)
    assert heads == [{"diameter": 0.4, "type": "standard"}, {"diameter": 0.6, "type": "high_flow"}, None, None]
    # filament 0 -> head 0 fine, filament 1 (0.4) -> head 1 (0.6) mismatch, unknown values ignored
    assert nozzle_mismatches([0.4, 0.4, None], {0: 0, 1: 1, 2: 2}, heads) == [
        {"filament": 1, "head": 1, "file": 0.4, "head_nozzle": 0.6}]


def test_file_nozzle_from_metadata() -> None:
    from custom_components.snapmaker_u1_card.parsing import parse_file_filaments
    fils = parse_file_filaments({"filament_type": "PLA;PETG", "nozzle_diameter_list": [0.4, 0.6]})
    assert [f["nozzle"] for f in fils] == [0.4, 0.6]
    fils = parse_file_filaments({"filament_type": "PLA;PETG", "nozzle_diameter": 0.4})
    assert [f["nozzle"] for f in fils] == [0.4, 0.4]
    assert parse_file_filaments({"filament_type": "PLA"})[0]["nozzle"] is None


async def test_slot_nozzle_attribute(hass: HomeAssistant, mock_client, notifications) -> None:
    st = _machine(mock_client)
    st["extruder"]["nozzle_diameter"] = 0.4
    st["extruder"]["nozzle_volume_type"] = "standard"
    await _setup(hass)
    slots = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["slots"]
    assert slots[0]["nozzle"] == {"diameter": 0.4, "type": "standard"}
    assert slots[1]["nozzle"] is None


# ── Maintenance push (1.6.0b4) ──────────────────────────────────────────────
async def test_maintenance_due_push(hass: HomeAssistant, mock_client, notifications) -> None:
    import time as _t
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["maintenance"])
    coord = entry.runtime_data
    # Pretend the monthly items were last done 40 days ago
    for key in ("rails", "belts", "carbon_rods"):
        coord.maintenance.done[key] = {"hours": 0.0, "at": _t.time() - 40 * 86400}
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    maint = [c for c in notifications if "Wartung" in c.data["title"] or "Maintenance" in c.data["title"]]
    assert len(maint) == 1
    assert "X-Carbonstangen" in maint[0].data["message"] or "carbon" in maint[0].data["message"]
    assert "image" not in maint[0].data["data"]
    # Not again on the next poll
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert len([c for c in notifications if "Wartung" in c.data["title"] or "Maintenance" in c.data["title"]]) == 1
    # Done -> may notify again later
    await hass.services.async_call(DOMAIN, "maintenance_done", {"item": "rails"}, blocking=True)
    await _refresh(hass, entry)
    assert "rails" not in coord._maint_notified


# ── Chamber heater (1.6.0b4) ────────────────────────────────────────────────
def test_chamber_helpers() -> None:
    from custom_components.snapmaker_u1_card.machine import (
        chamber_filter_gcode, chamber_gcode, find_chamber_heater, parse_chamber)
    assert find_chamber_heater(["extruder", "heater_bed"]) is None
    db = find_chamber_heater(["heater_generic dragonbreath", "output_pin dragonbreath_filter"])
    assert db["name"] == "dragonbreath" and db["filter"] == "dragonbreath_filter" and db["max"] == 75
    pb = find_chamber_heater(["heater_generic panda_breath"])
    assert pb["name"] == "panda_breath" and pb["filter"] is None and pb["min"] == 15
    status = {"heater_generic dragonbreath": {"temperature": 41.27, "target": 50.0, "power": 0.62},
              "output_pin dragonbreath_filter": {"value": 1.0}}
    assert parse_chamber(status, db) == {"name": "dragonbreath", "label": "DragonBreath", "min": 0, "max": 75,
                                         "temperature": 41.3, "target": 50.0, "power": 62, "filter": True}
    assert chamber_gcode(db, 55) == "SET_HEATER_TEMPERATURE HEATER=dragonbreath TARGET=55"
    assert chamber_gcode(pb, 0) == "SET_HEATER_TEMPERATURE HEATER=panda_breath TARGET=0"
    for bad in (10, 90, -1):  # Panda Breath: 0 or 15-80
        with pytest.raises(ValueError):
            chamber_gcode(pb, bad)
    assert chamber_filter_gcode(db, True) == "SET_PIN PIN=dragonbreath_filter VALUE=1"
    with pytest.raises(ValueError):
        chamber_filter_gcode(pb, True)


async def test_chamber_entities(hass: HomeAssistant, mock_client, notifications) -> None:
    mock_client["objects"].return_value = ["print_task_config", "heater_generic dragonbreath",
                                           "output_pin dragonbreath_filter"]
    st = mock_client["query"].return_value
    st["heater_generic dragonbreath"] = {"temperature": 38.0, "target": 0.0, "power": 0.0}
    st["output_pin dragonbreath_filter"] = {"value": 0.0}
    entry = await _setup(hass)
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_chamber_heater").state == "38.0"
    assert hass.states.get("switch.snapmaker_u1_card_chamber_heater_filter").state == "off"
    target = hass.states.get("number.snapmaker_u1_card_chamber_heater_target")
    assert target.state == "0.0" and target.attributes["max"] == 75
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        _status(mock_client, "printing", "abs.gcode")  # allowed during a print
        await _refresh(hass, entry)
        await hass.services.async_call("number", "set_value", {"entity_id": target.entity_id, "value": 55},
                                       blocking=True)
        gcode.assert_awaited_with("SET_HEATER_TEMPERATURE HEATER=dragonbreath TARGET=55")
        await hass.services.async_call("switch", "turn_on",
                                       {"entity_id": "switch.snapmaker_u1_card_chamber_heater_filter"}, blocking=True)
        gcode.assert_awaited_with("SET_PIN PIN=dragonbreath_filter VALUE=1")


async def test_no_chamber_no_entities(hass: HomeAssistant, mock_client, notifications) -> None:
    await _setup(hass)
    assert hass.states.get("sensor.snapmaker_u1_card_chamber_heater") is None
    assert hass.states.get("number.snapmaker_u1_card_chamber_heater_target") is None
