"""Show once in Home Assistant what a new minor version brings.

HACS only offers a link to the release notes in many setups, so after an
update to a new minor version (1.6, 1.7 …) the integration creates one
persistent notification with the highlights. Not on a fresh install, only
once per minor version (stored in .storage), dismissable as usual.
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, VERSION

STORE_KEY = f"{DOMAIN}.whats_new"
GITHUB = "https://github.com/Ironoxx/ha-snapmaker-u1-card"
KOFI = "https://ko-fi.com/ironoxx"

WHATS_NEW: dict[str, dict[str, tuple[str, str]]] = {
    "1.6": {
        "de": ("Snapmaker U1 Card 1.6 – das ist neu", f"""Das bisher größte Update der Integration:

- **Maschine steuern:** Flussrate, Bed-Mesh-Heatmap, G-Code-Konsole, Köpfe aufnehmen/ablegen, Top Cover und Kammerheizung, Düse je Kopf mit Warnung im Druckdialog
- **Sofortige Rückmeldung** bei Pause, Fortsetzen, Abbrechen und Licht
- **Kamera:** WebRTC direkt in der Karte (paxx12), RTSP automatisch, zweite Kamera
- **Spoolman:** SpoolLink ohne Doppelbuchung, Filament der Spule wird geladen (auch mehrfarbig), vorher → nachher je Druck, Spule wiegen, letzte Spule nach dem Neu-Einlegen mit einem Tipp
- **Slicer-Einstellungen** im Druckdialog
- **Wartung in Monaten** mit Push
- **Blueprint Status-Licht** (WLED oder jede Farblampe) und **eigene Akzentfarbe** für die Karte

Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v1.6.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 1.6 – what's new", f"""The biggest update of the integration so far:

- **Control the machine:** flow, bed mesh heatmap, G-code console, pick and park heads, top cover and chamber heater, nozzle per head with a warning in the print dialog
- **Instant feedback** for pause, resume, cancel and the light
- **Camera:** WebRTC right in the card (paxx12), RTSP detected automatically, second camera
- **Spoolman:** SpoolLink without double booking, a chosen spool loads its filament (multi-colour too), before → after per print, weigh a spool, previous spool back after reloading with one tap
- **Slicer settings** in the print dialog
- **Maintenance in months** with a push
- **Status light blueprint** (WLED or any colour light) and an **own accent colour** for the card

Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v1.6.0)

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
}


def minor(version: str) -> str:
    return ".".join(version.split(".")[:2])


async def async_show(hass: HomeAssistant, entry_created: object | None, version: str = VERSION) -> bool:
    """Create the notification once per minor version; True = shown."""
    store: Store = Store(hass, 1, STORE_KEY)
    data = await store.async_load() or {}
    current = minor(version)
    if data.get("seen") == current:
        return False
    await store.async_save({"seen": current})
    # Fresh install (entry just created, nothing seen yet): no "what's new"
    created = entry_created if hasattr(entry_created, "tzinfo") else None
    if data.get("seen") is None and created is not None and dt_util.utcnow() - created < timedelta(hours=1):
        return False
    texts = WHATS_NEW.get(current)
    if not texts:
        return False
    title, message = texts["de" if str(hass.config.language or "").lower().startswith("de") else "en"]
    persistent_notification.async_create(hass, message, title=title, notification_id=f"{DOMAIN}_whats_new_{current}")
    return True
