"""Load parsing.py and api.py without Home Assistant (both are HA-free)."""

import contextlib
import importlib.util
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "snapmaker_u1_card"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"u1card_{name}", PKG / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


parsing = _load("parsing")
api = _load("api")

try:  # part of the HA test plugin; without HA simply do nothing
    import pytest_socket  # noqa: F401
except ImportError:
    import pytest

    @pytest.fixture
    def socket_enabled():
        return None

# The HA test plugin puts its own testing_config with a regular
# custom_components package in front of sys.path. Importing early keeps
# this repository in the module cache, where the loader finds it.
with contextlib.suppress(ImportError):
    import custom_components.snapmaker_u1_card  # noqa: F401


# The live subscription (live.py) connects in the background and waits between
# attempts; in normal HA tests that would block wait_background_tasks.
# Tests for the subscription opt out with @pytest.mark.live.
try:
    import pytest as _pytest
    from custom_components.snapmaker_u1_card import live as _live
except ImportError:  # without HA
    _live = None
else:
    from custom_components.snapmaker_u1_card import webcam as _webcam

    @_pytest.fixture(autouse=True)
    def _no_live(request, monkeypatch):
        if "live" not in request.keywords:
            monkeypatch.setattr(_live.LiveListener, "start", lambda self, hass: None)
        # Camera detection talks HTTP to the printer; tests opt in with @pytest.mark.webcam
        if "webcam" not in request.keywords:
            async def _no_detect(self):
                self.mode = "none"
                self.next_check = float("inf")
                return "none"
            monkeypatch.setattr(_webcam.Webcam, "detect", _no_detect)
        yield


def pytest_configure(config):
    config.addinivalue_line("markers", "live: keep the live subscription enabled")
    config.addinivalue_line("markers", "webcam: keep the camera detection enabled")
