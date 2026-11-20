"""2.4.0b2: archive/delete spools, more create_spool fields, to-do lists, scheduled queue jobs."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import Context, HomeAssistant  # noqa: E402
from homeassistant.exceptions import HomeAssistantError, Unauthorized  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import async_fire_time_changed  # noqa: E402

from tests.test_init import API, DOMAIN, mock_client  # noqa: E402,F401
from tests.test_jobs_ha import transfer  # noqa: E402,F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: E402,F401
from tests.test_spoolman import SM, SPOOLS, _real_slots, _spool, spoolman  # noqa: E402,F401

URL = "http://spoolman.local:7912"


# ── Spools: archive, restore, delete ────────────────────────────────────────
@pytest.fixture
def spool_admin(spoolman):
    """set_archived / delete_spool / archived_spools on top of the spoolman fake."""
    archived = [dict(SPOOLS[6])]

    async def set_archived(self, spool_id, value):
        spoolman.setdefault("archive_calls", []).append((spool_id, value))
        if value:
            moved = [s for s in spoolman["spools"] if s["id"] == spool_id]
            spoolman["spools"] = [s for s in spoolman["spools"] if s["id"] != spool_id]
            archived.extend({**s, "archived": True} for s in moved)
        else:
            back = [s for s in archived if s["id"] == spool_id]
            archived[:] = [s for s in archived if s["id"] != spool_id]
            spoolman["spools"].extend({**s, "archived": False} for s in back)
        return {}

    async def delete_spool(self, spool_id):
        spoolman.setdefault("deleted", []).append(spool_id)
        spoolman["spools"] = [s for s in spoolman["spools"] if s["id"] != spool_id]

    async def archived_spools(self):
        return [dict(s) for s in archived]

    with patch(f"{SM}.set_archived", set_archived), patch(f"{SM}.delete_spool", delete_spool), \
         patch(f"{SM}.archived_spools", archived_spools):
        yield spoolman


async def test_archive_restore_and_delete_spool(hass: HomeAssistant, mock_client, spool_admin,
                                                hass_ws_client, hass_read_only_user) -> None:
    _real_slots(mock_client)
    entry = await _setup(hass, spoolman_url=URL)
    await _refresh(hass, entry)
    ids = lambda: [s["id"] for s in hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]["spools"]]  # noqa: E731
    assert 6 in ids()

    # spool 1 sits in head 1: refused, nothing sent to Spoolman
    with pytest.raises(HomeAssistantError, match="head 1"):
        await hass.services.async_call(DOMAIN, "spool_archive", {"spool_id": 1}, blocking=True)
    assert "archive_calls" not in spool_admin

    # free spool: archived, gone from the list right away
    res = await hass.services.async_call(DOMAIN, "spool_archive", {"spool_id": 6}, blocking=True, return_response=True)
    assert res == {"spool_id": 6, "archived": True} and 6 not in ids()

    # the card asks for the archived ones only on demand
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/spoolman/archived"})
    msg = await ws.receive_json()
    assert msg["success"] and [s["id"] for s in msg["result"]["spools"]] == [7, 6]
    assert msg["result"]["spools"][0]["archived"] is True

    # restore
    await hass.services.async_call(DOMAIN, "spool_archive", {"spool_id": 6, "archived": False}, blocking=True)
    assert 6 in ids()

    # delete: admins only, not for a spool in a head, pending bookings dropped
    with pytest.raises(Unauthorized):
        await hass.services.async_call(DOMAIN, "spool_delete", {"spool_id": 6}, blocking=True,
                                       context=Context(user_id=hass_read_only_user.id))
    with pytest.raises(HomeAssistantError, match="head 1"):
        await hass.services.async_call(DOMAIN, "spool_delete", {"spool_id": 1}, blocking=True)
    entry.runtime_data.spools.queue.append({"key": "x|0", "spool_id": 6, "grams": 3.0, "file": "a", "slot": 0})
    await hass.services.async_call(DOMAIN, "spool_delete", {"spool_id": 6}, blocking=True)
    assert spool_admin["deleted"] == [6] and 6 not in ids()
    assert not [q for q in entry.runtime_data.spools.queue if q["spool_id"] == 6]


async def test_create_spool_more_fields(hass: HomeAssistant, mock_client, spoolman) -> None:
    """Temperatures, density, diameter, article no. go into a new filament; lot and comment into the spool."""
    created = []

    async def create(self, kind, data):
        created.append((kind, data))
        if kind == "spool":
            spoolman["spools"].append({**_spool(200, "PETG", "PETG", "00ff00"), "id": 200})
        return {"id": 200 + len(created)}

    with patch(f"{SM}.vendors", AsyncMock(return_value=[{"id": 1, "name": "Sunlu"}])), \
         patch(f"{SM}.filaments", AsyncMock(return_value=[])), patch(f"{SM}.create", create):
        entry = await _setup(hass, spoolman_url=URL)
        await _refresh(hass, entry)
        await hass.services.async_call(DOMAIN, "create_spool", {
            "material": "PETG", "vendor": "Sunlu", "color": "00ff00", "weight": 1000,
            "extruder_temp": 240, "bed_temp": 80, "density": 1.27, "diameter": 1.75,
            "article_number": "SL-PETG-G", "lot_nr": "L42", "comment": "  Trockenbox 2  "}, blocking=True)
    fil = next(d for k, d in created if k == "filament")
    spool = next(d for k, d in created if k == "spool")
    assert fil["settings_extruder_temp"] == 240 and fil["settings_bed_temp"] == 80
    assert fil["density"] == 1.27 and fil["diameter"] == 1.75 and fil["article_number"] == "SL-PETG-G"
    assert spool["lot_nr"] == "L42" and spool["comment"] == "Trockenbox 2"
    assert "lot_nr" not in fil and "settings_extruder_temp" not in spool


# ── To-do lists ─────────────────────────────────────────────────────────────
async def test_todo_lists_off_by_default(hass: HomeAssistant, mock_client, spoolman) -> None:
    await _setup(hass, spoolman_url=URL)
    assert hass.states.async_all("todo") == []


async def test_maintenance_todo(hass: HomeAssistant, mock_client) -> None:
    entry = await _setup(hass, todo_maintenance=True)
    coord = entry.runtime_data
    coord._print_hours = 100.0
    coord.maintenance.done = {}
    coord.maintenance.baseline(0.0, 0.0)
    await _refresh(hass, entry)
    state = next(s for s in hass.states.async_all("todo"))
    assert int(state.state) >= 1, "due items count as open"
    items = await hass.services.async_call("todo", "get_items", {}, target={"entity_id": state.entity_id},
                                           blocking=True, return_response=True)
    first = items[state.entity_id]["items"][0]
    with patch.object(type(coord), "mark_maintenance") as mark:
        await hass.services.async_call("todo", "update_item", {"item": first["uid"], "status": "completed"},
                                       target={"entity_id": state.entity_id}, blocking=True)
    mark.assert_called_once_with(first["uid"])


async def test_shopping_list_own_and_external(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    # own list: spool 3 (120 g) and 6? no – threshold 150 g: only spool 3
    entry = await _setup(hass, spoolman_url=URL, spoolman_low=150, todo_shopping=True)
    await _refresh(hass, entry)
    todo = next(s for s in hass.states.async_all("todo"))
    assert todo.state == "1"
    items = (await hass.services.async_call("todo", "get_items", {}, target={"entity_id": todo.entity_id},
                                            blocking=True, return_response=True))[todo.entity_id]["items"]
    assert items[0]["uid"] == "spool-3" and "PLA Weiss" in items[0]["summary"] and "120 g" in items[0]["description"]
    # ticked off stays ticked; removed is hidden – both remembered
    await hass.services.async_call("todo", "update_item", {"item": "spool-3", "status": "completed"},
                                   target={"entity_id": todo.entity_id}, blocking=True)
    assert entry.runtime_data.shopping["state"] == {"3": "done"}
    assert hass.states.get(todo.entity_id).state == "0"
    # refilled (no longer low): forgotten
    next(s for s in spoolman["spools"] if s["id"] == 3)["remaining_weight"] = 900
    entry.runtime_data.spools.force()
    await _refresh(hass, entry)
    assert entry.runtime_data.shopping["state"] == {}
    await hass.config_entries.async_unload(entry.entry_id)

    # external list: items added once, no own entity
    added = []

    async def add_item(call):
        added.append(call.data["item"])

    async def get_items(call):
        return {"todo.einkauf": {"items": [{"summary": "Generic PLA Schwarz", "status": "needs_action"}]}}

    from homeassistant.core import SupportsResponse
    hass.services.async_register("todo", "add_item", add_item)
    hass.services.async_register("todo", "get_items", get_items, supports_response=SupportsResponse.ONLY)
    next(s for s in spoolman["spools"] if s["id"] == 3)["remaining_weight"] = 120
    entry2 = await _setup(hass, spoolman_url=URL, spoolman_low=700, todo_shopping=True, shopping_target="todo.einkauf")
    await _refresh(hass, entry2)
    await hass.async_block_till_done()
    # spools below 700 g: 1 (650, already on the list), 3 (120), 4 (400), 6 (500)
    assert sorted(added) == ["Generic PLA Silk Bronze", "Generic PLA Weiss", "Snapmaker PETG Rot"]
    assert entry2.runtime_data.shopping["sent"] == [1, 3, 4, 6]
    await _refresh(hass, entry2)
    await hass.async_block_till_done()
    assert len(added) == 3, "never added twice"


# ── Scheduled queue jobs ────────────────────────────────────────────────────
async def test_scheduled_job_asks_for_the_bed(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    hass.config.language = "de"
    coord = entry.runtime_data
    with pytest.raises(HomeAssistantError, match="Vergangenheit|past"):
        await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode",
                                       "start_at": (dt_util.now() - timedelta(hours=1)).isoformat()}, blocking=True)
    at = dt_util.utcnow() + timedelta(minutes=30)
    res = await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "start_at": at.isoformat()},
                                         blocking=True, return_response=True)
    job = res["job"]
    assert abs(job["start_at"] - at.timestamp()) < 1 and job["confirm_bed"] is True
    assert job["id"] in coord._job_timers

    async_fire_time_changed(hass, at + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert coord.queue.get(job["id"])["sched"] == "confirm"
    mock_client["start_print"].assert_not_called()
    note = next(c for c in notifications if "Druckbett frei" in c.data["message"])
    action = note.data["data"]["actions"][0]["action"]
    assert action.startswith("SU1_QSTART:")

    # "Bed clear – start" from the notification starts it
    hass.bus.async_fire("mobile_app_notification_action", {"action": action})
    await hass.async_block_till_done()
    mock_client["start_print"].assert_called_once()
    assert coord.queue.jobs == []


async def test_scheduled_job_overlapping_a_running_print(hass: HomeAssistant, mock_client, transfer,
                                                         notifications) -> None:
    """2.4.0b4 (Thomas: 1 h print in 1 h, 45 min print in 1 h 30 min): B waits, never starts onto A's part."""
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    hass.config.language = "de"
    coord = entry.runtime_data
    _status(mock_client, "printing", "x.gcode")
    await _refresh(hass, entry)
    at = dt_util.utcnow() + timedelta(minutes=5)
    await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "start_at": at.isoformat(),
                                                         "confirm_bed": False}, blocking=True)
    async_fire_time_changed(hass, at + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert coord.queue.jobs[0]["sched"] == "wait", "printer busy: waits, no question, no error"
    mock_client["start_print"].assert_not_called()
    # A ends: its part is on the bed -> question even without confirm_bed, no automatic start
    _status(mock_client, "complete", "x.gcode")
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    job = coord.queue.jobs[0]
    assert job["sched"] == "confirm" and job["bed_used"] is True
    mock_client["start_print"].assert_not_called()
    note = next(c for c in notifications if "Druckbett räumen" in c.data["message"])
    action = note.data["data"]["actions"][0]["action"]
    hass.bus.async_fire("mobile_app_notification_action", {"action": action})
    await hass.async_block_till_done()
    mock_client["start_print"].assert_called_once()
    assert coord.queue.jobs == []


async def test_bed_confirmation_while_still_printing(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    """Tapping "bed clear – start" while a print runs is no error: the job waits and asks again later."""
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    coord = entry.runtime_data
    at = dt_util.utcnow() + timedelta(minutes=5)
    await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "start_at": at.isoformat()},
                                   blocking=True)
    async_fire_time_changed(hass, at + timedelta(seconds=1))
    await hass.async_block_till_done()
    job = coord.queue.jobs[0]
    assert job["sched"] == "confirm"
    _status(mock_client, "printing", "x.gcode")  # someone started a print by hand meanwhile
    await _refresh(hass, entry)
    await coord.confirm_job(job["id"])
    assert job["sched"] == "wait" and job["bed_used"] is True
    mock_client["start_print"].assert_not_called()


async def test_right_after_previous_job(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    """2.4.0b4 after_prev: waits for the running print, then asks (always) – no start time needed."""
    entry = await _setup(hass)
    coord = entry.runtime_data
    _status(mock_client, "printing", "x.gcode")
    await _refresh(hass, entry)
    res = await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "after_prev": True,
                                                               "confirm_bed": False}, blocking=True, return_response=True)
    job = res["job"]
    assert job["after_prev"] is True and job["confirm_bed"] is True and "start_at" not in job
    assert coord.queue.jobs[0]["sched"] == "wait"
    _status(mock_client, "complete", "x.gcode")
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    assert coord.queue.jobs[0]["sched"] == "confirm"
    mock_client["start_print"].assert_not_called()


async def test_scheduled_job_missed_while_ha_was_off(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    at = dt_util.utcnow() + timedelta(minutes=10)
    await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "start_at": at.isoformat(),
                                                         "confirm_bed": False}, blocking=True)
    # HA "was off": the start time is long past when the entry loads again
    entry.runtime_data.queue.jobs[0]["start_at"] = (dt_util.utcnow() - timedelta(hours=2)).timestamp()
    entry.runtime_data._save(0)
    await hass.async_block_till_done()
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    job = entry.runtime_data.queue.jobs[0]
    assert job["sched"] == "missed"
    mock_client["start_print"].assert_not_called()
    assert any("verpasst" in c.data["message"] or "missed" in c.data["message"] for c in notifications)


# ── 2.4.0b3: edit spools, own Spoolman fields ───────────────────────────────
def test_extra_encoding():
    from custom_components.snapmaker_u1_card import parsing as p
    current = {"card_uids": '["04AB"]', "dryer": '"Box 1"'}
    out = p.encode_extra({"dryer": "Box 2", "dried": True, "temp": [40, 55], "old": None}, current)
    assert out == {"card_uids": '["04AB"]', "dryer": '"Box 2"', "dried": "true", "temp": "[40, 55]"}, "other fields kept"
    assert p.encode_extra({"dryer": ""}, current) == {"card_uids": '["04AB"]'}, "empty removes"
    assert p.decode_extra({"a": '"x"', "b": "5", "c": "plain"}) == {"a": "x", "b": 5, "c": "plain"}
    fields = p.compact_fields([
        {"key": "z", "name": "Z", "field_type": "text", "order": 2},
        {"key": "dryer", "name": "Trockner", "field_type": "choice", "choices": ["A", "B"], "multi_choice": False,
         "default_value": '"A"', "order": 1},
        {"key": "x", "field_type": "unknown"}])
    assert [f["key"] for f in fields] == ["dryer", "z"] and fields[0]["default"] == "A" and fields[0]["type"] == "choice"


async def test_update_spool_and_edit_view(hass: HomeAssistant, mock_client, spoolman, hass_ws_client) -> None:
    raw = {"id": 4, "remaining_weight": 400, "initial_weight": 1000, "spool_weight": 200, "price": 20, "location": "Regal",
           "lot_nr": "", "comment": "", "archived": False, "extra": {"card_uids": '["04AB"]'},
           "filament": {"id": 9, "name": "PLA Silk Bronze", "material": "PLA", "color_hex": "6f4c2f",
                        "vendor": {"id": 1, "name": "Generic"}, "density": 1.24, "diameter": 1.75,
                        "settings_extruder_temp": 210, "extra": {}}}
    patches = []

    async def update(self, kind, obj_id, data):
        patches.append((kind, obj_id, data))
        return {}

    fields = {"spool": [{"key": "dryer", "name": "Trockner", "field_type": "text"}], "filament": []}
    with patch(f"{SM}.spool", AsyncMock(return_value=raw)), patch(f"{SM}.update", update), \
         patch(f"{SM}.count_spools", AsyncMock(return_value=3)), \
         patch(f"{SM}.fields", AsyncMock(side_effect=lambda e: fields[e])), \
         patch(f"{SM}.vendors", AsyncMock(return_value=[{"id": 1, "name": "Generic"}])), \
         patch(f"{SM}.create", AsyncMock(return_value={"id": 5})) as create:
        entry = await _setup(hass, spoolman_url=URL)
        await _refresh(hass, entry)
        ws = await hass_ws_client(hass)
        await ws.send_json({"id": 1, "type": f"{DOMAIN}/spoolman/spool", "spool_id": 4})
        msg = await ws.receive_json()
        res = msg["result"]
        assert res["filament_spools"] == 3 and res["fields"]["spool"][0]["key"] == "dryer"
        assert res["spool"]["filament"]["extruder_temp"] == 210 and res["spool"]["extra"] == {"card_uids": ["04AB"]}
        await ws.send_json({"id": 2, "type": f"{DOMAIN}/spoolman/fields"})
        assert (await ws.receive_json())["result"]["spool"][0]["name"] == "Trockner"

        out = await hass.services.async_call(DOMAIN, "update_spool", {
            "spool_id": 4, "remaining": 350, "location": None, "extra": {"dryer": "Box 2"},
            "filament_extruder_temp": 215, "filament_bed_temp": None, "filament_vendor": "Sunlu"},
            blocking=True, return_response=True)
    assert out["filament_id"] == 9
    fil = next(d for k, _, d in patches if k == "filament")
    sp = next(d for k, _, d in patches if k == "spool")
    assert fil == {"settings_extruder_temp": 215, "settings_bed_temp": None, "vendor_id": 5}
    create.assert_awaited_once()  # vendor Sunlu created
    assert sp == {"remaining_weight": 350.0, "location": None,
                  "extra": {"card_uids": '["04AB"]', "dryer": '"Box 2"'}}, "SpoolLink's field kept"


async def test_create_spool_with_own_fields(hass: HomeAssistant, mock_client, spoolman) -> None:
    created = []

    async def create(self, kind, data):
        created.append((kind, data))
        return {"id": 300 + len(created)}

    with patch(f"{SM}.vendors", AsyncMock(return_value=[{"id": 1, "name": "Generic"}])), \
         patch(f"{SM}.filaments", AsyncMock(return_value=[])), patch(f"{SM}.create", create):
        entry = await _setup(hass, spoolman_url=URL)
        await _refresh(hass, entry)
        await hass.services.async_call(DOMAIN, "create_spool", {
            "material": "PLA", "weight": 1000, "extra": {"dryer": "Box 1", "dried": True},
            "filament_extra": {"shop": "x"}}, blocking=True)
    fil = next(d for k, d in created if k == "filament")
    spool = next(d for k, d in created if k == "spool")
    assert fil["extra"] == {"shop": '"x"'}
    assert spool["extra"] == {"dryer": '"Box 1"', "dried": "true"}


# ── 2.4.0b4: spool changed at the printer ───────────────────────────────────
def test_spool_fits_slot():
    from custom_components.snapmaker_u1_card import parsing as p
    creality = {"material": "PETG", "color": "#FFFFFF", "vendor": "Creality"}
    assert p.spool_fits_slot({"type": "PETG", "color": "#FFFFFF", "vendor": "Generic"}, creality)
    assert not p.spool_fits_slot({"type": "PETG", "color": "#FFFFFF", "vendor": "Sunlu"}, creality), "other vendor"
    assert not p.spool_fits_slot({"type": "PETG", "color": "#000000", "vendor": "Generic"}, creality), "other colour"
    assert not p.spool_fits_slot({"type": "ABS", "color": "#FFFFFF", "vendor": "Generic"}, creality), "other material"
    assert p.spool_fits_slot({"type": "PLA", "color": None, "vendor": "Generic"}, creality), "firmware default = unknown"


def test_usage_split_when_the_spool_changed_during_the_print():
    from custom_components.snapmaker_u1_card.spools import SpoolManager
    mgr = SpoolManager(object(), None, True)
    mgr.spools = [{"id": 3, "remaining_weight": 900.0}]
    record = {"started": "s1", "result": "complete", "map_table": [0], "file": "a.gcode",
              "filaments": [{"index": 0, "weight": 100.0}],
              "spool_ids": {"0": 3}, "spool_start": {"0": 40.0},
              "spool_changes": {"0": [{"spool_id": 7, "until": 0.4}]}}
    booked = mgr.book(record)
    assert [(b["spool_id"], b["grams"]) for b in booked] == [(7, 40.0), (3, 60.0)]
    assert [q["key"] for q in mgr.queue] == ["s1|0", "s1|0|1"], "first part keeps the old key"
    assert booked[0]["before"] == 40.0 and booked[1]["before"] == 900.0


def test_spool_changes_are_tracked_and_unload_keeps_the_spool():
    from custom_components.snapmaker_u1_card.coordinator.spools import SpoolMixin
    active = {"spool_ids": {"0": 7}}
    ids = SpoolMixin._track_spool_changes(active, {"0": None}, 0.39)
    assert ids == {"0": 7} and active["spool_changes"] == {}, "unloaded in the pause: still spool 7"
    active["spool_ids"] = ids
    active["spool_ids"] = SpoolMixin._track_spool_changes(active, {"0": 3}, 0.4)
    assert active["spool_ids"] == {"0": 3}
    assert active["spool_changes"] == {"0": [{"spool_id": 7, "until": 0.4}]}
