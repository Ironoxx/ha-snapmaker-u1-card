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


async def test_scheduled_job_without_question_waits_for_free_printer(hass: HomeAssistant, mock_client, transfer,
                                                                    notifications) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    _status(mock_client, "printing", "x.gcode")
    await _refresh(hass, entry)
    at = dt_util.utcnow() + timedelta(minutes=5)
    await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode", "start_at": at.isoformat(),
                                                         "confirm_bed": False}, blocking=True)
    async_fire_time_changed(hass, at + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert coord.queue.jobs[0]["sched"] == "due"
    mock_client["start_print"].assert_not_called()  # still printing
    _status(mock_client, "complete", "x.gcode")
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    mock_client["start_print"].assert_called_once()
    assert coord.queue.jobs == []


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
