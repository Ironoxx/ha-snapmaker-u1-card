"""Status-light blueprint: shipped, valid and working."""

import asyncio
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import async_fire_time_changed, async_mock_service  # noqa: E402

from custom_components.snapmaker_u1_card import blueprints as bp  # noqa: E402
from tests.test_init import mock_client  # noqa: E402,F401
from tests.test_power import _setup, auto_enable, notifications  # noqa: E402,F401

SRC = Path(bp.__file__).parent / "blueprints" / "status_light.yaml"
STATE = "sensor.snapmaker_u1_current_print_state"


async def test_blueprint_installed_and_updated(hass: HomeAssistant, mock_client) -> None:
    await _setup(hass)
    await hass.async_block_till_done()
    dst = Path(hass.config.path("blueprints", "automation", "snapmaker_u1_card", "status_light.yaml"))
    assert dst.read_text() == SRC.read_text()
    # older managed copy -> replaced; own edit without the marker -> kept
    dst.write_text("# managed: snapmaker_u1_card\nold")
    await bp.async_install(hass)
    assert dst.read_text() == SRC.read_text()
    dst.write_text("# my own version")
    await bp.async_install(hass)
    assert dst.read_text() == "# my own version"


async def test_status_light_automation(hass: HomeAssistant) -> None:
    target = Path(hass.config.path("blueprints", "automation", "snapmaker_u1_card"))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC, target / "status_light.yaml")
    on = async_mock_service(hass, "light", "turn_on")
    off = async_mock_service(hass, "light", "turn_off")
    hass.states.async_set(STATE, "standby")
    assert await async_setup_component(hass, "automation", {"automation": [{
        "id": "u1light",
        "use_blueprint": {"path": "snapmaker_u1_card/status_light.yaml", "input": {
            "state_sensor": STATE, "lights": {"entity_id": "light.regal"}, "complete_minutes": 1,
            "effect_printing": "Breathe"}},
    }]})
    await hass.async_block_till_done()
    assert hass.states.get("automation.snapmaker_u1_status_light") or hass.states.async_entity_ids("automation")

    hass.states.async_set(STATE, "printing")
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [0, 120, 255] and on[-1].data["effect"] == "Breathe"
    assert on[-1].data["brightness_pct"] == 80
    hass.states.async_set(STATE, "paused")
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [255, 170, 0] and "effect" not in on[-1].data
    hass.states.async_set(STATE, "error")
    await hass.async_block_till_done()
    assert on[-1].data["rgb_color"] == [255, 0, 0]
    hass.states.async_set(STATE, "complete")
    for _ in range(20):  # the run waits in its delay: do not block on it
        await asyncio.sleep(0)
    assert on[-1].data["rgb_color"] == [0, 200, 60]
    assert not off
    # after the "finished" time: off
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()
    assert len(off) == 1
    # finished, then the printer goes to standby: "finished" stays for the rest of the time
    hass.states.async_set(STATE, "printing")
    await hass.async_block_till_done()
    hass.states.async_set(STATE, "complete")
    for _ in range(20):
        await asyncio.sleep(0)
    hass.states.async_set(STATE, "standby")
    for _ in range(20):
        await asyncio.sleep(0)
    assert len(off) == 1, "not off right away"
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()
    assert len(off) == 2
