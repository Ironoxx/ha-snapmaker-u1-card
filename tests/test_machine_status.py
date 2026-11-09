"""machine_status (2.0): printer values and commands without the Moonraker integration (HA-free)."""

import importlib.util
from pathlib import Path

import pytest

_P = Path(__file__).resolve().parents[1] / "custom_components" / "snapmaker_u1_card" / "machine_status.py"
_spec = importlib.util.spec_from_file_location("u1card_machine_status", _P)
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)

OBJECTS = [
    "webhooks", "print_stats", "virtual_sdcard", "display_status", "toolhead", "gcode_move", "fan",
    "extruder", "extruder1", "heater_bed", "temperature_sensor cavity", "tmc2240 stepper_x",
    "fan_generic cavity_fan", "heater_fan e0_nozzle_fan", "output_pin e0_heat_sw", "led cavity_led",
    "filament_motion_sensor e0_filament", "mcu", "mcu e0", "print_task_config",
]


def test_subscription_only_known_objects():
    sub = ms.subscription(OBJECTS)
    assert sub["extruder1"] == ["temperature", "target", "power"]
    assert sub["temperature_sensor cavity"] == ["temperature"]
    assert sub["tmc2240 stepper_x"] == ["temperature"]
    assert sub["led cavity_led"] == ["color_data"]
    assert sub["mcu e0"] == ["last_stats"]
    assert "print_task_config" not in sub
    assert "system_stats" not in sub  # not reported by this printer
    assert "webhooks" in ms.subscription([])


def test_build_names_like_moonraker_integration():
    status = {
        "webhooks": {"state": "ready", "state_message": "Printer is ready"},
        "print_stats": {"state": "printing", "filename": "dog.gcode", "print_duration": 600.0,
                        "filament_used": 1234.0, "info": {"current_layer": 3, "total_layer": 90}},
        "virtual_sdcard": {"progress": 0.4567},
        "toolhead": {"position": [10.123, 20.0, 0.4, 0.0]},
        "gcode_move": {"speed_factor": 1.5, "speed": 6000.0},
        "fan": {"speed": 0.5},
        "heater_bed": {"temperature": 60.04, "target": 60.0, "power": 0.25},
        "extruder1": {"temperature": 219.96, "target": 220.0, "power": 1.0},
        "temperature_sensor cavity": {"temperature": 31.25},
        "tmc2240 stepper_x": {"temperature": 41.0},
        "fan_generic cavity_fan": {"speed": 0.3},
        "heater_fan e0_nozzle_fan": {"speed": 1.0},
        "output_pin e0_heat_sw": {"value": 1.0},
        "led cavity_led": {"color_data": [[0.0, 0.0, 0.0, 0.5]]},
        "filament_motion_sensor e0_filament": {"filament_detected": True},
        "mcu": {"last_stats": {"mcu_task_avg": 0.0001, "mcu_task_stddev": 0.0001, "mcu_awake": 0.5}},
        "mcu e0": {"last_stats": {}},
        "extruder2": "broken",
    }
    v, a = ms.build(status, {"memory_used": (40.0, {"unit_of_measurement": "%"}), "queue_state": "ready", "x": None})
    assert v["printer_state"] == "ready" and v["current_print_state"] == "printing"
    assert v["progress"] == 45.7 and a["progress"]["unit_of_measurement"] == "%"
    assert v["print_duration"] == 10.0 and v["filament_used"] == 1.23
    assert (v["current_layer"], v["total_layer"]) == (3, 90)
    assert v["toolhead_position_x"] == 10.12
    assert v["speed_factor"] == 150 and a["speed_factor"]["max"] == ms.SPEED_MAX
    assert v["print_speed"] == 150  # 6000 mm/min / 60 x 1.5
    assert v["fan_speed"] == 50
    assert v["bed_temperature"] == 60.0 and v["bed_target"] == 60 and v["bed_power"] == 25
    assert a["bed_target"]["max"] == ms.BED_MAX and a["extruder1_target"]["max"] == ms.NOZZLE_MAX
    assert v["cavity_temp"] == 31.2 or v["cavity_temp"] == 31.3
    assert v["stepper_x_temp"] == 41.0
    assert v["cavity_fan"] == 30 and v["cavity_fan_speed"] == 30 and v["e0_nozzle_fan"] == 100
    assert "e0_nozzle_fan_speed" not in v  # only fan_generic can be set
    assert v["output_pin_e0_heat_sw"] == "on"
    assert v["led_cavity_led"] == "on" and a["led_cavity_led"]["brightness"] == 128
    assert v["e0_filament"] == "on"
    assert v["mcu_load"] == 16.0 and v["mcu_awake"] == 10.0
    assert "mcu_e0_load" not in v
    assert v["memory_used"] == 40.0 and v["queue_state"] == "ready" and "x" not in v
    assert "extruder2_temperature" not in v


def test_print_speed_only_while_printing():
    v, _ = ms.build({"print_stats": {"state": "standby"}, "gcode_move": {"speed": 6000.0, "speed_factor": 1.0}})
    assert "print_speed" not in v
    v, _ = ms.build({"virtual_sdcard": {}, "display_status": {"progress": 0.5}})
    assert v["progress"] == 50.0


def test_set_gcode():
    assert ms.set_gcode("bed_target", 500, OBJECTS) == "SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET=120"
    assert ms.set_gcode("extruder1_target", "215.4", OBJECTS) == "SET_HEATER_TEMPERATURE HEATER=extruder1 TARGET=215"
    assert ms.set_gcode("fan_speed", 50, OBJECTS) == "M106 S128"
    assert ms.set_gcode("speed_factor", 1, OBJECTS) == "M220 S10"
    assert ms.set_gcode("cavity_fan_speed", 40, OBJECTS) == "SET_FAN_SPEED FAN=cavity_fan SPEED=0.40"
    for key, val in (("extruder3_target", 200), ("e0_nozzle_fan_speed", 10), ("bed_target", "nan"),
                     ("bed_target", "x"), ("anything", 1), ("bed_target; M112", 1)):
        with pytest.raises(ms.CommandError):
            ms.set_gcode(key, val, OBJECTS)


def test_switch_gcode():
    assert ms.switch_gcode("output_pin_e0_heat_sw", True, OBJECTS) == "SET_PIN PIN=e0_heat_sw VALUE=1"
    assert ms.switch_gcode("led_cavity_led", False, OBJECTS) == "SET_LED LED=cavity_led RED=0 GREEN=0 BLUE=0 WHITE=0"
    for key in ("output_pin_other", "led_x", "fan_speed", "led_cavity_led\nM112"):
        with pytest.raises(ms.CommandError):
            ms.switch_gcode(key, True, OBJECTS)


def test_machine_state_and_feeders() -> None:
    """2.2: Snapmaker's machine state (numbers over Moonraker) and the feeders per head."""
    from custom_components.snapmaker_u1_card.machine_status import feeders, filament_check, machine_state
    assert machine_state({}) is None
    idle = machine_state({"machine_state_manager": {"main_state": 0, "action_code": 0}})
    assert idle["main"] == "idle" and idle["busy"] is False and idle["needs_user"] is False
    cal = machine_state({"machine_state_manager": {"main_state": 2, "action_code": 201}})
    assert (cal["main"], cal["action"], cal["busy"]) == ("xyz_offset_calibrate", "wait_nozzle_cooling", True)
    probe = machine_state({"machine_state_manager": {"main_state": 2, "action_code": 198}})
    assert probe["action"] == "xyz_offset_probe" and probe["head"] == 2
    assert machine_state({"machine_state_manager": {"main_state": 8, "action_code": 514}})["needs_user"] is True
    assert machine_state({"machine_state_manager": {"main_state": "MachineMainState.UPGRADING", "action_code": 0}})["main"] == "upgrading"
    assert machine_state({"machine_state_manager": {"main_state": 99, "action_code": 999}})["main"] == "state_99"

    # as reported by Thomas' printer (all four heads loaded)
    ch = {"module_exist": True, "filament_detected": True, "disable_auto": False, "channel_state": "load_finish",
          "channel_error": "ok", "channel_error_state": "none", "channel_action_state": "load_finish"}
    status = {"filament_feed left": {"extruder1": ch, "extruder0": ch}, "filament_feed right": {"extruder2": ch, "extruder3": ch},
              **{f"filament_motion_sensor e{i}_filament": {"filament_detected": True, "enabled": True} for i in range(4)}}
    f = feeders(status)
    assert sorted(f) == [0, 1, 2, 3]
    assert f[2] == {"module": True, "at_feeder": True, "auto": True, "state": "load_finish", "action": "load_finish",
                    "error": "ok", "in_head": True, "sensor_on": True}
    assert filament_check(f[0], "load") == "loaded"
    assert filament_check(f[0], "unload") is None
    empty = {**f[1], "in_head": False, "state": "wait", "at_feeder": False}
    assert filament_check(empty, "unload") == "empty"
    assert filament_check(empty, "load") == "no_filament"
    assert filament_check({**empty, "at_feeder": True}, "load") is None
    assert filament_check({**empty, "at_feeder": True, "error": "jam"}, "load") == "feeder_error"
    assert filament_check({**empty, "auto": False}, "load") == "auto_off"
    assert filament_check(None, "load") is None, "no data: never block"


def test_machine_state_in_values() -> None:
    from custom_components.snapmaker_u1_card.machine_status import build
    v, a = build({"machine_state_manager": {"main_state": 3, "action_code": 257},
                  "filament_feed left": {"extruder0": {"module_exist": True, "filament_detected": False}}})
    assert v["machine_state"] == "bed_leveling" and a["machine_state"]["action"] == "bed_preheating"
    assert a["machine_state"]["busy"] is True
    assert v["filament_feed"]["0"]["at_feeder"] is False
