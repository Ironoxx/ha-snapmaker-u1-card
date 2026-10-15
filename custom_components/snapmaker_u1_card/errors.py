"""Fehlermeldungen der U1-Firmware im Klartext.

Die Firmware meldet Ausnahmen strukturiert (u1-klipper coded_exception.py,
exception_manager.py): Modul-ID, Index (meist der Kopf), Code, Stufe und eine
englische Rohmeldung. Abfragbar ueber die Objekte ``exception_manager``
(``exceptions``: alle offenen) und ``print_stats`` (``exception``: die, die
den Druck gestoppt hat).

Die Texte hier sind aus den Quellstellen der Firmware abgeleitet. Unbekannte
Codes fallen auf eine Modulbeschreibung plus Rohmeldung zurueck.
"""

from __future__ import annotations

from typing import Any

# Modul-IDs (exception_manager.ExceptionList)
MODULES: dict[int, tuple[str, str]] = {
    522: ("Bewegungssystem", "Motion system"),
    523: ("Druckkopf", "Toolhead"),
    524: ("Kamera", "Camera"),
    525: ("Filamentzufuhr", "Filament feeder"),
    526: ("Heizbett", "Heated bed"),
    527: ("Innenraum", "Chamber"),
    528: ("Referenzfahrt", "Homing"),
    529: ("G-Code", "G-code"),
    530: ("Kalibrierung", "Calibration"),
    531: ("Druckdatei", "Print file"),
    532: ("Fehlererkennung (Kamera)", "Defect detection (camera)"),
    533: ("Luftreiniger", "Air purifier"),
    2052: ("System", "System"),
}

# Module, deren Index einen Kopf bzw. Zufuhrkanal meint
_PER_HEAD = (523, 525)

# (Modul, Code) -> (deutsch, englisch, Hinweis deutsch, Hinweis englisch)
CATALOG: dict[tuple[int, int], tuple[str, str, str, str]] = {
    (522, 11): ("Schrittmotortreiber meldet einen Fehler", "Stepper driver reports an error",
                "Drucker aus- und wieder einschalten. Tritt es erneut auf: Kabel des Motors prüfen.",
                "Power-cycle the printer. If it happens again, check the motor cable."),
    (522, 17): ("Stromausfall erkannt", "Power loss detected",
                "Der Druck kann am Display fortgesetzt werden, sofern angeboten.",
                "The print can be resumed on the display if offered."),
    (523, 0): ("Filament leer", "Filament ran out",
               "Neue Spule einlegen und den Druck fortsetzen.",
               "Load a new spool and resume the print."),
    (523, 6): ("Kopf nicht konfiguriert", "Toolhead not configured", "", ""),
    (523, 37): ("Wartung der Druckköpfe empfohlen", "Toolhead maintenance recommended",
                "Werkzeugwechsel-Zähler hat die Wartungsgrenze erreicht. Wartung laut Snapmaker-Anleitung durchführen.",
                "The tool-change counter reached the maintenance limit. Follow Snapmaker's maintenance guide."),
    (523, 38): ("Filament verheddert", "Filament tangled",
                "Spule auf Knoten oder Verhaken prüfen, dann fortsetzen.",
                "Check the spool for knots or snags, then resume."),
    (523, 48): ("Kontaktproblem an den Pogo-Pins", "Pogo pin contact problem",
                "Kontakte zwischen Kopf und Dock reinigen und erneut versuchen.",
                "Clean the contacts between head and dock and retry."),
    (525, 3): ("Kein Filament an der Zufuhr", "No filament at the feeder",
               "Filament bis zum Anschlag einführen.", "Insert the filament until it stops."),
    (525, 10): ("Vorladen fehlgeschlagen", "Preloading failed", "", ""),
    (525, 11): ("Vorladen: Motor dreht nicht richtig", "Preload: motor speed fault",
                "Filamentweg auf Blockaden prüfen.", "Check the filament path for blockages."),
    (525, 12): ("Vorladen: Förderrad bewegt sich nicht", "Preload: feed wheel not moving",
                "Filament rutscht oder klemmt. Filament neu einlegen.", "Filament slips or is stuck. Reload it."),
    (525, 13): ("Vorladen: kein Filament erkannt", "Preload: no filament detected",
                "Filament bis zum Anschlag einführen.", "Insert the filament until it stops."),
    (525, 14): ("Vorladen: Zeitüberschreitung", "Preload: timeout",
                "Filamentweg prüfen und erneut laden.", "Check the filament path and load again."),
    (525, 15): ("Vorladen: Restfilament im Weg", "Preload: leftover filament in the path",
                "Altes Filamentstück aus dem Kopf entfernen.", "Remove the leftover filament from the head."),
    (525, 30): ("Laden fehlgeschlagen", "Loading failed", "", ""),
    (525, 31): ("Laden: Motor dreht nicht richtig", "Load: motor speed fault",
                "Filamentweg auf Blockaden prüfen.", "Check the filament path for blockages."),
    (525, 32): ("Laden: Förderrad bewegt sich nicht", "Load: feed wheel not moving",
                "Filament rutscht oder klemmt. Filament neu einlegen.", "Filament slips or is stuck. Reload it."),
    (525, 33): ("Laden: kein Filament erkannt", "Load: no filament detected",
                "Filament bis zum Anschlag einführen.", "Insert the filament until it stops."),
    (525, 34): ("Laden: Zeitüberschreitung", "Load: timeout",
                "Düse verstopft oder Filament klemmt. Düse prüfen.", "Nozzle clogged or filament stuck. Check the nozzle."),
    (525, 35): ("Laden: Förderweg zu lang", "Load: feed distance exceeded",
                "Filament kommt nicht an der Düse an. Bowden und Düse prüfen.",
                "Filament does not reach the nozzle. Check tube and nozzle."),
    (525, 51): ("Extrudieren beim Wechsel fehlgeschlagen", "Extrusion during change failed",
                "Düse auf Verstopfung prüfen.", "Check the nozzle for a clog."),
    (526, 2): ("Heizbett-Fehler", "Heated bed fault",
               "Drucker aus- und wieder einschalten. Tritt es erneut auf: Snapmaker-Support.",
               "Power-cycle the printer. If it persists, contact Snapmaker support."),
    (528, 0): ("Z-Referenzfahrt abgebrochen: erst X und Y referenzieren", "Z homing aborted: home X and Y first", "", ""),
    (528, 5): ("Endschalter nach dem Zurückfahren noch ausgelöst", "Endstop still triggered after retract",
               "Achse auf Hindernisse prüfen.", "Check the axis for obstructions."),
    (528, 6): ("Referenzfahrt außerhalb der Toleranz", "Homing distance out of tolerance",
               "Achse auf Hindernisse oder lose Riemen prüfen.", "Check the axis for obstructions or loose belts."),
    (528, 9): ("Sonde hat vor der Bewegung ausgelöst", "Probe triggered before movement",
               "Düse und Druckplatte auf Rückstände prüfen.", "Check nozzle and plate for debris."),
    (528, 11): ("Präzise Referenzfahrt: Koordinaten unplausibel", "Precise homing: implausible coordinates", "", ""),
    (528, 12): ("Präzise Referenzfahrt fehlgeschlagen", "Precise homing failed",
                "Achsen auf Hindernisse prüfen und erneut versuchen.", "Check the axes for obstructions and retry."),
    (530, 2): ("Vor dem Antasten referenzieren", "Home before probing", "", ""),
    (530, 10): ("Druckplatte wurde entfernt", "Build plate was removed",
                "Platte wieder auflegen.", "Put the plate back."),
    (530, 11): ("Druckplatte wurde nicht entfernt", "Build plate was not removed", "", ""),
    (530, 17): ("PEI-Platte liegt nicht richtig", "PEI plate not positioned correctly",
                "Platte an den Anschlägen ausrichten.", "Align the plate with its stops."),
    (530, 24): ("Kalibrierung des Ursprungs fehlgeschlagen", "Origin calibration failed", "", ""),
    (530, 27): ("Referenzfahrt instabil", "Homing is unstable", "", ""),
    (530, 29): ("Manuelles Bettnivellieren nötig", "Manual bed leveling required",
                "Nivellierung am Display starten.", "Start leveling on the display."),
    (531, 0): ("Dateiliste nicht lesbar", "Unable to read the file list", "", ""),
    (531, 1): ("Speicher belegt", "Storage busy", "", ""),
    (532, 1): ("Verschmutztes Druckbett erkannt", "Dirty bed detected",
               "Druckplatte reinigen.", "Clean the build plate."),
    (532, 2): ("Spaghetti erkannt", "Spaghetti detected",
               "Druck prüfen. Abgelöstes Teil oder Fadensalat.", "Check the print. Detached part or spaghetti."),
    (532, 3): ("Rückstände auf dem Druckbett erkannt", "Residue on the bed detected",
               "Druckbett räumen.", "Clear the bed."),
    (532, 4): ("Verschmutzte Düse erkannt", "Dirty nozzle detected",
               "Düse reinigen.", "Clean the nozzle."),
}


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def describe_error(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Eine Firmware-Ausnahme aufbereiten; None fuer leere Eintraege."""
    module, code, index = _int(raw.get("id")), _int(raw.get("code")), _int(raw.get("index"))
    if module is None or code is None:
        return None
    message = str(raw.get("message") or "").strip()
    if not message or message == "class CodedException":
        message = ""
    entry = CATALOG.get((module, code))
    mod = MODULES.get(module, ("Drucker", "Printer"))
    if entry:
        de, en, hint_de, hint_en = entry
    else:
        de, en, hint_de, hint_en = mod[0], mod[1], "", ""
    if module in _PER_HEAD and index is not None:
        de, en = f"{de} (Kopf {index + 1})", f"{en} (head {index + 1})"
    level = _int(raw.get("level"))
    return {
        "key": f"{module:04d}-{index or 0:04d}-{code:04d}",
        "id": module, "index": index, "code": code, "level": level,
        "known": entry is not None,
        "message": message,
        "text": {"de": de, "en": en},
        "hint": {"de": hint_de, "en": hint_en},
    }


def collect_errors(status: dict[str, Any]) -> list[dict[str, Any]]:
    """Offene Ausnahmen aus exception_manager plus die Druck-Ausnahme, ohne Dubletten."""
    raw: list[dict[str, Any]] = []
    em = status.get("exception_manager") or {}
    if isinstance(em.get("exceptions"), list):
        raw += [e for e in em["exceptions"] if isinstance(e, dict)]
    stats = status.get("print_stats") or {}
    exc = stats.get("exception")
    if isinstance(exc, dict) and stats.get("state") == "error":
        raw.append(exc)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        info = describe_error(item)
        if info is None or info["key"] in seen:
            continue
        # Platzhalter der Firmware fuer "keine Ausnahme" (Code 0 ohne Text)
        if info["id"] == 522 and info["code"] == 0 and not info["message"]:
            continue
        seen.add(info["key"])
        out.append(info)
    return out


def error_text(info: dict[str, Any], lang: str) -> str:
    key = "de" if lang.lower().startswith("de") else "en"
    text = info["text"][key]
    if not info.get("known") and info.get("message"):
        text = f"{text}: {info['message']}"
    hint = info["hint"][key]
    return f"{text}. {hint}" if hint else text
