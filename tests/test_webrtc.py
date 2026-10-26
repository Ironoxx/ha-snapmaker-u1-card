"""WebRTC relay view for the paxx12 camera (signalling only)."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402

from custom_components.snapmaker_u1_card.api import MoonrakerError  # noqa: E402
from tests.test_init import mock_client  # noqa: E402,F401
from tests.test_power import _refresh, _setup, auto_enable, notifications  # noqa: E402,F401


async def test_webrtc_relay_view(hass: HomeAssistant, mock_client, hass_client, hass_client_no_auth) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    url = f"/api/snapmaker_u1_card/webrtc/{entry.entry_id}"
    client = await hass_client()
    # no WebRTC camera found
    resp = await client.post(url, json={"type": "request"})
    assert resp.status == 404
    coord.webcam.webrtc_url = "http://192.168.0.25/webcam/webrtc"
    await _refresh(hass, entry)
    assert hass.states.get("sensor.snapmaker_u1_card_print_files").attributes["webrtc"] is True
    sent = []

    async def signal(target, body):
        sent.append((target, body))
        return {"type": "offer", "id": "x", "sdp": "v=0"}

    with patch.object(coord.client, "webrtc_signal", side_effect=signal):
        resp = await client.post(url, json={"type": "request", "iceServers": []})
        assert resp.status == 200 and (await resp.json())["id"] == "x"
        assert sent == [("http://192.168.0.25/webcam/webrtc", {"type": "request", "keepAlive": True, "iceServers": []})]
        assert (await client.post(url, json={"type": "control"})).status == 400
        assert (await client.post(url, data="kein json")).status == 400
    with patch.object(coord.client, "webrtc_signal", AsyncMock(side_effect=MoonrakerError("weg"))):
        assert (await client.post(url, json={"type": "request"})).status == 502
    assert (await client.post("/api/snapmaker_u1_card/webrtc/nope", json={"type": "request"})).status == 404
    anon = await hass_client_no_auth()
    assert (await anon.post(url, json={"type": "request"})).status == 401
