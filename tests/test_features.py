"""Error texts, pause at layer, queue, statistics, maintenance, timelapse backup, layer view."""

from datetime import UTC
from pathlib import Path

import pytest

from custom_components.snapmaker_u1_card.errors import (
    collect_errors,
    describe_error,
    error_text,
)
from custom_components.snapmaker_u1_card.jobs import (
    JobQueue,
    add_layer_pauses,
    is_pause_copy,
    original_file,
    pause_file_name,
)
from custom_components.snapmaker_u1_card.stats import (
    Maintenance,
    build_stats,
    job_grams,
)
from custom_components.snapmaker_u1_card.upload import safe_folder, safe_name


# ── Errors ──────────────────────────────────────────────────────────────────
def test_known_error_per_head() -> None:
    info = describe_error({"id": 523, "index": 2, "code": 0, "level": 2, "message": "e2_filament runout"})
    assert info["text"]["de"] == "Filament leer (Kopf 3)"
    assert info["text"]["en"] == "Filament ran out (head 3)"
    assert error_text(info, "de").startswith("Filament leer (Kopf 3). Neue Spule")


def test_unknown_error_keeps_raw_message() -> None:
    info = describe_error({"id": 529, "index": 0, "code": 99, "message": "Unknown command: FOO"})
    assert not info["known"]
    assert error_text(info, "en") == "G-code: Unknown command: FOO"


def test_collect_dedupes_and_skips_placeholder() -> None:
    status = {
        "exception_manager": {"exceptions": [
            {"id": 532, "index": 0, "code": 2, "level": 2, "message": "detected noodle"},
            {"id": 532, "index": 0, "code": 2, "level": 2, "message": "detected noodle"},
        ]},
        "print_stats": {"state": "error", "exception": {"id": 522, "index": 0, "code": 0,
                                                         "message": "class CodedException", "level": 3}},
    }
    errs = collect_errors(status)
    assert [e["text"]["de"] for e in errs] == ["Spaghetti erkannt"]
    # Print not in error state: ignore an old print_stats.exception
    status2 = {"print_stats": {"state": "standby", "exception": {"id": 526, "index": 0, "code": 2, "message": "x"}}}
    assert collect_errors(status2) == []


# ── Pause at layer ─────────────────────────────────────────────────────────
ORCA = """; HEADER_BLOCK_START
; total layer number: 4
; HEADER_BLOCK_END
G28
;LAYER_CHANGE
;Z:0.2
SET_PRINT_STATS_INFO CURRENT_LAYER=1
G1 X1 E1
;LAYER_CHANGE
;Z:0.4
SET_PRINT_STATS_INFO CURRENT_LAYER=2
G1 X2 E1
;LAYER_CHANGE
;Z:0.6
SET_PRINT_STATS_INFO CURRENT_LAYER=3
G1 X3 E1
;LAYER_CHANGE
;Z:0.8
SET_PRINT_STATS_INFO CURRENT_LAYER=4
G1 X4 E1
; layer_change_gcode = SET_PRINT_STATS_INFO CURRENT_LAYER={layer_num + 1}
"""


def _lines_before_layer(text: str, layer: int) -> list[str]:
    lines = text.splitlines()
    idx = [i for i, ln in enumerate(lines) if ln.startswith(";LAYER_CHANGE")][layer - 1]
    return lines[idx - 2: idx]


def test_pause_inserted_before_layer_change(tmp_path: Path) -> None:
    src, dst = tmp_path / "a.gcode", tmp_path / "b.gcode"
    src.write_text(ORCA)
    res = add_layer_pauses(src, dst, [3, 2])
    assert res == {"layers": [2, 3], "total": 4, "missing": []}
    out = dst.read_text()
    assert out.count("\nPAUSE\n") == 2
    assert _lines_before_layer(out, 2) == ["; snapmaker_u1_card: Pause vor Schicht 2", "PAUSE"]
    assert _lines_before_layer(out, 3)[-1] == "PAUSE"
    # otherwise unchanged
    assert out.replace("; snapmaker_u1_card: Pause vor Schicht 2\nPAUSE\n", "") \
        .replace("; snapmaker_u1_card: Pause vor Schicht 3\nPAUSE\n", "") \
        .split("\n", 1)[1] == ORCA


def test_pause_missing_layer_and_no_markers(tmp_path: Path) -> None:
    src, dst = tmp_path / "a.gcode", tmp_path / "b.gcode"
    src.write_text(ORCA)
    assert add_layer_pauses(src, dst, [9])["missing"] == [9]
    src.write_text("G28\nG1 X1\n")
    with pytest.raises(ValueError):
        add_layer_pauses(src, dst, [2])


def test_pause_cura_markers(tmp_path: Path) -> None:
    src, dst = tmp_path / "a.gcode", tmp_path / "b.gcode"
    src.write_text(";LAYER:0\nG1\n;LAYER:1\nG1\n;LAYER:2\nG1\n")
    assert add_layer_pauses(src, dst, [2])["layers"] == [2]
    assert dst.read_text().split(";LAYER:1")[0].endswith("PAUSE\n")


def test_pause_names() -> None:
    name = pause_file_name("sub/Box.gcode", [12, 3, 12])
    assert name == "sub/Box.u1pause-3-12.gcode"
    assert is_pause_copy(name) and not is_pause_copy("sub/Box.gcode")
    assert original_file(name) == "sub/Box.gcode"


# ── Queue ──────────────────────────────────────────────────────────────────
def test_queue_order() -> None:
    q = JobQueue(None)
    a = q.add({"file": "a.gcode", "mapping": {0: 2}})
    q.add({"file": "b.gcode"})
    c = q.add({"file": "c.gcode"})
    assert a["mapping"] == {"0": 2}
    assert q.move(c["id"], 0)
    assert [j["file"] for j in q.jobs] == ["c.gcode", "a.gcode", "b.gcode"]
    assert q.get(None)["file"] == "c.gcode"
    assert q.remove(a["id"]) and not q.remove("nope")
    restored = JobQueue(q.as_stored() + [{"bad": 1}])
    assert [j["file"] for j in restored.jobs] == ["c.gcode", "b.gcode"]


# ── Statistics ─────────────────────────────────────────────────────────────
def test_stats_months_and_totals() -> None:
    now = 1_760_000_000.0  # 2025-10-09
    jobs = [
        {"status": "completed", "start_time": now - 86400, "print_duration": 7200, "filename": "a.gcode",
         "metadata": {"filament_weight_total": 20.0}},
        {"status": "cancelled", "start_time": now - 86400 * 20, "print_duration": 1800, "filename": "b.gcode",
         "filament_used": 500, "metadata": {"filament_weight_total": 40.0, "filament_total": 2000}},
        {"status": "completed", "start_time": now - 86400 * 400, "print_duration": 3600, "filename": "a.gcode",
         "metadata": {}},
        {"status": "in_progress", "start_time": now, "print_duration": 10},
    ]
    history = [{"ended": now - 86000, "energy": 0.5, "total_cost": 0.3}]
    st = build_stats(jobs, history, now, UTC)
    assert len(st["months"]) == 12 and st["months"][-1]["month"] == "2025-10"
    oct_ = st["months"][-1]
    assert (oct_["prints"], oct_["hours"], oct_["filament_g"], oct_["energy"], oct_["cost"]) == (1, 2.0, 20.0, 0.5, 0.3)
    assert st["months"][-2]["failed"] == 1 and st["months"][-2]["filament_g"] == 10.0
    t = st["totals"]
    assert (t["prints"], t["completed"], t["failed"], t["success_rate"]) == (3, 2, 1, 66.7)
    assert t["hours"] == 3.5 and t["filament_kg"] == 0.03
    assert st["top_files"][0] == {"file": "a.gcode", "count": 2}
    assert job_grams({"status": "error", "metadata": {"filament_weight_total": 5}}) is None


def test_maintenance_baseline_and_due() -> None:
    m = Maintenance(None)
    assert m.baseline(100.0, 1.0)
    assert not m.baseline(120.0, 2.0)  # only the first time
    items = {i["key"]: i for i in m.status(140.0, {"belts": 0}, {"belts": 0})}
    assert "belts" not in items and "filter" not in items  # 0 = off (hours and months)
    assert items["plate"]["due"] and items["plate"]["used_h"] == 40.0
    assert not items["nozzle"]["due"] and items["nozzle"]["remaining_h"] == 60.0
    m.mark_done("plate", 140.0, 3.0)
    assert not {i["key"]: i for i in m.status(141.0, {})}["plate"]["due"]
    with pytest.raises(KeyError):
        m.mark_done("nope", 1.0, 1.0)


def test_maintenance_months() -> None:
    """Calendar intervals from Snapmaker's U1 guide; hours or months, whichever comes first."""
    day = 86400.0
    m = Maintenance(None)
    m.baseline(100.0, 0.0)
    items = {i["key"]: i for i in m.status(101.0, {}, None, 20 * day)}
    # month-only items (default 0 h) are listed with their month interval
    assert items["lead_screws"]["interval_m"] == 3 and "interval_h" not in items["lead_screws"]
    assert not items["rails"]["due"] and items["rails"]["remaining_d"] == pytest.approx(10.4, abs=0.1)
    items = {i["key"]: i for i in m.status(101.0, {}, None, 35 * day)}
    assert items["rails"]["due"] and items["carbon_rods"]["due"]  # monthly
    assert not items["lead_screws"]["due"] and not items["pogo"]["due"]
    assert items["rails"]["progress"] > 100
    # hours still count: plate (30 h) due by hours, months off for it
    items = {i["key"]: i for i in m.status(131.0, {}, None, 1 * day)}
    assert items["plate"]["due"] and "interval_m" not in items["plate"]
    # own month values from the options
    items = {i["key"]: i for i in m.status(101.0, {}, {"rails": 2}, 35 * day)}
    assert not items["rails"]["due"]
    # the more advanced measure decides what is shown: 16 of 30 days beats 1 of 300 h
    rails = {i["key"]: i for i in m.status(101.0, {}, None, 16 * day)}["rails"]
    assert rails["by"] == "months" and rails["progress"] == 53 and rails["remaining_h"] == 299.0
    rails = {i["key"]: i for i in m.status(390.0, {}, None, 1 * day)}["rails"]
    assert rails["by"] == "hours"
    assert {i["key"]: i for i in m.status(101.0, {}, None, 1 * day)}["plate"]["by"] == "hours"


def test_maintenance_filter_only_with_top_cover() -> None:
    m = Maintenance(None)
    m.baseline(0.0, 0.0)
    assert "filter" not in {i["key"] for i in m.status(10.0, {"filter": 150}, None, 1.0)}
    assert "filter" in {i["key"] for i in m.status(10.0, {"filter": 150}, None, 1.0, has_filter=True)}


# ── Upload ─────────────────────────────────────────────────────────────────
def test_upload_names() -> None:
    assert safe_name("../../etc/Box v2.gcode") == "Box v2.gcode"
    assert safe_name("C:\\x\\a.3MF") == "a.3MF"
    assert safe_name(".hidden.gcode") == "hidden.gcode"
    assert safe_name("evil.sh") is None
    assert safe_folder("../a/./b//c") == "a/b/c"


# ── Layer view ─────────────────────────────────────────────────────────────
LAYERED = """; HEADER
G28
G90
M83
G1 X0 Y0 E5 ; Spuelstrich vor der ersten Schicht (ignoriert)
;LAYER_CHANGE
;Z:0.2
T0
G1 Z0.2
G1 X10 Y10 F3000
G1 X20 Y10 E1
G1 X20.1 Y10 E0.01
G1 X20 Y20 E1
G1 X50 Y50
G1 X60 Y50 E1
T1
G1 X60 Y60 E1
;LAYER_CHANGE
;Z:0.4
G1 X10 Y10
G91
G1 X5 Y0 E0.5
G90
;LAYER_CHANGE
;Z:0.6
G1 X0 Y0
"""


def test_parse_layers(tmp_path: Path) -> None:
    from custom_components.snapmaker_u1_card.layers import layer_payload, parse_layers

    src, out = tmp_path / "a.gcode", tmp_path / "l.jsonl"
    src.write_text(LAYERED)
    meta = parse_layers(src, out)
    assert meta["total"] == 3 and meta["tools"] == [0, 1]
    assert meta["bbox"] == [10.0, 10.0, 60.0, 60.0]
    one = layer_payload(meta, out, 1)
    assert one["z"] == 0.2
    segs = one["segs"]
    # Travel splits the polylines, so does a tool change; too short steps are dropped,
    # the end point is kept
    assert [s[0] for s in segs] == [0, 0, 1]
    assert segs[0][1] == [10.0, 10.0, 20.0, 10.0, 20.0, 20.0]
    assert segs[1][1] == [50.0, 50.0, 60.0, 50.0]
    assert segs[2][1] == [60.0, 50.0, 60.0, 60.0]
    # file positions ascending and within the layer
    starts = [s[2] for s in segs]
    assert starts == sorted(starts) and one["start"] <= starts[0] < one["end"]
    assert LAYERED.encode()[starts[0]:].startswith(b"G1 X20 Y10 E1")
    # relative coordinates (G91)
    assert layer_payload(meta, out, 2)["segs"][0][1] == [10.0, 10.0, 15.0, 10.0]
    # An empty layer stays, unknown layers do not exist
    assert layer_payload(meta, out, 3)["segs"] == []
    assert layer_payload(meta, out, 4) is None


def test_view_box_ignores_purge_lines_and_uses_objects(tmp_path: Path) -> None:
    """Purge moves at the bed edge must not stretch the viewport to the whole bed."""
    from custom_components.snapmaker_u1_card.layers import parse_layers

    lines = ["EXCLUDE_OBJECT_DEFINE NAME=Teil CENTER=130,130 POLYGON=[[120,120],[140,120],[140,140],[120,140]]",
             "G90", "M83"]
    for n in range(1, 6):
        lines += [";LAYER_CHANGE", f"G1 Z{n * 0.2:.1f}", "T0"]
        # purge move at the front edge, as at a tool change
        lines += ["G1 X5 Y2", "G1 X260 Y2 E3"]
        # part: many short moves in the range 120..140
        for i in range(60):
            y = 121 + (i % 19)
            lines += [f"G1 X121 Y{y}", f"G1 X139 Y{y} E0.5"]
    src, out = tmp_path / "a.gcode", tmp_path / "l.jsonl"
    src.write_text("\n".join(lines) + "\n")
    meta = parse_layers(src, out)
    x0, y0, x1, y1 = meta["bbox"]
    assert 115 <= x0 <= 121 and 115 <= y0 <= 121, meta["bbox"]
    assert 139 <= x1 <= 145 and 139 <= y1 <= 145, meta["bbox"]
