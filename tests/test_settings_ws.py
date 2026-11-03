"""Settings in the card (2.0): options over the websocket, same validation as the options flow."""

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402

from tests.test_init import DOMAIN, mock_client  # noqa: E402,F401
from tests.test_power import SWITCH, _setup, auto_enable  # noqa: E402,F401


async def test_settings_get_and_set(hass: HomeAssistant, hass_ws_client, mock_client) -> None:
    entry = await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/settings/get", "language": "de"})
    res = await ws.receive_json()
    assert res["success"], res
    r = res["result"]
    fields = {f["key"]: f for f in r["fields"]}
    assert fields["power_switch"]["type"] == "entity" and "switch" in fields["power_switch"]["domains"]
    assert fields["power_sensor"].get("device_class") == "power"
    assert fields["auto_off_temp"]["type"] == "number" and fields["auto_off_temp"]["unit"] == "°C"
    assert fields["auto_off"]["type"] == "boolean"
    assert fields["notify_events"]["type"] == "select" and fields["notify_events"]["multiple"]
    assert fields["live_notify_image"]["option_labels"]["camera"] != "camera", "translated option labels"
    assert r["sections"]["filament"]["name"] == "Filamentpreise"
    assert fields["price_pla"]["label"] == "PLA"
    assert r["values"]["power"]["power_switch"] == SWITCH
    assert r["values"]["filament"]["price_pla"] == 20.0

    # change two values, remove a price
    await ws.send_json({"id": 2, "type": f"{DOMAIN}/settings/set", "values": {
        "power": {"auto_off_temp": 45}, "filament": {"price_pla": 22.5, "price_petg": None}}})
    res = await ws.receive_json()
    assert res["success"], res
    assert res["result"]["changed"] is True
    await hass.async_block_till_done()
    assert entry.options["auto_off_temp"] == 45 and isinstance(entry.options["auto_off_temp"], int)
    assert entry.options["filament_prices"] == {"PLA": 22.5}
    assert entry.options["power_switch"] == SWITCH, "untouched values stay"

    # same validation as the options flow
    await ws.send_json({"id": 3, "type": f"{DOMAIN}/settings/set", "values": {
        "power": {"power_switch": None, "auto_off": True}}})
    res = await ws.receive_json()
    assert not res["success"] and res["error"]["code"] == "auto_needs_switch"
    await ws.send_json({"id": 4, "type": f"{DOMAIN}/settings/set", "values": {"power": {"auto_off_temp": 500}}})
    res = await ws.receive_json()
    assert not res["success"] and res["error"]["code"] == "invalid"
    assert entry.options["auto_off_temp"] == 45


async def test_settings_admin_only(hass: HomeAssistant, hass_ws_client, hass_read_only_access_token,
                                   mock_client) -> None:
    await _setup(hass)
    ws = await hass_ws_client(hass, hass_read_only_access_token)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/settings/get"})
    res = await ws.receive_json()
    assert not res["success"] and res["error"]["code"] == "unauthorized"
