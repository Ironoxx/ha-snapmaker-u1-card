<img src="custom_components/snapmaker_u1_card/brand/icon.png" width="96" align="right" alt="" />

# Snapmaker U1 Card für Home Assistant

[English](README.md) | **Deutsch**

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz) [![Release](https://img.shields.io/github/v/release/Ironoxx/ha-snapmaker-u1-card)](https://github.com/Ironoxx/ha-snapmaker-u1-card/releases/latest) [![Ko-fi](https://img.shields.io/badge/Ko--fi-Kaffee%20spendieren-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/ironoxx)

Eine Home-Assistant-Integration mit eingebauter Dashboard-Karte für den **Snapmaker U1**:

- **Geladene Filamente live**: Material, Unterart, Hersteller, Farbe (auch mehrfarbig) und RFID-Erkennung je Druckkopf, direkt aus der Drucker-Firmware.
- **Kopf-Details**: Das Regler-Symbol am Kopf zeigt die RFID-Daten der Spule (Gewicht, Durchmesser, Düsen-/Bett-/Trocknungstemperatur, Herstelldatum, SKU). Dort lassen sich **Material, Hersteller und Farbe von Hand setzen**, etwa für Spulen ohne Chip.
- **Druckstart mit Filamentzuordnung wie in Snapmaker Orca**: Du tippst eine Datei an, die Karte schlägt vor, welches Filament der Datei auf welchen Kopf kommt. Grundlage sind Material und Farbe. Du kannst die Zuordnung ändern, Bettnivellierung, Flusskalibrierung und Zeitraffer wählen und dann starten.
- **Dateiliste mit Vorschaubildern**, Druckzeit, Gewicht und Farbpunkten je Datei.
- **Kamera** als Livestream über Home Assistant, mit automatischem Rückfall auf Standbilder. Zoom mit zwei Fingern, Doppeltipp, Strg+Mausrad oder Lupen-Knöpfen, Vollbild; gezoomt verschiebt man mit einem Finger bzw. der linken Maustaste. Während des Drucks liegen Fortschritt, Schicht, Restzeit, Fertig-Uhrzeit und aktiver Kopf direkt auf dem Bild.
- **Schichtansicht** unter dem Kamerabild: Bahnen der aktuellen Schicht in den Farben der geladenen Spulen, gedruckter Teil kräftig, der Rest blass.
- **Reiter** statt langer Seite: Übersicht, Steuerung, Dateien, Verlauf, Zeitraffer, System. Auf dem Handy nur Symbole.
- **Mini-Karte** `snapmaker-u1-mini-card` für Übersichts-Dashboards: Status, Fortschritt, Filamente mit Spoolman-Rest, Netzschalter.
- **Visueller Editor** für beide Karten, kein YAML nötig.
- **Werkzeugwechsel**: gesamt, je Kopf, im laufenden bzw. letzten Druck und Stand bis zur empfohlenen Wartung.
- **Netzschalter**: beliebige Steckdose (Shelly, KNX, Zigbee …). Ausschalten fährt den Drucker vorher sauber herunter und ist während eines Drucks gesperrt. Auf Wunsch automatisch aus nach dem Druck und automatisch ein beim Druckstart aus der Karte.
- **Strom und Kosten je Druck**: Verbrauch aus dem Energiezähler, Kosten mit Preis-Entität (auch dynamische Tarife), Filamentkosten aus Slicer-Gewicht und Preis je kg.
- **Druckhistorie** der letzten 20 Drucke mit Ergebnis, Dauer, Gewicht, kWh, Wechseln und Kosten.
- **Live statt Abfragen**: Moonraker meldet Statuswechsel, Schicht, aktiven Kopf und Fehler sofort (WebSocket-Abo). Die regelmäßige Abfrage läuft dann nur noch alle 30 s als Abgleich.
- **Benachrichtigung** aufs Handy bei Druckende, Fehler oder Pause (z. B. Filament leer), bei neuen Druckermeldungen im Druck, nach der ersten Schicht, kurz vor Ende und wenn eine Spule nicht reicht, mit Kamerabild.
- **Kosten vor dem Druck** im Startdialog: Filament aus Slicer-Gewicht × Preis, Strom aus Druckzeit × mittlerer Leistung deiner bisherigen Drucke × aktuellem Preis.
- **Sprachsteuerung über Assist**: „Wie weit ist der Drucker?“, „Pausiere den Drucker“, „Drucker fortsetzen“.
- **Restzeit aus dem Zeitprofil der Datei**, geeicht mit der echten Druckdauer; Sensoren *Restzeit* und *Fertig um*.
- **Knöpfe in der Benachrichtigung**: Pausieren, Fortsetzen, Abbrechen (mit Rückfrage), Licht.
- **Ergebnisfoto** bei Druckende in der Historie, **Temperaturverlauf** der letzten 20 min, **Dateiverwaltung** mit Suche über alle Dateien, Ordnern, Umbenennen und Löschen.
- **Firmware-Stand** als Update-Entität, **Selbsttest**, **Statistik je Material und Farbe**, **Leerlauf-Abschaltung**.
- **Sicherung der Drucker-Konfiguration** (printer.cfg & Co.) täglich nach `/config/snapmaker_u1_backup/`, nur bei Änderung.
- **Diagnose-Download** unter *Geräte & Dienste* für die Fehlersuche, Zugangsdaten geschwärzt, und Diagnose-Entität **Live-Verbindung** (an/aus), auch in der Karte unter *System*.
- **Zeitraffer** vom Drucker direkt in der Karte abspielen und herunterladen; auf Wunsch automatisch in den Medienordner von Home Assistant sichern.
- **Datei hochladen** aus der Karte (auch über Nabu Casa), danach direkt der Druckdialog.
- **Warteschlange** mit Zuordnung und Optionen je Auftrag. Startet nie von selbst: nach dem Druck Bett räumen, antippen.
- **Pause vor Schicht** (z. B. für Magnete oder Muttern) und **Nachdruck aus der Historie** mit der damaligen Zuordnung.
- **Druckermeldungen im Klartext** statt Firmware-Codes, mit Hinweis, was zu tun ist.
- **Diagramme** der letzten 12 Monate (Drucke, Stunden, Filament, Kosten) aus Moonrakers Druckhistorie, also auch rückwirkend.
- **Wartungsplaner** in Druckstunden (Druckplatte, Düsen, Führungen, Riemen, Filter) plus Werkzeugwechsel-Zähler der Firmware.
- **Spulenverwaltung mit [Spoolman](https://github.com/Donkie/Spoolman)** (optional): Spule je Kopf mit Restgewicht, automatische Zuordnung, Warnung, wenn eine Spule für den Druck nicht reicht, und Abbuchung des Verbrauchs je Kopf nach dem Druck.
- **Druckereinstellungen** als Schalter und in der Karte: Filament automatisch nachfüllen, Nachfüllen ohne Farbprüfung, Verhedderungs-Erkennung (mit Empfindlichkeit), Licht aus nach dem Druck. Am Drucker gespeichert, auch während eines Drucks änderbar.
- **Kamera wach halten** (optional): für Stock-Firmware, deren Kamerabild nach einer Weile stehen bleibt.
- **Zustandsfarbe**: ein dünner Rahmen in der Farbe des Zustands (druckt, pausiert, Fehler, fertig).
- Temperaturen, Sollwerte, Lüfter, Licht, Achsen, Diagnose und Statistik.

Alles läuft über die Home-Assistant-Verbindung. Das funktioniert lokal, über VPN und über Nabu Casa gleich, ohne CORS- oder Mixed-Content-Probleme.

**Das Design folgt deinem Home-Assistant-Theme**: Farben, Hell/Dunkel, Schrift und Rundungen kommen aus dem aktiven Theme (Material-You-Tokens, wo vorhanden). Die Karte passt sich so jedem Dashboard an.

> Sprache: Karte und Integration folgen der Sprache von Home Assistant (Deutsch, sonst Englisch).

> **Tester gesucht!** Die Integration läuft im Alltag, ist aber noch jung und bisher an wenigen Druckern erprobt. Wer einen Snapmaker U1 hat und mittesten möchte: einfach installieren und Erfahrungen, Fehler oder Wünsche als [Issue](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues) melden – am besten mit der Diagnose-Datei (*Geräte & Dienste → Snapmaker U1 Card → ⋮ → Diagnose herunterladen*), der Firmware-Version und, bei Druckproblemen, der G-Code-Datei. Test und Nutzung erfolgen freiwillig, ohne Gewähr und auf eigenes Risiko.

> Kein offizielles Produkt von Snapmaker und nicht mit Snapmaker verbunden. „Snapmaker“ und „U1“ sind Marken ihrer Inhaber und stehen hier nur, um den unterstützten Drucker zu nennen. Nutzung auf eigenes Risiko.

## Screenshots

![Übersicht mit Kamera, letztem Druck und Druckköpfen](docs/screenshots/uebersicht.png)

| Druckstart mit Filamentzuordnung | Verlauf und Statistik |
|---|---|
| ![Druckstart](docs/screenshots/druckstart.png) | ![Verlauf](docs/screenshots/verlauf.png) |
| **Steuerung** | **System, Wartung und Diagnose** |
| ![Steuerung](docs/screenshots/steuerung.png) | ![System](docs/screenshots/system.png) |
| **Zeitraffer** | |
| ![Zeitraffer](docs/screenshots/zeitraffer.png) | |

## Voraussetzungen

| Was | Wozu | Pflicht |
|---|---|---|
| Home Assistant 2025.3 oder neuer | | ja |
| [HACS](https://hacs.xyz) | Installation und Updates | empfohlen |
| [Moonraker-Integration](https://github.com/marcolivierarsenault/moonraker-home-assistant) | Temperaturen, Lüfter, Licht, Achsen, Schicht, Kamera und Systemwerte in der Karte | ja |
| Snapmaker U1 im Netzwerk, feste IP-Adresse (DHCP-Reservierung im Router) | Verbindung | ja |
| Drucker-Firmware: Snapmaker-Stock, Extended Firmware (paxx12) oder Stock mit Bespok3d | | ja |
| Home-Assistant-Companion-App | Push-Benachrichtigungen mit Bild und Knöpfen | optional |
| Steckdose/Schalter in HA (Shelly, Zigbee, KNX …), Energiezähler, Strompreis-Sensor | Netzschalter, Auto-Ein/-Aus, Strom und Kosten | optional |
| [Spoolman](https://github.com/Donkie/Spoolman) | Spulenverwaltung | optional |

Beide Integrationen sprechen direkt mit Moonraker auf dem Drucker (Port 80). Auf der Stock-Firmware ist dafür kein API-Schlüssel nötig.

## Installation

### 1. Moonraker-Integration

1. HACS → *Integrationen* → nach **Moonraker** suchen → installieren → Home Assistant neu starten.
2. *Einstellungen → Geräte & Dienste → Integration hinzufügen → „Moonraker“*.
3. **Host:** IP-Adresse des Druckers (z. B. `192.168.1.50`), **Port:** `80`, API-Schlüssel leer lassen.
4. Prüfen: Unter dem neuen Gerät erscheinen Sensoren wie `sensor.<name>_printer_state` und eine Kamera.

Die Karte findet die Entitäten der Moonraker-Integration selbst, auch bei anderem Gerätenamen. Nur bei mehreren Druckern muss man in der Karte den Präfix (`prefix`) angeben.

### 2. Snapmaker U1 Card

1. **HACS** → ⋮ → *Benutzerdefinierte Repositories* → `https://github.com/Ironoxx/ha-snapmaker-u1-card`, Typ *Integration* → hinzufügen → **Snapmaker U1 Card** installieren → Home Assistant neu starten.
   *Ohne HACS:* `snapmaker_u1_card-<Version>-install.zip` aus dem [neuesten Release](https://github.com/Ironoxx/ha-snapmaker-u1-card/releases/latest) entpacken, den Ordner `custom_components/snapmaker_u1_card` nach `/config/custom_components/` kopieren, neu starten.
2. *Einstellungen → Geräte & Dienste → Integration hinzufügen → „Snapmaker U1 Card“* → IP-Adresse des Druckers, Port `80`.
3. Im zweiten Schritt die Einstellungen ausfüllen (alles optional, später unter *Konfigurieren* änderbar, siehe [Einstellungen](#einstellungen-der-integration)).
4. **Selbsttest:** In der Karte unter *System → Selbsttest* (oder Dienst `snapmaker_u1_card.self_test`). Er zeigt, ob Drucker, Moonraker-Integration, Kamera, Strom-Entitäten und Benachrichtigungen passen.

### 3. Karte ins Dashboard

Dashboard bearbeiten → *Karte hinzufügen* → **Snapmaker U1** (oder **Snapmaker U1 Mini**) auswählen. Alles Weitere geht im visuellen Editor. In YAML:

```yaml
type: custom:snapmaker-u1-card
```

Am besten in einer Ansicht vom Typ *Panel* oder *Abschnitte* mit voller Breite; auf dem Handy passt sich die Karte an.

Fertig. Eine Ressource musst du **nicht** selbst anlegen: Die Integration lädt die Karte auf zwei Wegen selbst.

1. Über die Startseite von Home Assistant (`add_extra_js_url`).
2. Als Dashboard-Ressource `/local/snapmaker_u1_card/snapmaker-u1-card.js?v=…`. Die Integration legt sie an, hält sie bei Updates aktuell und entfernt sie mit der Integration. Unter *Dashboards → Ressourcen* also bitte stehen lassen.

Der zweite Weg ist nötig, weil Home Assistant Seiten schon ausliefert, bevor eigene Integrationen gestartet sind. Wer in diesem Fenster lädt (Tab oder App während eines Neustarts), bekäme sonst „Custom element doesn't exist: snapmaker-u1-card“, bis er neu lädt. Gab es `/config/www` vorher nicht, greift der zweite Weg erst nach einem weiteren Neustart.

## Update

Ordner `custom_components/snapmaker_u1_card` ersetzen (oder in HACS aktualisieren) und Home Assistant neu starten. Einstellungen, Historie, Warteschlange, Wartungsstände, Spulenzuordnung und gesicherte Zeitraffer bleiben erhalten:

| Was | Wo |
|---|---|
| Einstellungen | Konfigurationseintrag (`.storage/core.config_entries`) |
| Historie, Warteschlange, Wartung, Spoolman-Zuordnung, offene Buchungen | `.storage/snapmaker_u1_card.<eintrag>.print_switches` |
| Vorschaubilder, Schichtansicht (Zwischenspeicher, wird neu erzeugt) | `.storage/snapmaker_u1_card/` |
| Sicherungen der Drucker-Konfiguration | `snapmaker_u1_backup/` |
| Sätze für Assist (bei jedem Start aktualisiert) | `custom_sentences/de/…` und `custom_sentences/en/…` |
| gesicherte Zeitraffer | `<Medien>/snapmaker_u1/` |

Nicht die Integration löschen und neu hinzufügen: Das legt einen neuen Eintrag an, Einstellungen und Historie gehören dann zum alten.

## Einstellungen der Integration

Bei der Einrichtung kommt nach der Adresse direkt ein zweiter Schritt mit allen Einstellungen. Später stehen sie unter *Geräte & Dienste → Snapmaker U1 Card → Konfigurieren*. Alle Felder sind freiwillig, die Karte übernimmt sie automatisch.

| Abschnitt | Felder |
|---|---|
| Strom und Verbrauch | Netzschalter, Leistungssensor (W), Energiezähler (kWh), Strompreis-Entität (EUR/kWh oder ct/kWh), vor dem Abschalten herunterfahren, Auto-Ein beim Druckstart, Auto-Aus nach dem Druck (Temperatur, Verzögerung), Ausschalten nach Leerlauf (Stunden) |
| Benachrichtigungen & Kamera | `notify.mobile_app_…`-Dienste, Anlässe (fertig, abgebrochen, Fehler, pausiert, Meldung im Druck, erste Schicht fertig, gleich fertig, Filament reicht nicht), Vorwarnung „gleich fertig“ in Minuten (10), „Teil entnehmbar“ ab Betttemperatur (35 °C), Kamera für Bild und Ergebnisfoto, **Kamera wach halten** (aus / während eines Drucks / immer) |
| Filamentpreise | € je kg für PLA, PETG, ABS, ASA, TPU, PA und sonstige. `PLA-CF` nutzt den PLA-Preis |
| Zeitraffer sichern | Ein/aus, wie viele neueste auf dem Drucker bleiben (0 = nie löschen) |
| Wartung | Intervall je Punkt in Druckstunden (0 = ausblenden) |
| Spoolman | Adresse (leer = aus), Verbrauch je Kopf abbuchen (an/aus), Warnschwelle in g |
| Dateien | Anzahl neuester Dateien, Drucker-Konfiguration sichern (an) |

## Kartenoptionen

Alle Optionen sind freiwillig und bis auf Kopfnamen und Presets auch im visuellen Editor einstellbar.

| Option | Standard | Bedeutung |
|---|---|---|
| `layout` | `tabs` | `tabs` = Reiter, `scroll` = alle Bereiche untereinander |
| `camera_overlay` | `true` | Fortschritt auf dem Kamerabild (`hide_overlay: true` schaltet es ebenfalls ab) |
| `state_accent` | `true` | Rahmen in der Theme-Farbe des Zustands (druckt, pausiert, Fehler, fertig) |
| `camera_height` | automatisch | Höhe des Kamerabilds in px. Leer = Seitenverhältnis des Bildes, höchstens `camera_max_height` |
| `camera_max_height` | `520` | Obergrenze bei automatischer Höhe in px |
| `camera_mode` | `stream` | `stream` = Livebild, `still` = Einzelbilder (spart WLAN) |
| `refresh` | `2` | Sekunden zwischen Einzelbildern (`still` und Rückfall) |
| `camera_fit` | `contain` | `contain`, `cover`, `fill` |
| `show` | alle | Bereiche: `stage layer job queue files toolheads climate motion system maintenance charts stats history timelapse` |
| `hide` | – | Bereiche ausblenden (Gegenstück zu `show`, nutzt der Editor) |
| `controls_lock` | `60` | Sperre für Temperatur- und Lüfterregler, Schnellwahl, Heizungsschalter und Referenzfahrt: `off`, Sekunden (`30`, `60`, `120`, `300`) bis zur automatischen Sperre nach der letzten Bedienung, oder `manual` (offen, bis man wieder sperrt). Im Druck fragt die Karte vor jeder Änderung einer Solltemperatur nach. Alt: `unlock_controls: true` = `off` |
| `timelapse_limit` | `8` | angezeigte Zeitraffer |
| `files_limit` | `12` | angezeigte Dateien |
| `nozzle_presets` / `bed_presets` | `[0,210,240,260]` / `[0,55,65,85]` | Schnellwahl-Temperaturen |
| `toolheads` | – | Kopfnamen, z. B. `- name: Links` (Material und Farbe kommen vom Drucker) |
| `network_tracker` | – | `device_tracker` für einen WLAN-Chip im Kopf |
| `prefix`, `camera`, `thumbnail`, `filaments_sensor`, `files_sensor` | automatisch | nur bei mehreren Druckern nötig |

### Mini-Karte

```yaml
type: custom:snapmaker-u1-mini-card
navigation_path: /dashboard-drucker/0   # optional: beim Antippen dorthin, sonst Statusdialog
```

| Option | Standard | Bedeutung |
|---|---|---|
| `printer_name` | `U1` | Anzeigename |
| `navigation_path` | – | Ziel beim Antippen |
| `hide_filaments` | `false` | Filamentreihe ausblenden |
| `prefix` | automatisch | nur bei mehreren Druckern |

## Entitäten

| Entität | Inhalt |
|---|---|
| `sensor.…_filamente` | Anzahl geladener Slots, Attribut `slots` mit allen vier Köpfen, `preferences` |
| `sensor.…_slot_1` … `_slot_4` | Material des Slots oder `leer`, Farbe und Hersteller als Attribute – gut für Automationen |
| `sensor.…_druckdateien` | neueste Druckdateien mit Filamenten und Vorschaubild |
| `sensor.…_werkzeugwechsel` | Kopfwechsel gesamt (Firmware-Zähler), Attribut `heads` je Kopf mit `switches`, `retries`, `errors`, `since_maintenance` |
| `sensor.…_werkzeugwechsel_druck` | Wechsel im laufenden Druck, sonst im letzten; Attribute `in_progress`, `file`, `result`, `started`, `ended` |
| `switch.…_netzschalter` | sicherer Netzschalter (nur mit eingetragenem Schalter). **Automationen sollten diesen schalten, nicht die Steckdose direkt.** |
| `sensor.…_energie_druck` | kWh des laufenden bzw. letzten Drucks (nur mit Energiezähler) |
| `sensor.…_kosten_druck` | Stromkosten bisher bzw. Gesamtkosten des letzten Drucks; Attribute `energy_cost`, `filament_cost` |
| `sensor.…_druckhistorie` | Anzahl, Attribut `prints` mit den letzten 20 Drucken |
| `sensor.…_zeitraffer` | Anzahl, Attribut `videos`; mit Sicherung `archive` (gesicherte Videos, Status) |
| `sensor.…_warteschlange` | Anzahl Aufträge, Attribut `jobs` (id, Datei, Zuordnung, Optionen, Pause) |
| `sensor.…_druckstunden` | Druckstunden gesamt (Moonraker), Attribute `months`, `totals`, `top_files` |
| `sensor.…_wartung_fallig` | Anzahl fälliger Wartungspunkte, Attribut `items` |
| `sensor.…_druckermeldungen` | Anzahl offener Firmware-Meldungen, Attribut `errors` mit Text (de/en), Hinweis und Rohcode |
| `switch.…_filament_automatisch_nachfullen`, `…_nachfullen_ohne_farbprufung`, `…_verhedderungs_erkennung`, `…_licht_aus_nach_dem_druck` | Firmware-Einstellungen (am Drucker gespeichert) |
| `select.…_empfindlichkeit_verhedderungs_erkennung` | `low`, `medium`, `high` |

Die Slot-Sensoren tragen zusätzlich das Attribut `rfid` mit den Daten des Spulen-Chips.

Ereignis `snapmaker_u1_card_print_finished` bei jedem Druckende, mit `file`, `name`, `result`, `duration_s`, `tool_changes`, `energy_kwh`, `energy_cost`, `filament_g`, `filament_cost`, `total_cost` – für eigene Automationen.

## Dienste

### `snapmaker_u1_card.start_print`

```yaml
action: snapmaker_u1_card.start_print
data:
  filename: Benchy_PLA.gcode
  mapping: {"0": 2, "1": 0}   # Filament 1 → Kopf 3, Filament 2 → Kopf 1; weglassen = automatisch
  bed_leveling: true
  flow_calibration: false
  timelapse: false
```

Ohne `mapping` nimmt der Dienst denselben Vorschlag wie die Karte. Mit `pause_layers: [12, 40]` hält der Drucker vor diesen Schichten an.

**Wie „Pause vor Schicht“ funktioniert.** Klipper und die U1-Firmware haben dafür keinen Befehl. Die Integration legt deshalb eine Kopie der Datei an (`<Name>.u1pause-12-40.gcode`), schreibt dort `PAUSE` vor den Schichtwechsel (`;LAYER_CHANGE` aus Orca/Snapmaker Orca, auch Cura-Markierungen) und druckt die Kopie. Die Firmware behandelt `PAUSE` in Dateien ausdrücklich. Die Kopie ist in der Dateiliste ausgeblendet und wird nach dem Druck gelöscht; die Historie zeigt die Originaldatei. Fortsetzen am Display oder mit dem Knopf in der Karte.

### Warteschlange

```yaml
action: snapmaker_u1_card.queue_add      # gleiche Felder wie start_print
data: {filename: Halter.gcode, mapping: {"0": 1}, pause_layers: [8]}
action: snapmaker_u1_card.queue_start    # ersten Auftrag starten (oder job_id)
action: snapmaker_u1_card.queue_move     # job_id, position (0 = vorne)
action: snapmaker_u1_card.queue_remove   # job_id
action: snapmaker_u1_card.queue_clear
```

Moonrakers eigene Warteschlange (`[job_queue]`) ist auf dem U1 nicht geladen und kennt keine Filamentzuordnung, deshalb führt die Integration die Liste selbst. Sie übersteht Neustarts. Nach einem Druck kommt eine Benachrichtigung „Nächster Auftrag wartet“ (an die eingetragenen Dienste).

### `snapmaker_u1_card.maintenance_done` / `backup_timelapses` / `backup_config`

`item: plate | nozzle | rails | belts | filter` setzt den Wartungszähler zurück. `backup_timelapses` sichert sofort und räumt danach auf dem Drucker auf. `backup_config` sichert die Drucker-Konfiguration sofort und antwortet mit `status` (`saved`, `unchanged`, `empty`), Anzahl Dateien, übersprungenen Dateien und den vorhandenen Ständen.

### `snapmaker_u1_card.set_filament` / `set_preference`

```yaml
action: snapmaker_u1_card.set_filament   # Spule ohne RFID; nicht während eines Drucks
data:
  slot: 2            # Kopf 1–4
  type: PETG
  sub_type: HF       # optional
  vendor: Generic    # optional
  color: "#1B5E20"   # optional
  force: false       # true = auch eine offizielle Snapmaker-Spule überschreiben

action: snapmaker_u1_card.set_preference
data:
  preference: auto_replenish   # replenish_ignore_color | entangle_detect | end_led_off | entangle_sensitivity
  value: true                  # entangle_sensitivity: low | medium | high
```

Beides geht an die Firmware (`SET_PRINT_FILAMENT_CONFIG`, `SET_PRINT_PREFERENCES` aus u1-klipper `print_task_config.py`). Der Drucker speichert die Werte selbst, das Display zeigt sie ebenfalls.

### `snapmaker_u1_card.refresh`

Lädt Dateiliste, Zeitraffer und Filamente sofort neu.

### `snapmaker_u1_card.power_on` / `power_off`

Einschalten (optional `wait: true`: erst zurück, wenn Klipper bereit ist) bzw. sicher ausschalten: herunterfahren (`machine.shutdown`), warten bis der Drucker nicht mehr antwortet plus 10 s, dann Strom aus.

Abgelehnt bzw. abgebrochen wird das Ausschalten, wenn

- ein Druck läuft oder pausiert ist, auch wenn der Drucker gerade kurz nicht antwortet (WLAN-Aussetzer zählt nicht als „fertig“),
- der Drucker direkt vor dem Herunterfahren oder vor dem Abschalten meldet, dass er druckt oder eine Heizung einen Sollwert hat (z. B. Druck am Display gestartet),
- der Drucker gerade über Auto-Ein hochfährt.

Für einen abgestürzten Drucker, der noch als druckend erfasst ist: `force: true` (die Karte bietet das nur an, wenn der Drucker nicht antwortet). Während des Herunterfahrens nimmt `start_print` keine Drucke an.

## Wie die Filamentzuordnung funktioniert

Die Integration startet Drucke genauso wie Snapmaker Orca im LAN-Modus, über den Moonraker-Aufruf `server.files.start_local_print` mit `options.map_table`. Der Drucker setzt das in `SDCARD_PRINT_FILE_WITH_PARAMETERS … MAP_TABLE="[[0, 2], [1, 0]]"` um. Die Firmware prüft dabei wie gewohnt, ob der Drucker frei ist und die Düsen passen.

Belegt ist das aus Snapmakers offenem Quellcode:
[u1-klipper](https://github.com/Snapmaker/u1-klipper) (`klippy/extras/print_task_config.py`) und
[u1-moonraker](https://github.com/Snapmaker/u1-moonraker) (`components/snapmakercloud.py`, `components/klippy_apis.py`).

Der Vorschlag wählt je Filament der Datei einen geladenen Kopf in dieser Reihenfolge: gleiches Material, ähnlichste Farbe, noch frei. Ein leerer Kopf blockiert den Start. Ein abweichendes Material zeigt die Karte nur als Warnung an.

## Werkzeugwechsel

Die Firmware zählt jeden erfolgreichen Kopfwechsel dauerhaft pro Kopf (`switch_count` in `extruder` … `extruder3`, Quelle: `ExtruderSwitchRecorder` in u1-klipper `klippy/kinematics/extruder.py`). Ältere Firmware ohne diese Felder: Die beiden Sensoren sind dann *nicht verfügbar*, die Karte blendet die Zeilen aus.

Einen Zähler pro Druck hat die Firmware nicht. Die Integration merkt sich den Stand bei Druckbeginn und bildet die Differenz bei Druckende. Der Stand wird gespeichert und übersteht einen Neustart von Home Assistant während des Drucks. Mitgezählt wird jeder Wechsel im Druckzeitraum, also auch Aufnahmen für Kalibrierungen am Druckanfang. Läuft Home Assistant während eines ganzen Drucks nicht, fehlt dieser Druck.

Die Wartungsschwelle ist der Firmware-Standard von 25 100 Wechseln je Kopf. Ab 90 % färbt die Karte den Wert gelb. Zurücksetzen nach einer Wartung: `RESET_EXTRUDER_MAINTENANCE_COUNT` in der Konsole.

## Strom, Kosten und Historie

- **Verbrauch je Druck** ist die Differenz des Energiezählers zwischen Druckbeginn und -ende.
- **Stromkosten** werden laufend aufsummiert (Verbrauch seit der letzten Abfrage × Preis in diesem Moment). Dynamische Tarife rechnen so richtig.
- **Filamentkosten**: Gewicht je Material aus den Slicer-Daten der Datei × Preis je kg. Bei abgebrochenen Drucken wird das Gewicht im Verhältnis gefördertes/geplantes Filament gekürzt. Fehlt für ein verwendetes Material ein Preis, entfallen die Filamentkosten statt einer falschen Summe.
- **Gesamtkosten im Verlauf** (Kachel und Diagramm): Drucke, die die Integration erfasst hat, mit ihren echten Kosten (Filament + Strom). Ältere Drucke aus Moonraker, also vor der Installation, werden mit dem Filamentpreis geschätzt; die Kachel zeigt dann „≈“. Damit passen Summe und Material-Tabelle zusammen. *Strom* zählt nur gemessene Drucke.
- **Auto-Aus** greift nur nach *fertig* oder *abgebrochen*, nie nach einem Fehler, und erst wenn alle Düsen und das Bett unter der eingestellten Temperatur sind.
- Ist der Drucker aus, zeigt die Karte Einschalten, Dateien (bei Auto-Ein), Historie und Zeitraffer. Die Filamentzuordnung nutzt dann den Stand vor dem Ausschalten.

**Vorschaubilder** bekommen je nach Helligkeit des Teils einen passenden Grund: dunkle Teile (schwarzes Filament) einen hellen, sehr helle einen dunklen. Die Karte misst dazu die mittlere Helligkeit der deckenden Pixel; Bilder ohne Transparenz bleiben unverändert.

**Kosten vor dem Druck.** Der Startdialog zeigt „≈ 0,48 €“ und darunter die Aufteilung. Filament: Gewicht je Material aus den Slicer-Daten × Preis je kg (fehlt ein Preis, entfällt dieser Teil). Strom: geschätzte Druckzeit × mittlere Leistung aller bisherigen Drucke ab 10 min (Energie ÷ Dauer aus der Historie) × aktueller Strompreis. Vor dem ersten gemessenen Druck gibt es nur den Filamentteil.

## Live-Verbindung und Benachrichtigungen

Die Integration abonniert bei Moonraker `print_stats`, `toolhead.extruder`, `virtual_sdcard` und `exception_manager` (`printer.objects.subscribe`). Moonraker schickt nur Änderungen, höchstens alle 250 ms. Statuswechsel und neue Meldungen lösen sofort einen Abgleich aus, ein Kopfwechsel aktualisiert die Karte direkt, und die Schichtansicht holt ihre Dateiposition aus dem Abo statt beim Drucker. Steht das Abo, fragt die Integration nur alle 30 s nach (sonst alle 10 s). Bricht die Verbindung ab, verbindet sie mit 5–60 s Abstand neu; bei ausgeschaltetem Drucker gar nicht.

| Anlass | Wann |
|---|---|
| Meldung vom Drucker | neue Firmware-Meldung, während gedruckt wird. Pausiert der Drucker deshalb, kommt nur die Pause-Meldung (mit dem Text) |
| Erste Schicht fertig | Wechsel von Schicht 1 auf 2. Wer erst mitten im Druck einsteigt (Neustart von HA), bekommt keine |
| Gleich fertig | Restzeit (siehe unten) unter der eingestellten Minutenzahl, einmal je Druck |
| Filament reicht nicht | beim Druckstart, wenn laut Spoolman eine Spule weniger Rest hat als die Datei auf diesem Kopf braucht |
| Spule läuft gleich leer | im Druck, wenn eine Spule laut Zeitprofil in weniger als 30 min leer ist. Mit Hinweis, ob die Firmware per **Auto-Nachfüllen** von einem Kopf mit gleichem Material (und gleicher Farbe, außer „Farbe ignorieren“ ist am Drucker an) weitermacht oder pausieren wird |
| Teil entnehmbar | nach einem fertigen Druck, sobald das Bett unter die eingestellte Temperatur (35 °C) gefallen ist |

**Knöpfe in der Benachrichtigung** (Companion-App): bei Meldungen während des Drucks *Pausieren* und *Licht*, bei Pause *Fortsetzen* und *Abbrechen …*. Abbrechen fragt mit einer zweiten Benachrichtigung nach („Ja, abbrechen“), ein versehentlicher Tipp bricht also nichts ab. Die Knöpfe wirken nur, solange der Zustand passt (Pausieren nur im Druck usw.).

**Restzeit.** Beim Druckstart lädt die Integration die Datei einmal vom Drucker und erstellt ein Zeitprofil: je Dateiposition die Fahrzeit (Strecke ÷ Vorschub, Pausen per G4) und das geförderte Filament je Werkzeug. Daraus zwei Schätzungen: Slicer-Gesamtzeit nach dem Profil verteilt, und gemessene Dauer × Rest ÷ Erledigtes. Am Anfang zählt der Slicer, gegen Ende die gemessene Geschwindigkeit. Ergebnis als Sensoren *Restzeit* und *Fertig um*; die Karte, „Gleich fertig“ und Assist nutzen sie. Ohne Profil (Datei nicht lesbar) gilt der Dateifortschritt.

**Ergebnisfoto.** Mit eingestellter Kamera speichert die Integration direkt nach der letzten Bahn ein Bild – sobald die Dateiposition die letzte Extrusion erreicht (+2 s, weil Klipper der Bewegung vorausliest), also bevor der End-G-Code das Bett absenkt. Ohne Zeitprofil: in der letzten Schicht ab 99,5 %. Bei Abbruch oder Fehler entsteht das Bild in dem Moment. Es liegt unter `.storage/snapmaker_u1_card/thumbs/<Eintrag>/results/` und erscheint in der Historie neben dem Vorschaubild; Antippen vergrößert es in der Karte (Antippen oder Esc schließt). Gespeichert bleiben die Fotos der Drucke in der Historie.

## Dateiverwaltung

Über der Dateiliste: Suche (über **alle** Dateien auf dem Drucker, nicht nur die neuesten), Sortierung (neueste, Name, Druckzeit) und Ordner-Chips. Ältere Treffer erscheinen als Liste; Antippen lädt Metadaten und Vorschau nach und öffnet den Druckdialog. Im Druckdialog: *Umbenennen / verschieben* (Unterordner mit `/`, werden angelegt) und *Löschen*. Beides ist gesperrt, solange die Datei gedruckt wird oder in der Warteschlange steht. Dienste: `file_details`, `move_file`, `delete_file`.

## Temperaturverlauf

Im Reiter *Steuerung*: Ist- und Solltemperatur der aktiven Köpfe und des Betts der letzten 20 Minuten. Die Daten speichert Moonraker ohnehin (`/server/temperature_store`); die Karte holt sie alle 10 s über die Integration, nur solange der Reiter sichtbar ist.

## Leerlauf-Abschaltung

Option *Ausschalten nach Leerlauf* (Stunden, 0 = aus): Läuft kein Druck, ist keine Heizung an (auch kein Vorheizen am Display) und ist das länger her als eingestellt, fährt die Integration den Drucker sauber herunter und schaltet die Steckdose aus. Die Firmware selbst kennt nur `idle_timeout` (Heizung und Motoren aus nach 10 min), schaltet aber nie ab.

## Firmware und Selbsttest

- **Update-Entität „Firmware“**: installiert laut Drucker (`/machine/system_info`), neueste aus Snapmakers Release-Commits der Firmware-Quellen auf GitHub (`Snapmaker/u1-moonraker`, `Snapmaker/u1-klipper`), einmal am Tag. Installiert wird weiter am Drucker (Display oder Snapmaker-App); die Entität meldet nur. Hinweis: Snapmaker kann die Veröffentlichung auf GitHub ändern; dann bleibt „neueste“ beim letzten bekannten Stand.
- **Selbsttest** (*System*-Reiter oder Dienst `self_test`): Drucker und Klipper, Live-Verbindung, Firmware, freier Speicher am Drucker (Warnung unter 500 MiB), Moonraker-Integration, Kamera (holt ein Bild), Netzschalter/Energie/Preis-Entitäten, Benachrichtigungsdienste, Spoolman, Assist-Sätze, Medienordner. ✓ in Ordnung, ! Hinweis, ✗ Fehler.

## Statistik je Material

Unter den Monatsdiagrammen: Drucke, Verbrauch, Kosten und Erfolgsquote je Material sowie die meistgenutzten Farben – aus Moonrakers Druckhistorie, also rückwirkend. Abgebrochene Drucke zählen anteilig.

## Sprachsteuerung (Assist)

Die Integration meldet drei Intents an und legt die Sätze unter `/config/custom_sentences/de/snapmaker_u1_card.yaml` (bzw. `en/`) ab:

- „Wie weit ist der Drucker?“, „Wie lange braucht der 3D-Drucker noch?“, „Was macht der Drucker?“, „Status vom Drucker“ → z. B. „benchy ist bei 40 Prozent, Schicht 121 von 300, noch etwa 6 Minuten.“
- „Pausiere den Drucker“, „Druck pausieren“
- „Drucker fortsetzen“, „Setze den Druck fort“, „Druck weiter“

Englisch: „How far is the printer?“, „Pause the printer“, „Resume the print“. Die Dateien aktualisiert die Integration bei jedem Start. Wer eigene Sätze pflegen will, löscht die erste Zeile (`# snapmaker_u1_card: automatisch erzeugt`), dann bleibt die Datei unberührt. Abbrechen per Sprache gibt es absichtlich nicht.

## Sicherung der Drucker-Konfiguration

Einmal am Tag, nie während eines Drucks, holt die Integration alle Dateien aus Moonrakers Wurzel `config` (printer.cfg, moonraker.conf, Makros …) nach `/config/snapmaker_u1_backup/<Drucker>/<Datum_Uhrzeit>/`. Ein neuer Stand entsteht nur, wenn sich etwas geändert hat; die letzten 10 bleiben. Logs, Datenbanken und Dateien über 2 MB werden übersprungen. Weil die Sicherungen im HA-Konfigordner liegen, sind sie auch in jedem Home-Assistant-Backup. Der letzte Stand steht in der Karte unter *System → Wartung*, mit Knopf zum sofortigen Sichern.

## Spulenverwaltung mit Spoolman

Optional. Ohne Spoolman-Adresse erscheint in Karte und Integration nichts davon.

**Zuordnung Spule → Kopf.** Moonraker kennt für Spoolman nur *eine* aktive Spule; bei vier Köpfen übernimmt das die Integration selbst. Je geladenem Kopf wird eine aktive (nicht archivierte) Spule gesucht:

1. gleiches Material (`PLA-CF` passt zu `PLA`),
2. ähnliche Farbe (Spule ohne Farbangabe: nur Material). Weicht die Farbe deutlich ab, wird **nichts** zugeordnet. Eine falsche Spule wäre schlimmer, weil von ihr abgebucht würde,
3. Unterart im Namen (z. B. „Silk“), gleicher Hersteller,
4. angebrochene, zuletzt benutzte Spule vor neuer.

Jede Spule wird höchstens einem Kopf zugeordnet. In der Karte tippst du auf die Spulenzeile eines Kopfes und wählst „Automatisch“, „Keine Spule“ oder eine bestimmte Spule. Eine manuelle Wahl bleibt bestehen, bis in dem Kopf ein anderes Filament erkannt wird (Material, Farbe oder Hersteller ändern sich) oder die Spule in Spoolman archiviert wird.

**Abbuchen.** Nach jedem Druck bucht die Integration je Kopf ab: Gewicht laut Slicer je Filament, über die Zuordnungstabelle des Drucks (`print_task_config.extruder_map_table`) auf die Köpfe verteilt; bei Abbruch anteilig nach tatsächlich geförderter Länge. Ist Spoolman gerade nicht erreichbar, wird die Buchung gespeichert und nachgeholt, auch über einen Neustart von Home Assistant hinweg. Die Historie zeigt je Druck `#Spule −g` (⏳ = noch nicht gebucht).

> **Nicht doppelt buchen:** Bucht bereits etwas anderes ab (z. B. ein `[spoolman]`-Abschnitt in Moonrakers Konfiguration oder paxx12 SpoolLink), in der Integration *Verbrauch abbuchen* ausschalten.

Grenzen: Wechselt die Firmware mitten im Druck automatisch auf einen anderen Kopf (Auto-Nachfüllen bei leerer Spule), wird der gesamte Verbrauch dem zuletzt gemeldeten Kopf zugerechnet.

Dienst zum Zuordnen, z. B. für Automationen:

```yaml
action: snapmaker_u1_card.set_spool
data:
  slot: 2        # Kopf 1–4
  spool_id: 12   # 0 = keine Spule; weglassen = wieder automatisch
```

Die Spule je Kopf steht auch an `sensor.…_slot_1` … `_slot_4` (Attribute `spool`, `spool_remaining`), z. B. für eine Benachrichtigung bei wenig Restfilament.

## Zeitraffer

Die Stock-Firmware legt Zeitraffer im Moonraker-Ordner `camera` ab (`Name_JJJJMMTThhmmss.mp4` mit `_cover.jpg`). Die Integration durchsucht alle Ordner außer Konfiguration und Logs, findet also auch Fluidd-Zeitraffer (`timelapse`). Abgespielt wird über einen angemeldeten Proxy der Integration mit kurzlebig signierten Links. Er liefert nur Dateien aus der Liste aus, nie beliebige Pfade vom Drucker.

**Sichern.** Mit *Zeitraffer sichern* kopiert die Integration jedes neue Video samt Vorschaubild nach `<Medien>/snapmaker_u1/` (im Medienbrowser unter „Lokale Medien“, in der Karte unter „Gesichert in Medien“, abspielbar auch bei ausgeschaltetem Drucker). Während eines Drucks wird nicht kopiert.

**Auf dem Drucker aufräumen.** Moonraker gibt den Ordner `camera` nur lesend frei; löschen kann nur Snapmakers interner Kameradienst (`camera.delete_timelapse_instance`), dessen Parameter nicht dokumentiert sind. Die Integration löscht deshalb nur Videos, die vollständig gesichert sind, sichert vorher immer alles, ermittelt die Parameterform beim ersten Mal und merkt sie sich. Lehnt der Dienst alle Formen ab, bleibt alles stehen und die Karte zeigt „Löschen auf dem Drucker wird von der Firmware nicht unterstützt“.

## Schichtansicht

Sobald die Karte die Schichtansicht während eines Drucks zum ersten Mal anfragt, lädt die Integration die Datei einmal vom Drucker und zerlegt sie in Schichten (`;LAYER_CHANGE` bzw. `SET_PRINT_STATS_INFO`). Die Karte holt nur die aktuelle Schicht (`/api/snapmaker_u1_card/layers/…`, angemeldet) und alle 5 s die Dateiposition (`virtual_sdcard.file_position`, aus dem Live-Abo, ohne Anfrage beim Drucker): was davor liegt, ist gedruckt. Farbe je Filament: Kopf laut Zuordnung → Farbe der dort geladenen Spule, sonst die Farbe aus der Datei. Bögen (G2/G3) werden in kurze Stücke zerlegt, Punkte näher als 0,35 mm zusammengefasst. Bei großen Dateien dauert die Vorbereitung einige Sekunden.

## Druckermeldungen

Die U1-Firmware meldet Fehler strukturiert (Modul, Kopf, Code). Die Integration übersetzt bekannte Codes, z. B. „Filament leer (Kopf 2)“, „Vorladen: kein Filament erkannt“, „Spaghetti erkannt“, „PEI-Platte liegt nicht richtig“, und hängt einen Hinweis an. Unbekannte Codes erscheinen mit der Rohmeldung der Firmware. Die Meldungen stehen oben in der Karte, in Benachrichtigungen bei Fehler/Pause und in der Historie.

## Fehlersuche

- **Karte zeigt keine Temperaturen, kein Licht, keine Kamera**: Die Moonraker-Integration fehlt oder ist nicht verbunden (siehe [Installation](#1-moonraker-integration)). Der Selbsttest meldet das.
- **Integration findet den Drucker nicht**: IP prüfen (`http://<IP>/server/info` im Browser muss JSON zeigen), Port 80, Drucker eingeschaltet. Nach einem IP-Wechsel: *Geräte & Dienste → Snapmaker U1 Card → ⋮ → Neu konfigurieren* (Einstellungen und Historie bleiben). Besser eine feste IP vergeben.
- **„401/403“ von Moonraker** (geänderte Firmware mit Anmeldung): API-Schlüssel aus der Weboberfläche des Druckers bei der Einrichtung eintragen.
- **Kamerabild friert ein**: Prüf, ob noch ein Kamera-Keepalive-Add-on oder eine zweite Kamera-Entität auf den Drucker zugreift. Mit `camera_mode: still` testen.
- **„Custom element doesn't exist: snapmaker-u1-card“**: Die Seite wurde während eines Neustarts von Home Assistant geladen, und die Ressource unter *Dashboards → Ressourcen* fehlt (oder `/config/www` war beim Start neu). Seite neu laden; bleibt es, prüfen, ob die Ressource `/local/snapmaker_u1_card/…` existiert.
- **Zeitraffer aus der Sicherung spielen nicht ab**: Die Karte holt die Adresse über die Medienquelle von Home Assistant. Ohne `default_config` muss `media_source:` in der `configuration.yaml` stehen.
- **Dashboard oder Karten-Auswahl lädt endlos**: Home Assistant spricht HTTP/1.1, auch über HTTPS und Nabu Casa (dort wird die TLS-Verbindung nur durchgereicht). Der Browser öffnet dann höchstens 6 gleichzeitige Verbindungen zu Home Assistant, für alle Tabs und Fenster zusammen. Jede hängende Anfrage belegt eine davon; sind alle belegt, kann das Frontend keinen Code mehr nachladen. Die Karte vermeidet das: Livestream nur, solange sie sichtbar ist und nie im Bearbeitungsmodus; Zeitraffer-Vorschaubilder kommen aus Home Assistant selbst (keine Anfrage an den Drucker); Videos werden bei ausgeschaltetem Drucker gar nicht erst angefragt. Andere Live-Kameras (z. B. Frigate) auf `camera_view: auto` stellen. Prüfen: F12 → Netzwerk; Anfragen mit Status „pending“/„stalled“ zeigen, was hängt.
- **„Druckstart abgelehnt“**: Den Text liefert der Drucker, z. B. „Printer is busy“ oder einen Düsenkonflikt.
- **Kein Icon unter Geräte & Dienste**: Eigene Icons zeigt Home Assistant ab 2026.3. In der HACS-Liste zeigen derzeit alle eigenen Integrationen einen grauen Platzhalter; das ist ein bekannter HACS-Fehler ([hacs/integration#5171](https://github.com/hacs/integration/issues/5171)) und erledigt sich mit einem HACS-Update.
- **Kamerabild bleibt nach einer Weile stehen (Stock-Firmware)**: In den Optionen der Integration *Kamera wach halten* einschalten. Sie schickt alle 10 s `camera.start_monitor`, wie die Snapmaker-App.
- **Keine Benachrichtigung**: Dienstname prüfen (Entwicklerwerkzeuge → Aktionen → `notify.mobile_app_…`). Das Kamerabild hängt nur die Companion-App an.
- **Diagnose**: *Geräte & Dienste → Snapmaker U1 Card → ⋮ → Diagnose herunterladen*. Enthält Optionen, Zustand des Live-Abos, Rohstatus des Druckers, Fehler und Warteschlange; Adresse, API-Schlüssel, Spoolman-Adresse und Benachrichtigungsziele sind geschwärzt.
- **Sprachbefehl wird nicht erkannt**: Unter *Entwicklerwerkzeuge → Assist* den Satz testen. Steht dort eine andere Absicht, kollidiert er mit einem eingebauten Satz; dann eigene Sätze in der Datei ergänzen (erste Zeile löschen, siehe oben).
- **Keine Dateien**: Unter *Geräte & Dienste → Snapmaker U1 Card* prüfen, ob die Integration verbunden ist. Danach den Dienst `refresh` aufrufen.

## Unterstützen

Die Integration ist kostenlos. Wer sich bedanken möchte: Ein Stern auf GitHub, Rückmeldungen als Beta-Tester und gemeldete Fehler helfen am meisten – und wer mag, spendiert einen Kaffee:

[![Unterstützen auf Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/ironoxx)

## Lizenz

MIT – siehe [LICENSE](LICENSE). Ohne Gewähr.
