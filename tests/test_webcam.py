"""1.5: camera detection (live / still / wake / none) and the own camera entity."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402

from custom_components.snapmaker_u1_card import webcam as wc  # noqa: E402
from custom_components.snapmaker_u1_card.api import MoonrakerClient, MoonrakerError  # noqa: E402
from tests.test_init import mock_client  # noqa: E402,F401
from tests.test_power import _refresh, _setup, auto_enable, notifications  # noqa: E402,F401

pytestmark = pytest.mark.webcam  # real detection logic (conftest stubs it elsewhere)

JPEG_A = b"\xff\xd8AAAA\xff\xd9"
JPEG_B = b"\xff\xd8BBBB\xff\xd9"


def _client() -> MoonrakerClient:
    return MoonrakerClient(None, "192.168.0.25")


def test_resolve_url() -> None:
    c = _client()
    assert c.resolve_url("/webcam/?action=stream") == "http://192.168.0.25/webcam/?action=stream"
    assert c.resolve_url("http://127.0.0.1:8080/stream") == "http://192.168.0.25:8080/stream"
    assert c.resolve_url("http://cam.lan/x") == "http://cam.lan/x"
    assert c.resolve_url("") is None


@pytest.fixture
def no_sleep():
    with patch.object(wc.asyncio, "sleep", AsyncMock()):
        yield


async def test_detect_live(no_sleep) -> None:
    c = _client()
    cam = wc.Webcam(c)
    with patch.object(c, "webcams", AsyncMock(return_value=[{"stream_url": "/webcam/?action=stream",
                                                             "snapshot_url": "/webcam/?action=snapshot"}])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=JPEG_A)):
        assert await cam.detect() == "live"
    assert cam.stream_url == "http://192.168.0.25/webcam/?action=stream"


async def test_detect_still_then_stream_retry(no_sleep) -> None:
    c = _client()
    cam = wc.Webcam(c)
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(return_value=JPEG_A)):
        assert await cam.detect() == "still"
        assert await cam.image() == JPEG_A
    # a broken live stream falls back to still images and blocks the stream for a while
    cam.mode = "live"
    cam.stream_failed()
    assert cam.mode == "still"
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=JPEG_A)) as frame, \
         patch.object(c, "fetch_image", AsyncMock(return_value=JPEG_A)):
        assert await cam.detect() == "still"
        frame.assert_not_awaited()


async def test_detect_stock_wake(no_sleep) -> None:
    c = _client()
    cam = wc.Webcam(c)
    shots = iter([JPEG_A, JPEG_B])
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(return_value=None)), \
         patch.object(c, "camera_wake", AsyncMock()) as wake, \
         patch.object(c, "download", AsyncMock(side_effect=lambda *a, **k: next(shots))):
        assert await cam.detect() == "wake"
        assert wake.await_count >= 1


async def test_detect_stale_monitor_is_none(no_sleep) -> None:
    """An old monitor.jpg that never changes must not count as a working camera."""
    c = _client()
    cam = wc.Webcam(c)
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(return_value=None)), \
         patch.object(c, "camera_wake", AsyncMock()), \
         patch.object(c, "download", AsyncMock(return_value=JPEG_A)):
        assert await cam.detect() == "none"
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(return_value=None)), \
         patch.object(c, "camera_wake", AsyncMock()), \
         patch.object(c, "download", AsyncMock(side_effect=MoonrakerError("404"))):
        assert await cam.detect() == "none"


async def test_wake_rate_limited_and_failures_redetect(no_sleep) -> None:
    c = _client()
    cam = wc.Webcam(c)
    cam.mode = "wake"
    cam.next_check = 1e18
    with patch.object(c, "camera_wake", AsyncMock()) as wake, \
         patch.object(c, "download", AsyncMock(return_value=JPEG_A)):
        await cam.image()
        cam._image = None
        await cam.image()
        assert wake.await_count == 1  # second call within 10 s
    with patch.object(c, "camera_wake", AsyncMock()), \
         patch.object(c, "download", AsyncMock(side_effect=MoonrakerError("x"))):
        for _ in range(wc.FAIL_LIMIT):
            cam._image = None
            await cam.image()
    assert cam.due()


async def test_camera_entity(hass: HomeAssistant, mock_client, notifications) -> None:
    with patch.object(wc.Webcam, "_probe", AsyncMock(return_value=("wake", None, None))):
        entry = await _setup(hass)
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    coord = entry.runtime_data
    assert coord.webcam.mode == "wake"
    ent = next(s for s in hass.states.async_all("camera") if s.entity_id.startswith("camera.snapmaker_u1_card"))
    assert ent.attributes["mode"] == "wake" and ent.state != "unavailable"
    # without a configured camera the own entity serves notification image and result photo
    assert coord.camera_entity() == ent.entity_id
    with patch.object(wc.Webcam, "image", AsyncMock(return_value=JPEG_A)):
        from homeassistant.components.camera import async_get_image
        img = await async_get_image(hass, ent.entity_id)
        assert img.content == JPEG_A
    # nothing found: unavailable, no camera for notifications
    coord.webcam.mode = "none"
    coord.async_update_listeners()
    await hass.async_block_till_done()
    assert hass.states.get(ent.entity_id).state == "unavailable"
    assert coord.camera_entity() is None


async def test_live_stream_falls_back(hass: HomeAssistant, mock_client, notifications) -> None:
    with patch.object(wc.Webcam, "_probe", AsyncMock(return_value=("live", "http://p/s", "http://p/snap"))):
        entry = await _setup(hass)
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
    coord = entry.runtime_data
    from custom_components.snapmaker_u1_card.camera import U1Camera
    cam = U1Camera(coord)
    cam.hass = hass
    cam.entity_id = "camera.test_u1"
    still = AsyncMock(return_value="still-stream")
    with patch.object(coord.client, "open_stream", AsyncMock(side_effect=MoonrakerError("down"))), \
         patch.object(U1Camera, "handle_async_still_stream", still), \
         patch.object(U1Camera, "async_write_ha_state"):
        assert await cam.handle_async_mjpeg_stream(object()) == "still-stream"
    assert coord.webcam.mode == "still"
    still.assert_awaited_once()


async def test_slow_stream_rechecked_soon(no_sleep) -> None:
    """A stream that fails the first check is retried, and still mode re-checks it after 5 min."""
    c = _client()
    cam = wc.Webcam(c)
    frames = AsyncMock(side_effect=[None, JPEG_A])
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", frames):
        assert await cam.detect() == "live"  # second try within the same detection
    assert frames.await_args.kwargs["timeout"] == wc.FIRST_FRAME_S
    cam = wc.Webcam(c)
    with patch.object(c, "webcams", AsyncMock(return_value=[])), \
         patch.object(c, "first_mjpeg_frame", AsyncMock(return_value=None)), \
         patch.object(c, "fetch_image", AsyncMock(return_value=JPEG_A)):
        assert await cam.detect() == "still"
    assert "no MJPEG frame" in cam.stream_error
    remaining = cam.next_check - wc.time.monotonic()
    assert 0 < remaining <= wc.STREAM_RETRY_S + 1, remaining
