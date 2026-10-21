"""1.4.0: remaining time from slicer marks, learning, progress notification budget, result photo timing."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402

from custom_components.snapmaker_u1_card.coordinator import progress as prog  # noqa: E402
from custom_components.snapmaker_u1_card.layers import (  # noqa: E402
    PRIOR_WEIGHT_S,
    estimate_remaining,
    parse_layers,
    slicer_left,
)
from tests.test_init import API, mock_client  # noqa: E402,F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: E402,F401

# Start sequence as layer 0 (SET_PRINT_STATS_INFO), slicer marks M73 R in minutes
GCODE = "\n".join([
    "M73 P0 R10",
    "SET_PRINT_STATS_INFO TOTAL_LAYER=2 CURRENT_LAYER=0",
    "G28", "G1 X10 Y10 Z0.2 F6000", "G1 X60 E5 F1200",
    "M73 P0 R9",
    "SET_PRINT_STATS_INFO TOTAL_LAYER=2 CURRENT_LAYER=1",
    "M83", "G1 X100 Y100 E2 F3000",
    "M73 P50 R5",
    "SET_PRINT_STATS_INFO TOTAL_LAYER=2 CURRENT_LAYER=2",
    "G1 X120 Y100 E2 F3000",
    "M73 P100 R0",
    "PRINT_END",
]) + "\n"


def _meta(tmp_path: Path) -> dict:
    src = tmp_path / "a.gcode"
    src.write_text(GCODE)
    return parse_layers(src, tmp_path / "out.jsonl")


def test_slicer_marks_and_begin(tmp_path) -> None:
    meta = _meta(tmp_path)
    data = GCODE.encode()
    assert meta["begin"] == data.index(b"SET_PRINT_STATS_INFO TOTAL_LAYER=2 CURRENT_LAYER=1")
    assert [v for _, v in meta["slicer"]] == [600, 540, 300, 0]
    mid = (data.index(b"M73 P0 R9") + data.index(b"M73 P50 R5")) // 2
    assert 300 < slicer_left(meta, mid) < 540
    assert slicer_left(meta, 0) == 600 and slicer_left(meta, len(data)) == 0


def test_estimate_uses_slicer_and_measured_speed(tmp_path) -> None:
    meta = _meta(tmp_path)
    data = GCODE.encode()
    begin = meta["begin"]
    at5 = data.index(b"M73 P50 R5")
    # in the start sequence: start time left + slicer time of the print
    s_begin = slicer_left(meta, begin)
    assert estimate_remaining(meta, 10, 60, 600, prep_s=300) == pytest.approx(240 + s_begin)
    assert estimate_remaining(meta, 10, 60, 600) == pytest.approx(s_begin)
    # printing: slicer 540 -> 300 done in 480 s instead of 240 s (half speed)
    done = s_begin - 300
    rem = estimate_remaining(meta, at5, 300 + 2 * done, 600, begin_duration=300)
    f = (PRIOR_WEIGHT_S + 2 * done) / (PRIOR_WEIGHT_S + done)
    assert rem == pytest.approx(300 * f)
    # history factor carries the estimate before measurements count
    assert estimate_remaining(meta, begin, 300, 600, begin_duration=300, factor=0.9) == pytest.approx(s_begin * 0.9)


@pytest.fixture
def gfile():
    async def download_to(self, root, path, target, hass_):
        target.write_text(GCODE)
        return len(GCODE)

    with patch(f"{API}.download_to", download_to):
        yield


async def test_begin_is_recorded_and_learned(hass: HomeAssistant, mock_client, notifications, gfile) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    data = GCODE.encode()
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=200)
    st["virtual_sdcard"] = {"file_position": 10, "progress": 0.0}
    await _refresh(hass, entry)
    await hass.async_block_till_done(wait_background_tasks=True)
    await _refresh(hass, entry)
    assert "begin_s" not in coord._print_state["active"]
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=300)
    st["virtual_sdcard"] = {"file_position": coord.layer_view["meta"]["begin"] + 1, "progress": 0.1}
    await _refresh(hass, entry)
    active = coord._print_state["active"]
    s_print = active["slicer_print_s"]
    assert active["begin_s"] == 300 and 300 < s_print <= 540
    # finished: start time and speed factor go into the history
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=300 + 0.9 * s_print)
    st["virtual_sdcard"] = {"file_position": len(data) - 5, "progress": 0.99}
    await _refresh(hass, entry)
    _status(mock_client, "complete", "sub/new.gcode", print_duration=300 + 0.9 * s_print)
    await _refresh(hass, entry)
    last = coord._history()[0]
    assert last["prep_s"] == 300 and last["speed_factor"] == pytest.approx(0.9, abs=0.002)
    assert coord._speed_prior() == (pytest.approx(0.9, abs=0.002), 300)


# ── Progress notification ───────────────────────────────────────────────────
def _live(calls):
    return [c for c in calls if (c.data.get("data") or {}).get("tag", "").startswith("snapmaker_u1_card_live")]


async def test_progress_notification_budget(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"], live_notify_budget=3)
    coord = entry.runtime_data
    sw = next(s.entity_id for s in hass.states.async_all("switch") if s.entity_id.endswith("live_notify")
              or "fortschritt" in s.entity_id or "progress" in s.entity_id)
    assert hass.states.get(sw).state == "off"
    await hass.services.async_call("switch", "turn_on", {"entity_id": sw}, blocking=True)
    assert coord.live_notify_on

    # the coordinator's own polls see the same print (no stray "print over")
    _status(mock_client, "printing", "a.gcode", print_duration=100)
    await _refresh(hass, entry)
    active = coord._print_state["active"]
    active["begin_s"] = 100
    active["name"] = "Teil"
    clock = [1000.0]
    with patch.object(prog.time, "monotonic", lambda: clock[0]):
        coord._live_tick("printing", active, 0.05, 3600, 3, 100)
        await hass.async_block_till_done()
        first = _live(notifications)
        assert len(first) == 1
        d = first[0].data["data"]
        assert d["progress"] == 5 and d["chronometer"] is True and d["alert_once"] is True
        assert d["importance"] == "low" and d["when"] > time.time()
        assert "Schicht 3/100" in first[0].data["message"] or "Layer 3/100" in first[0].data["message"]
        # same step, small drift: nothing
        coord._live_tick("printing", active, 0.08, 3500, 5, 100)
        # new 10 % step but too soon: nothing
        coord._live_tick("printing", active, 0.12, 3300, 9, 100)
        await hass.async_block_till_done()
        assert len(_live(notifications)) == 1
        clock[0] += prog.MIN_GAP_S + 1
        coord._live_tick("printing", active, 0.12, 3300, 9, 100)
        # pause ignores the gap, countdown stops
        coord._live_tick("paused", active, 0.12, 3300, 9, 100)
        await hass.async_block_till_done()
        sent = _live(notifications)
        assert len(sent) == 3 and "chronometer" not in sent[-1].data["data"]
        # budget (3) used up: no further updates today
        clock[0] += prog.MIN_GAP_S + 1
        coord._live_tick("printing", active, 0.5, 1800, 50, 100)
        await hass.async_block_till_done()
        assert len(_live(notifications)) == 3
        assert hass.states.get(sw).attributes.get("sent_today") in (3, None) or coord.live_sent_today() == 3
        # print over: the notification is removed (outside the budget)
        coord._live_tick("standby", None, None, None, None, None)
        await hass.async_block_till_done()
        clears = [c for c in _live(notifications) if c.data["message"] == "clear_notification"]
        assert len(clears) == 1


async def test_progress_notification_waits_for_start_sequence(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    coord = entry.runtime_data
    await coord.async_set_live_notify(True)
    coord._live_tick("printing", {"file": "a", "started": 1.0}, 0.0, 3600, 0, 10)
    await hass.async_block_till_done()
    assert _live(notifications) == []
    await coord.async_set_live_notify(False)
    coord._live_tick("printing", {"file": "a", "started": 1.0, "begin_s": 50}, 0.1, 3600, 1, 10)
    await hass.async_block_till_done()
    assert _live(notifications) == []


# ── Result photo once the head has left the part ────────────────────────────
async def test_photo_waits_for_head(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, camera="camera.cam")
    coord = entry.runtime_data
    positions = iter([[140, 135, 20, 0], [140, 135, 20, 0], [250, 300, 21, 0]])
    calls = []

    async def query(*objects, fields=None):
        calls.append(objects)
        return {"motion_report": {"live_position": next(positions)}}

    saved = AsyncMock()
    with patch.object(coord.client, "query_objects", query), patch.object(type(coord), "_save_photo", saved), \
         patch("custom_components.snapmaker_u1_card.coordinator.notify.EARLY_PHOTO_DELAY_S", 0), \
         patch("custom_components.snapmaker_u1_card.coordinator.notify.asyncio.sleep", AsyncMock()):
        await coord._photo_when_clear("camera.cam", Path("/tmp/x.jpg"), [98, 94, 180, 176])
    assert len(calls) == 3
    saved.assert_awaited_once()
