"""Laedt parsing.py und api.py ohne Home Assistant (beide sind HA-frei)."""

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

try:  # im HA-Testplugin enthalten; ohne HA einfach nichts tun
    import pytest_socket  # noqa: F401
except ImportError:
    import pytest

    @pytest.fixture
    def socket_enabled():
        return None

# Das HA-Testplugin haengt beim Start eine eigene testing_config mit einem
# regulaeren custom_components-Paket vor sys.path. Frueh importiert bleibt
# dieses Repository im Modul-Cache und wird vom Loader gefunden.
with contextlib.suppress(ImportError):
    import custom_components.snapmaker_u1_card  # noqa: F401


# Das Live-Abo (live.py) verbindet sich im Hintergrund und wartet zwischen den
# Versuchen; in den normalen HA-Tests wuerde das wait_background_tasks blockieren.
# Tests fuer das Abo markieren sich mit @pytest.mark.live.
try:
    import pytest as _pytest
    from custom_components.snapmaker_u1_card import live as _live
except ImportError:  # ohne HA
    _live = None
else:
    @_pytest.fixture(autouse=True)
    def _no_live(request, monkeypatch):
        if "live" not in request.keywords:
            monkeypatch.setattr(_live.LiveListener, "start", lambda self, hass: None)
        yield


def pytest_configure(config):
    config.addinivalue_line("markers", "live: Live-Abo nicht abschalten")
