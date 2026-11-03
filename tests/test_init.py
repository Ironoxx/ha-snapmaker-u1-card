"""The integration in a real Home Assistant test instance."""

from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.config_entries import SOURCE_USER  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.exceptions import HomeAssistantError  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

DOMAIN = "snapmaker_u1_card"
API = "custom_components.snapmaker_u1_card.api.MoonrakerClient"

PTC = {
    "filament_type": ["PLA", "PETG", "NONE", "NONE"],
    "filament_sub_type": ["Matte", "HF", "NONE", "NONE"],
    "filament_vendor": ["Snapmaker", "Generic", "NONE", "NONE"],
    "filament_color_rgba": ["FFFFFFFF", "000000FF", "FFFFFFFF", "FFFFFFFF"],
    "filament_exist": [True, True, False, False],
    "filament_official": [True, False, False, False],
    "extruder_map_table": [0, 1, 2, 3] + [0] * 28,
    "auto_bed_leveling": True, "flow_calibrate": False, "time_lapse_camera": False,
}
META = {
    "filament_type": "PETG;PLA", "filament_colour": "#111111;#EEEEEE",
    "filament_weight": [4.0, 6.0], "estimated_time": 600,
    "thumbnails": [{"width": 300, "height": 300, "relative_path": ".thumbs/t.png"}],
}


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, hass, tmp_path):
    # The real frontend package (hass_frontend) is not installed in tests.
    hass.config.components.add("frontend")
    # Own config directory: thumbnails would otherwise end up in the
    # shared testing_config of the test package.
    hass.config.config_dir = str(tmp_path)
    yield


@pytest.fixture
def mock_client():
    status = {
        "print_task_config": PTC,
        "print_stats": {"state": "standby", "filename": ""},
        **{n: {"switch_count": 100 * (i + 1), "last_maintenance_count": 0, "retry_count": 0, "error_count": 0}
           for i, n in enumerate(("extruder", "extruder1", "extruder2", "extruder3"))},
    }
    files = {
        "gcodes": [
            {"path": "old.gcode", "modified": 1, "size": 1},
            {"path": "sub/new.gcode", "modified": 9, "size": 1},
            {"path": "notes.txt", "modified": 10, "size": 1},
        ],
        # As on the real U1 (stock firmware), folder "camera"
        "camera": [
            {"path": "Nuss_2_PLA_1h17m_20261008195643.mp4", "modified": 20, "size": 17019965},
            {"path": "Nuss_2_PLA_1h17m_20261008195643_cover.jpg", "modified": 19, "size": 32859},
            {"path": "Nuss_2_PLA_1h17m_20261008195643.jpg", "modified": 19, "size": 2576},
        ],
    }
    HIST = [{"status": "completed", "start_time": 1.7e9, "print_duration": 3600, "filename": "a.gcode", "metadata": {"filament_weight_total": 10.0}}]
    with patch(f"{API}.query_objects", AsyncMock(return_value=status)) as q, \
         patch(f"{API}.list_files", AsyncMock(side_effect=lambda root="gcodes": files.get(root, []))), \
         patch(f"{API}.list_roots", AsyncMock(return_value=["config", "logs", "gcodes", "camera"])), \
         patch(f"{API}.klippy_ready", AsyncMock(return_value=True)) as ready, \
         patch(f"{API}.file_metadata", AsyncMock(return_value=META)), \
         patch(f"{API}.download", AsyncMock(return_value=b"\x89PNG")) as dl, \
         patch(f"{API}.start_print", AsyncMock(return_value={"state": "success"})) as sp, \
         patch(f"{API}.history", AsyncMock(return_value=HIST)), \
         patch(f"{API}.download_to", AsyncMock(side_effect=OSError("kein Netz im Test"))), \
         patch(f"{API}.cpu_count", AsyncMock(return_value=4)), \
         patch(f"{API}.components", AsyncMock(return_value=["file_manager", "history"])) as comps, \
         patch(f"{API}.object_list", AsyncMock(return_value=["print_task_config", "extruder", "heater_bed"])) as objs, \
         patch(f"{API}.firmware_version", AsyncMock(return_value="1.6.0")), \
         patch(f"{API}.history_totals", AsyncMock(return_value={"total_print_time": 36000.0})):
        yield {"query": q, "download": dl, "start_print": sp, "ready": ready, "files": files, "components": comps,
               "objects": objs}


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, data={"host": "192.0.2.10", "port": 80}, unique_id="192.0.2.10")
    entry.add_to_hass(hass)
    with patch("custom_components.snapmaker_u1_card.add_extra_js_url") as js:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    js.assert_called_once()
    assert js.call_args.args[1].startswith("/snapmaker_u1_card/card/snapmaker-u1-card.js?v=")
    return entry


async def test_sensors(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    fil = hass.states.get("sensor.snapmaker_u1_card_filaments")
    assert fil is not None, [s.entity_id for s in hass.states.async_all()]
    assert fil.state == "2"
    assert fil.attributes["slots"][0]["type"] == "PLA"
    assert fil.attributes["preferences"]["bed_leveling"] is True
    assert hass.states.get("sensor.snapmaker_u1_card_slot_2").state == "PETG HF"
    assert hass.states.get("sensor.snapmaker_u1_card_slot_3").state == "leer"

    files = hass.states.get("sensor.snapmaker_u1_card_print_files")
    assert files.state == "2"  # .txt filtered
    paths = [f["path"] for f in files.attributes["files"]]
    assert paths == ["sub/new.gcode", "old.gcode"]  # newest first
    thumb = files.attributes["files"][0]["thumb"]
    assert thumb.startswith(f"/snapmaker_u1_card/thumbs/{entry.entry_id}/")
    mock_client["download"].assert_any_await("sub/.thumbs/t.png")


async def test_start_print_explicit_mapping(hass: HomeAssistant, mock_client) -> None:
    await _setup(hass)
    resp = await hass.services.async_call(
        DOMAIN, "start_print",
        {"filename": "sub/new.gcode", "mapping": {"0": 1, "1": 0}, "bed_leveling": False, "timelapse": True},
        blocking=True, return_response=True,
    )
    assert resp["map_table"] == "[[0, 1], [1, 0]]"
    kwargs = mock_client["start_print"].await_args.kwargs
    assert mock_client["start_print"].await_args.args == ("sub/new.gcode",)
    assert kwargs["map_table"] == "[[0, 1], [1, 0]]"
    assert kwargs["bed_leveling"] is False and kwargs["timelapse"] is True
    assert kwargs["flow_calibration"] is None


async def test_start_print_auto_mapping(hass: HomeAssistant, mock_client) -> None:
    await _setup(hass)
    await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode"}, blocking=True)
    # PETG black -> slot 2 (index 1), PLA light -> slot 1 (index 0)
    assert mock_client["start_print"].await_args.kwargs["map_table"] == "[[0, 1], [1, 0]]"


async def test_start_print_error_surfaces(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerError

    await _setup(hass)
    mock_client["start_print"].side_effect = MoonrakerError("Printer is busy, cannot start print")
    with pytest.raises(HomeAssistantError, match="busy"):
        await hass.services.async_call(
            DOMAIN, "start_print", {"filename": "x.gcode", "mapping": {"0": 0}}, blocking=True
        )


async def test_invalid_mapping_rejected(hass: HomeAssistant, mock_client) -> None:
    import voluptuous as vol

    await _setup(hass)
    with pytest.raises((vol.Invalid, HomeAssistantError)):
        await hass.services.async_call(
            DOMAIN, "start_print", {"filename": "x.gcode", "mapping": {"0": 7}}, blocking=True
        )


async def test_config_flow(hass: HomeAssistant, mock_client) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.snapmaker_u1_card.async_setup_entry", AsyncMock(return_value=True)), \
         patch("custom_components.snapmaker_u1_card.async_setup", AsyncMock(return_value=True)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "http://192.0.2.10/", "port": 80, "api_key": ""}
        )
        # Second step: all settings right away during setup
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "settings"
        schema = result["data_schema"].schema
        assert {str(k) for k in schema} == {"power", "notify", "filament", "spoolman", "files", "timelapse", "maintenance"}
        # No section with a default: the frontend would otherwise drop the pre-filled
        # values and report "Not all required fields are filled in".
        for key in schema:
            assert key.default is vol.UNDEFINED, f"Abschnitt {key} hat default"
        settings = {
            "power": {"shutdown_host": True, "auto_on": False, "auto_off": False, "auto_off_temp": 50, "auto_off_delay": 5},
            "notify": {"notify_events": ["complete"]}, "filament": {"price_pla": 19.5},
            "spoolman": {"spoolman_deduct": True, "spoolman_low": 100}, "files": {"files_limit": 24},
            "timelapse": {"timelapse_archive": True, "timelapse_keep": 3},
            "maintenance": {"maint_plate": 25, "maint_nozzle": 100, "maint_rails": 300, "maint_belts": 500, "maint_filter": 0},
        }
        result = await hass.config_entries.flow.async_configure(result["flow_id"], settings)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "192.0.2.10"
    opts = result["options"]
    assert opts["timelapse_archive"] is True and opts["timelapse_keep"] == 3
    assert opts["filament_prices"] == {"PLA": 19.5} and opts["maintenance"]["plate"] == 25


async def test_config_flow_not_u1(hass: HomeAssistant, mock_client) -> None:
    mock_client["query"].return_value = {}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.11", "port": 80, "api_key": ""}
    )
    assert result["errors"] == {"base": "not_u1"}


async def test_unload(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_static_paths_serve_card_and_thumbnail(hass: HomeAssistant, hass_client, mock_client) -> None:
    await _setup(hass)
    client = await hass_client()
    resp = await client.get("/snapmaker_u1_card/card/snapmaker-u1-card.js")
    assert resp.status == 200
    assert "snapmaker-u1-card" in await resp.text()
    thumb = hass.states.get("sensor.snapmaker_u1_card_print_files").attributes["files"][0]["thumb"]
    resp = await client.get(thumb)
    assert resp.status == 200
    assert await resp.read() == b"\x89PNG"


async def test_tool_changes(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    q = mock_client["query"]
    assert "print_stats" in q.await_args.kwargs["fields"]
    total = hass.states.get("sensor.snapmaker_u1_card_tool_changes")
    assert total.state == "1000"
    assert total.attributes["heads"][1]["switches"] == 200
    printing = hass.states.get("sensor.snapmaker_u1_card_tool_changes_print")
    assert printing.state == "unknown"

    # Start the print via the service: the baseline is set right away
    status = q.return_value
    await hass.services.async_call(DOMAIN, "start_print", {"filename": "sub/new.gcode", "mapping": {"0": 0}}, blocking=True)
    status["print_stats"] = {"state": "printing", "filename": "sub/new.gcode"}
    status["extruder"]["switch_count"] += 12
    status["extruder1"]["switch_count"] += 11
    coordinator = entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    st = hass.states.get("sensor.snapmaker_u1_card_tool_changes_print")
    assert st.state == "23" and st.attributes["in_progress"] is True
    assert st.attributes["file"] == "sub/new.gcode"

    # Integration restart in the middle of a print: the baseline survives
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    status["extruder"]["switch_count"] += 5
    status["print_stats"] = {"state": "complete", "filename": "sub/new.gcode"}
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    st = hass.states.get("sensor.snapmaker_u1_card_tool_changes_print")
    assert st.state == "28"
    assert st.attributes["in_progress"] is False
    assert st.attributes["result"] == "complete"
    assert hass.states.get("sensor.snapmaker_u1_card_tool_changes").state == "1028"


async def test_tool_changes_unavailable_without_counters(hass: HomeAssistant, mock_client) -> None:
    mock_client["query"].return_value = {"print_task_config": PTC, "print_stats": {"state": "standby"}}
    await _setup(hass)
    assert hass.states.get("sensor.snapmaker_u1_card_tool_changes").state == "unavailable"
    assert hass.states.get("sensor.snapmaker_u1_card_filaments").state == "2"


async def test_machine_values_and_commands(hass: HomeAssistant, mock_client) -> None:
    """2.0: values and controls without the Moonraker integration."""
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import entity_registry as er

    status = mock_client["query"].return_value
    status["webhooks"] = {"state": "ready", "state_message": "ok"}
    status["heater_bed"] = {"temperature": 60.0, "target": 60.0, "power": 0.4}
    status["extruder"].update(temperature=210.0, target=215.0, power=0.3)
    status["fan"] = {"speed": 0.5}
    status["gcode_move"] = {"speed_factor": 1.0, "speed": 3000.0}
    status["led cavity_led"] = {"color_data": [[1.0, 1.0, 1.0, 1.0]]}
    mock_client["objects"].return_value = ["print_task_config", "extruder", "heater_bed", "fan", "gcode_move",
                                           "webhooks", "print_stats", "led cavity_led"]
    with patch(f"{API}.gcode", AsyncMock()) as gcode, \
         patch(f"{API}.print_action", AsyncMock()) as action, \
         patch(f"{API}.emergency_stop", AsyncMock()) as estop:
        await _setup(hass)
        await hass.async_block_till_done()
        ent = er.async_get(hass)
        mine = {e.translation_key: e.entity_id for e in ent.entities.values() if e.platform == DOMAIN}
        machine = hass.states.get(mine["machine"])
        assert machine is not None and machine.state == "ready"
        values = machine.attributes["values"]
        assert values["bed_temperature"] == 60.0 and values["extruder_target"] == 215
        assert values["led_cavity_led"] == "on"
        assert machine.attributes["attrs"]["bed_target"]["max"] == 120
        assert hass.states.get(mine["bed_temperature"]).state == "60.0"
        assert hass.states.get(mine["bed_target"]).state == "60.0"
        assert hass.states.get(mine["chamber_light"]).state == "on"
        assert "pause_print" in mine and "emergency_stop" in mine

        async def cmd(**data):
            await hass.services.async_call(DOMAIN, "machine_command", data, blocking=True)

        await cmd(action="pause")
        action.assert_awaited_with("pause")
        await cmd(action="emergency_stop")
        estop.assert_awaited_once()
        await cmd(action="set", target="bed_target", value=70)
        gcode.assert_awaited_with("SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET=70")
        await cmd(action="switch", target="led_cavity_led", value=False)
        assert "SET_LED LED=cavity_led RED=0" in gcode.await_args.args[0]
        await cmd(action="home", target="z")
        assert gcode.await_args.args[0] == "G28 Z"
        with pytest.raises(ServiceValidationError):
            await cmd(action="set", target="extruder3_target", value=200)
        with pytest.raises(ServiceValidationError):
            await cmd(action="switch", target="output_pin_nope", value=True)
        # number entity -> same command
        await hass.services.async_call("number", "set_value", {"entity_id": mine["nozzle_target"], "value": 200},
                                       blocking=True)
        assert gcode.await_args.args[0] == "SET_HEATER_TEMPERATURE HEATER=extruder TARGET=200"
        await hass.services.async_call("button", "press", {"entity_id": mine["resume_print"]}, blocking=True)
        action.assert_awaited_with("resume")


async def test_machine_entities_added_when_values_appear(hass: HomeAssistant, mock_client) -> None:
    """Chamber temperature and fans only come after the object list: their entities follow (b3 bug)."""
    from homeassistant.helpers import entity_registry as er

    status = mock_client["query"].return_value
    status["webhooks"] = {"state": "ready"}
    status["heater_bed"] = {"temperature": 22.0, "target": 0.0, "power": 0.0}
    entry = await _setup(hass)
    ent = er.async_get(hass)

    def mine():
        return {e.translation_key for e in ent.entities.values() if e.platform == DOMAIN}

    assert "machine" in mine() and "cavity_temperature" not in mine() and "part_fan" not in mine()
    # later the printer reports the chamber sensor and the part fan
    status["temperature_sensor cavity"] = {"temperature": 26.0}
    status["fan"] = {"speed": 0.0}
    mock_client["objects"].return_value = [*mock_client["objects"].return_value, "temperature_sensor cavity", "fan"]
    coord = entry.runtime_data
    coord._objects = mock_client["objects"].return_value
    await coord.async_refresh()
    await hass.async_block_till_done()
    assert {"cavity_temperature", "part_fan"} <= mine()
    cavity = next(e.entity_id for e in ent.entities.values() if e.translation_key == "cavity_temperature")
    assert hass.states.get(cavity).state == "26.0"
    # no duplicates on further updates
    n = len(mine())
    await coord.async_refresh()
    await hass.async_block_till_done()
    assert len(mine()) == n
