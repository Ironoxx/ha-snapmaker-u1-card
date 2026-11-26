"""2.4.2: own device name per printer, entity IDs unchanged."""

from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers import device_registry as dr  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402
from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: E402

from tests.test_init import DOMAIN, auto_enable, mock_client  # noqa: E402,F401


async def _add(hass: HomeAssistant, host: str, title: str | None = None) -> MockConfigEntry:
    assert await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, data={"host": host, "port": 80}, unique_id=host,
                            title=title or f"Snapmaker U1 ({host})")
    entry.add_to_hass(hass)
    with patch("custom_components.snapmaker_u1_card.add_extra_js_url"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _device(hass: HomeAssistant, entry) -> dr.DeviceEntry:
    return dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})


async def test_one_printer_keeps_the_name(hass: HomeAssistant, mock_client) -> None:
    entry = await _add(hass, "192.0.2.10")
    assert _device(hass, entry).name == "Snapmaker U1 Card"
    assert hass.states.get("sensor.snapmaker_u1_card_filaments") is not None


async def test_renamed_entry_names_the_device_ids_stay(hass: HomeAssistant, mock_client) -> None:
    """A fresh entry with an own title: device "Werkstatt", entity IDs as before 2.4.2."""
    entry = await _add(hass, "192.0.2.10", title="Werkstatt")
    assert _device(hass, entry).name == "Werkstatt"
    st = hass.states.get("sensor.snapmaker_u1_card_filaments")
    assert st is not None and st.name.startswith("Werkstatt")
    assert hass.states.get("camera.snapmaker_u1_card_camera") is not None


async def test_second_printer_both_named_after_their_entry(hass: HomeAssistant, mock_client) -> None:
    first = await _add(hass, "192.0.2.10")
    second = await _add(hass, "192.0.2.11")
    assert _device(hass, first).name == "Snapmaker U1 (192.0.2.10)", "renamed when the second came"
    assert _device(hass, second).name == "Snapmaker U1 (192.0.2.11)"
    # IDs of the first unchanged, the second gets _2 as before
    assert hass.states.get("sensor.snapmaker_u1_card_filaments") is not None
    assert hass.states.get("sensor.snapmaker_u1_card_filaments_2") is not None
    # a name the user gave the device stays
    reg = dr.async_get(hass)
    reg.async_update_device(_device(hass, first).id, name_by_user="Links")
    await hass.config_entries.async_reload(first.entry_id)
    await hass.async_block_till_done()
    assert _device(hass, first).name_by_user == "Links"


async def test_notification_title_names_the_printer(hass: HomeAssistant, mock_client) -> None:
    await _add(hass, "192.0.2.10")
    second = await _add(hass, "192.0.2.11", title="Werkstatt")
    calls = []

    async def handler(call) -> None:
        calls.append(call)

    hass.services.async_register("notify", "mobile_app_handy", handler)
    coord = second.runtime_data
    with patch.object(type(coord), "_notify_targets", return_value=[("mobile_app_handy", None)]):
        coord._notify("first_layer", {"name": "Box"})
        await hass.async_block_till_done()
    assert calls and calls[0].data["title"].startswith("Werkstatt:")
