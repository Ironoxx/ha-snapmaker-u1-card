"""Firmware preferences, setting a slot's filament, RFID data and camera wake-up."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from tests.test_init import API, DOMAIN, mock_client  # noqa: F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: F401

PREFS = {"auto_replenish_filament": True, "replenish_ignore_color": False,
         "filament_entangle_detect": False, "filament_entangle_sen": "medium", "end_led_turn_off": True}
TAG = {"VENDOR": "Snapmaker", "OFFICIAL": True, "WEIGHT": 1000, "DIAMETER": 175,
       "DRYING_TEMP": 55, "DRYING_TIME": 8, "HOTEND_MIN_TEMP": 190, "HOTEND_MAX_TEMP": 230,
       "SKU": 900001, "MF_DATE": "20250812"}


def _with_prefs(mock_client) -> None:
    st = mock_client["query"].return_value
    st["print_task_config"] = {**st["print_task_config"], **PREFS}
    st["filament_detect"] = {"info": [TAG, {"VENDOR": "NONE"}, {}, {}]}


async def test_preference_entities_and_service(hass: HomeAssistant, mock_client, notifications) -> None:
    _with_prefs(mock_client)
    entry = await _setup(hass)
    assert hass.states.get("switch.snapmaker_u1_card_auto_replenish_filament").state == "on"
    assert hass.states.get("switch.snapmaker_u1_card_light_off_after_print").state == "on"
    assert hass.states.get("switch.snapmaker_u1_card_filament_entangle_detection").state == "off"
    assert hass.states.get("select.snapmaker_u1_card_entangle_detection_sensitivity").state == "medium"

    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        await hass.services.async_call("switch", "turn_off",
                                       {"entity_id": "switch.snapmaker_u1_card_auto_replenish_filament"},
                                       blocking=True)
        gcode.assert_awaited_with("SET_PRINT_PREFERENCES AUTO_REPLENISH_FILAMENT=0")
        await hass.services.async_call("select", "select_option",
                                       {"entity_id": "select.snapmaker_u1_card_entangle_detection_sensitivity",
                                        "option": "high"}, blocking=True)
        gcode.assert_awaited_with("SET_PRINT_PREFERENCES FILAMENT_ENTANGLE_SEN=high")
        # Also changeable during a print
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        await hass.services.async_call(DOMAIN, "set_preference",
                                       {"preference": "entangle_detect", "value": True}, blocking=True)
        gcode.assert_awaited_with("SET_PRINT_PREFERENCES FILAMENT_ENTANGLE_DETECT=1")
        with pytest.raises(Exception):
            await hass.services.async_call(DOMAIN, "set_preference",
                                           {"preference": "entangle_sensitivity", "value": True}, blocking=True)


async def test_preferences_unavailable_on_old_firmware(hass: HomeAssistant, mock_client, notifications) -> None:
    await _setup(hass)
    assert hass.states.get("switch.snapmaker_u1_card_auto_replenish_filament").state == "unavailable"


async def test_set_filament_and_rfid(hass: HomeAssistant, mock_client, notifications) -> None:
    _with_prefs(mock_client)
    entry = await _setup(hass)
    slots = hass.states.get("sensor.snapmaker_u1_card_filaments").attributes["slots"]
    assert slots[0]["rfid"]["weight_g"] == 1000 and slots[0]["rfid"]["drying_temp"] == 55
    assert slots[1]["rfid"] is None
    assert hass.states.get("sensor.snapmaker_u1_card_slot_1").attributes["rfid"]["sku"] == 900001

    entry.runtime_data.data.slots[0]["official"] = True
    with patch(f"{API}.gcode", AsyncMock()) as gcode:
        await hass.services.async_call(DOMAIN, "set_filament",
                                       {"slot": 2, "type": "petg", "sub_type": "HF", "color": "#112233"},
                                       blocking=True)
        gcode.assert_awaited_with('SET_PRINT_FILAMENT_CONFIG CONFIG_EXTRUDER=1 VENDOR="Generic" '
                                  'FILAMENT_TYPE="PETG" FILAMENT_SUBTYPE="HF" FILAMENT_COLOR_RGBA=112233FF')
        # Official spool only with force
        with pytest.raises(HomeAssistantError, match="force"):
            await hass.services.async_call(DOMAIN, "set_filament", {"slot": 1, "type": "PLA"}, blocking=True)
        await hass.services.async_call(DOMAIN, "set_filament", {"slot": 1, "type": "PLA", "force": True},
                                       blocking=True)
        assert gcode.await_args.args[0].endswith("FORCE=1")
        # Not during a print
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        with pytest.raises(HomeAssistantError, match="during a print"):
            await hass.services.async_call(DOMAIN, "set_filament", {"slot": 2, "type": "PLA"}, blocking=True)
        # Invalid characters never reach the printer
        _status(mock_client)
        await _refresh(hass, entry)
        calls = gcode.await_count
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(DOMAIN, "set_filament", {"slot": 2, "type": "PLA", "vendor": "a;b"},
                                           blocking=True)
        assert gcode.await_count == calls


async def test_camera_wake(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, camera_wake="printing")
    coord = entry.runtime_data
    assert coord._unsub_wake is not None
    with patch(f"{API}.camera_wake", AsyncMock()) as wake:
        coord._camera_wake_tick(None)
        await hass.async_block_till_done()
        wake.assert_not_awaited()  # not printing
        _status(mock_client, "printing", "a.gcode")
        await _refresh(hass, entry)
        coord._camera_wake_tick(None)
        await hass.async_block_till_done()
        wake.assert_awaited_once()


async def test_camera_wake_off_by_default(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    assert entry.runtime_data._unsub_wake is None


async def test_camera_wake_service(hass: HomeAssistant, mock_client, notifications) -> None:
    """Card-requested wake works with the option off and is limited to one call per 5 s."""
    entry = await _setup(hass)
    with patch(f"{API}.camera_wake", AsyncMock()) as wake:
        await hass.services.async_call(DOMAIN, "camera_wake", {}, blocking=True)
        await hass.services.async_call(DOMAIN, "camera_wake", {}, blocking=True)
        wake.assert_awaited_once()
        entry.runtime_data._wake_last -= 10
        await hass.services.async_call(DOMAIN, "camera_wake", {}, blocking=True)
        assert wake.await_count == 2


async def test_archive_limits(hass: HomeAssistant, tmp_path) -> None:
    """Media folder limits: newest N kept, pruned videos are not fetched again."""
    import os
    import time as _time

    from custom_components.snapmaker_u1_card.archive import TimelapseArchive

    folder, cache = tmp_path / "media", tmp_path / "cache"
    folder.mkdir()
    cache.mkdir()
    now = _time.time()
    for i in range(4):
        (folder / f"v{i}.mp4").write_bytes(b"x")
        (folder / f"v{i}.jpg").write_bytes(b"j")
        (cache / f"v{i}.jpg").write_bytes(b"j")
        os.utime(folder / f"v{i}.mp4", (now - i * 86400 * 10, now - i * 86400 * 10))  # v0 newest
    client = AsyncMock()
    arch = TimelapseArchive(client, folder, None)
    assert await arch.prune_archive(hass, 0, 0) == []
    assert sorted(await arch.prune_archive(hass, 2, 0, cache)) == ["v2.mp4", "v3.mp4"]
    assert sorted(p.name for p in folder.iterdir()) == ["v0.jpg", "v0.mp4", "v1.jpg", "v1.mp4"]
    assert sorted(p.name for p in cache.iterdir()) == ["v0.jpg", "v1.jpg"]
    # Age limit: v1 is 10 days old
    assert await arch.prune_archive(hass, 0, 5) == ["v1.mp4"]
    # Still on the printer: not downloaded again, the state survives a restart
    again = TimelapseArchive(client, folder, arch.as_stored())
    saved = await again.backup(hass, [{"root": "camera", "path": "v3.mp4", "size": 1}], tmp_path, None)
    assert saved == [] and client.download_to.await_count == 0


async def test_energy_price_sources(hass: HomeAssistant, mock_client, notifications) -> None:
    """Price entity first, then a fixed price, then the energy dashboard."""
    from custom_components.snapmaker_u1_card.parsing import energy_dashboard_price

    entry = await _setup(hass)  # test setup: price entity at 30 ct/kWh
    assert entry.runtime_data.energy_price_source == (0.3, "sensor.strompreis")
    hass.config_entries.async_update_entry(entry, options={**entry.options, "energy_price": None,
                                                           "energy_price_fixed": 0.29})
    await hass.async_block_till_done()  # options change reloads the entry
    assert entry.runtime_data.energy_price_source == (0.29, "fixed")

    hass.states.async_set("sensor.tarif", "31.5", {"unit_of_measurement": "ct/kWh"})
    prefs = {"energy_sources": [
        {"type": "solar", "stat_energy_from": "x"},
        {"type": "grid", "flow_from": [{"stat_energy_from": "a", "entity_energy_price": "sensor.tarif",
                                        "number_energy_price": None}]},
    ]}
    assert energy_dashboard_price(prefs, hass.states) == (0.315, "sensor.tarif")
    prefs["energy_sources"][1]["flow_from"][0].update(entity_energy_price=None, number_energy_price=0.25)
    assert energy_dashboard_price(prefs, hass.states) == (0.25, "fixed")
    assert energy_dashboard_price({"energy_sources": []}, hass.states) == (None, None)
    assert energy_dashboard_price(None, hass.states) == (None, None)

    class Manager:
        data = prefs
    hass.config_entries.async_update_entry(entry, options={**entry.options, "energy_price_fixed": None})
    await hass.async_block_till_done()
    coord = entry.runtime_data
    coord._energy_manager = Manager()
    assert coord.energy_price_source == (0.25, "energy:fixed")
