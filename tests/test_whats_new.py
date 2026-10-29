"""'What's new' notification after an update to a new minor version."""

from datetime import timedelta

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402

from custom_components.snapmaker_u1_card import whats_new as wn  # noqa: E402
from tests.test_init import mock_client  # noqa: E402,F401
from tests.test_power import _setup, auto_enable, notifications  # noqa: E402,F401


async def test_shown_once_after_update(hass: HomeAssistant) -> None:
    from homeassistant.components import persistent_notification as pn
    shown = []
    orig = pn.async_create
    pn.async_create = lambda h, msg, title=None, notification_id=None: shown.append((title, msg, notification_id))
    try:
        old = dt_util.utcnow() - timedelta(days=30)
        hass.config.language = "de"
        assert await wn.async_show(hass, old, "1.6.1") is True
        title, msg, nid = shown[-1]
        assert title == "Snapmaker U1 Card 1.6 – das ist neu" and nid == "snapmaker_u1_card_whats_new_1.6"
        assert "WebRTC" in msg and "ko-fi.com/ironoxx" in msg and "github.com/Ironoxx" in msg
        # only once per minor version
        assert await wn.async_show(hass, old, "1.6.2") is False
        assert len(shown) == 1
        # next minor version without texts: nothing, but remembered
        assert await wn.async_show(hass, old, "1.7.0") is False
    finally:
        pn.async_create = orig


async def test_not_on_fresh_install_and_english(hass: HomeAssistant) -> None:
    from homeassistant.components import persistent_notification as pn
    shown = []
    orig = pn.async_create
    pn.async_create = lambda h, msg, title=None, notification_id=None: shown.append(title)
    try:
        assert await wn.async_show(hass, dt_util.utcnow(), "1.6.0") is False, "fresh install"
        assert not shown
    finally:
        pn.async_create = orig
    # an existing install in English
    hass2_store = wn.Store(hass, 1, wn.STORE_KEY)
    await hass2_store.async_save({"seen": "1.5"})
    hass.config.language = "en"
    pn.async_create = lambda h, msg, title=None, notification_id=None: shown.append(title)
    try:
        assert await wn.async_show(hass, dt_util.utcnow(), "1.6.0") is True, "seen 1.5 -> update, even if entry is new"
        assert shown == ["Snapmaker U1 Card 1.6 – what's new"]
    finally:
        pn.async_create = orig


async def test_setup_checks_once(hass: HomeAssistant, mock_client) -> None:
    calls = []
    orig = wn.async_show

    async def spy(h, created, version=wn.VERSION):
        calls.append(created)
        return False

    wn.async_show = spy
    try:
        await _setup(hass)
    finally:
        wn.async_show = orig
    assert len(calls) == 1
