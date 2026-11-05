"""Show once in Home Assistant what a new minor version brings.

HACS only offers a link to the release notes in many setups, so after an
update to a new minor version (1.6, 1.7 …) the integration creates one
persistent notification with the highlights. Not on a fresh install, only
once per minor version (stored in .storage), dismissable as usual.

``ANNOUNCEMENTS`` are one-off news independent of the version (e.g. the
integration joined the HACS default list), each shown once, same rules.
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
    "2.0": {
        "de": ("Snapmaker U1 Card 2.0 – das ist neu", f"""**Keine Moonraker-Integration mehr nötig.** Die Integration liest alle Druckerwerte selbst und steuert den Drucker direkt:

- **Werte live vom Drucker:** Temperaturen, Lüfter, Licht, Achsen, Schicht, Fortschritt, MCU- und Systemlast – innerhalb einer Sekunde statt alle 30 s
- **Steuerung über die Integration:** Pause, Fortsetzen, Abbrechen, Not-Halt, Referenzfahrt, Solltemperaturen, Lüfter, Geschwindigkeit, Licht
- **Neue Entitäten** für Temperaturen, Fortschritt, Druckstatus, Schicht, Solltemperaturen, Knöpfe und Licht – plus Dienst `machine_command` für Automationen
- **Einstellungen direkt in der Karte** (System → Einstellungen), übersichtlich mit aktuellen Werten
- **Spoolman:** neue Spule direkt aus der Karte anlegen, Filamentpreise aus Spoolman
- **Kamera unterwegs flüssig** über Home Assistant (RTSP), **Temperaturverlauf** mit Innenraum, Schrittmotortreibern und CPU
- **Kamera-Zoom** geht nach 60 s oder beim Verlassen der Seite zurück
- Die Moonraker-Integration kann deaktiviert werden; wenn sie bleibt, ist sie nur noch Rückfall

Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v2.0.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 2.0 – what's new", f"""**No Moonraker integration needed any more.** The integration reads all printer values itself and controls the printer directly:

- **Live values from the printer:** temperatures, fans, light, axes, layer, progress, MCU and system load – within a second instead of every 30 s
- **Controls through the integration:** pause, resume, cancel, emergency stop, homing, target temperatures, fans, speed, light
- **New entities** for temperatures, progress, print state, layer, targets, buttons and light – plus the service `machine_command` for automations
- **Settings right in the card** (System → Settings), clearly laid out with current values
- **Spoolman:** create a new spool right from the card, filament prices from Spoolman
- **Smooth camera away from home** through Home Assistant (RTSP), **temperature chart** with chamber, stepper drivers and CPU
- **Camera zoom** goes back after 60 s or when you leave the page
- The Moonraker integration can be disabled; if it stays, it is only a fallback

Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v2.0.0)

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
    "2.1": {
        "de": ("Snapmaker U1 Card 2.1 – das ist neu", f"""- **Reiter Spoolman:** alle Spulen mit Restgewicht, Filter und Suche; neue Spule mit Vorschlägen aus Spoolman und dem Spoolman-Katalog
- **Neue Sprachen:** Spanisch, Französisch, Italienisch, Portugiesisch, Niederländisch und Türkisch
- **Deine Währung** aus Home Assistant statt fest €
- **G-Code-Vorschau:** Schichtansicht mit Schiebereglern für Schicht und Fortschritt, Vorschau jeder Datei im Druckdialog
- **Top Cover steuern:** Modus (Leerlauf, Kammer kühlen, vorheizen, heiß) und Kammer-Soll direkt in der Karte und als Entitäten
- **Kammer ist warm:** Benachrichtigung, sobald Kammerheizung oder Top Cover das Soll erreicht (in den Einstellungen einschalten)
- **Luftfilter-Wartung** zählt die echten Filterstunden der Top Cover
- **Temperaturverlauf** mit Panda Breath / DragonBreath
- **Kamera unterwegs:** kein Neustart des Streams mehr, wenn sich die Karte neu aufbaut

Top Cover, Panda Breath und DragonBreath werden automatisch erkannt; ohne sie ändert sich nichts. Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v2.1.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 2.1 – what's new", f"""- **Spoolman tab:** every spool with its remaining weight, filter and search; new spool with suggestions from Spoolman and its catalogue
- **New languages:** Spanish, French, Italian, Portuguese, Dutch and Turkish
- **Your currency** from Home Assistant instead of a fixed €
- **G-code preview:** layer view with sliders for layer and progress, preview of any file in the print dialog
- **Control the top cover:** mode (idle, cool, preheat, hot) and chamber target right in the card and as entities
- **Chamber is warm:** notification once the chamber heater or top cover reaches its target (turn it on in the settings)
- **Air filter maintenance** counts the real filter hours of the top cover
- **Temperature chart** with Panda Breath / DragonBreath
- **Camera away from home:** the stream no longer restarts when the card rebuilds

Top cover, Panda Breath and DragonBreath are detected automatically; without them nothing changes. Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v2.1.0)

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
}

# One-off news, shown once each (key stays in .storage).
ANNOUNCEMENTS: dict[str, dict[str, tuple[str, str]]] = {
    "hacs_default": {
        "de": ("Snapmaker U1 Card ist offiziell in HACS 🎉", f"""Die Integration ist jetzt in der **Standardliste von HACS** aufgenommen.

- Neue Nutzer finden sie direkt über die Suche in HACS (ab Home Assistant 2026.11 unter *Einstellungen → Marketplace*), ohne benutzerdefiniertes Repository.
- Für dich ändert sich nichts: Updates kommen wie bisher über HACS.

Danke an alle, die getestet, Fehler gemeldet und mitgebaut haben!

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card is officially in HACS 🎉", f"""The integration is now part of the **HACS default list**.

- New users find it straight away by searching in HACS (on Home Assistant 2026.11 and newer under *Settings → Marketplace*), no custom repository needed.
- Nothing changes for you: updates keep coming through HACS.

Thanks to everyone who tested, reported bugs and contributed!

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
}


def minor(version: str) -> str:
    return ".".join(version.split(".")[:2])


async def async_show(hass: HomeAssistant, entry_created: object | None, version: str = VERSION) -> bool:
    """Create the notification once per minor version (and each announcement once); True = shown."""
    store: Store = Store(hass, 1, STORE_KEY)
    data = await store.async_load() or {}
    current = minor(version)
    announced = list(data.get("announced") or [])
    pending = [key for key in ANNOUNCEMENTS if key not in announced]
    if data.get("seen") == current and not pending:
        return False
    await store.async_save({"seen": current, "announced": announced + pending})
    # Fresh install (entry just created, nothing seen yet): no "what's new", no news
    created = entry_created if hasattr(entry_created, "tzinfo") else None
    if data.get("seen") is None and created is not None and dt_util.utcnow() - created < timedelta(hours=1):
        return False
    lang = "de" if str(hass.config.language or "").lower().startswith("de") else "en"
    shown = False
    texts = WHATS_NEW.get(current) if data.get("seen") != current else None
    if texts:
        title, message = texts[lang]
        persistent_notification.async_create(hass, message, title=title, notification_id=f"{DOMAIN}_whats_new_{current}")
        shown = True
    for key in pending:
        title, message = ANNOUNCEMENTS[key][lang]
        persistent_notification.async_create(hass, message, title=title, notification_id=f"{DOMAIN}_news_{key}")
        shown = True
    return shown
