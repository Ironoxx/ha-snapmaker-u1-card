"""File inspector: slicer settings read from the end of the G-code."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.exceptions import HomeAssistantError  # noqa: E402

from tests.test_init import API, DOMAIN, mock_client  # noqa: E402,F401
from tests.test_parsing import ORCA_TAIL  # noqa: E402
from tests.test_power import _setup, auto_enable, notifications  # noqa: E402,F401


async def test_file_settings_service(hass: HomeAssistant, mock_client) -> None:
    await _setup(hass)
    with patch(f"{API}.read_tail", AsyncMock(return_value=ORCA_TAIL.encode())) as tail:
        res = await hass.services.async_call(DOMAIN, "file_settings", {"path": "sub/new.gcode"},
                                             blocking=True, return_response=True)
        assert res["settings"]["layer_height"] == 0.2 and res["settings"]["infill"] == 15
        assert tail.await_args.args[0] == "sub/new.gcode"
        # cached per file version
        await hass.services.async_call(DOMAIN, "file_settings", {"path": "sub/new.gcode"},
                                       blocking=True, return_response=True)
        assert tail.await_count == 1
    with pytest.raises(HomeAssistantError, match="does not exist"):
        await hass.services.async_call(DOMAIN, "file_settings", {"path": "nope.gcode"},
                                       blocking=True, return_response=True)


async def test_read_tail_with_and_without_range() -> None:
    from custom_components.snapmaker_u1_card.api import MoonrakerClient

    class Resp:
        def __init__(self, status, body):
            self.status, self.body = status, body
            self.content = self

        async def read(self):
            return self.body

        async def iter_chunked(self, n):
            for i in range(0, len(self.body), n):
                yield self.body[i:i + n]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class Session:
        def __init__(self, resp):
            self.resp, self.headers = resp, None

        def get(self, url, headers=None, timeout=None):
            self.headers = headers
            return self.resp

    body = bytes(range(256)) * 4000  # ~1 MB
    s = Session(Resp(206, body[-1000:]))
    assert await MoonrakerClient(s, "h").read_tail("a.gcode", 1000) == body[-1000:]
    assert s.headers["Range"] == "bytes=-1000"
    # server ignores Range: streams the file, keeps only the end
    s = Session(Resp(200, body))
    assert await MoonrakerClient(s, "h").read_tail("a.gcode", 1000) == body[-1000:]
