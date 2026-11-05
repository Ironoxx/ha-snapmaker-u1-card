"""paxx12 display mirror: detection apart from the cameras, picture and touch relay."""

import struct
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402

from custom_components.snapmaker_u1_card import screen as sc  # noqa: E402
from custom_components.snapmaker_u1_card import webcam as wc  # noqa: E402
from custom_components.snapmaker_u1_card.api import MoonrakerClient, MoonrakerError  # noqa: E402
from tests.test_init import mock_client  # noqa: E402,F401
from tests.test_power import _refresh, _setup, auto_enable, notifications  # noqa: E402,F401
from tests.test_webcam import no_rtsp, no_sleep  # noqa: E402,F401


def _png(width: int = 480, height: int = 320) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"


GUI = {"name": "gui", "stream_url": "/screen/", "snapshot_url": "/screen/snapshot"}
CASE = {"name": "case", "stream_url": "/webcam/stream.mjpg", "snapshot_url": "/webcam/snapshot.jpg"}


def test_helpers() -> None:
    assert sc.is_screen(GUI)
    assert sc.is_screen({"snapshot_url": "http://192.168.0.25/screen/snapshot?t=1"})
    assert not sc.is_screen(CASE)
    assert sc.png_size(_png(800, 480)) == (800, 480)
    assert sc.png_size(b"\xff\xd8jpeg") is None
    assert sc.png_size(None) is None


@pytest.mark.screen
async def test_detect_and_touch_rules() -> None:
    c = MoonrakerClient(None, "192.168.0.25")
    mirror = sc.ScreenMirror(c)
    # listed with an absolute URL to another host: touches still only go to the configured printer
    other = {"name": "gui", "snapshot_url": "http://10.0.0.9/screen/snapshot"}
    with patch.object(c, "webcams", AsyncMock(return_value=[CASE, other])), \
         patch.object(c, "fetch_image", AsyncMock(return_value=_png())) as fetch:
        assert await mirror.detect() == (480, 320)
    fetch.assert_awaited_once_with("http://192.168.0.25/screen/snapshot", timeout=3)
    assert mirror.touch_url == "http://192.168.0.25/screen/touch"
    assert not mirror.due()

    # inside the panel only
    assert mirror.clean_touch({"a": "down", "x": 0, "y": 0}) == ("down", 0, 0)
    assert mirror.clean_touch({"a": "up", "x": 479, "y": 319}) == ("up", 479, 319)
    for bad in ({"a": "down", "x": 480, "y": 1}, {"a": "down", "x": 1, "y": 320}, {"a": "down", "x": -1, "y": 1},
                {"a": "tap", "x": 1, "y": 1}, {"a": "down", "x": "1", "y": 1}, {"a": "down", "x": True, "y": 1},
                {"a": "down", "x": 1}, ["down", 1, 1], None):
        assert mirror.clean_touch(bad) is None, bad

    # rate limit: a burst passes, a flood does not, the bucket refills
    with patch.object(sc.time, "monotonic", return_value=1000.0):
        mirror._tokens, mirror._tokens_at = float(sc.TOUCH_BURST), 1000.0
        assert all(mirror.allow_touch() for _ in range(sc.TOUCH_BURST))
        assert not mirror.allow_touch()
    with patch.object(sc.time, "monotonic", return_value=1000.5):
        assert mirror.allow_touch()

    # no PNG (stock firmware): no mirror, looked at again later
    mirror = sc.ScreenMirror(c)
    with patch.object(c, "webcams", AsyncMock(return_value=[CASE])), \
         patch.object(c, "fetch_image", AsyncMock(return_value=None)):
        assert await mirror.detect() is None
    assert mirror.clean_touch({"a": "down", "x": 1, "y": 1}) is None
    assert mirror.next_check < float("inf")


@pytest.mark.webcam
async def test_mirror_is_no_camera(no_sleep, no_rtsp) -> None:
    """The mirror is listed as second webcam, but Camera 2 stays a real (USB) camera."""
    c = MoonrakerClient(None, "192.168.0.25")

    async def image(url, timeout=5):
        return _png() if "/screen/" in url else None

    cam2 = wc.Webcam(c, second=True)
    with patch.object(c, "webcams", AsyncMock(return_value=[CASE, GUI])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(side_effect=image)):
        assert await cam2.detect() == "none"


async def test_screen_views(hass: HomeAssistant, mock_client, hass_client, hass_client_no_auth,
                            hass_read_only_access_token) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    base = f"/api/snapmaker_u1_card/screen/{entry.entry_id}"
    files = "sensor.snapmaker_u1_card_print_files"
    client = await hass_client()
    down = {"a": "down", "x": 10, "y": 20}

    # no mirror: nothing to show or touch
    assert hass.states.get(files).attributes["screen"] is None
    assert (await client.get(f"{base}/snapshot")).status == 404
    assert (await client.post(f"{base}/touch", json=down)).status == 404

    coord.screen.size = (480, 320)
    await _refresh(hass, entry)
    assert hass.states.get(files).attributes["screen"] == {"width": 480, "height": 320}

    # fresh picture, never cached
    with patch.object(coord.client, "fetch_image", AsyncMock(return_value=_png())) as fetch:
        resp = await client.get(f"{base}/snapshot")
        assert resp.status == 200 and await resp.read() == _png()
        assert resp.headers["Content-Type"] == "image/png"
        assert resp.headers["Cache-Control"] == "no-store"
        fetch.assert_awaited_with("http://192.0.2.10/screen/snapshot", timeout=3)
    with patch.object(coord.client, "fetch_image", AsyncMock(return_value=None)):
        assert (await client.get(f"{base}/snapshot")).status == 502

    # touches: validated against the panel, relayed to the configured printer
    with patch.object(coord.client, "screen_touch", AsyncMock()) as touch:
        assert (await client.post(f"{base}/touch", json=down)).status == 200
        touch.assert_awaited_once_with("http://192.0.2.10/screen/touch", "down", 10, 20)
        assert (await client.post(f"{base}/touch", json={"a": "down", "x": 480, "y": 1})).status == 400
        assert (await client.post(f"{base}/touch", data="kein json")).status == 400
        with patch.object(coord.screen, "allow_touch", return_value=False):
            assert (await client.post(f"{base}/touch", json=down)).status == 429
    with patch.object(coord.client, "screen_touch", AsyncMock(side_effect=MoonrakerError("weg"))):
        assert (await client.post(f"{base}/touch", json=down)).status == 502
    assert (await client.get("/api/snapmaker_u1_card/screen/nope/snapshot")).status == 404

    # touch is admin only, the picture is not; nothing without login
    read_only = await hass_client(hass_read_only_access_token)
    assert (await read_only.post(f"{base}/touch", json=down)).status == 403
    with patch.object(coord.client, "fetch_image", AsyncMock(return_value=_png())):
        assert (await read_only.get(f"{base}/snapshot")).status == 200
    anon = await hass_client_no_auth()
    assert (await anon.get(f"{base}/snapshot")).status == 401
    assert (await anon.post(f"{base}/touch", json=down)).status == 401
