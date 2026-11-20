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
    "2.2": {
        "de": ("Snapmaker U1 Card 2.2 – das ist neu", f"""- **Bausteine:** neue Karte *Snapmaker U1 – Bereich* – Kamera, Druckauftrag, Köpfe, Bettnivellierung, Meldungen … als eigene Karten im Abschnitte-Dashboard
- **Maschinenstatus:** Kalibrierung, Laden/Entladen, Firmware-Update und Störungen im Status; Auto-Aus schaltet während einer Kalibrierung nicht mehr ab
- **Laden/Entladen mit Prüfung:** Knöpfe nur, wenn es klappen kann, mit Begründung; danach wird der Sensor im Kopf geprüft
- **paxx12** wird erkannt, mit Version und Update-Vergleich
- **Übersicht:** Druckerdisplay in echter Größe, Slicer-Vorschau im Druck, Füllstand der Spulen, Verbrauch des letzten Drucks je Kopf
- **Bedienung:** Schnellwahl 85/100/115 %, Höhenwerte in der Bettnivellierung, größere Knöpfe, einheitlichere Schrift

Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v2.2.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 2.2 – what's new", f"""- **Building blocks:** new card *Snapmaker U1 – Section* – camera, print job, heads, bed mesh, messages … as cards of their own in a sections dashboard
- **Machine state:** calibration, loading/unloading, firmware update and faults in the status; auto-off no longer switches off during a calibration
- **Load/unload with checks:** buttons only when it can work, with the reason; the head sensor is checked afterwards
- **paxx12** is detected, with version and update comparison
- **Overview:** printer display at its real size, slicer preview in the print, spool fill levels, usage of the last print per head
- **Controls:** quick buttons 85/100/115 %, heights in the bed mesh, bigger buttons, more even type

Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v2.2.0)

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
    "2.3": {
        "de": ("Snapmaker U1 Card 2.3 – das ist neu", f"""- **Kopf verfahren:** Steuerkreuz für X/Y/Z mit 0,1 / 1 / 10 / 50 mm, „Kopf nach vorne“ und „Mitte“ (Steuerungs-Reiter, Dienst `move`)
- **Zweite Benachrichtigungsgruppe:** eigene Ziele und Anlässe, unter Android mit eigenem Ton (Einstellungen → Benachrichtigungen – Gruppe 2)
- **Fortschritt** zählt nur den G-Code – kein Start bei 1 % mehr wegen der Vorschaubilder
- **Spoolman:** Abbuchung je Spule richtig erkannt; Spulen, die Moonraker nicht bucht, bucht die Integration
- **Druckermeldungen** auch auf Spanisch, Französisch, Italienisch, Niederländisch, Portugiesisch und Türkisch, dazu ein Verlauf im System-Reiter
- **Vereinfachtes Chinesisch** für die Karte (danke HYYYQZ)
- **Status-Licht-Blueprint:** Pulsieren und Ton am Druckende
- **paxx12:** WLAN-Signal und eMMC-Verschleiß als Diagnose-Sensoren
- Füllstand der Spulen auch in der Mini-Karte und im Druckdialog

Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v2.3.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 2.3 – what's new", f"""- **Move the head:** X/Y/Z pad with 0.1 / 1 / 10 / 50 mm, "head to the front" and "center" (control tab, service `move`)
- **Second notification group:** own targets and events, on Android with its own sound (settings → Notifications – group 2)
- **Progress** counts the G-code only – no more start at 1 % because of the thumbnails
- **Spoolman:** booking per spool detected correctly; spools Moonraker does not book are booked by the integration
- **Printer messages** also in Spanish, French, Italian, Dutch, Portuguese and Turkish, plus a history in the system tab
- **Simplified Chinese** for the card (thanks HYYYQZ)
- **Status light blueprint:** pulse and sound at the end of a print
- **paxx12:** WLAN signal and eMMC wear as diagnostic sensors
- Spool fill level also in the mini card and the print dialog

Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v2.3.0)

⭐ [Project on GitHub]({GITHUB}) · ☕ [Coffee on Ko-fi]({KOFI})"""),
    },
    "2.4": {
        "de": ("Snapmaker U1 Card 2.4 – das ist neu", f"""- **Geführte Einrichtung** Schritt für Schritt (Strom, Benachrichtigungen, Spoolman)
- **Dashboard-Vorlagen:** Voll, Minimal oder Wartung & Diagnose per Knopf (Karte → Einstellungen)
- **Uhr und eigene Knöpfe** in der großen Karte (Karten-Editor, Standard aus); Knöpfe mit Home-Assistant-Aktionen, je nach Druckphase sichtbar
- **Licht-Knopf** schaltet auf Wunsch weitere Lampen mit (z. B. WLED)
- **Druckereignis-Entität** für eigene Automationen (fertig, Pause, Fehler, Spule leer …)
- **Mini-Karte** kompakt wie die Kachel-Karte: Symbol = Netzschalter, wechselnde Infozeile
- **Selbsttest** prüft mehr: Netzschalter, Spule je Kopf, Uhrzeit des Druckers, Wartung, paxx12, Blueprint
- **paxx12-Einstellungen** zum Ansehen in den Karten-Einstellungen
- **Kollidierende Kartennamen** (andere Karte „snapmaker-u1-card“) erscheinen unter Reparaturen
- **Spoolman-Reiter:** Spulen bearbeiten, archivieren, wiederherstellen und löschen, in einen Kopf legen, sortieren und nach Lagerort gruppieren, QR-Etiketten drucken, beim Anlegen auch Temperaturen, Charge, Kommentar und deine eigenen Spoolman-Felder
- **Startzeit für Aufträge** in der Warteschlange oder **direkt danach**, mit Rückfrage „Druckbett frei?“ samt Kamerabild, sobald ein Druck davor fertig wurde
- **Druckdetails** in der Historie (Foto, Spulen, Kosten, Zeitraffer, nochmal drucken); **Zeitraffer** als eine Liste aus Drucker und Sicherung
- **Ersatzspule** im Startdialog, wenn eine Spule nicht reicht; Spulenwechsel im Druck wird anteilig abgebucht
- **Aufgabenlisten** (Optionen, Standard aus): fällige Wartung und Einkaufsliste für knappe Spulen
- Startdialog zeigt **fällige Wartung**; die Karte lädt auf Handy und Tablet schneller (kleiner, komprimiert, aus dem Cache, nur die eigene Sprache)

Bitte das Dashboard einmal neu laden. Alle Details: [Versionshinweise]({GITHUB}/releases/tag/v2.4.0)

⭐ [Projekt auf GitHub]({GITHUB}) · ☕ [Kaffee auf Ko-fi]({KOFI})"""),
        "en": ("Snapmaker U1 Card 2.4 – what's new", f"""- **Guided setup** step by step (power, notifications, Spoolman)
- **Dashboard templates:** Full, Minimal or Maintenance & diagnostics with one tap (card → Settings)
- **Clock and own buttons** in the full card (card editor, off by default); buttons with Home Assistant actions, shown per print phase
- **Light button** can switch further lights too (e.g. WLED)
- **Print event entity** for your own automations (finished, paused, error, spool runs out …)
- **Mini card** compact like the tile card: icon = power switch, cycling info line
- **Self test** checks more: power switch, spool per head, printer clock, maintenance, paxx12, blueprint
- **paxx12 settings** to view in the card's settings
- **Colliding card names** (another "snapmaker-u1-card") show up under Repairs
- **Spoolman tab:** edit, archive, restore and delete spools, put one in a head, sort and group by location, print QR labels, temperatures, lot, comment and your own Spoolman fields when creating one
- **Start time for queued jobs** or **right after**, with a "bed clear?" question and camera image once a print before it finished
- **Print details** in the history (photo, spools, cost, timelapse, print again); **timelapses** as one list from printer and backup
- **Spare spool** in the print dialog when a spool runs short; a spool changed during a print is booked pro rata
- **To-do lists** (options, off by default): due maintenance and a shopping list for low spools
- Print dialog shows **due maintenance**; the card loads faster on phones and tablets (smaller, compressed, from the cache, only its own language)

Please reload the dashboard once. All details: [release notes]({GITHUB}/releases/tag/v2.4.0)

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
