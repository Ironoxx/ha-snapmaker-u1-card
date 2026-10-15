"""Tiny helper for backend texts that reach the user (errors, notifications).

The card and the config flow are translated through the frontend. Messages
created in Python (service errors, push notifications) follow the Home
Assistant language instead: German for ``de*``, English for everything else.
"""

from __future__ import annotations

from typing import Any


def is_german(hass: Any) -> bool:
    """True if Home Assistant runs in German."""
    lang = getattr(getattr(hass, "config", None), "language", None) or "en"
    return str(lang).lower().startswith("de")


def tr(hass: Any, de: str, en: str) -> str:
    """Pick the German or English variant of a message."""
    return de if is_german(hass) else en
