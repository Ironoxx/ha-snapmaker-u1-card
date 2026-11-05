"""Ship the blueprints with the integration.

HACS installs integrations only, so the status-light blueprint is copied to
``config/blueprints/automation/snapmaker_u1_card/`` at start. An existing file
is only replaced when it is exactly a version this integration shipped
earlier (by SHA-256): your own edits are never overwritten.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
BLUEPRINTS = ("status_light.yaml",)
# SHA-256 of every version shipped so far; add the new hash when a blueprint changes
# (a test checks that the current file is listed).
SHIPPED = {
    "status_light.yaml": {
        "617d453738dbd201fdd312a2dc2d70e37b9fcd093b51f82a8bd2eeaafcba5a04",
        "80c32a7aafd09ac2d9dcd18c4a6b65a093a561425e49e839020b05fde68c43bc",
        "e080a374f83e8569af6d9df96d7a3c96a54d47a06863bfcd745935e5f19f8346",
    },
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _copy(src: Path, dst: Path, shipped: set[str]) -> bool:
    """Write dst if missing or an untouched earlier version; True if written."""
    new = src.read_text(encoding="utf-8")
    if dst.exists():
        old = dst.read_text(encoding="utf-8")
        if old == new or sha256(old) not in shipped:
            return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(new, encoding="utf-8")
    return True


async def async_install(hass: HomeAssistant) -> None:
    """Copy (or update) the blueprints; never fails the setup."""
    here = Path(__file__).parent / "blueprints"
    target = Path(hass.config.path("blueprints", "automation", DOMAIN))
    for name in BLUEPRINTS:
        try:
            if await hass.async_add_executor_job(_copy, here / name, target / name, SHIPPED.get(name, set())):
                _LOGGER.info("Blueprint %s installed in %s", name, target)
        except OSError as err:
            _LOGGER.warning("Blueprint %s could not be installed: %s", name, err)
