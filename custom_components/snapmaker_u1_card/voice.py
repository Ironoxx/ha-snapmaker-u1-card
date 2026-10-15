"""Sprachsteuerung ueber Assist.

Die Integration meldet drei Intents an (Status, Pause, Fortsetzen) und legt
passende Saetze unter ``/config/custom_sentences/<de|en>/snapmaker_u1_card.yaml``
ab. Diese Dateien gehoeren der Integration (Kopfzeile ``MARKER``): sie werden
bei jedem Start aktualisiert, solange die Kopfzeile drinsteht. Wer die Saetze
selbst pflegen will, loescht die Kopfzeile, dann bleibt die Datei unberuehrt.

Beispiele: "Wie weit ist der Drucker?", "Pausiere den Drucker",
"Drucker fortsetzen"; "How far is the printer?", "Pause the printer".
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from .api import MoonrakerError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

INTENT_STATUS = "SnapmakerU1Status"
INTENT_PAUSE = "SnapmakerU1Pause"
INTENT_RESUME = "SnapmakerU1Resume"
MARKER = "# snapmaker_u1_card: automatisch erzeugt"
FILENAME = f"{DOMAIN}.yaml"

SENTENCES = {
    "de": f"""{MARKER} – Kopfzeile loeschen, um die Datei selbst zu pflegen.
language: "de"
intents:
  {INTENT_STATUS}:
    data:
      - sentences:
          - "wie weit ist [der] (drucker|3D-drucker|3D drucker)"
          - "wie lange (braucht|druckt) [der] (drucker|3D-drucker|3D drucker) [noch]"
          - "wann ist [der] (drucker|3D-drucker|3D drucker) fertig"
          - "was macht [der] (drucker|3D-drucker|3D drucker)"
          - "(status|stand) [vom|des] (drucker|druckers|3D-drucker|3D-druckers)"
          - "wie weit ist [der] druck"
  {INTENT_PAUSE}:
    data:
      - sentences:
          - "(pausiere|pausier|halte) [den] (drucker|3D-drucker|3D drucker) [an]"
          - "(drucker|3D-drucker|3D drucker) pausieren"
          - "(pausiere|pausier) [den] druck"
          - "druck pausieren"
  {INTENT_RESUME}:
    data:
      - sentences:
          - "setze [den] (drucker|3D-drucker|3D drucker) fort"
          - "setze [den] druck fort"
          - "(drucker|3D-drucker|3D drucker) fortsetzen"
          - "druck fortsetzen"
          - "(drucke|druck) weiter"
""",
    "en": f"""{MARKER} – delete this line to maintain the file yourself.
language: "en"
intents:
  {INTENT_STATUS}:
    data:
      - sentences:
          - "how far [along] is the [3D] printer"
          - "how long until the print is (done|finished)"
          - "when (is|will) the [3D] printer [be] (done|finished)"
          - "what is the [3D] printer doing"
          - "[3D] printer status"
  {INTENT_PAUSE}:
    data:
      - sentences:
          - "pause the [3D] (printer|print)"
  {INTENT_RESUME}:
    data:
      - sentences:
          - "(resume|continue) the [3D] (printer|print)"
""",
}

STATE_DE = {
    "standby": "bereit", "printing": "druckt", "paused": "pausiert", "complete": "fertig",
    "cancelled": "abgebrochen", "error": "im Fehlerzustand",
}
STATE_EN = {
    "standby": "ready", "printing": "printing", "paused": "paused", "complete": "finished",
    "cancelled": "cancelled", "error": "in an error state",
}


def _minutes(seconds: float) -> tuple[int, int]:
    total = max(1, round(seconds / 60))
    return divmod(total, 60)


def status_speech(coord: Any, de: bool) -> str:
    """Antwortsatz fuer den Status (auch ohne Druck)."""
    from .coordinator import remaining_seconds

    data = coord.data or coord._prev
    if not data.online:
        return "Der Drucker ist aus oder nicht erreichbar." if de else "The printer is off or unreachable."
    state = coord.current_print_state() or "standby"
    active = coord._print_state.get("active") or {}
    name = active.get("name") or ("der Druck" if de else "the print")
    if state not in ("printing", "paused"):
        last = (coord._print_state.get("last") or {}).get("name")
        word = (STATE_DE if de else STATE_EN).get(state, state)
        if de:
            return f"Der Drucker ist {word}." + (f" Zuletzt gedruckt: {last}." if last and state != "standby" else "")
        return f"The printer is {word}." + (f" Last print: {last}." if last and state != "standby" else "")
    parts = []
    pct = round((data.progress or 0) * 100)
    if de:
        parts.append(f"{name} ist {'pausiert bei' if state == 'paused' else 'bei'} {pct} Prozent")
    else:
        parts.append(f"{name} is {'paused at' if state == 'paused' else 'at'} {pct} percent")
    if data.layer and data.total_layers:
        parts.append(f"Schicht {data.layer} von {data.total_layers}" if de
                     else f"layer {data.layer} of {data.total_layers}")
    left = data.remaining if data.remaining is not None else remaining_seconds(data.print_duration, data.progress)
    if left is not None and state == "printing":
        h, m = _minutes(left)
        if de:
            parts.append(f"noch etwa {h} Stunden {m} Minuten" if h else f"noch etwa {m} Minuten")
        else:
            parts.append(f"about {h} hours {m} minutes left" if h else f"about {m} minutes left")
    return ", ".join(parts) + "."


def _coordinators(hass: HomeAssistant) -> list[Any]:
    return [e.runtime_data for e in hass.config_entries.async_loaded_entries(DOMAIN)]


class _Base(intent.IntentHandler):
    platforms = None

    def __init__(self, intent_type: str) -> None:
        self.intent_type = intent_type

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        de = (intent_obj.language or hass.config.language or "de").lower().startswith("de")
        response = intent_obj.create_response()
        coords = _coordinators(hass)
        if not coords:
            response.async_set_speech("Kein Snapmaker U1 eingerichtet." if de else "No Snapmaker U1 set up.")
            return response
        texts = [await self.handle(c, de) for c in coords]
        response.async_set_speech(" ".join(texts))
        return response

    async def handle(self, coord: Any, de: bool) -> str:
        raise NotImplementedError


class StatusIntent(_Base):
    async def handle(self, coord: Any, de: bool) -> str:
        return status_speech(coord, de)


class ActionIntent(_Base):
    def __init__(self, intent_type: str, action: str, need: str) -> None:
        super().__init__(intent_type)
        self.action, self.need = action, need

    async def handle(self, coord: Any, de: bool) -> str:
        state = coord.current_print_state()
        if state != self.need:
            # Pause/Fortsetzen braucht am Drucker einige Sekunden (Kopf parken bzw. anfahren)
            if self.action == "pause" and state == "paused":
                return "Der Druck ist bereits pausiert." if de else "The print is already paused."
            if self.action == "resume" and state == "printing":
                return "Der Druck läuft bereits." if de else "The print is already running."
            if self.action == "pause":
                return "Es läuft gerade kein Druck." if de else "Nothing is printing right now."
            return "Der Druck ist nicht pausiert." if de else "The print is not paused."
        try:
            await coord.client.print_action(self.action)
        except MoonrakerError as err:
            _LOGGER.warning("Sprachbefehl %s fehlgeschlagen: %s", self.action, err)
            return "Der Drucker hat nicht reagiert." if de else "The printer did not respond."
        await coord.async_request_refresh()
        if self.action == "pause":
            return "Druck wird pausiert." if de else "Pausing the print."
        return "Druck wird fortgesetzt." if de else "Resuming the print."


def _write_sentences(config_dir: str) -> bool:
    changed = False
    for lang, text in SENTENCES.items():
        target = Path(config_dir) / "custom_sentences" / lang / FILENAME
        if target.exists():
            current = target.read_text(encoding="utf-8")
            if not current.startswith(MARKER) or current == text:
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        changed = True
    return changed


async def async_setup_voice(hass: HomeAssistant) -> None:
    intent.async_register(hass, StatusIntent(INTENT_STATUS))
    intent.async_register(hass, ActionIntent(INTENT_PAUSE, "pause", "printing"))
    intent.async_register(hass, ActionIntent(INTENT_RESUME, "resume", "paused"))
    try:
        changed = await hass.async_add_executor_job(_write_sentences, hass.config.config_dir)
    except OSError as err:
        _LOGGER.warning("Saetze fuer Assist nicht geschrieben: %s", err)
        return
    if changed and hass.services.has_service("conversation", "reload"):
        await hass.services.async_call("conversation", "reload", {}, blocking=False)
