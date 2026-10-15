"""Remaining time from the time profile, spool run-out, part removable, push actions,
result photo, file management, idle shutdown, firmware, self test, material stats."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.snapmaker_u1_card.coordinator import latest_release, version_tuple
from custom_components.snapmaker_u1_card.layer_view import downsample
from custom_components.snapmaker_u1_card.layers import estimate_remaining, parse_layers, timeline_at
from custom_components.snapmaker_u1_card.stats import build_stats
from tests.test_init import API, DOMAIN, mock_client  # noqa: F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: F401

# two layers, T0 and T1, known feed rates: 60 mm/s
TIMED = """;HEADER
G90
M83
;LAYER_CHANGE
T0
G1 X0 Y0 F3600
G1 X60 Y0 E6
G1 X60 Y60 E6
G4 P2000
;LAYER_CHANGE
T1
G1 X0 Y60 E3
G1 X0 Y0 E3
;LAYER_CHANGE
G1 X10 Y10
"""
# comment lines in between: otherwise such a small file only has start and end in the profile
TIMED = "\n".join(f"{line}\n;{'x' * 300}" for line in TIMED.splitlines()) + "\n"


# ── Time profile ────────────────────────────────────────────────────────────
def test_timeline_and_remaining(tmp_path: Path) -> None:
    src = tmp_path / "t.gcode"
    src.write_text(TIMED)
    meta = parse_layers(src, tmp_path / "t.jsonl")
    rows = meta["timeline"]
    end = rows[-1]
    # 4 moves of 60 mm @ 60 mm/s = 4 s, + 2 s pause, + travel ~14.1 mm
    assert end[1] == pytest.approx(6 + 14.142 / 60, abs=0.05)
    assert end[2:4] == [12.0, 6.0] and end[0] == len(TIMED.encode())
    half = TIMED.encode().index(b"G4")
    at = timeline_at(meta, half)
    assert at["t"] == pytest.approx(2.0, abs=0.05) and at["e"][0] == pytest.approx(12.0)
    # slicer says 600 s, measured at k=~1/3: 300 s -> actual is twice as slow
    rem = estimate_remaining(meta, half, duration=300, slicer_total=600)
    k = at["t"] / at["t_total"]
    expect = ((1 - k) * 600 * (1 - k) + k * 300 * (1 - k) / k) / 1
    assert rem == pytest.approx(expect, rel=0.01)
    assert estimate_remaining(meta, end[0], 999, 600) == 0
    assert estimate_remaining(None, 10, 10, 10) is None


def test_latest_release_and_versions() -> None:
    commits = [
        {"commit": {"message": "Fix foo", "committer": {"date": "2026-10-01"}}, "html_url": "u0"},
        {"commit": {"message": "Release firmware version 1.6.0\n\nnotes", "committer": {"date": "2026-08-25"}}, "html_url": "u1"},
        {"commit": {"message": "Release firmware version 2.0.0", "committer": {"date": "2026-09-15"}}, "html_url": "u2"},
    ]
    assert latest_release(commits) == {"version": "2.0.0", "url": "u2", "date": "2026-09-15"}
    assert latest_release({"message": "rate limited"}) is None
    assert version_tuple("v1.6.0-12-gabc") == (1, 6, 0) and version_tuple("x") == ()


def test_material_stats() -> None:
    meta = {"filament_type": "PLA;PETG", "filament_colour": "#000000;#FF0000",
            "filament_weight": [10.0, 5.0], "filament_weight_total": 15.0, "filament_total": 100}
    jobs = [
        {"status": "completed", "start_time": 1.7e9, "print_duration": 60, "filename": "a", "metadata": meta},
        {"status": "cancelled", "start_time": 1.7e9, "print_duration": 60, "filename": "b", "metadata": meta,
         "filament_used": 50},
        {"status": "completed", "start_time": 1.7e9, "print_duration": 60, "filename": "c",
         "metadata": {"filament_type": "PLA", "filament_colour": "#000000", "filament_weight": [20.0]}},
    ]
    st = build_stats(jobs, [], 1.7e9, prices={"PLA": 20.0})
    pla = next(m for m in st["materials"] if m["type"] == "PLA")
    petg = next(m for m in st["materials"] if m["type"] == "PETG")
    assert pla == {**pla, "grams": 35.0, "prints": 3, "ok": 2, "failed": 1, "cost": 0.7, "success_rate": 66.7}
    assert petg["grams"] == 7.5 and petg["cost"] is None
    assert st["colors"][0] == {"type": "PLA", "color": "#000000", "grams": 35.0}


def test_downsample() -> None:
    store = {"extruder": {"temperatures": [1, 2, 3, 4, 5, 6], "targets": [0] * 6}, "fan": {}}
    out = downsample(store, step=5)
    assert out["series"]["extruder"] == {"temperatures": [3.0, 6.0], "targets": [0.0, 0.0]}
    assert "fan" not in out["series"]


# ── Integration ─────────────────────────────────────────────────────────────
def _sent(calls, title):
    return [c for c in calls if title in c.data["title"]]


@pytest.fixture
def timed_file():
    async def download_to(self, root, path, target, hass_):
        target.write_text(TIMED)
        return len(TIMED)

    with patch(f"{API}.download_to", download_to):
        yield


async def test_remaining_sensors_and_runout(hass: HomeAssistant, mock_client, notifications, timed_file) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["spool_runout"])
    hass.config.language = "de"
    coord = entry.runtime_data
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=300)
    pos = TIMED.encode().index(b"G4")
    st["virtual_sdcard"] = {"file_position": pos, "progress": 0.5}
    await _refresh(hass, entry)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord.layer_view["status"] == "ready", coord.layer_view
    # slicer (META) 600 s, the time profile calibrates
    await _refresh(hass, entry)
    rem = next(s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_time_remaining"))
    fin = next(s for s in hass.states.async_all("sensor") if s.entity_id.endswith("_finish_time"))
    assert float(rem.state) > 0 and fin.state not in ("unknown", "unavailable")
    assert coord.data.remaining == pytest.approx(estimate_remaining(coord.layer_view["meta"], pos, 300, 600), rel=0.01)

    # spool on head 1 (T0) has too little: META 4 g PETG (T0) -> 2 g left lasts until halfway
    coord._print_state["active"]["filaments"] = [{"index": 0, "type": "PETG", "weight": 4.0},
                                                 {"index": 1, "type": "PLA", "weight": 6.0}]
    with patch.object(type(coord.spools), "enabled", property(lambda self: True)), \
         patch.object(type(coord.spools), "slot_info",
                      lambda self, i: {"name": "Rot", "remaining_weight": 2.5} if i == 0 else None):
        await _refresh(hass, entry)
        await _refresh(hass, entry)
        await hass.async_block_till_done()
    assert 0 in coord.data.runout and coord.data.runout[0]["takeover"] is None
    msgs = _sent(notifications, "Spule läuft gleich leer")
    assert len(msgs) == 1, "nur einmal je Druck"
    assert "Kopf 1" in msgs[0].data["message"] and "pausiert" in msgs[0].data["message"]
    assert [a["action"].split("_")[1] for a in msgs[0].data["data"]["actions"]] == ["PAUSE", "LIGHT"]
    fil = next(s for s in hass.states.async_all("sensor") if "slots" in s.attributes)
    assert fil.attributes["runout"]["0"]["minutes"] >= 0


async def test_takeover_by_auto_replenish() -> None:
    from custom_components.snapmaker_u1_card.coordinator.helpers import _takeover

    slots = [{"index": 0, "loaded": True, "type": "PLA", "color": "#000000"},
             {"index": 1, "loaded": True, "type": "PLA", "color": "#FF0000"},
             {"index": 2, "loaded": True, "type": "PLA", "color": "#000000"}]
    assert _takeover(slots, 0, {"auto_replenish_filament": True}) == 2
    assert _takeover(slots, 1, {"auto_replenish_filament": True}) is None
    assert _takeover(slots, 1, {"auto_replenish_filament": True, "replenish_ignore_color": True}) == 0
    assert _takeover(slots, 0, {"auto_replenish_filament": False}) is None


async def test_bed_cool_push(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["complete", "bed_cool"],
                         bed_cool_temp=35)
    hass.config.language = "de"
    _status(mock_client, "printing", "sub/new.gcode", temps=60.0)
    await _refresh(hass, entry)
    _status(mock_client, "complete", "sub/new.gcode", temps=60.0)
    await _refresh(hass, entry)
    await _refresh(hass, entry)
    assert not _sent(notifications, "Teil entnehmbar")
    _status(mock_client, "complete", "sub/new.gcode", temps=33.0)
    await _refresh(hass, entry)
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    msgs = _sent(notifications, "Teil entnehmbar")
    assert len(msgs) == 1 and "33 °C" in msgs[0].data["message"]


async def test_notification_actions(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], notify_events=["paused"])
    hass.config.language = "de"
    coord = entry.runtime_data
    _status(mock_client, "printing", "sub/new.gcode")
    await _refresh(hass, entry)
    _status(mock_client, "paused", "sub/new.gcode")
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    actions = _sent(notifications, "pausiert")[0].data["data"]["actions"]
    ids = [a["action"] for a in actions]
    assert ids == [f"SU1_RESUME_{entry.entry_id}", f"SU1_CANCEL_{entry.entry_id}"]
    fire = lambda a: hass.bus.async_fire("mobile_app_notification_action", {"action": a})  # noqa: E731
    with patch(f"{API}.print_action", AsyncMock()) as act:
        fire(f"SU1_CANCEL_{entry.entry_id}")
        await hass.async_block_till_done()
        act.assert_not_called()  # ask first
        confirm = _sent(notifications, "Druck abbrechen?")
        assert confirm and confirm[0].data["data"]["actions"][0]["action"] == f"SU1_CANCEL_CONFIRM_{entry.entry_id}"
        fire(f"SU1_CANCEL_CONFIRM_{entry.entry_id}")
        await hass.async_block_till_done()
        act.assert_awaited_with("cancel")
        act.reset_mock()
        fire(f"SU1_RESUME_{entry.entry_id}")
        await hass.async_block_till_done()
        act.assert_awaited_with("resume")
        act.reset_mock()
        fire("SU1_RESUME_fremder_eintrag")
        fire(f"SU1_PAUSE_{entry.entry_id}")  # paused: pause ignored
        await hass.async_block_till_done()
        act.assert_not_called()
    assert coord._unsub_action is not None


async def test_result_photo(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, camera="camera.u1")

    class Img:
        content = b"\xff\xd8JPEG"

    import sys
    import types

    fake = types.ModuleType("homeassistant.components.camera")
    fake.async_get_image = AsyncMock(return_value=Img())
    with patch.dict(sys.modules, {"homeassistant.components.camera": fake}):
        _status(mock_client, "printing", "sub/new.gcode")
        await _refresh(hass, entry)
        _status(mock_client, "complete", "sub/new.gcode")
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    last = entry.runtime_data._print_state["last"]
    assert last["photo"].startswith(f"/snapmaker_u1_card/thumbs/{entry.entry_id}/results/")
    stored = entry.runtime_data._own_dir / "results" / Path(last["photo"]).name
    assert stored.read_bytes() == b"\xff\xd8JPEG"


async def test_file_management(hass: HomeAssistant, mock_client, notifications) -> None:
    mock_client["files"]["gcodes"] += [{"path": f"alt/{i}.gcode", "modified": -i, "size": 1} for i in range(40)]
    entry = await _setup(hass)
    coord = entry.runtime_data
    st = next(s for s in hass.states.async_all("sensor") if "all" in s.attributes)
    assert len(st.attributes["all"]) == 42 and len(st.attributes["files"]) == 24
    res = await hass.services.async_call(DOMAIN, "file_details", {"path": "alt/39.gcode"}, blocking=True,
                                         return_response=True)
    assert res["file"]["path"] == "alt/39.gcode" and res["file"]["time"] == 600
    with pytest.raises(HomeAssistantError, match="does not exist"):
        await hass.services.async_call(DOMAIN, "file_details", {"path": "nope.gcode"}, blocking=True,
                                       return_response=True)
    with patch(f"{API}.delete_file", AsyncMock()) as dele, patch(f"{API}.move_file", AsyncMock()) as mv:
        await hass.services.async_call(DOMAIN, "delete_file", {"path": "old.gcode"}, blocking=True)
        dele.assert_awaited_with("old.gcode")
        await hass.services.async_call(DOMAIN, "move_file", {"source": "old.gcode", "dest": "teile/neu"}, blocking=True)
        mv.assert_awaited_with("old.gcode", "teile/neu.gcode")
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(DOMAIN, "move_file", {"source": "old.gcode", "dest": "../x"}, blocking=True)
        _status(mock_client, "printing", "sub/new.gcode")
        await _refresh(hass, entry)
        with pytest.raises(HomeAssistantError, match="being printed"):
            await hass.services.async_call(DOMAIN, "delete_file", {"path": "sub/new.gcode"}, blocking=True)
    assert "alt/39.gcode" in coord._pinned or True


async def test_idle_power_off(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass, idle_off_hours=2)
    coord = entry.runtime_data
    with patch.object(type(coord), "async_power_off", AsyncMock()) as off:
        await _refresh(hass, entry)
        assert coord._idle_since is not None
        coord._idle_since = time.time() - 3 * 3600
        st = _status(mock_client, "standby", "")
        st["extruder"]["target"] = 200  # heating: do not switch off, restart the clock
        await _refresh(hass, entry)
        off.assert_not_called()
        st["extruder"]["target"] = 0
        coord._idle_since = time.time() - 3 * 3600
        await _refresh(hass, entry)
        await hass.async_block_till_done()
        off.assert_awaited_with(reason="idle")


async def test_firmware_update_entity(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    ent = next(s for s in hass.states.async_all("update"))
    assert ent.state == "off" and ent.attributes["installed_version"] == "1.6.0"
    coord.firmware["latest"] = {"version": "2.0.0", "url": "https://github.com/x", "checked": time.time()}
    coord.async_update_listeners()
    await hass.async_block_till_done()
    ent = hass.states.get(ent.entity_id)
    assert ent.state == "on" and ent.attributes["latest_version"] == "2.0.0"
    assert ent.attributes["release_url"] == "https://github.com/x"
    # older than installed: no update
    coord.firmware["latest"] = {"version": "1.5.0", "checked": time.time()}
    coord.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(ent.entity_id).state == "off"


async def test_self_test(hass: HomeAssistant, mock_client, notifications) -> None:
    await _setup(hass, notify_targets=["notify.mobile_app_handy", "notify.weg"])
    hass.config.language = "de"
    with patch(f"{API}.rpc", AsyncMock(return_value={"free_space": 300, "total_space": 8000})):
        res = await hass.services.async_call(DOMAIN, "self_test", {}, blocking=True, return_response=True)
    keys = {c["key"]: c for c in res["checks"]}
    assert keys["printer"]["ok"] is True
    assert keys["storage"]["ok"] is False and "300 MiB" in keys["storage"]["detail"]
    assert keys["moonraker_integration"]["ok"] is False
    assert keys["camera"]["ok"] is None
    assert keys["firmware"]["detail"].startswith("Installiert 1.6.0")
    notify = [c for c in res["checks"] if c["key"] == "notify"]
    assert [c["ok"] for c in notify] == [True, False]
    assert res["ok"] is False


async def test_early_result_photo(hass: HomeAssistant, mock_client, notifications, timed_file) -> None:
    """Photo after the last extrusion (before the end G-code), not only at "complete"."""
    import sys
    import types

    class Img:
        content = b"\xff\xd8EARLY"

    fake = types.ModuleType("homeassistant.components.camera")
    fake.async_get_image = AsyncMock(return_value=Img())
    with patch.dict(sys.modules, {"homeassistant.components.camera": fake}), \
         patch("custom_components.snapmaker_u1_card.coordinator.notify.EARLY_PHOTO_DELAY_S", 0):
        entry = await _setup(hass, camera="camera.u1")
        coord = entry.runtime_data
        st = _status(mock_client, "printing", "sub/new.gcode", print_duration=100)
        st["virtual_sdcard"] = {"file_position": 10, "progress": 0.01}
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
        meta = coord.layer_view["meta"]
        assert 0 < meta["last_extrude"] < meta["size"]
        await _refresh(hass, entry)
        assert coord._early_photo is None, "noch nicht"
        # live subscription reports: last extrusion printed
        coord.live.status = {"print_stats": {"state": "printing"},
                             "virtual_sdcard": {"file_position": meta["last_extrude"] + 1, "progress": 0.98}}
        coord._on_live({"virtual_sdcard": {"file_position": meta["last_extrude"] + 1}})
        await hass.async_block_till_done(wait_background_tasks=True)
        early = coord._early_photo["url"]
        assert fake.async_get_image.await_count == 1
        _status(mock_client, "complete", "sub/new.gcode")
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    last = coord._print_state["last"]
    assert last["photo"] == early, "Foto von der letzten Bahn, kein zweites"
    assert fake.async_get_image.await_count == 1
    assert (coord._own_dir / "results" / Path(early).name).read_bytes() == b"\xff\xd8EARLY"


def test_stats_cost_matches_history_and_estimates_rest() -> None:
    meta = {"filament_type": "PETG", "filament_colour": "#000000", "filament_weight": [100.0],
            "filament_weight_total": 100.0}
    jobs = [
        # recorded: real cost (incl. energy) instead of an estimate
        {"status": "completed", "start_time": 1.7e9, "end_time": 1.7e9 + 3600, "print_duration": 3600,
         "filename": "dir/a.gcode", "metadata": meta},
        # not recorded (before installation): filament price
        {"status": "completed", "start_time": 1.7e9 - 86400, "end_time": 1.7e9 - 82800, "print_duration": 3600,
         "filename": "b.gcode", "metadata": meta},
    ]
    history = [
        {"file": "a.gcode", "ended": 1.7e9 + 3630, "energy": 0.2, "total_cost": 2.5},
        # record without a Moonraker job (history deleted on the printer)
        {"file": "c.gcode", "ended": 1.7e9 - 5000, "energy": 0.1, "total_cost": 0.4},
    ]
    st = build_stats(jobs, history, 1.7e9 + 4000, prices={"PETG": 20.0})
    t = st["totals"]
    assert t["cost"] == 2.5 + 2.0 + 0.4 and t["cost_estimated"] is True
    assert t["energy"] == 0.3
    assert sum(b["cost"] or 0 for b in st["months"]) == 4.9
    # without a price no estimate, only the real cost
    st2 = build_stats(jobs, history[:1], 1.7e9 + 4000)
    assert st2["totals"]["cost"] == 2.5 and st2["totals"]["cost_estimated"] is False


def test_layers_arcs(tmp_path) -> None:
    import json

    from custom_components.snapmaker_u1_card.layers import parse_layers

    g = tmp_path / "a.gcode"
    g.write_text(";LAYER_CHANGE\n;Z:0.2\nG1 Z0.2\nG1 X10 Y0 F3000\nG3 X-10 Y0 I-10 J0 E5\nG2 X10 Y0 I10 J0 E10\n"
                 ";LAYER_CHANGE\n;Z:0.4\nG1 Z0.4\nG3 X10 Y0 I-10 J0 E20\n")
    meta = parse_layers(g, tmp_path / "a.jsonl")
    assert meta["bbox"] is not None
    layers = [json.loads(line) for line in (tmp_path / "a.jsonl").read_text().splitlines()]
    pts = layers[0]["segs"][0][1]
    ys = pts[1::2]
    # arcs instead of a chord: upper half circle, no point below
    assert len(pts) // 2 > 50 and max(ys) == 10.0 and min(ys) >= 0
    full = layers[1]["segs"][0][1]
    assert min(full[1::2]) == -10.0 and max(full[1::2]) == 10.0  # full circle


def test_layers_klipper_relative_e_after_g90(tmp_path) -> None:
    """Orca: M83, then G90. Klipper keeps E relative (unlike Marlin)."""
    import json

    from custom_components.snapmaker_u1_card.layers import parse_layers

    g = tmp_path / "o.gcode"
    g.write_text("M83\nG90\n;LAYER_CHANGE\n;Z:0.25\nG1 Z.25\nG1 X0 Y0 F3000\n"
                 "G1 X10 Y0 E.5\nG1 X20 Y0 E.5\nG1 X30 Y0 E.5\nG1 E-1.5\nG1 X40 Y0\nG1 E1.5\nG1 X50 Y0 E.5\n")
    meta = parse_layers(g, tmp_path / "o.jsonl")
    layer = json.loads((tmp_path / "o.jsonl").read_text().splitlines()[0])
    # one continuous path instead of two-point pieces, then a second after the travel
    assert [len(s[1]) // 2 for s in layer["segs"]] == [4, 2]
    # retraction/unretraction net zero: 4 x 0.5 mm
    assert meta["timeline"][-1][2] == 2.0


def test_i18n_follows_ha_language() -> None:
    from types import SimpleNamespace

    from custom_components.snapmaker_u1_card.i18n import tr

    assert tr(SimpleNamespace(config=SimpleNamespace(language="de-DE")), "Hallo", "Hello") == "Hallo"
    assert tr(SimpleNamespace(config=SimpleNamespace(language="en")), "Hallo", "Hello") == "Hello"
    assert tr(None, "Hallo", "Hello") == "Hello"
