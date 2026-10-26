"""Ship the blueprints with the integration.

HACS installs integrations only, so the status-light blueprint is copied to
``config/blueprints/automation/snapmaker_u1_card/`` at start. A copy that is
still marked as managed is replaced when a newer one ships; remove the
``managed`` line from the file to keep your own edits.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
BLUEPRINTS = ("status_light.yaml",)
MANAGED = "managed: snapmaker_u1_card"


def _copy(src: Path, dst: Path) -> bool:
    new = src.read_text(encoding="utf-8")
    if dst.exists():
        old = dst.read_text(encoding="utf-8")
        if old == new or MANAGED not in old:
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
            if await hass.async_add_executor_job(_copy, here / name, target / name):
                _LOGGER.info("Blueprint %s installed in %s", name, target)
        except OSError as err:
            _LOGGER.warning("Blueprint %s could not be installed: %s", name, err)
