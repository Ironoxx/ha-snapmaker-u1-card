# Changelog

Each `## x.y.z` section becomes the text of the GitHub release, which HACS shows
in the update dialog. Newest first. After updating: restart Home Assistant and
reload the dashboard (the card shows a hint if the browser still has the old one).

## 2.1.0b2

Beta. Spoolman stock and suggestions for new spools. Includes everything from 2.1.0b1 (top cover mode and chamber target, chamber-warm notification, real filter hours, chamber heater in the chart, camera keeps running when the card rebuilds).

**Spoolman stock**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold).
- Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`.

**New spool with suggestions**
- Typing in *Search filament* shows your own Spoolman filaments first, then matches from Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the same suggestions Spoolman's own interface uses; 1.75 mm only, fetched once a day).
- A pick fills vendor, material, name, colour, net weight and empty spool weight. An own filament is used as it is; a catalogue entry is imported into Spoolman once (with colour, density and temperatures) and reused afterwards.
- Vendor and material fields suggest the known names. New fields: location, and in the *Spoolman* tab the head to assign (or none). Picking a spool for a head stays under the print heads.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`; `material` is optional with either ID.
- The catalogue needs Spoolman 0.18 or newer with internet access; otherwise only your own filaments are suggested.

### Deutsch

Beta. Spoolman-Bestand und Vorschläge für neue Spulen. Enthält alles aus 2.1.0b1 (Top-Cover-Modus und Kammer-Soll, Meldung „Kammer ist warm“, echte Filterstunden, Kammerheizung im Verlauf, Kamera läuft beim Neuaufbau der Karte weiter).

**Spoolman-Bestand**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle).
- Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`.

**Neue Spule mit Vorschlägen**
- Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann Treffer aus dem Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm, einmal am Tag geladen).
- Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule. Ein eigenes Filament wird so genommen; ein Katalog-Eintrag wird einmal in Spoolman übernommen (mit Farbe, Dichte und Temperaturen) und danach wiederverwendet.
- Hersteller und Material schlagen bekannte Namen vor. Neu: Ort, und im Reiter *Spoolman* der Kopf zum Zuordnen (oder keiner). Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`; `material` ist mit einer der IDs optional.
- Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang; sonst werden nur deine eigenen Filamente vorgeschlagen.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.0b1

Beta. Top cover and chamber heater features, and a smoother camera away from home.

**Testers wanted:** I built the top cover and Panda Breath / DragonBreath parts from the firmware without owning the hardware. If you have one, please try it and report back in an [issue](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues), ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Top cover**
- Mode right in the card (chips on the top cover panel) and as `select.…_top_cover_mode`: idle, cool, preheat, hot (`SET_PURIFIER_MODE`).
- Chamber target as a slider (presets 35/45/55 °C, up to 70 °C) and as `number.…_top_cover_chamber_target`.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover instead of print hours.

**Chamber heater and notifications**
- New notification *Chamber is warm* (event `chamber_ready`, off by default): once when the chamber heater (Panda Breath / DragonBreath) or the top cover in preheat/hot reaches its target. A new target arms it again; no message after a restart.
- The temperature chart shows the chamber heater with its target.

**Camera**
- Away from home (Nabu Casa) the stream through Home Assistant restarted every time the card rebuilt (pause, Spoolman weight, maintenance progress and so on): HA's player closes its connection when it leaves the page. The camera frame now stays in place during a rebuild. With `debug_camera: true` the browser console shows what caused a rebuild.

### Deutsch

Beta. Funktionen für Top Cover und Kammerheizung, und eine ruhigere Kamera unterwegs.

**Tester gesucht:** Top Cover und Panda Breath / DragonBreath habe ich nach der Firmware gebaut, ohne die Hardware selbst zu haben. Wer eins hat: bitte ausprobieren und als [Issue](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues) melden, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Top Cover**
- Modus direkt in der Karte (Chips im Top-Cover-Bereich) und als `select.…_top_cover_modus`: Leerlauf, Kammer kühlen, vorheizen, heiß (`SET_PURIFIER_MODE`).
- Kammer-Soll als Regler (Schnellwerte 35/45/55 °C, bis 70 °C) und als `number.…_top_cover_kammer_soll`.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover statt Druckstunden.

**Kammerheizung und Benachrichtigungen**
- Neue Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus): einmal, wenn die Kammerheizung (Panda Breath / DragonBreath) oder die Top Cover beim Vorheizen/Heiß ihr Soll erreicht. Ein neues Soll schaltet sie wieder scharf; nach einem Neustart keine Meldung.
- Der Temperaturverlauf zeigt die Kammerheizung mit ihrem Soll.

**Kamera**
- Unterwegs (Nabu Casa) startete der Stream über Home Assistant bei jedem Neuaufbau der Karte neu (Pause, Spoolman-Gewicht, Wartungsfortschritt usw.): Der Player von HA baut seine Verbindung ab, sobald er die Seite verlässt. Der Kamerarahmen bleibt beim Neuaufbau jetzt stehen. Mit `debug_camera: true` zeigt die Browser-Konsole, was einen Neuaufbau ausgelöst hat.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0

**No Moonraker integration needed any more.** The card used to need a second integration for temperatures, fans, light, axes, layer and most controls. Since 2.0 the Snapmaker U1 Card integration talks to the printer itself for all of it. One integration, one setup, and everything reacts faster: values arrive over the live connection within about a second instead of every 30 s. Thanks to everyone who tested the seven betas!

**Straight from the printer**
- All printer values: temperatures (bed, four nozzles, chamber, stepper drivers), targets and heater power, fans, light, outputs, filament sensors, axis position, speed, layer, progress, MCU load, CPU temperature and load, memory, job queue and print totals. The objects come from the printer's object list, so modified configurations work too.
- All controls: pause, resume, cancel, emergency stop, homing (locked during a print), target temperatures, part and chamber fan, speed, chamber light and switches. New service `machine_command` for automations; only objects the printer reports are accepted and values are clamped.
- New entities: temperatures, progress, print state, layer, targets, part fan, speed, buttons, chamber light and the diagnostic sensors *Printer values* and *CPU temperature*.
- An existing Moonraker integration may stay as a fallback, or be disabled or removed.

**Settings in the card**
- *System → Settings* (admins): the same settings as *Configure* in Home Assistant, grouped, with the current value next to each chosen entity and the Spoolman price next to each filament price. Same checks as in Home Assistant; only changed sections are saved.

**Camera**
- Away from home (Nabu Casa) the card plays the RTSP stream through Home Assistant instead of MJPEG through the proxy: H.264, far less data, smooth. At home the direct WebRTC stays. Without RTSP (stock firmware) nothing changes. Option `camera_ha_stream`.
- The zoom goes back after 60 s without interaction and whenever you leave the page (option `camera_zoom_reset`).

**Temperature chart**
- Besides heads and bed: chamber, X/Y stepper drivers (while the motors run), CPU and any further temperature sensor of the printer configuration. Tap an entry in the legend to hide or show its line.

**Spoolman**
- Create a spool right from the card, prefilled with the head's filament; vendor and filament are reused or created. Service `create_spool`.
- Filament prices from Spoolman: the spool in each head counts at the end of a print, otherwise the Spoolman average per material; your own prices fill the gaps.

**Fixes since 1.6.3**
- "Second camera found" without a USB camera (paxx12 lists the built-in camera twice).
- Stepper temperatures now appear in the card once the motors are on.

**Good to know when updating**
- Restart Home Assistant and reload the dashboard.
- Best do without the Moonraker integration now: it queries the printer a second time and only adds load. *Settings → Devices & services → Moonraker → ⋮ → Disable* (or remove it). Your own automations with its entities need the new entities instead.
- The README is shorter now; details moved to the [docs](https://github.com/Ironoxx/ha-snapmaker-u1-card/tree/main/docs).

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Keine Moonraker-Integration mehr nötig.** Bisher brauchte die Karte für Temperaturen, Lüfter, Licht, Achsen, Schicht und die meisten Steuerungen eine zweite Integration. Seit 2.0 spricht die Integration Snapmaker U1 Card dafür selbst mit dem Drucker. Eine Integration, eine Einrichtung, und alles reagiert schneller: Werte kommen über die Live-Verbindung innerhalb etwa einer Sekunde statt alle 30 s. Danke an alle, die die sieben Betas getestet haben!

**Direkt vom Drucker**
- Alle Druckerwerte: Temperaturen (Bett, vier Düsen, Innenraum, Schrittmotortreiber), Sollwerte und Heizleistung, Lüfter, Licht, Ausgänge, Filamentsensoren, Achsposition, Geschwindigkeit, Schicht, Fortschritt, MCU-Last, CPU-Temperatur und -Last, Speicher, Warteschlange und Druckstatistik. Die Objekte kommen aus der Objektliste des Druckers, geänderte Konfigurationen funktionieren also auch.
- Alle Steuerungen: Pause, Fortsetzen, Abbrechen, Not-Halt, Referenzfahrt (im Druck gesperrt), Solltemperaturen, Bauteil- und Innenraumlüfter, Geschwindigkeit, Innenraumlicht und Schalter. Neuer Dienst `machine_command` für Automationen; nur Objekte, die der Drucker meldet, Werte werden begrenzt.
- Neue Entitäten: Temperaturen, Fortschritt, Druckstatus, Schicht, Sollwerte, Bauteillüfter, Geschwindigkeit, Knöpfe, Innenraumlicht und die Diagnose-Sensoren *Druckerwerte* und *CPU-Temperatur*.
- Eine vorhandene Moonraker-Integration darf als Rückfall bleiben oder deaktiviert bzw. entfernt werden.

**Einstellungen in der Karte**
- *System → Einstellungen* (Admins): dieselben Einstellungen wie *Konfigurieren* in Home Assistant, gegliedert, mit dem aktuellen Wert neben jeder gewählten Entität und dem Spoolman-Preis neben jedem Filamentpreis. Dieselben Prüfungen wie in Home Assistant; gespeichert werden nur geänderte Bereiche.

**Kamera**
- Unterwegs (Nabu Casa) spielt die Karte den RTSP-Stream über Home Assistant ab statt MJPEG über den Proxy: H.264, viel weniger Daten, flüssig. Zu Hause bleibt das direkte WebRTC. Ohne RTSP (Stock-Firmware) ändert sich nichts. Option `camera_ha_stream`.
- Der Zoom geht nach 60 s ohne Bedienung und beim Verlassen der Seite zurück (Option `camera_zoom_reset`).

**Temperaturverlauf**
- Neben Köpfen und Bett: Innenraum, Schrittmotortreiber X/Y (solange die Motoren laufen), CPU und jeder weitere Temperatursensor der Druckerkonfiguration. Ein Tipp auf einen Eintrag der Legende blendet die Linie aus oder ein.

**Spoolman**
- Neue Spule direkt aus der Karte anlegen, vorausgefüllt mit dem Filament des Kopfs; Hersteller und Filament werden wiederverwendet oder angelegt. Dienst `create_spool`.
- Filamentpreise aus Spoolman: Am Druckende zählt die Spule im jeweiligen Kopf, sonst der Spoolman-Durchschnitt je Material; eigene Preise füllen die Lücken.

**Behoben seit 1.6.3**
- „Zweite Kamera gefunden“ ohne USB-Kamera (paxx12 listet die eingebaute Kamera doppelt).
- Stepper-Temperaturen erscheinen jetzt in der Karte, sobald die Motoren laufen.

**Gut zu wissen beim Update**
- Home Assistant neu starten und das Dashboard neu laden.
- Am besten verzichtest du jetzt auf die Moonraker-Integration: Sie fragt den Drucker ein zweites Mal ab und belastet ihn nur zusätzlich. *Einstellungen → Geräte & Dienste → Moonraker → ⋮ → Deaktivieren* (oder entfernen). Eigene Automationen mit deren Entitäten brauchen dann die neuen Entitäten.
- Das README ist jetzt kürzer; die Details stehen in den [Docs](https://github.com/Ironoxx/ha-snapmaker-u1-card/tree/main/docs/de).

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b7

**Seventh beta of 2.0.** Installs only with *Show beta versions* turned on for this repository in HACS. Everything from b1–b6 is included (details below).

**New**
- **Smooth camera away from home:** over Nabu Casa (or another way without a direct path to the printer) the card used to fall back to MJPEG through the HA proxy – choppy, like the stock firmware. With RTSP enabled (paxx12) it now plays the RTSP stream through Home Assistant's own streaming (WebRTC via HA with Nabu Casa's relay servers, else HLS): H.264, far less data, smooth. With Nabu Casa it no longer waits 8 s for a direct WebRTC attempt that cannot work. At home the direct WebRTC stays (fastest). Without RTSP (stock firmware) nothing changes. Card option `camera_ha_stream: off` turns it off.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Siebte Beta von 2.0.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus b1–b6 ist enthalten (Details unten).

**Neu**
- **Flüssige Kamera unterwegs:** Über Nabu Casa (oder einen anderen Weg ohne direkte Verbindung zum Drucker) fiel die Karte bisher auf MJPEG über den HA-Proxy zurück – ruckelig wie bei der Original-Firmware. Mit eingeschaltetem RTSP (paxx12) spielt sie jetzt den RTSP-Stream über das eigene Streaming von Home Assistant ab (WebRTC über HA mit den Vermittlungsservern von Nabu Casa, sonst HLS): H.264, viel weniger Daten, flüssig. Bei Nabu Casa wartet sie nicht mehr 8 s auf einen direkten WebRTC-Versuch, der dort nicht klappen kann. Zu Hause bleibt das direkte WebRTC (am schnellsten). Ohne RTSP (Stock-Firmware) ändert sich nichts. Kartenoption `camera_ha_stream: off` schaltet es ab.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b6

**Sixth beta of 2.0.** Installs only with *Show beta versions* turned on for this repository in HACS. Everything from b1–b5 is included (details below).

**New**
- **CPU temperature of the printer's computer:** Moonraker sends it once a second; the integration records it for the temperature chart (last 20 minutes, can be hidden via the legend like every line), shows it in the *System* tab and offers it as a diagnostic sensor *CPU temperature*. Useful in a closed enclosure with ABS/ASA.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Sechste Beta von 2.0.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus b1–b5 ist enthalten (Details unten).

**Neu**
- **CPU-Temperatur des Rechners im Drucker:** Moonraker sendet sie jede Sekunde; die Integration zeichnet sie für den Temperaturverlauf auf (letzte 20 Minuten, wie jede Linie über die Legende ausblendbar), zeigt sie im Reiter *System* und bietet sie als Diagnose-Sensor *CPU-Temperatur* an. Nützlich im geschlossenen Gehäuse mit ABS/ASA.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b5

**Fifth beta of 2.0.** Installs only with *Show beta versions* turned on for this repository in HACS. Everything from b1–b4 is included (details below).

**New**
- **Temperature chart with chamber and stepper drivers:** besides the heads and the bed, the chart in the *Control* tab now shows the chamber air and the X/Y stepper drivers (while the motors are on – gaps when they are off). Further temperature sensors in the printer configuration (e.g. added by a mod) show up automatically. Tap an entry in the legend to hide or show its line; the choice is remembered per browser.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Fünfte Beta von 2.0.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus b1–b4 ist enthalten (Details unten).

**Neu**
- **Temperaturverlauf mit Innenraum und Schrittmotortreibern:** Neben Köpfen und Bett zeigt das Diagramm im Reiter *Steuerung* jetzt auch die Innenraumluft und die Treiber X/Y (solange die Motoren an sind – Lücken, wenn sie aus sind). Weitere Temperatursensoren aus der Druckerkonfiguration (z. B. durch einen Mod) erscheinen automatisch. Ein Tipp auf einen Eintrag der Legende blendet die Linie aus oder ein; die Wahl merkt sich der Browser.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b4

**Fourth beta of 2.0 – fixes from testing b3.** Installs only with *Show beta versions* turned on for this repository in HACS. Everything from b1–b3 is included (details below).

**Fixed**
- Chamber temperature, part fan and speed stayed *unavailable*: these values only arrive once the printer's object list is known, and their entities were only created at the very first update. Each entity is now created as soon as its value shows up; existing entries are taken over.
- Stepper temperatures (X/Y) never appeared in the card: Klipper only reports the driver temperature while the motors are on, and the rows were only built at the first render. They now appear after homing or during a print and disappear when the motors switch off.

**Improved**
- Settings in the card: long lists of notify services fold away (chosen ones first), long names wrap, correct singular ("1 target", "1 material").
- Diagnostics include the printer values, the object list and the subscription.
- README: screenshot of the settings in the card.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Vierte Beta von 2.0 – Korrekturen aus dem Test von b3.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus b1–b3 ist enthalten (Details unten).

**Behoben**
- Innenraumtemperatur, Bauteillüfter und Geschwindigkeit blieben *nicht verfügbar*: Diese Werte kommen erst, wenn die Objektliste des Druckers bekannt ist, und ihre Entitäten wurden nur beim allerersten Abruf angelegt. Jetzt entsteht jede Entität, sobald ihr Wert auftaucht; vorhandene Einträge werden übernommen.
- Stepper-Temperaturen (X/Y) erschienen nie in der Karte: Klipper meldet die Treibertemperatur nur bei eingeschalteten Motoren, und die Zeilen wurden nur beim ersten Aufbau angelegt. Jetzt erscheinen sie nach der Referenzfahrt oder im Druck und verschwinden, wenn die Motoren abschalten.

**Verbessert**
- Einstellungen in der Karte: lange Listen von Benachrichtigungsdiensten werden eingeklappt (gewählte zuerst), lange Namen brechen um, richtige Einzahl („1 Ziel“, „1 Material“).
- Die Diagnose enthält die Druckerwerte, die Objektliste und das Abo.
- README: Screenshot der Einstellungen in der Karte.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b3

**Third beta of 2.0 – the last one before 2.0.0.** Installs only with *Show beta versions* turned on for this repository in HACS. Everything from b1 and b2 is included: the card no longer needs the Moonraker integration (details below).

**New**
- **Settings right in the card:** *System → Settings* (admins only). The same options as *Configure* in Home Assistant, but grouped with a short summary per section, the current value next to each chosen entity (e.g. "Thomi 3D: on", "85 W") and the Spoolman price next to each filament price. Only changed sections are saved, with the same checks as in Home Assistant; the integration then reloads briefly.
- **Filament prices from Spoolman:** at the end of a print the price of the spool in each head counts, otherwise the average price per kg of your spools of that material. Your own prices only apply to materials without a price in Spoolman. The print cost sensor now also exists with Spoolman alone.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Dritte Beta von 2.0 – die letzte vor 2.0.0.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus b1 und b2 ist enthalten: Die Karte braucht keine Moonraker-Integration mehr (Details unten).

**Neu**
- **Einstellungen direkt in der Karte:** *System → Einstellungen* (nur für Admins). Dieselben Optionen wie *Konfigurieren* in Home Assistant, aber gegliedert mit kurzer Zusammenfassung je Bereich, dem aktuellen Wert neben jeder gewählten Entität (z. B. „Thomi 3D: an“, „85 W“) und dem Spoolman-Preis neben jedem Filamentpreis. Gespeichert werden nur geänderte Bereiche, mit denselben Prüfungen wie in Home Assistant; die Integration lädt danach kurz neu.
- **Filamentpreise aus Spoolman:** Am Druckende zählt der Preis der Spule im jeweiligen Kopf, sonst der Durchschnittspreis je kg deiner Spulen dieses Materials. Eigene Preise gelten nur für Materialien ohne Preis in Spoolman. Der Sensor für die Druckkosten entsteht jetzt auch mit Spoolman allein.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b2

**Second beta of 2.0** – thanks for testing b1! Installs only with *Show beta versions* turned on for this repository in HACS. Everything from 2.0.0b1 is included: the card no longer needs the Moonraker integration (details below at 2.0.0b1).

**New**
- **Create a spool in Spoolman from the card:** the spool picker has *Create new spool*, prefilled with the head's material, vendor and colour (RFID data if there is a tag). Vendor and filament are reused if they exist, otherwise created; the new spool is assigned to the head right away (with SpoolLink via `SET_SPOOL_ID`). Also as service `snapmaker_u1_card.create_spool`.
- **Camera zoom goes back by itself:** after 60 s without interaction and always when you leave the page, switch apps or scroll the card away. Card option `camera_zoom_reset` (seconds, `0` = never).

**Fixed**
- "Second camera (USB) found" without a USB camera: paxx12 lists the built-in camera twice (MJPEG and WebRTC). Only a webcam in another folder (`/webcam2/`) now counts as a second camera. The entity *Camera 2* then becomes unavailable and can be deleted.
- Self test: disabled Moonraker integration entities are no longer counted.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Zweite Beta von 2.0** – danke fürs Testen von b1! Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist. Alles aus 2.0.0b1 ist enthalten: Die Karte braucht keine Moonraker-Integration mehr (Details unten bei 2.0.0b1).

**Neu**
- **Spule in Spoolman direkt aus der Karte anlegen:** In der Spulenauswahl gibt es *Neue Spule anlegen*, vorausgefüllt mit Material, Hersteller und Farbe des Kopfs (RFID-Daten, wenn ein Tag da ist). Hersteller und Filament werden wiederverwendet, wenn es sie gibt, sonst angelegt; die neue Spule wird dem Kopf sofort zugeordnet (mit SpoolLink per `SET_SPOOL_ID`). Auch als Dienst `snapmaker_u1_card.create_spool`.
- **Kamera-Zoom geht von selbst zurück:** nach 60 s ohne Bedienung und immer, wenn man die Seite verlässt, die App wechselt oder die Karte wegscrollt. Kartenoption `camera_zoom_reset` (Sekunden, `0` = nie).

**Behoben**
- „Zweite Kamera (USB) gefunden“ ohne USB-Kamera: paxx12 listet die eingebaute Kamera doppelt (MJPEG und WebRTC). Als zweite Kamera zählt jetzt nur eine Webcam in einem anderen Ordner (`/webcam2/`). Die Entität *Kamera 2* wird dann nicht verfügbar und kann gelöscht werden.
- Selbsttest: Deaktivierte Entitäten der Moonraker-Integration werden nicht mehr mitgezählt.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 2.0.0b1

**Beta of 2.0 – please test and report back.** Installs only if you turn on *Show beta versions* for this repository in HACS (in the redownload dialog). Everything from 1.6.3 is included.

**No Moonraker integration needed any more.** The card used to need a second integration for temperatures, fans, light, axes, layer and the controls. Since 2.0 the Snapmaker U1 Card integration talks to the printer for all of it itself – over the live subscription it already had, so values arrive within a second instead of every 30 s.

**What's new**
- **All printer values from the integration:** temperatures (bed, all four nozzles, chamber, stepper drivers), target temperatures and heater power, fans (part, chamber, nozzle fans), light, output pins, filament sensors, axes position, speed, layer, progress, MCU load and awake time, system load, memory, job queue and print totals. Objects are taken from the printer's object list, so other configs work too.
- **All controls through the integration:** pause, resume, cancel, emergency stop, homing (all/X/Y/Z, locked during a print), target temperatures, part fan, chamber fan, speed, chamber light and switches. New service `snapmaker_u1_card.machine_command` for automations – only objects the printer reports are accepted, values are clamped.
- **New entities:** printer values (one diagnostic sensor the card reads), bed/nozzle/chamber temperature, progress, print state, layer, target temperatures, part fan, speed, buttons for pause/resume/cancel/emergency stop/homing and the chamber light.
- **Fallback:** an existing Moonraker integration can stay. The card prefers the integration's values and only falls back to the Moonraker entities when its own are missing (e.g. an older backend).
- **Status-light blueprint** also accepts the integration's *Print state* sensor.
- **Self test:** "Values straight from the printer – Moonraker integration not needed" instead of a warning when it is missing.
- Notification button *Light* and the light for the result photo use the integration's own light.

**Good to know**
- Restart Home Assistant and reload the dashboard.
- The Moonraker integration's camera is no longer needed either: the integration has had its own camera since 1.5.
- If you set `prefix` in the card for several printers, keep it: it still selects the printer.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Beta von 2.0 – bitte testen und Rückmeldung geben.** Wird nur installiert, wenn in HACS für dieses Repository *Betaversionen anzeigen* eingeschaltet ist (im Dialog „Erneut herunterladen“). Alles aus 1.6.3 ist enthalten.

**Keine Moonraker-Integration mehr nötig.** Bisher brauchte die Karte für Temperaturen, Lüfter, Licht, Achsen, Schicht und die Steuerung eine zweite Integration. Seit 2.0 spricht die Integration Snapmaker U1 Card dafür selbst mit dem Drucker – über das Live-Abo, das sie ohnehin hatte. Werte kommen dadurch innerhalb einer Sekunde statt alle 30 s.

**Neu**
- **Alle Druckerwerte von der Integration:** Temperaturen (Bett, alle vier Düsen, Innenraum, Schrittmotortreiber), Solltemperaturen und Heizleistung, Lüfter (Bauteil, Innenraum, Düsenlüfter), Licht, Ausgänge, Filamentsensoren, Achsposition, Geschwindigkeit, Schicht, Fortschritt, MCU-Last und Wachzeit, Systemlast, Speicher, Warteschlange und Druckstatistik. Die Objekte kommen aus der Objektliste des Druckers, andere Konfigurationen funktionieren also auch.
- **Alle Steuerungen über die Integration:** Pause, Fortsetzen, Abbrechen, Not-Halt, Referenzfahrt (alle/X/Y/Z, im Druck gesperrt), Solltemperaturen, Bauteillüfter, Innenraumlüfter, Geschwindigkeit, Innenraumlicht und Schalter. Neuer Dienst `snapmaker_u1_card.machine_command` für Automationen – nur Objekte, die der Drucker meldet, Werte werden begrenzt.
- **Neue Entitäten:** Druckerwerte (ein Diagnose-Sensor, den die Karte liest), Bett-/Düsen-/Innenraumtemperatur, Fortschritt, Druckstatus, Schicht, Solltemperaturen, Bauteillüfter, Geschwindigkeit, Knöpfe für Pause/Fortsetzen/Abbrechen/Not-Halt/Referenzfahrt und das Innenraumlicht.
- **Rückfall:** Eine vorhandene Moonraker-Integration kann bleiben. Die Karte nimmt bevorzugt die Werte der Integration und greift nur auf die Moonraker-Entitäten zurück, wenn eigene fehlen (z. B. älteres Backend).
- **Blueprint Status-Licht** nimmt auch den Sensor *Druckstatus* der Integration.
- **Selbsttest:** „Werte direkt vom Drucker – Moonraker-Integration nicht nötig“ statt einer Warnung, wenn sie fehlt.
- Benachrichtigungsknopf *Licht* und das Licht fürs Ergebnisfoto nutzen das eigene Licht der Integration.

**Gut zu wissen**
- Home Assistant neu starten und das Dashboard neu laden.
- Die Kamera der Moonraker-Integration wird ebenfalls nicht mehr gebraucht: Die Integration hat seit 1.5 eine eigene.
- Wer in der Karte bei mehreren Druckern `prefix` gesetzt hat, lässt ihn so: Er wählt weiterhin den Drucker.

⭐ Gefällt dir das? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Kauf mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 1.6.3

Bug fix release on top of the big 1.6 update – the full list of what's new in 1.6 is below.

**Fixed in 1.6.3**
- Camera with WebRTC: the image frame took the format of the MJPEG stream (e.g. 4:3) while the WebRTC video is 16:9 – black bars above and below. The playing video now sets the format.
- Spools from Spoolman via SpoolLink showed an "RFID" badge although the spool has no tag; they now show "Spoolman". A real tag stays "RFID".
- Timelapses showed up twice when the firmware lists the same folder under two Moonraker roots.
- "Print finished": energy and cost use the language's decimal separator (0,04 kWh); a single head pick is no longer listed as a tool change (also in the history).
- Fullscreen camera on a large screen: progress, state and buttons grow with the screen.
- Tablet layout: the print heads now sit on the left under the job (always visible), the layer view uses the full right column, and there is no empty overview tab while idle.

**Fixed in 1.6.2 / 1.6.1**
- Maintenance: text and bar follow whichever of hours and months comes first; *Replace the air filter* only with a top cover.
- After an update to a new minor version, Home Assistant shows a notification with the highlights once.

**The big one.** 1.6 is the largest update so far: machine control, a much smarter Spoolman, WebRTC camera, slicer settings before printing, a status-light blueprint and lots of small things that make the card feel faster. Everything below is new since 1.5.2. Thanks to everyone who tested the betas!

**Control the machine**
- **Flow** (M221) slider next to the speed, also during a print.
- **Bed mesh heatmap** of the probed points with spread, lowest and highest point.
- **G-code console** with the printer's answers; during a print only safe tuning commands are accepted.
- **Pick and park heads** from the head details (service `tool_change`), locked during a print.
- **Top cover** support (chamber mode, exhaust/circulation fan, filter runtime) and **chamber heaters** BIQU Panda Breath / DragonBreath (paxx12 firmware) – their entities only appear when the hardware is there.
- **Nozzle per head**: diameter and high flow in the head details; the print dialog warns when a file was sliced for another nozzle.

**Instant feedback**
- Pause, resume and cancel show "Pausing …" / "Resuming …" / "Cancelling …" right after the tap, the light toggles immediately, switches pulse until confirmed.
- The print state comes from the integration's live connection – a pause shows up seconds earlier.

**Camera**
- **WebRTC in the card** (paxx12 Extended Firmware): less delay and far less data than MJPEG, MJPEG stays as fallback (option `camera_webrtc`).
- paxx12 2.x stream detected correctly, **RTSP** offered to Home Assistant automatically, **second camera** (USB) with a switch button.

**Spoolman**
- **paxx12 SpoolLink** detected automatically: no double booking, spool per head comes from the printer, choosing a spool sends `SET_SPOOL_ID`.
- Choosing a spool **loads its filament** into the head (material, sub type, vendor, colour) – **multi-colour spools** with all their colours.
- **Before → after per print** in the history (`#5 550 g → 460 g`).
- **Weigh a spool** in the head details – Spoolman is only needed to add new spools.
- **Unload and reload a head:** it offers its previous spool ("Use #5 … again?"), one tap restores it. Option: offer, set automatically or off.

**Files and printing**
- **Slicer settings in the print dialog:** layer height, walls, infill, supports, brim, plate, speeds and temperatures per filament (service `file_settings`).

**Notifications and maintenance**
- **Maintenance in calendar months** (Snapmaker's U1 maintenance guide) next to print hours, with a *Maintenance due* push.
- Progress notification: camera image or model preview; it now disappears reliably when the print is finished, also after a restart during the print.

**Look and automations**
- **Status light blueprint** installed with the integration: colours WLED or any colour light by the print state.
- **Own accent colour** for the card and the mini card.
- The card is also available as `custom:snapmaker-u1-card-ironoxx` (another integration ships a card with the same name; the self test tells you).

**Good to know when updating**
- Restart Home Assistant and reload the dashboard.
- Card sections `mesh` and `console` are new; if you list sections with `show:`, add them.
- With SpoolLink the integration no longer books usage itself – Moonraker does.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

Bugfix-Version auf dem großen 1.6-Update – die komplette Liste der Neuerungen in 1.6 steht darunter.

**Behoben in 1.6.3**
- Kamera mit WebRTC: Der Bildrahmen übernahm das Format des MJPEG-Streams (z. B. 4:3), das WebRTC-Video ist aber 16:9 – schwarze Balken oben und unten. Jetzt bestimmt das laufende Video das Format.
- Spulen aus Spoolman über SpoolLink zeigten ein „RFID“-Abzeichen, obwohl die Spule keinen Tag hat; jetzt steht dort „Spoolman“. Ein echter Tag bleibt „RFID“.
- Zeitraffer erschienen doppelt, wenn die Firmware denselben Ordner unter zwei Moonraker-Wurzeln anbietet.
- „Druck fertig“: Energie und Kosten mit dem Dezimaltrennzeichen der Sprache (0,04 kWh); einmaliges Aufnehmen des einzigen Kopfes zählt nicht mehr als Kopfwechsel (auch in der Historie).
- Vollbild-Kamera auf großen Bildschirmen: Fortschritt, Status und Knöpfe wachsen mit.
- Tablet-Layout: Die Druckköpfe stehen jetzt links unter dem Druckauftrag (immer sichtbar), die Schichtansicht nutzt die volle rechte Spalte, und im Leerlauf gibt es keinen leeren Übersicht-Reiter.

**Behoben in 1.6.2 / 1.6.1**
- Wartung: Text und Balken folgen dem, was zuerst fällig ist (Stunden oder Monate); *Luftfilter wechseln* nur mit Top Cover.
- Nach einem Update auf eine neue Unterversion zeigt Home Assistant einmal eine Benachrichtigung mit den Neuerungen.

**Das große Update.** 1.6 ist die bisher größte Version: Maschinensteuerung, ein deutlich schlaueres Spoolman, WebRTC-Kamera, Slicer-Einstellungen vor dem Druck, ein Blueprint fürs Status-Licht und viele Kleinigkeiten, durch die sich die Karte schneller anfühlt. Alles hier ist neu seit 1.5.2. Danke an alle, die die Betas getestet haben!

**Maschine steuern**
- **Flussrate** (M221) als Regler neben der Geschwindigkeit, auch im Druck.
- **Bed-Mesh-Heatmap** der Messpunkte mit Spanne, tiefstem und höchstem Punkt.
- **G-Code-Konsole** mit den Antworten des Druckers; im Druck nur sichere Feineinstellungen.
- **Köpfe aufnehmen und ablegen** in den Kopfdetails (Dienst `tool_change`), im Druck gesperrt.
- **Top Cover** (Kammermodus, Abluft-/Umluftlüfter, Filter-Laufzeit) und **Kammerheizungen** BIQU Panda Breath / DragonBreath (paxx12-Firmware) – die Entitäten erscheinen nur, wenn die Hardware da ist.
- **Düse je Kopf**: Durchmesser und High Flow in den Kopfdetails; der Druckdialog warnt, wenn die Datei für eine andere Düse geslict wurde.

**Sofortige Rückmeldung**
- Pause, Fortsetzen und Abbrechen zeigen direkt nach dem Tippen „Pausiere …“ / „Setze fort …“ / „Breche ab …“, das Licht schaltet sofort um, Schalter pulsieren bis zur Bestätigung.
- Der Druckzustand kommt aus der Live-Verbindung der Integration – eine Pause erscheint Sekunden früher.

**Kamera**
- **WebRTC in der Karte** (paxx12 Extended Firmware): weniger Verzögerung und viel weniger Daten als MJPEG, MJPEG bleibt als Rückfall (Option `camera_webrtc`).
- Stream von paxx12 2.x wird richtig erkannt, **RTSP** automatisch an Home Assistant übergeben, **zweite Kamera** (USB) mit Umschalter.

**Spoolman**
- **paxx12 SpoolLink** wird automatisch erkannt: kein doppeltes Abbuchen, die Spule je Kopf kommt vom Drucker, die Spulenwahl schickt `SET_SPOOL_ID`.
- Eine gewählte Spule **lädt ihr Filament** in den Kopf (Material, Unterart, Hersteller, Farbe) – **mehrfarbige Spulen** mit allen Farben.
- **Vorher → nachher je Druck** in der Historie (`#5 550 g → 460 g`).
- **Spule wiegen** in den Kopfdetails – Spoolman selbst brauchst du nur noch zum Anlegen neuer Spulen.
- **Kopf entladen und neu einlegen:** Er bietet seine vorherige Spule an („Wieder #5 …?“), ein Tipp übernimmt sie. Option: vorschlagen, automatisch setzen oder aus.

**Dateien und Drucken**
- **Slicer-Einstellungen im Druckdialog:** Schichthöhe, Wände, Infill, Stützen, Brim, Druckplatte, Geschwindigkeiten und Temperaturen je Filament (Dienst `file_settings`).

**Benachrichtigungen und Wartung**
- **Wartung in Kalendermonaten** (Snapmakers U1-Wartungsanleitung) neben Druckstunden, mit Push *Wartung fällig*.
- Fortschritts-Benachrichtigung: Kamerabild oder Modellvorschau; sie verschwindet jetzt zuverlässig bei Druckende, auch nach einem Neustart während des Drucks.

**Aussehen und Automationen**
- **Blueprint Status-Licht** wird mit installiert: färbt WLED oder jede Farblampe nach dem Druckzustand.
- **Eigene Akzentfarbe** für Karte und Mini-Karte.
- Die Karte gibt es zusätzlich als `custom:snapmaker-u1-card-ironoxx` (eine andere Integration bringt eine Karte mit gleichem Namen mit; der Selbsttest weist darauf hin).

**Gut zu wissen beim Update**
- Home Assistant neu starten und das Dashboard neu laden.
- Die Kartenbereiche `mesh` und `console` sind neu; wer Bereiche per `show:` aufzählt, ergänzt sie.
- Mit SpoolLink bucht die Integration den Verbrauch nicht mehr selbst ab – das macht Moonraker.

⭐ Gefällt dir die Karte? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Spendier mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 1.6.2

Bug fix release on top of the big 1.6 update – the full list of what's new in 1.6 is below.

**Fixed in 1.6.2**
- Maintenance: for items counted in hours and months (linear shafts, belts) the text showed the remaining hours while the bar followed the months. Text and bar now both follow whichever comes first ("14 days left").
- Maintenance: *Replace the air filter* only appears once a top cover was detected – the U1 has no air filter without it.
- 1.6.1: after an update to a new minor version, Home Assistant shows a notification with the highlights once.

**The big one.** 1.6 is the largest update so far: machine control, a much smarter Spoolman, WebRTC camera, slicer settings before printing, a status-light blueprint and lots of small things that make the card feel faster. Everything below is new since 1.5.2. Thanks to everyone who tested the betas!

**Control the machine**
- **Flow** (M221) slider next to the speed, also during a print.
- **Bed mesh heatmap** of the probed points with spread, lowest and highest point.
- **G-code console** with the printer's answers; during a print only safe tuning commands are accepted.
- **Pick and park heads** from the head details (service `tool_change`), locked during a print.
- **Top cover** support (chamber mode, exhaust/circulation fan, filter runtime) and **chamber heaters** BIQU Panda Breath / DragonBreath (paxx12 firmware) – their entities only appear when the hardware is there.
- **Nozzle per head**: diameter and high flow in the head details; the print dialog warns when a file was sliced for another nozzle.

**Instant feedback**
- Pause, resume and cancel show "Pausing …" / "Resuming …" / "Cancelling …" right after the tap, the light toggles immediately, switches pulse until confirmed.
- The print state comes from the integration's live connection – a pause shows up seconds earlier.

**Camera**
- **WebRTC in the card** (paxx12 Extended Firmware): less delay and far less data than MJPEG, MJPEG stays as fallback (option `camera_webrtc`).
- paxx12 2.x stream detected correctly, **RTSP** offered to Home Assistant automatically, **second camera** (USB) with a switch button.

**Spoolman**
- **paxx12 SpoolLink** detected automatically: no double booking, spool per head comes from the printer, choosing a spool sends `SET_SPOOL_ID`.
- Choosing a spool **loads its filament** into the head (material, sub type, vendor, colour) – **multi-colour spools** with all their colours.
- **Before → after per print** in the history (`#5 550 g → 460 g`).
- **Weigh a spool** in the head details – Spoolman is only needed to add new spools.
- **Unload and reload a head:** it offers its previous spool ("Use #5 … again?"), one tap restores it. Option: offer, set automatically or off.

**Files and printing**
- **Slicer settings in the print dialog:** layer height, walls, infill, supports, brim, plate, speeds and temperatures per filament (service `file_settings`).

**Notifications and maintenance**
- **Maintenance in calendar months** (Snapmaker's U1 maintenance guide) next to print hours, with a *Maintenance due* push.
- Progress notification: camera image or model preview; it now disappears reliably when the print is finished, also after a restart during the print.

**Look and automations**
- **Status light blueprint** installed with the integration: colours WLED or any colour light by the print state.
- **Own accent colour** for the card and the mini card.
- The card is also available as `custom:snapmaker-u1-card-ironoxx` (another integration ships a card with the same name; the self test tells you).

**Good to know when updating**
- Restart Home Assistant and reload the dashboard.
- Card sections `mesh` and `console` are new; if you list sections with `show:`, add them.
- With SpoolLink the integration no longer books usage itself – Moonraker does.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

Bugfix-Version auf dem großen 1.6-Update – die komplette Liste der Neuerungen in 1.6 steht darunter.

**Behoben in 1.6.2**
- Wartung: Bei Punkten, die nach Stunden und Monaten zählen (Linearführungen, Riemen), zeigte der Text die restlichen Stunden, der Balken aber die Monate. Text und Balken folgen jetzt beide dem, was zuerst fällig ist („noch 14 Tage“).
- Wartung: *Luftfilter wechseln* erscheint nur noch, wenn eine Top Cover erkannt wurde – ohne sie hat der U1 keinen Luftfilter.
- 1.6.1: Nach einem Update auf eine neue Unterversion zeigt Home Assistant einmal eine Benachrichtigung mit den Neuerungen.


**Das große Update.** 1.6 ist die bisher größte Version: Maschinensteuerung, ein deutlich schlaueres Spoolman, WebRTC-Kamera, Slicer-Einstellungen vor dem Druck, ein Blueprint fürs Status-Licht und viele Kleinigkeiten, durch die sich die Karte schneller anfühlt. Alles hier ist neu seit 1.5.2. Danke an alle, die die Betas getestet haben!

**Maschine steuern**
- **Flussrate** (M221) als Regler neben der Geschwindigkeit, auch im Druck.
- **Bed-Mesh-Heatmap** der Messpunkte mit Spanne, tiefstem und höchstem Punkt.
- **G-Code-Konsole** mit den Antworten des Druckers; im Druck nur sichere Feineinstellungen.
- **Köpfe aufnehmen und ablegen** in den Kopfdetails (Dienst `tool_change`), im Druck gesperrt.
- **Top Cover** (Kammermodus, Abluft-/Umluftlüfter, Filter-Laufzeit) und **Kammerheizungen** BIQU Panda Breath / DragonBreath (paxx12-Firmware) – die Entitäten erscheinen nur, wenn die Hardware da ist.
- **Düse je Kopf**: Durchmesser und High Flow in den Kopfdetails; der Druckdialog warnt, wenn die Datei für eine andere Düse geslict wurde.

**Sofortige Rückmeldung**
- Pause, Fortsetzen und Abbrechen zeigen direkt nach dem Tippen „Pausiere …“ / „Setze fort …“ / „Breche ab …“, das Licht schaltet sofort um, Schalter pulsieren bis zur Bestätigung.
- Der Druckzustand kommt aus der Live-Verbindung der Integration – eine Pause erscheint Sekunden früher.

**Kamera**
- **WebRTC in der Karte** (paxx12 Extended Firmware): weniger Verzögerung und viel weniger Daten als MJPEG, MJPEG bleibt als Rückfall (Option `camera_webrtc`).
- Stream von paxx12 2.x wird richtig erkannt, **RTSP** automatisch an Home Assistant übergeben, **zweite Kamera** (USB) mit Umschalter.

**Spoolman**
- **paxx12 SpoolLink** wird automatisch erkannt: kein doppeltes Abbuchen, die Spule je Kopf kommt vom Drucker, die Spulenwahl schickt `SET_SPOOL_ID`.
- Eine gewählte Spule **lädt ihr Filament** in den Kopf (Material, Unterart, Hersteller, Farbe) – **mehrfarbige Spulen** mit allen Farben.
- **Vorher → nachher je Druck** in der Historie (`#5 550 g → 460 g`).
- **Spule wiegen** in den Kopfdetails – Spoolman selbst brauchst du nur noch zum Anlegen neuer Spulen.
- **Kopf entladen und neu einlegen:** Er bietet seine vorherige Spule an („Wieder #5 …?“), ein Tipp übernimmt sie. Option: vorschlagen, automatisch setzen oder aus.

**Dateien und Drucken**
- **Slicer-Einstellungen im Druckdialog:** Schichthöhe, Wände, Infill, Stützen, Brim, Druckplatte, Geschwindigkeiten und Temperaturen je Filament (Dienst `file_settings`).

**Benachrichtigungen und Wartung**
- **Wartung in Kalendermonaten** (Snapmakers U1-Wartungsanleitung) neben Druckstunden, mit Push *Wartung fällig*.
- Fortschritts-Benachrichtigung: Kamerabild oder Modellvorschau; sie verschwindet jetzt zuverlässig bei Druckende, auch nach einem Neustart während des Drucks.

**Aussehen und Automationen**
- **Blueprint Status-Licht** wird mit installiert: färbt WLED oder jede Farblampe nach dem Druckzustand.
- **Eigene Akzentfarbe** für Karte und Mini-Karte.
- Die Karte gibt es zusätzlich als `custom:snapmaker-u1-card-ironoxx` (eine andere Integration bringt eine Karte mit gleichem Namen mit; der Selbsttest weist darauf hin).

**Gut zu wissen beim Update**
- Home Assistant neu starten und das Dashboard neu laden.
- Die Kartenbereiche `mesh` und `console` sind neu; wer Bereiche per `show:` aufzählt, ergänzt sie.
- Mit SpoolLink bucht die Integration den Verbrauch nicht mehr selbst ab – das macht Moonraker.

⭐ Gefällt dir die Karte? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Spendier mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 1.6.1

**New**
- After an update to a new minor version, Home Assistant shows a notification with the highlights once (not on a fresh install). Many setups only showed a link to the release notes. Coming from 1.5.x: everything new in 1.6 is listed under 1.6.0 below.

---
**Deutsch**
- Neu: Nach einem Update auf eine neue Unterversion zeigt Home Assistant einmal eine Benachrichtigung mit den Neuerungen (nicht bei einer Neuinstallation). Bei vielen war im Update-Dialog nur ein Link zu den Versionshinweisen zu sehen. Von 1.5.x kommend: alles Neue in 1.6 steht unten bei 1.6.0.

## 1.6.0

**The big one.** 1.6.0 is the largest update so far: machine control, a much smarter Spoolman, WebRTC camera, slicer settings before printing, a status-light blueprint and lots of small things that make the card feel faster. Everything below is new since 1.5.2. Thanks to everyone who tested the betas!

**Control the machine**
- **Flow** (M221) slider next to the speed, also during a print.
- **Bed mesh heatmap** of the probed points with spread, lowest and highest point.
- **G-code console** with the printer's answers; during a print only safe tuning commands are accepted.
- **Pick and park heads** from the head details (service `tool_change`), locked during a print.
- **Top cover** support (chamber mode, exhaust/circulation fan, filter runtime) and **chamber heaters** BIQU Panda Breath / DragonBreath (paxx12 firmware) – their entities only appear when the hardware is there.
- **Nozzle per head**: diameter and high flow in the head details; the print dialog warns when a file was sliced for another nozzle.

**Instant feedback**
- Pause, resume and cancel show "Pausing …" / "Resuming …" / "Cancelling …" right after the tap, the light toggles immediately, switches pulse until confirmed.
- The print state comes from the integration's live connection – a pause shows up seconds earlier.

**Camera**
- **WebRTC in the card** (paxx12 Extended Firmware): less delay and far less data than MJPEG, MJPEG stays as fallback (option `camera_webrtc`).
- paxx12 2.x stream detected correctly, **RTSP** offered to Home Assistant automatically, **second camera** (USB) with a switch button.

**Spoolman**
- **paxx12 SpoolLink** detected automatically: no double booking, spool per head comes from the printer, choosing a spool sends `SET_SPOOL_ID`.
- Choosing a spool **loads its filament** into the head (material, sub type, vendor, colour) – **multi-colour spools** with all their colours.
- **Before → after per print** in the history (`#5 550 g → 460 g`).
- **Weigh a spool** in the head details – Spoolman is only needed to add new spools.
- **Unload and reload a head:** it offers its previous spool ("Use #5 … again?"), one tap restores it. Option: offer, set automatically or off.

**Files and printing**
- **Slicer settings in the print dialog:** layer height, walls, infill, supports, brim, plate, speeds and temperatures per filament (service `file_settings`).

**Notifications and maintenance**
- **Maintenance in calendar months** (Snapmaker's U1 maintenance guide) next to print hours, with a *Maintenance due* push.
- Progress notification: camera image or model preview; it now disappears reliably when the print is finished, also after a restart during the print.

**Look and automations**
- **Status light blueprint** installed with the integration: colours WLED or any colour light by the print state.
- **Own accent colour** for the card and the mini card.
- The card is also available as `custom:snapmaker-u1-card-ironoxx` (another integration ships a card with the same name; the self test tells you).

**Good to know when updating**
- Restart Home Assistant and reload the dashboard.
- Card sections `mesh` and `console` are new; if you list sections with `show:`, add them.
- With SpoolLink the integration no longer books usage itself – Moonraker does.

⭐ Like it? Star the project on [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/ironoxx)

---
**Deutsch**

**Das große Update.** 1.6.0 ist die bisher größte Version: Maschinensteuerung, ein deutlich schlaueres Spoolman, WebRTC-Kamera, Slicer-Einstellungen vor dem Druck, ein Blueprint fürs Status-Licht und viele Kleinigkeiten, durch die sich die Karte schneller anfühlt. Alles hier ist neu seit 1.5.2. Danke an alle, die die Betas getestet haben!

**Maschine steuern**
- **Flussrate** (M221) als Regler neben der Geschwindigkeit, auch im Druck.
- **Bed-Mesh-Heatmap** der Messpunkte mit Spanne, tiefstem und höchstem Punkt.
- **G-Code-Konsole** mit den Antworten des Druckers; im Druck nur sichere Feineinstellungen.
- **Köpfe aufnehmen und ablegen** in den Kopfdetails (Dienst `tool_change`), im Druck gesperrt.
- **Top Cover** (Kammermodus, Abluft-/Umluftlüfter, Filter-Laufzeit) und **Kammerheizungen** BIQU Panda Breath / DragonBreath (paxx12-Firmware) – die Entitäten erscheinen nur, wenn die Hardware da ist.
- **Düse je Kopf**: Durchmesser und High Flow in den Kopfdetails; der Druckdialog warnt, wenn die Datei für eine andere Düse geslict wurde.

**Sofortige Rückmeldung**
- Pause, Fortsetzen und Abbrechen zeigen direkt nach dem Tippen „Pausiere …“ / „Setze fort …“ / „Breche ab …“, das Licht schaltet sofort um, Schalter pulsieren bis zur Bestätigung.
- Der Druckzustand kommt aus der Live-Verbindung der Integration – eine Pause erscheint Sekunden früher.

**Kamera**
- **WebRTC in der Karte** (paxx12 Extended Firmware): weniger Verzögerung und viel weniger Daten als MJPEG, MJPEG bleibt als Rückfall (Option `camera_webrtc`).
- Stream von paxx12 2.x wird richtig erkannt, **RTSP** automatisch an Home Assistant übergeben, **zweite Kamera** (USB) mit Umschalter.

**Spoolman**
- **paxx12 SpoolLink** wird automatisch erkannt: kein doppeltes Abbuchen, die Spule je Kopf kommt vom Drucker, die Spulenwahl schickt `SET_SPOOL_ID`.
- Eine gewählte Spule **lädt ihr Filament** in den Kopf (Material, Unterart, Hersteller, Farbe) – **mehrfarbige Spulen** mit allen Farben.
- **Vorher → nachher je Druck** in der Historie (`#5 550 g → 460 g`).
- **Spule wiegen** in den Kopfdetails – Spoolman selbst brauchst du nur noch zum Anlegen neuer Spulen.
- **Kopf entladen und neu einlegen:** Er bietet seine vorherige Spule an („Wieder #5 …?“), ein Tipp übernimmt sie. Option: vorschlagen, automatisch setzen oder aus.

**Dateien und Drucken**
- **Slicer-Einstellungen im Druckdialog:** Schichthöhe, Wände, Infill, Stützen, Brim, Druckplatte, Geschwindigkeiten und Temperaturen je Filament (Dienst `file_settings`).

**Benachrichtigungen und Wartung**
- **Wartung in Kalendermonaten** (Snapmakers U1-Wartungsanleitung) neben Druckstunden, mit Push *Wartung fällig*.
- Fortschritts-Benachrichtigung: Kamerabild oder Modellvorschau; sie verschwindet jetzt zuverlässig bei Druckende, auch nach einem Neustart während des Drucks.

**Aussehen und Automationen**
- **Blueprint Status-Licht** wird mit installiert: färbt WLED oder jede Farblampe nach dem Druckzustand.
- **Eigene Akzentfarbe** für Karte und Mini-Karte.
- Die Karte gibt es zusätzlich als `custom:snapmaker-u1-card-ironoxx` (eine andere Integration bringt eine Karte mit gleichem Namen mit; der Selbsttest weist darauf hin).

**Gut zu wissen beim Update**
- Home Assistant neu starten und das Dashboard neu laden.
- Die Kartenbereiche `mesh` und `console` sind neu; wer Bereiche per `show:` aufzählt, ergänzt sie.
- Mit SpoolLink bucht die Integration den Verbrauch nicht mehr selbst ab – das macht Moonraker.

⭐ Gefällt dir die Karte? Gib dem Projekt einen Stern auf [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Spendier mir einen Kaffee auf Ko-fi](https://ko-fi.com/ironoxx)

## 1.5.2

**New**
- Notifications: new option *Open when tapped* (`notify_click_url`) – tapping a notification of the integration (also the progress notification) opens this dashboard, e.g. `/dashboard-printer/0`.
- Progress notification: shows the camera image when expanded (option *Progress notification: camera image*, on by default; refreshed with each progress update, no extra pushes).

**Fixed**
- The "print finished" notification attached a live camera image taken when the print already counted as finished – the bed was lowered by then. It now shows the result photo (taken once the head has left the part) and waits up to 20 s for it.

---
**Deutsch**
- Neu: Option *Beim Antippen öffnen* (`notify_click_url`) – ein Tipp auf eine Benachrichtigung der Integration (auch die Fortschritts-Benachrichtigung) öffnet dieses Dashboard, z. B. `/dashboard-drucker/0`.
- Neu: Die Fortschritts-Benachrichtigung zeigt aufgeklappt das Kamerabild (Option *Fortschritts-Benachrichtigung: Kamerabild*, standardmäßig an; aktualisiert mit jedem Fortschritts-Update, keine zusätzlichen Pushes).
- Behoben: Die „Druck fertig“-Meldung hängte ein Live-Bild an, das erst entstand, als der Druck schon als fertig galt – da war das Bett bereits abgesenkt. Jetzt kommt das Ergebnisfoto (aufgenommen, sobald der Kopf vom Teil weg ist); die Meldung wartet bis zu 20 s darauf.

## 1.5.1

**Fixed**
- Camera: a live stream could be detected as "still images" when its first frame took longer than 3 s (camera starting up, busy WiFi), and it then stayed on still images for a day. The detection now waits up to 8 s, tries twice, and in still mode checks the stream again every 5 minutes. If the stream check fails, the self test and the camera attribute `stream_error` say why.

---
**Deutsch**
- Behoben: Kamera – ein Livestream konnte als „Standbilder“ erkannt werden, wenn sein erstes Bild länger als 3 s brauchte (Kamera startet, WLAN ausgelastet), und blieb dann einen Tag bei Standbildern. Die Erkennung wartet jetzt bis zu 8 s, versucht es zweimal und prüft den Stream im Standbild-Modus alle 5 Minuten erneut. Scheitert die Prüfung, nennen Selbsttest und das Kamera-Attribut `stream_error` den Grund.

## 1.5.0

Same as the beta 1.5.0b1, now for everyone. Coming from an older version: also see 1.4.0–1.4.4 below (remaining time, progress notification, exclude objects, top view, and the fix for the remaining time shown 60× too high).

**New**
- Own camera entity that works with stock and modified firmware alike. The integration finds out by itself how to get an image: live MJPEG stream (e.g. paxx12 Extended firmware), snapshot images, or the stock camera, which it wakes with `camera.start_monitor` as needed. Shown as attribute `mode` (`live` / `still` / `wake` / `none`), in the self test and the diagnostics. A failing stream falls back to still images and is retried after 5 minutes.
- The card uses this camera automatically (`camera_mode: auto`, new default); notification images and the result photo use it when no camera is set in the options. Without any camera the card shows a short hint instead of a black area.

**Fixed**
- `monitor.jpg` of the stock firmware can never show up as a timelapse preview.

---
**Deutsch**
- Neu: Eigene Kamera-Entität, die mit Stock- und angepasster Firmware funktioniert. Die Integration erkennt selbst, wie sie an ein Bild kommt: MJPEG-Livestream (z. B. paxx12 Extended Firmware), Snapshot-Bilder oder die Stock-Kamera, die sie bei Bedarf per `camera.start_monitor` weckt. Sichtbar als Attribut `mode` (`live` / `still` / `wake` / `none`), im Selbsttest und in der Diagnose. Fällt der Stream aus, gibt es Standbilder, nach 5 Minuten neuer Versuch.
- Neu: Die Karte nutzt diese Kamera automatisch (`camera_mode: auto`, neuer Standard); Benachrichtigungsbild und Ergebnisfoto nutzen sie, wenn in den Optionen keine Kamera gewählt ist. Ganz ohne Kamera zeigt die Karte einen kurzen Hinweis statt einer schwarzen Fläche.
- Behoben: `monitor.jpg` der Stock-Firmware kann nicht mehr als Zeitraffer-Vorschau auftauchen.

## 1.5.0b1

Beta – only offered with "show beta versions" in HACS.

**New**
- Own camera entity that works with stock and modified firmware alike. The integration finds out by itself how to get an image: live MJPEG stream (e.g. paxx12 Extended firmware), snapshot images, or the stock camera, which it wakes with `camera.start_monitor` as needed. Shown as attribute `mode` (`live` / `still` / `wake` / `none`), in the self test and the diagnostics. A failing stream falls back to still images and is retried after 5 minutes.
- The card uses this camera automatically (`camera_mode: auto`, new default); notification images and the result photo use it when no camera is set in the options. Without any camera the card shows a short hint instead of a black area.

**Fixed**
- `monitor.jpg` of the stock firmware can never show up as a timelapse preview.

---
**Deutsch**
- Neu: Eigene Kamera-Entität, die mit Stock- und angepasster Firmware funktioniert. Die Integration erkennt selbst, wie sie an ein Bild kommt: MJPEG-Livestream (z. B. paxx12 Extended Firmware), Snapshot-Bilder oder die Stock-Kamera, die sie bei Bedarf per `camera.start_monitor` weckt. Sichtbar als Attribut `mode` (`live` / `still` / `wake` / `none`), im Selbsttest und in der Diagnose. Fällt der Stream aus, gibt es Standbilder, nach 5 Minuten neuer Versuch.
- Neu: Die Karte nutzt diese Kamera automatisch (`camera_mode: auto`, neuer Standard); Benachrichtigungsbild und Ergebnisfoto nutzen sie, wenn in den Optionen keine Kamera gewählt ist. Ganz ohne Kamera zeigt die Karte einen kurzen Hinweis statt einer schwarzen Fläche.
- Behoben: `monitor.jpg` der Stock-Firmware kann nicht mehr als Zeitraffer-Vorschau auftauchen.

## 1.4.4

**Fixed**
- Remaining time in the card was 60 times too high when the integration's own *Time remaining* sensor was used (e.g. "80 h" instead of 80 min). The card now reads the unit of every duration sensor (h, min, s), so a display unit changed by the user is handled too. The finish time and the calculation itself were not affected.

---
**Deutsch**
- Behoben: Die Restzeit in der Karte war mit dem eigenen Sensor *Restzeit* 60-mal zu hoch (z. B. „80 h“ statt 80 min). Die Karte liest jetzt die Einheit jedes Zeit-Sensors (h, min, s), auch wenn die Anzeigeeinheit geändert wurde. „Fertig um“ und die Berechnung selbst waren nicht betroffen.

## 1.4.3

**New**
- Top view: the nozzle moves smoothly along the paths of the current layer, with a gantry bar across the plate. The printer reports its position every few seconds; the card plays the way in between. Turned off with "reduce motion" in the system settings.
- Own background image for the top view: `bed_image` (e.g. `/local/u1_top.png`) with `bed_image_area` (printer coordinates the image covers in mm, default the plate `0, 0, 270, 270`), `bed_image_opacity` and `bed_grid`. Good for a photo of your own printer taken from above. Also in the card editor under "Top view".

---
**Deutsch**
- Neu: In der Draufsicht fährt die Düse flüssig die Bahnen der aktuellen Schicht ab, mit Querbrücke über der Platte. Der Drucker meldet seine Position alle paar Sekunden, die Karte spielt den Weg dazwischen ab. Aus bei „Bewegung reduzieren“ in den Systemeinstellungen.
- Neu: Eigenes Hintergrundbild für die Draufsicht: `bed_image` (z. B. `/local/u1_oben.png`) mit `bed_image_area` (welche Druckerkoordinaten das Bild abdeckt, Standard die Platte `0, 0, 270, 270`), `bed_image_opacity` und `bed_grid`. Passt z. B. für ein Foto des eigenen Druckers von oben. Auch im Karteneditor unter „Draufsicht“.

## 1.4.2

**New**
- Layer view as a top view of the whole printer (option `layer_view: bed`, or the grid button in the layer view; the choice is remembered per browser): the 270 × 270 mm plate to scale with a 10/50 mm grid, the four heads parked behind it in their filament colours (the active one outlined, shown as "away" while printing) and a nozzle marker where the printer is right now. The zoomed part view stays the default.

---
**Deutsch**
- Neu: Schichtansicht als Draufsicht auf den ganzen Drucker (Option `layer_view: bed` oder Raster-Knopf in der Schichtansicht; die Wahl merkt sich der Browser): Druckplatte 270 × 270 mm im Maßstab mit 10/50-mm-Raster, dahinter die vier geparkten Köpfe in Filamentfarbe (aktiver umrandet, beim Druck als „unterwegs“) und ein Düsen-Marker an der aktuellen Druckstelle. Standard bleibt die vergrößerte Teilansicht.

## 1.4.1

**New**
- Exclude objects during a print: the layer view shows the outline of every object (from `EXCLUDE_OBJECT_DEFINE`). Tap an outline or the object chip below, confirm, and the printer skips that object from now on (Klipper `EXCLUDE_OBJECT`); the rest keeps printing. The object being printed is highlighted, excluded ones are struck through and faded. The last remaining object cannot be excluded. Also available as service `snapmaker_u1_card.exclude_object`.

---
**Deutsch**
- Neu: Objekte während des Drucks ausschließen. Die Schichtansicht zeigt die Umrisse aller Objekte; Umriss oder Objekt-Chip antippen, bestätigen – der Drucker lässt das Objekt ab sofort aus (Klipper `EXCLUDE_OBJECT`), der Rest läuft weiter. Das gerade gedruckte Objekt ist hervorgehoben, ausgeschlossene sind durchgestrichen und blass. Das letzte verbleibende Objekt lässt sich nicht ausschließen. Auch als Dienst `snapmaker_u1_card.exclude_object`.

## 1.4.0

**New**
- Progress notification for Android: ongoing notification with progress bar and a countdown to the expected end. Switch in the card (System tab) and as an entity, off by default. Uses very few pushes: the countdown runs on the phone, updates only every 10 % or when the end time moves noticeably (about 12–15 per print), with a daily budget per phone (option, default 150). End/error/pause notifications are not affected.
- Download the G-code from the print dialog (through Home Assistant, also works remotely).

**Improved**
- Much more accurate remaining time: uses the slicer's own remaining time from the file (Orca `M73`), corrected by the measured speed from the first layer on. The start sequence (leveling, calibration) no longer distorts it, and the integration learns start duration and speed from your previous prints.
- Result photo: taken once the head has moved away from the part (head position from the printer), with the chamber light on, instead of a fixed 2 s after the last line.

---
**Deutsch**
- Neu: Fortschritts-Benachrichtigung für Android mit Balken und Countdown bis zum Ende. Schalter in der Karte (System-Reiter) und als Entität, standardmäßig aus. Sehr sparsam: Der Countdown läuft auf dem Handy, Updates nur alle 10 % oder wenn sich das Ende deutlich verschiebt (etwa 12–15 je Druck), mit Tagesbudget je Handy (Option, Standard 150). Fertig-, Fehler- und Pause-Meldungen sind nicht betroffen.
- Neu: G-Code im Druckdialog herunterladen (über Home Assistant, auch unterwegs).
- Verbessert: Deutlich genauere Restzeit – nutzt die Slicer-Restzeit aus der Datei (Orca `M73`), korrigiert mit der gemessenen Geschwindigkeit ab der ersten Schicht. Die Startsequenz (Leveling, Kalibrierung) verfälscht sie nicht mehr, Startdauer und Tempo lernt die Integration aus deinen bisherigen Drucken.
- Verbessert: Ergebnisfoto entsteht, sobald der Kopf vom Teil weggefahren ist (Kopfposition vom Drucker), mit eingeschaltetem Licht – statt fest 2 s nach der letzten Zeile.

## 1.3.2

**Fixed**
- Diagnostics download: the Spoolman address is now redacted (it was visible in the Spoolman block). Please don't post older diagnostics files publicly without checking.

**Improved**
- Diagnostics include the installed and the latest firmware version.

---
**Deutsch**
- Behoben: Diagnose-Download schwärzt jetzt die Spoolman-Adresse (stand vorher im Spoolman-Abschnitt im Klartext).
- Verbessert: Diagnose enthält die installierte und die neueste Firmware-Version.

## 1.3.1

**New**
- Faster camera: the card loads the stream directly from the printer (`camera_direct: auto`, default) instead of through Home Assistant – less delay, no load on HA. Works when HA is opened via `http://` in your home network; on `https://` or away from home the card automatically uses the HA proxy as before. Own stream address: `camera_direct_url`. Turn off with `camera_direct: off`.

**Improved**
- If the HA camera stream delivers nothing, the card switches to still images after 6 s instead of 10 s.

---
**Deutsch**
- Neu: Schnellere Kamera – Stream direkt vom Drucker statt über HA (`camera_direct: auto`, Standard). Greift, wenn HA im Heimnetz per `http://` geöffnet ist; bei `https://` oder unterwegs nimmt die Karte automatisch den Weg über HA. Eigene Adresse: `camera_direct_url`, abschalten mit `camera_direct: off`.
- Verbessert: Liefert der HA-Stream nichts, wechselt die Karte nach 6 s statt 10 s auf Einzelbilder.

## 1.3.0

**New**
- Emergency stop option `emergency_stop`: `show` (with confirmation), `hold` (hold the button for 1 s) or `hide`. The HA button entity always stays.
- Own confirmation dialog for emergency stop and cancel print (instead of the browser popup).
- Tablet / wall monitor layout (`layout: tablet`): camera and current job on the left, tabs on the right.
- Camera wake-up (`camera_wake`, on by default): if the image freezes on stock firmware, the card asks the printer to restart the camera (new service `snapmaker_u1_card.camera_wake`).
- Notice when the browser still runs an old card after an update, with a reload button.

---
**Deutsch**
- Neu: Not-Halt anzeigen / gesichert (1 s halten) / ausblenden · eigener Bestätigungsdialog · Tablet-/Monitor-Layout · Kamera wecken bei stehendem Bild (Stock-Firmware) · Hinweis bei veralteter Karte im Browser-Cache.

## 1.2.3

- Camera: printer state as a small badge in the corner instead of a dimmed overlay while idle.
- Toolheads: visible "Filament" button to edit the loaded filament.

## 1.2.2

- Electricity price from a price entity, a fixed price or the Energy dashboard.
- Self test: Spoolman check fixed.

## 1.2.1

- Timelapse archive limits (number and age), five config backups.

## 1.2.0

- Printer settings (auto replenish, tangle detection, LED off at the end) as switches and in the card.
- RFID spool data and filament editing per toolhead.
- Option to keep the camera awake on stock firmware.
