"""2.4.2: a name per printer.

Before 2.4.2 every printer's device was called "Snapmaker U1 Card", so with several U1
the device list, entity pickers and notifications looked the same for all of them.

* One printer and the default entry title: the device keeps "Snapmaker U1 Card".
* Several printers, or an entry renamed in Home Assistant: the device takes the
  entry's title ("Snapmaker U1 (192.168.1.50)" or e.g. "Werkstatt"). Renaming the
  entry reloads it (update listener), so the device follows.
* A name the user gave the device itself (``name_by_user``) always wins – Home
  Assistant shows that one and this module never touches it.

Entity IDs must not follow the device name (dashboards, automations and the docs use
``snapmaker_u1_card_…``). See ``U1Entity.add_to_platform_start``: new entities suggest
the ID they would have got with the old device name; existing ones keep theirs anyway.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

DEFAULT_DEVICE_NAME = "Snapmaker U1 Card"


def default_title(entry: ConfigEntry) -> str:
    """Title the config flow gives a new entry."""
    return f"Snapmaker U1 ({entry.data.get(CONF_HOST)})"


def device_name(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Device name for this printer (see the module doc)."""
    title = (entry.title or "").strip()
    if title and title != default_title(entry):
        return title  # renamed by the user
    others = [e for e in hass.config_entries.async_entries(DOMAIN)
              if e.entry_id != entry.entry_id and e.disabled_by is None]
    return (title or default_title(entry)) if others else DEFAULT_DEVICE_NAME


def several_printers(hass: HomeAssistant) -> bool:
    """More than one printer set up (enabled entries)."""
    return len([e for e in hass.config_entries.async_entries(DOMAIN) if e.disabled_by is None]) > 1


@callback
def async_refresh_device_names(hass: HomeAssistant) -> None:
    """Bring every printer's device name up to date, e.g. after a second printer was added.

    Only the integration's own name changes; entity IDs and ``name_by_user`` stay.
    """
    reg = dr.async_get(hass)
    for entry in hass.config_entries.async_entries(DOMAIN):
        device = reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
        name = device_name(hass, entry)
        if device is not None and device.name != name:
            reg.async_update_device(device.id, name=name)
