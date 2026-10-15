import ast

import pytest

from conftest import parsing as p

# Excerpt from u1-companion/docs/PROTOCOL.md 3.2 (derived from Snapmaker's source code)
PTC = {
    "filament_vendor": ["Snapmaker", "Snapmaker", "Snapmaker", "NONE"],
    "filament_type": ["PLA", "PLA", "PETG", "NONE"],
    "filament_sub_type": ["Basic", "Matte", "HF", "NONE"],
    "filament_color": [4278190080, 4294308065, 4292027178, 4294967295],
    "filament_color_rgba": ["000000FF", "F5F0E1FF", "D3232AFF", "FFFFFFFF"],
    "filament_color_multi": [
        {"nums": 1, "alpha": 255, "mode": 0, "colors": ["000000"]},
        {"nums": 1, "alpha": 255, "mode": 0, "colors": ["F5F0E1"]},
        {"nums": 2, "alpha": 255, "mode": 1, "colors": ["D3232A", "FBC02D", "000000"]},
        {},
    ],
    "filament_official": [True, True, False, False],
    "filament_exist": [True, True, True, False],
    "extruder_map_table": [0, 1, 2, 3] + [0] * 28,
    "auto_bed_leveling": True, "flow_calibrate": False, "time_lapse_camera": True,
}

META = {
    "filament_type": "PLA;PLA;PETG;PLA",
    "filament_colour": "#F2F2F2;#D32F2F;#101010;#00FF00",
    "filament_name": '"Generic PLA";"Generic PLA";"Snapmaker PETG HF";"Unused"',
    "filament_weight": [12.5, 3.1, 7.0, 0.0],
    "filament_total": 8123.4, "filament_weight_total": 22.6,
    "estimated_time": 4200, "layer_count": 120,
    "thumbnails": [
        {"width": 48, "height": 48, "relative_path": ".thumbs/a-48x48.png"},
        {"width": 300, "height": 300, "relative_path": ".thumbs/a-300x300.png"},
        {"width": 500, "height": 500, "relative_path": ".thumbs/a-500x500.png"},
    ],
}


def test_slots():
    slots = p.parse_slots(PTC)
    assert [s["type"] for s in slots] == ["PLA", "PLA", "PETG", None]
    assert slots[0]["color"] == "#000000" and slots[1]["color"] == "#F5F0E1"
    assert slots[2]["colors"] == ["#D3232A", "#FBC02D"]  # nums=2 cuts off the third colour
    assert (slots[3]["loaded"], slots[3]["vendor"], slots[3]["type"]) == (False, None, None)
    assert slots[0]["official"] and not slots[2]["official"]


def test_slots_empty_payload():
    slots = p.parse_slots(None)
    assert len(slots) == 4 and not any(s["loaded"] for s in slots)


def test_preferences():
    assert p.parse_preferences(PTC) == {"bed_leveling": True, "flow_calibration": False, "timelapse": True}


def test_file_filaments():
    fil = p.parse_file_filaments(META)
    assert [f["used"] for f in fil] == [True, True, True, False]
    assert fil[0]["name"] == "Generic PLA" and fil[1]["color"] == "#D32F2F"
    assert fil[2]["type"] == "PETG" and fil[2]["weight"] == 7.0


def test_file_without_weights_counts_all_used():
    fil = p.parse_file_filaments({"filament_type": "PLA;PETG", "filament_colour": "#FFFFFF;#000000"})
    assert [f["used"] for f in fil] == [True, True]


def test_suggest_mapping_type_then_color():
    slots = p.parse_slots(PTC)
    fil = p.parse_file_filaments(META)
    # light grey PLA -> beige PLA (1); red PLA -> PLA slot with the closest colour;
    # PETG -> PETG slot (2)
    m = p.suggest_mapping(fil, slots)
    assert m[0] == 1 and m[2] == 2
    assert m[1] in (0, 1)
    assert 3 not in m  # unused


def test_suggest_mapping_without_loaded_slots():
    m = p.suggest_mapping(p.parse_file_filaments(META), p.parse_slots(None))
    assert m == {0: 0, 1: 1, 2: 2}


def test_map_table_roundtrip_through_klipper_parser():
    """Check the format the way Snapmaker's firmware reads it."""
    table = p.map_table_option({1: 0, 0: 2})
    assert table == "[[0, 2], [1, 0]]"
    # klippy_apis.start_print_advanced: KEY="value"
    script = f'SDCARD_PRINT_FILE_WITH_PARAMETERS FILENAME="a b.gcode" MAP_TABLE="{table}" BED_LEVEL="1"'
    params = dict(arg.split("=", 1) for arg in _split_gcode_params(script.split(" ", 1)[1]))
    assert params["FILENAME"] == "a b.gcode"
    assert ast.literal_eval(params["MAP_TABLE"]) == [[0, 2], [1, 0]]


@pytest.mark.parametrize("bad", [{0: 4}, {32: 0}, {-1: 0}])
def test_map_table_rejects_invalid(bad):
    with pytest.raises(ValueError):
        p.map_table_option(bad)


def test_thumbnail_choice_and_path():
    assert p.pick_thumbnail(META) == ".thumbs/a-300x300.png"
    assert p.thumbnail_source("sub/dir/x.gcode", ".thumbs/a.png") == "sub/dir/.thumbs/a.png"
    assert p.thumbnail_source("x.gcode", ".thumbs/a.png") == ".thumbs/a.png"


def test_describe_file():
    info = p.describe_file("sub/Benchy.gcode", {"modified": 5, "size": 9}, META)
    assert info["name"] == "Benchy" and info["filament"] == 8.12 and info["weight"] == 22.6


def test_color_helpers():
    assert p.normalize_color("1b5e20ff") == "#1B5E20"
    assert p.normalize_color(0xFF1B5E20) == "#1B5E20"
    assert p.normalize_color("NONE") is None
    assert p.color_distance("#000000", "#000000") == 0


def _split_gcode_params(eargs):
    """Copy of u1-klipper/klippy/gcode.py (_split_gcode_params)."""
    result, current, in_quote, quote_char = [], [], False, None
    for ch in eargs:
        if in_quote:
            if ch == quote_char:
                in_quote = False
            else:
                current.append(ch)
        elif ch in ('"', "'"):
            in_quote, quote_char = True, ch
        elif ch in (" ", "\t"):
            if current:
                result.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        result.append("".join(current))
    return result


# ── Tool changes ────────────────────────────────────────────────────────────
def _ext(sw, maint=0, retry=0, err=0):
    return {"switch_count": sw, "last_maintenance_count": maint, "retry_count": retry, "error_count": err}


def test_parse_tool_changes():
    tc = p.parse_tool_changes({
        "extruder": _ext(100, 40, 2, 1), "extruder1": _ext(50), "extruder2": _ext(0), "extruder3": _ext(7),
    })
    assert tc["total"] == 157
    assert tc["heads"][0] == {"index": 0, "switches": 100, "retries": 2, "errors": 1, "since_maintenance": 60}
    assert tc["maintenance_threshold"] == 25100


def test_parse_tool_changes_missing_firmware_support():
    assert p.parse_tool_changes({"extruder": {"temperature": 20}}) is None
    assert p.parse_tool_changes(None) is None


def _c(sw, en=None):
    return {"switches": sw, "energy": en}


def test_track_print_full_cycle():
    track = p.track_print
    st = {"active": None, "last": None}
    st, fin, ch = track(st, "standby", "", _c(1000, 5.0), 1.0)
    assert not ch and fin is None and st["active"] is None
    st, fin, ch = track(st, "printing", "a.gcode", _c(1000, 5.0), 2.0)
    assert ch and st["active"]["start"] == {"switches": 1000, "energy": 5.0}
    st, fin, ch = track(st, "printing", "a.gcode", _c(1042, 5.25), 3.0)
    assert not ch
    assert p.print_progress(st, _c(1042, 5.25)) == {"switches": 42, "energy": 0.25, "energy_cost": None}
    st, fin, ch = track(st, "paused", "a.gcode", _c(1050, 5.3), 4.0)
    assert not ch and fin is None
    st, fin, ch = track(st, "complete", "a.gcode", _c(1061, 5.4), 5.0)
    assert ch and st["active"] is None
    assert fin == st["last"] == {
        "file": "a.gcode", "result": "complete", "started": 2.0, "ended": 5.0,
        "switches": 61, "energy": 0.4,
    }
    assert p.print_progress(st, _c(1061, 5.4)) == {"switches": None, "energy": None, "energy_cost": None}


def test_track_print_unknown_counters():
    # Old firmware, no energy meter: the print is still recorded (event).
    st, _, _ = p.track_print({"active": None, "last": None}, "printing", "a", _c(None), 1.0)
    st, fin, _ = p.track_print(st, "error", "a", _c(None), 9.0)
    assert fin["result"] == "error" and fin["switches"] is None and fin["energy"] is None
    # Energy meter only available during the print: the baseline is moved along
    st, _, _ = p.track_print(st, "printing", "b", _c(None, None), 10.0)
    st, _, ch = p.track_print(st, "printing", "b", _c(None, 2.0), 11.0)
    assert ch and st["active"]["start"]["energy"] == 2.0


def test_track_print_back_to_back_and_reset():
    track = p.track_print
    st, _, _ = track({"active": None, "last": None}, "printing", "a.gcode", _c(10), 1.0)
    # the next print started between two polls
    st, fin, ch = track(st, "printing", "b.gcode", _c(30), 2.0)
    assert ch and fin["switches"] == 20 and fin["result"] == "unknown"
    assert st["active"]["file"] == "b.gcode" and st["active"]["start"]["switches"] == 30
    # counters reset on the printer
    st, _, ch = track(st, "printing", "b.gcode", _c(3), 3.0)
    assert ch and st["active"]["start"]["switches"] == 3
    st, fin, _ = track(st, "cancelled", "b.gcode", _c(8), 4.0)
    assert fin["switches"] == 5 and fin["result"] == "cancelled"


def test_track_print_pending_start():
    track = p.track_print
    st = {"active": None, "last": {"file": "old", "switches": 3, "result": "complete", "started": 0, "ended": 1}}
    st, fin, _ = track(st, None, "a.gcode", _c(100), 10.0, pending=True)
    assert fin is None
    # printer still reports the old state: not finished
    st, fin, ch = track(st, "complete", "old", _c(100), 15.0)
    assert not ch and fin is None and st["active"]["pending"] and st["last"]["file"] == "old"
    assert p.print_progress(st, _c(100)) == {"switches": None, "energy": None, "energy_cost": None}
    st, _, ch = track(st, "printing", "a.gcode", _c(101), 20.0)
    assert ch and "pending" not in st["active"] and st["active"]["start"]["switches"] == 100
    st, fin, _ = track(st, "complete", "a.gcode", _c(109), 30.0)
    assert fin["switches"] == 9 and fin["file"] == "a.gcode"
    # a start that never gets going expires without a record
    st, _, _ = track(st, None, "b.gcode", _c(109), 40.0, pending=True)
    st, fin, ch = track(st, "standby", "", _c(109), 40.0 + p.START_GRACE_S + 1)
    assert ch and fin is None and st["active"] is None and st["last"]["file"] == "a.gcode"


def test_migrate_print_state_from_41():
    old = {"active": {"file": "a", "start_total": 50, "started": 1.0}, "last": None}
    new = p.migrate_print_state(old)
    assert new["active"] == {"file": "a", "started": 1.0, "start": {"switches": 50}}
    assert p.migrate_print_state(None) == {"active": None, "last": None, "history": [], "files": [], "timelapses": []}
    # last print from 4.1.x ends up in the history
    last = {"file": "x", "result": "complete"}
    assert p.migrate_print_state({"last": last})["history"] == [last]


def test_energy_kwh():
    assert p.energy_kwh("1500", "Wh") == 1.5
    assert p.energy_kwh("2.5", "kWh") == 2.5
    assert p.energy_kwh("unavailable", "kWh") is None
    assert p.energy_kwh("3", "J") is None



# ── Cost, filament, history, timelapses ────────────────────────────────────
def test_dynamic_price_is_summed_over_the_print():
    track = p.track_print
    st = {"active": None, "last": None, "history": []}
    st, _, _ = track(st, "printing", "a", _c(0, 10.0), 0.0, price=0.30)
    st, _, _ = track(st, "printing", "a", _c(0, 10.5), 1.0, price=0.30)   # 0.5 kWh x 0.30
    st, _, _ = track(st, "printing", "a", _c(0, 11.5), 2.0, price=0.10)   # 1.0 kWh x 0.10
    assert p.print_progress(st, _c(0, 11.5))["energy_cost"] == pytest.approx(0.25)
    # the last segment is still charged when finishing
    st, fin, _ = track(st, "complete", "a", _c(0, 12.0), 3.0, price=0.20)  # 0.5 x 0.20
    assert fin["energy"] == pytest.approx(2.0)
    assert fin["energy_cost"] == pytest.approx(0.35)
    # history/files are kept when advancing
    assert "history" in st


def test_track_print_records_stats():
    st, _, _ = p.track_print({"active": None, "last": None}, "printing", "a", _c(0), 0.0)
    st["active"].update(filaments=[{"type": "PLA", "weight": 10.0}], filament_total=4000.0, name="A")
    st, _, _ = p.track_print(st, "printing", "a", _c(0), 1.0, stats={"print_duration": 300.5, "filament_used": 1000.0})
    st, fin, _ = p.track_print(st, "cancelled", "a", _c(0), 2.0, stats={"print_duration": 999})
    # no running values are added after the print end
    assert fin["print_duration"] == 300.5 and fin["filament_used"] == 1000.0
    assert fin["filaments"] == [{"type": "PLA", "weight": 10.0}] and fin["name"] == "A"


def test_summarize_print_costs():
    rec = {
        "file": "a.gcode", "result": "complete", "started": 0.0, "ended": 3700.0,
        "print_duration": 3600.0, "energy": 0.5, "energy_cost": 0.151234,
        "filaments": [{"type": "PLA", "weight": 20.0}, {"type": "PETG-HF", "weight": 5.0}],
    }
    out = p.summarize_print(rec, {"PLA": 20.0, "PETG": 30.0})
    assert out["filament_g"] == 25.0
    assert out["filament_cost"] == pytest.approx(0.55)  # 20 g x 20 €/kg + 5 g x 30 €/kg
    assert out["energy_cost"] == 0.15 and out["total_cost"] == pytest.approx(0.70)
    assert out["duration"] == 3600.0 and out["materials"] == ["PETG-HF", "PLA"]
    assert "filaments" not in out
    # Missing price for one material: no filament cost instead of a wrong total
    assert "filament_cost" not in p.summarize_print(rec, {"PLA": 20.0})
    assert p.summarize_print(rec, {"OTHER": 10.0})["filament_cost"] == pytest.approx(0.25)


def test_summarize_cancelled_print_scales_weight():
    rec = {"result": "cancelled", "filament_used": 1000.0, "filament_total": 4000.0,
           "filaments": [{"type": "PLA", "weight": 40.0}]}
    out = p.summarize_print(rec, {"PLA": 25.0})
    assert out["filament_g"] == 10.0 and out["filament_cost"] == 0.25


def test_price_per_kwh_units():
    assert p.price_per_kwh("0.32", "EUR/kWh") == pytest.approx(0.32)
    assert p.price_per_kwh("32.5", "ct/kWh") == pytest.approx(0.325)
    assert p.price_per_kwh("320", "€/MWh") == pytest.approx(0.32)
    assert p.price_per_kwh("unknown", "EUR/kWh") is None


def test_pick_timelapses_u1_naming():
    entries = [
        {"path": "Nuss_2_PLA_1h17m_20261008195643.mp4", "modified": 20, "size": 17019965},
        {"path": "Nuss_2_PLA_1h17m_20261008195643_cover.jpg", "modified": 19},
        {"path": "Nuss_2_PLA_1h17m_20261008195643.jpg", "modified": 19},
        {"path": "Jeep_20261007181520.mp4", "modified": 10},
        {"path": "Jeep_20261007181520.jpg", "modified": 9},
        {"path": "fluidd/frame.mp4", "modified": 30},
        {"path": "fluidd/frame_0001.jpg", "modified": 30},
        {"path": ".hidden.mp4", "modified": 99},
    ]
    vids = p.pick_timelapses("camera", entries)
    assert [v["path"] for v in vids] == ["fluidd/frame.mp4", "Nuss_2_PLA_1h17m_20261008195643.mp4", "Jeep_20261007181520.mp4"]
    nuss = vids[1]
    assert nuss["name"] == "Nuss 2 PLA 1h17m" and nuss["recorded"] == "2026-10-08T19:56:43"
    assert nuss["poster"] == "Nuss_2_PLA_1h17m_20261008195643_cover.jpg"
    assert vids[2]["poster"] == "Jeep_20261007181520.jpg"
    assert vids[0]["poster"] == "fluidd/frame_0001.jpg" and vids[0]["recorded"] is None


def test_cost_gap_when_price_unknown():
    act = {"energy_prev": 1.0, "energy_cost": 0.0}
    act = p._accumulate_cost(act, 1.5, None)  # price briefly gone
    assert act["energy_prev"] == 1.0
    act = p._accumulate_cost(act, 2.0, 0.30)
    assert act["energy_prev"] == 2.0 and round(act["energy_cost"], 4) == 0.30
