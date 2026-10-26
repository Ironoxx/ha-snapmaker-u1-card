"""Spool management with Spoolman: assignment, manual choice, usage per head."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.exceptions import HomeAssistantError  # noqa: E402

from conftest import parsing as p  # noqa: E402
from tests.test_init import API, DOMAIN, mock_client  # noqa: E402,F401
from tests.test_power import _refresh, _setup, _status, auto_enable  # noqa: E402,F401

SM = "custom_components.snapmaker_u1_card.api.SpoolmanClient"


def _spool(sid, name, material, color, vendor="Generic", remaining=500.0, used=100.0, archived=False, last_used=None):
    return {"id": sid, "remaining_weight": remaining, "initial_weight": 1000.0, "used_weight": used,
            "archived": archived, "last_used": last_used,
            "filament": {"name": name, "material": material, "color_hex": color, "weight": 1000,
                         "vendor": {"name": vendor}}}


# sample setup: PLA black/white, PLA Silk bronze/gold
SLOTS = p.parse_slots({
    "filament_vendor": ["Generic"] * 4, "filament_type": ["PLA"] * 4,
    "filament_sub_type": ["", "", "Silk", "Silk"],
    "filament_color_rgba": ["000000FF", "FFFFFFFF", "6F4C2FFF", "FEE5A5FF"],
    "filament_exist": [True] * 4,
})
SPOOLS = [
    _spool(1, "PLA Schwarz", "PLA", "000000", remaining=650),
    _spool(2, "PLA Weiss", "PLA", "FFFFFF", remaining=900, used=100),
    _spool(3, "PLA Weiss", "PLA", "FFFFFF", remaining=120, used=880, last_used="2026-10-10T08:00:00"),
    _spool(4, "PLA Silk Bronze", "PLA", "6F4C2F", remaining=400),
    _spool(5, "PLA Silk Gold", "PLA", "FEE5A5", remaining=980),
    _spool(6, "PETG Rot", "PETG", "D32F2F", vendor="Snapmaker", used=0),
    _spool(7, "PLA Schwarz alt", "PLA", "000000", remaining=10, archived=True),
]


# ── Pure logic ──────────────────────────────────────────────────────────────
def test_suggest_spools_matches_material_color_and_prefers_recent():
    spools = [p.compact_spool(s) for s in SPOOLS]
    assert p.suggest_spools(SLOTS, spools) == {0: 1, 1: 3, 2: 4, 3: 5}
    # manual is fixed, a spool is never assigned twice
    assert p.suggest_spools(SLOTS, spools, {1: 2})[1] == 2
    # no matching material -> no assignment instead of a wrong spool
    petg_only = [p.compact_spool(SPOOLS[5])]
    assert p.suggest_spools(SLOTS, petg_only) == {0: None, 1: None, 2: None, 3: None}
    # archived spools never
    assert 7 not in p.suggest_spools(SLOTS, spools).values()
    # Blue PLA, but only white/gold/black PLA spools: no wrong spool
    blue = [{**SLOTS[3], "color": "#1E88E5"}]
    assert p.suggest_spools(blue, spools) == {3: None}
    # spool without a colour: the material is enough
    nocolor = [p.compact_spool({**SPOOLS[0], "filament": {**SPOOLS[0]["filament"], "color_hex": None}})]
    assert p.suggest_spools([SLOTS[0]], nocolor) == {0: 1}


def test_grams_per_slot_uses_map_table_and_cancel_ratio():
    rec = {"result": "complete", "map_table": [2, 0] + [0] * 30,
           "filaments": [{"index": 0, "weight": 10.0}, {"index": 1, "weight": 4.0}]}
    assert p.grams_per_slot(rec) == {2: 10.0, 0: 4.0}
    # two logical filaments on the same head are added up
    rec2 = {**rec, "map_table": [1, 1]}
    assert p.grams_per_slot(rec2) == {1: 14.0}
    # cancelled halfway
    rec3 = {**rec, "result": "cancelled", "filament_used": 500.0, "filament_total": 1000.0}
    assert p.grams_per_slot(rec3) == {2: 5.0, 0: 2.0}
    assert p.grams_per_slot({"filaments": []}) == {}


# ── Integration ────────────────────────────────────────────────────────────
@pytest.fixture
def spoolman():
    state = {"spools": [dict(s) for s in SPOOLS if not s["archived"]], "used": [], "fail": False}

    async def spools(self):
        if state["fail"]:
            from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError
            raise MoonrakerConnectionError("Spoolman nicht erreichbar")
        return [dict(s) for s in state["spools"]]

    async def use_weight(self, spool_id, grams):
        if state["fail"]:
            from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError
            raise MoonrakerConnectionError("weg")
        state["used"].append((spool_id, grams))
        for s in state["spools"]:
            if s["id"] == spool_id:
                s["remaining_weight"] -= grams
        return {}

    async def set_remaining(self, spool_id, grams):
        state.setdefault("set", []).append((spool_id, grams))
        for s in state["spools"]:
            if s["id"] == spool_id:
                s["remaining_weight"] = grams
        return {}

    with patch(f"{SM}.spools", spools), patch(f"{SM}.use_weight", use_weight), \
         patch(f"{SM}.set_remaining", set_remaining), \
         patch(f"{SM}.info", AsyncMock(return_value={"version": "0.27.0"})):
        yield state


def _real_slots(mock_client):
    st = mock_client["query"].return_value
    st["print_task_config"] = {
        **st["print_task_config"],
        "filament_vendor": ["Generic"] * 4, "filament_type": ["PLA"] * 4,
        "filament_sub_type": ["", "", "Silk", "Silk"],
        "filament_color_rgba": ["000000FF", "FFFFFFFF", "6F4C2FFF", "FEE5A5FF"],
        "filament_exist": [True] * 4, "extruder_map_table": list(range(4)) + [0] * 28,
    }


async def test_without_url_nothing_appears(hass: HomeAssistant, mock_client) -> None:
    await _setup(hass)
    attrs = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes
    assert "spoolman" not in attrs
    assert "spool" not in hass.states.get("sensor.snapmaker_u1_card_slot_1").attributes


async def test_assignment_manual_override_and_reset(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    await _refresh(hass, entry)
    sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
    assert sm["online"] is True and sm["url"] == "http://spoolman.local:7912"
    assert {k: (v or {}).get("id") for k, v in sm["slots"].items()} == {"0": 1, "1": 3, "2": 4, "3": 5}
    assert hass.states.get("sensor.snapmaker_u1_card_slot_2").attributes["spool_remaining"] == 120

    # manual: head 2 gets spool 2
    await hass.services.async_call(DOMAIN, "set_spool", {"slot": 2, "spool_id": 2}, blocking=True)
    sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
    assert sm["slots"]["1"]["id"] == 2 and sm["slots"]["1"]["manual"] is True
    # stays stable over further polls
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]["slots"]["1"]["id"] == 2

    # unknown spool is refused
    with pytest.raises(HomeAssistantError, match="Spool 99"):
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 1, "spool_id": 99}, blocking=True)

    # different filament in head 2 -> manual assignment expires, automatic again
    mock_client["query"].return_value["print_task_config"]["filament_color_rgba"][1] = "000000FF"
    await _refresh(hass, entry)
    sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
    assert sm["slots"]["1"] is None or sm["slots"]["1"]["manual"] is False

    # back to automatic
    await hass.services.async_call(DOMAIN, "set_spool", {"slot": 3}, blocking=True)
    assert hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]["slots"]["2"]["id"] == 4


async def test_print_books_usage_per_head_and_retries(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    coord = entry.runtime_data
    # file: two filaments; the print maps T0 -> head 3 (bronze), T1 -> head 1 (black)
    meta = {"filament_type": "PLA;PLA", "filament_colour": "#6F4C2F;#000000",
            "filament_weight": [12.0, 3.5], "filament_total": 5000.0}
    with patch(f"{API}.file_metadata", AsyncMock(return_value=meta)):
        st = _status(mock_client, "printing", "nuss.gcode")
        st["print_task_config"]["extruder_map_table"] = [2, 0] + [0] * 30
        await _refresh(hass, entry)
        await _refresh(hass, entry)
        # Spoolman fails at the print end: the booking stays pending
        spoolman["fail"] = True
        _status(mock_client, "complete", "nuss.gcode")
        await _refresh(hass, entry)
    assert spoolman["used"] == []
    assert len(coord.spools.queue) == 2
    last = hass.states.get("sensor.snapmaker_u1_card_print_history").attributes["prints"][0] \
        if hass.states.get("sensor.snapmaker_u1_card_print_history") else coord.data.history[0]
    assert {(s["slot"], s["spool_id"], s["grams"]) for s in last["spools"]} == {(2, 4, 12.0), (0, 1, 3.5)}

    # back again: booked later, exactly once
    spoolman["fail"] = False
    coord.spools.force()
    await _refresh(hass, entry)
    await _refresh(hass, entry)
    assert sorted(spoolman["used"]) == [(1, 3.5), (4, 12.0)]
    assert coord.spools.queue == []
    assert all(sp["booked"] is True for sp in coord.data.history[0]["spools"]), "in der Historie als gebucht markiert"
    # before/after per spool: head 3 started with 400 g, Spoolman has 388 g left afterwards
    coord.spools.force()
    await _refresh(hass, entry)
    spools = {sp["spool_id"]: sp for sp in coord.data.history[0]["spools"]}
    assert spools[4]["before"] == 400.0 and spools[4]["after"] == 388.0
    assert coord.data.history[0]["spools_final"] is True
    sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
    assert sm["slots"]["2"]["remaining_weight"] == 388.0


async def test_no_booking_when_disabled(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912", spoolman_deduct=False)
    meta = {"filament_type": "PLA", "filament_colour": "#000000", "filament_weight": [5.0]}
    with patch(f"{API}.file_metadata", AsyncMock(return_value=meta)):
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        _status(mock_client, "complete", "a.gcode")
        await _refresh(hass, entry)
    entry.runtime_data.spools.force()
    await _refresh(hass, entry)
    assert spoolman["used"] == []


async def test_queue_survives_restart(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    coord = entry.runtime_data
    meta = {"filament_type": "PLA", "filament_colour": "#000000", "filament_weight": [5.0]}
    with patch(f"{API}.file_metadata", AsyncMock(return_value=meta)):
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        spoolman["fail"] = True
        _status(mock_client, "complete", "a.gcode")
        await _refresh(hass, entry)
    assert len(coord.spools.queue) == 1
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(entry.runtime_data.spools.queue) == 1
    spoolman["fail"] = False
    entry.runtime_data.spools.force()
    await _refresh(hass, entry)
    assert spoolman["used"] == [(1, 5.0)]


async def test_options_validate_spoolman_url(hass: HomeAssistant, mock_client) -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerConnectionError

    entry = await _setup(hass)
    base = {"power": {"shutdown_host": True, "auto_on": False, "auto_off": False,
                      "auto_off_temp": 50, "auto_off_delay": 5},
            "notify": {"notify_events": ["complete"]}, "filament": {}, "files": {"files_limit": 24},
            "timelapse": {"timelapse_archive": False, "timelapse_keep": 5},
            "maintenance": {"maint_plate": 30, "maint_nozzle": 100, "maint_rails": 300, "maint_belts": 500, "maint_filter": 0}}
    with patch(f"{SM}.info", AsyncMock(side_effect=MoonrakerConnectionError("nein"))):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**base, "spoolman": {"spoolman_url": "http://falsch:7912",
                                                     "spoolman_deduct": True, "spoolman_low": 100}})
    assert result["errors"] == {"base": "spoolman_unreachable"}
    with patch(f"{SM}.info", AsyncMock(return_value={"version": "0.27.0"})), \
         patch(f"{SM}.spools", AsyncMock(return_value=[])):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**base, "spoolman": {"spoolman_url": "192.168.0.10:7912/",
                                                     "spoolman_deduct": True, "spoolman_low": 150}})
        await hass.async_block_till_done()
    assert result["type"] == "create_entry"
    assert entry.options["spoolman_url"] == "192.168.0.10:7912/"
    assert entry.options["spoolman_low"] == 150
    assert entry.runtime_data.spools.client.url == "http://192.168.0.10:7912"


# ── Choosing a spool loads its filament into the printer (1.6.0b2) ──────────
def test_spool_filament_mapping():
    to_fw = p.spool_filament
    assert to_fw(p.compact_spool(_spool(1, "PLA Matte Black", "PLA", "1C1C1C", vendor="GEEETECH"))) == {
        "type": "PLA", "sub_type": "Matte", "vendor": "GEEETECH", "color": "#1C1C1C"}
    assert to_fw(p.compact_spool(_spool(2, "CR-PETG Black", "petg", "000000", vendor="Creality")))["sub_type"] == ""
    assert to_fw(p.compact_spool(_spool(3, "Seide", "PLA Silk", "FEE5A5")))["sub_type"] == "Silk"
    # characters Klipper would cut the command at are dropped
    assert to_fw(p.compact_spool(_spool(4, "x", "PLA", "FFFFFF", vendor='Bad"Vendor;#')))["vendor"] == "BadVendor"
    assert to_fw(p.compact_spool(_spool(5, "no material", "", "FFFFFF"))) is None
    assert to_fw(None) is None


async def test_choosing_spool_writes_filament(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    ptc = mock_client["query"].return_value["print_task_config"]
    ptc["filament_official"] = [False] * 4  # spools without RFID tag, like Thomas' heads
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    await _refresh(hass, entry)
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        # Head 1 shows the stock "PLA Generic black", the spool is red PETG from Snapmaker
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 1, "spool_id": 6}, blocking=True)
        gcode.assert_awaited_with('SET_PRINT_FILAMENT_CONFIG CONFIG_EXTRUDER=0 VENDOR="Snapmaker" '
                                  'FILAMENT_TYPE="PETG" FILAMENT_SUBTYPE="NONE" FILAMENT_COLOR_RGBA=D32F2FFF')
        # The printer reports the new filament: the manual choice must survive the changed fingerprint
        ptc["filament_vendor"][0], ptc["filament_type"][0], ptc["filament_color_rgba"][0] = "Snapmaker", "PETG", "D32F2FFF"
        await _refresh(hass, entry)
        await _refresh(hass, entry)
        sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
        assert sm["slots"]["0"]["id"] == 6 and sm["slots"]["0"]["manual"] is True
        assert hass.states.get("sensor.snapmaker_u1_card_slot_1").state.startswith("PETG")

        # Same filament already loaded: nothing written
        calls = gcode.await_count
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 1, "spool_id": 6}, blocking=True)
        assert gcode.await_count == calls

        # Official RFID spool: the tag wins, only the assignment changes
        entry.runtime_data.data.slots[1]["official"] = True
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 2, "spool_id": 1}, blocking=True)
        assert gcode.await_count == calls

        # During a print: assignment yes, filament no (the firmware refuses)
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 3, "spool_id": 2}, blocking=True)
        assert gcode.await_count == calls
        sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
        assert sm["slots"]["2"]["id"] == 2



async def test_moonraker_books_itself(hass: HomeAssistant, mock_client, spoolman) -> None:
    """Moonraker has [spoolman] (paxx12 SpoolLink): no own booking, but before/after in the history."""
    _real_slots(mock_client)
    mock_client["components"].return_value = ["file_manager", "spoolman", "spoollink"]
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    coord = entry.runtime_data
    ptc = mock_client["query"].return_value["print_task_config"]
    ptc["filament_spool_id"] = [5, 0, 0, 0]  # SpoolLink: head 1 holds spool 5
    await _refresh(hass, entry)
    sm = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["spoolman"]
    assert sm["external_booking"] is True and sm["books"] is False and sm["spoollink"] is True
    assert sm["slots"]["0"]["id"] == 5 and sm["slots"]["0"]["source"] == "printer"
    assert sm["slots"]["1"] is None, "no own guessing with SpoolLink"

    meta = {"filament_type": "PLA", "filament_colour": "#000000", "filament_weight": [20.0]}
    with patch(f"{API}.file_metadata", AsyncMock(return_value=meta)):
        st = _status(mock_client, "printing", "a.gcode")
        st["print_task_config"]["extruder_map_table"] = [0] * 32
        await _refresh(hass, entry)
        await _refresh(hass, entry)
        # Moonraker books while printing
        for s in spoolman["spools"]:
            if s["id"] == 5:
                s["remaining_weight"] -= 20.0
        _status(mock_client, "complete", "a.gcode")
        await _refresh(hass, entry)
    coord.spools.force()
    await _refresh(hass, entry)
    assert spoolman["used"] == [], "never booked twice"
    sp = coord.data.history[0]["spools"][0]
    assert sp["booked"] == "moonraker" and sp["before"] == 980.0 and sp["after"] == 960.0

    # choosing a spool goes through SpoolLink's own command
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 2, "spool_id": 3}, blocking=True)
        gcode.assert_awaited_with("SET_SPOOL_ID CHANNEL=1 SPOOL_ID=3")
        await hass.services.async_call(DOMAIN, "set_spool", {"slot": 2, "spool_id": 0}, blocking=True)
        gcode.assert_awaited_with("SET_SPOOL_ID CHANNEL=1 SPOOL_ID=0")
        with pytest.raises(HomeAssistantError, match="SpoolLink"):
            await hass.services.async_call(DOMAIN, "set_spool", {"slot": 2}, blocking=True)


async def test_weigh_spool(hass: HomeAssistant, mock_client, spoolman) -> None:
    _real_slots(mock_client)
    for s in spoolman["spools"]:
        s["spool_weight"] = 200.0 if s["id"] == 1 else None
    entry = await _setup(hass, spoolman_url="http://spoolman.local:7912")
    await _refresh(hass, entry)
    # head 1 has spool 1 (automatic); scale shows 742 g with the spool
    res = await hass.services.async_call(DOMAIN, "weigh_spool", {"slot": 1, "weight": 742},
                                         blocking=True, return_response=True)
    assert res["spool_id"] == 1 and res["remaining_weight"] == 542.0 and res["before"] == 650.0
    assert spoolman["set"] == [(1, 542.0)]
    # net weight, by ID
    await hass.services.async_call(DOMAIN, "weigh_spool", {"spool_id": 2, "weight": 300, "gross": False},
                                   blocking=True, return_response=True)
    assert spoolman["set"][-1] == (2, 300.0)
    # no empty spool weight known: gross refused with a hint
    with pytest.raises(HomeAssistantError, match="empty spool"):
        await hass.services.async_call(DOMAIN, "weigh_spool", {"spool_id": 2, "weight": 900},
                                       blocking=True, return_response=True)
