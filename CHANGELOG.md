# Changelog

Each `## x.y.z` section becomes the text of the GitHub release, which HACS shows
in the update dialog. Newest first. After updating: restart Home Assistant and
reload the dashboard (the card shows a hint if the browser still has the old one).

## 2.2.0

Building blocks for your own dashboard, a printer that tells what it is doing, loading/unloading with checks and paxx12 detection.

**Building blocks**
- New card *Snapmaker U1 – Section* (`custom:snapmaker-u1-section-card`): single sections of the card – camera, print job, heads, bed mesh, console, maintenance, messages … – as cards of their own, to arrange freely in a *Sections* dashboard. Pick the sections in the editor (each with a short description); their order counts. With one section the Home Assistant card frame is the panel itself.
- `show:` now also sets the order (`layout: scroll` and the section card); new `layout: bare` (only the sections, no head, no tabs).

**What the printer is doing**
- New sensor *Machine state* from Snapmaker's own `machine_state_manager`: calibration (XYZ, bed, flow, resonance), loading/unloading, firmware update, fault … with the current step and head as attributes. The card shows it in the status outside a print, e.g. "XYZ calibration · Nozzle cooling down (Head 2)".
- **Auto-off and idle-off no longer switch off during a calibration** (thanks to TheKlonko on Reddit): anything Klipper does outside a print counts as busy; the after-print delay starts again afterwards. During a firmware update the power is never cut, not even with `force`.
- New section *Messages*: firmware errors, a fault state, a step waiting for a confirmation on the display ("Confirm at the printer") and feeder faults – or "No messages".

**Load / unload with checks**
- *Load* only when filament waits at the feeder and none is in the head, *Unload* only with filament in the head; otherwise the button is off and says why. The new service `snapmaker_u1_card.filament` refuses the same way.
- Afterwards the head sensor is checked; picking and parking a head is checked too. Errors show as a short message in the card instead of a pop-up.

**paxx12 Extended Firmware**
- Detected via its `/firmware-config/`: the system tab shows "paxx12 2.0.0-paxx12-24 · up to date (base 2.0.0.205)", the self test has its own line, the firmware update entity compares with paxx12's releases (with a note not to use the stock update).

**Overview**
- **Printer display on the overview** at its real size, no empty frame (paxx12). Option `display_place`: `overview` (default), `tab` or `off`.
- **Slicer preview in the running print** next to file name and progress.
- **Spools show their fill level** from Spoolman, larger and with a light edge so black filament stands out; the spool of the printing head turns slowly (off with "reduce motion").
- **Usage of the last print per head** as bars in the spool colours; tap for the details (Spoolman spool, before → after).

**Controls and look**
- Speed quick buttons **85 / 100 / 115 %**, flow 95 / 100 / 105 %; current value marked. Own values with `speed_presets` / `flow_presets`.
- **Bed mesh** uses the panel width with heights in every cell (up to 12 × 12 points); off with `mesh_values: false`.
- **Bigger buttons** for touch: lock, display touch, zoom and quick buttons.
- One font with even digit widths (monospace only in the G-code console), fewer font sizes.
- Layer view: the object list for excluding is folded by default.

### Deutsch

Bausteine für das eigene Dashboard, ein Drucker, der sagt, was er gerade macht, Laden/Entladen mit Prüfung und paxx12-Erkennung.

**Bausteine**
- Neue Karte *Snapmaker U1 – Bereich* (`custom:snapmaker-u1-section-card`): einzelne Bereiche der Karte – Kamera, Druckauftrag, Köpfe, Bettnivellierung, Konsole, Wartung, Meldungen … – als eigene Karten, frei anzuordnen in einem *Abschnitte*-Dashboard. Bereiche im Editor wählen (jeder mit kurzer Beschreibung); die Reihenfolge zählt. Mit einem Bereich ist der Kartenrahmen von Home Assistant selbst das Panel.
- `show:` legt jetzt auch die Reihenfolge fest (`layout: scroll` und die Bereichs-Karte); neu `layout: bare` (nur die Bereiche, ohne Kopf und Reiter).

**Was der Drucker gerade macht**
- Neuer Sensor *Maschinenstatus* aus Snapmakers eigenem `machine_state_manager`: Kalibrierung (XYZ, Bett, Fluss, Resonanz), Laden/Entladen, Firmware-Update, Störung … mit aktuellem Schritt und Kopf als Attribute. Die Karte zeigt das außerhalb eines Drucks im Status, z. B. „XYZ-Kalibrierung · Düse kühlt ab (Kopf 2)“.
- **Auto-Aus und Leerlauf-Aus schalten nicht mehr während einer Kalibrierung ab** (danke an TheKlonko auf Reddit): alles, was Klipper außerhalb eines Drucks tut, zählt als beschäftigt; die Wartezeit nach dem Druck beginnt danach neu. Während eines Firmware-Updates wird nie abgeschaltet, auch nicht mit `force`.
- Neuer Bereich *Meldungen*: Firmware-Fehler, ein Störungszustand, ein Schritt, der am Display auf Bestätigung wartet („Am Drucker bestätigen“), und Störungen am Einzug – oder „Keine Meldungen“.

**Laden / Entladen mit Prüfung**
- *Laden* nur, wenn Filament am Einzug wartet und keins im Kopf ist, *Entladen* nur mit Filament im Kopf; sonst ist der Knopf aus und sagt warum. Der neue Dienst `snapmaker_u1_card.filament` lehnt genauso ab.
- Danach wird der Sensor im Kopf geprüft; Kopf aufnehmen und ablegen wird ebenso geprüft. Fehler erscheinen als kurze Meldung in der Karte statt als Pop-up.

**paxx12 Extended Firmware**
- Erkannt über ihre `/firmware-config/`: Der System-Reiter zeigt „paxx12 2.0.0-paxx12-24 · aktuell (Basis 2.0.0.205)“, der Selbsttest hat eine eigene Zeile, die Firmware-Update-Entität vergleicht mit den paxx12-Releases (mit dem Hinweis, nicht das Stock-Update zu nehmen).

**Übersicht**
- **Druckerdisplay in der Übersicht** in echter Größe, ohne leeren Rahmen (paxx12). Option `display_place`: `overview` (Standard), `tab` oder `off`.
- **Vorschaubild des Slicers im laufenden Druck** neben Dateiname und Fortschritt.
- **Spulen zeigen ihren Füllstand** aus Spoolman, größer und mit hellem Rand, damit schwarzes Filament sichtbar bleibt; die Spule des druckenden Kopfs dreht sich langsam (aus bei „Bewegung reduzieren“).
- **Verbrauch des letzten Drucks je Kopf** als Balken in den Spulenfarben; antippen zeigt die Details (Spoolman-Spule, vorher → nachher).

**Bedienung und Aussehen**
- Schnellwahl Geschwindigkeit **85 / 100 / 115 %**, Flussrate 95 / 100 / 105 %; aktueller Wert markiert. Eigene Werte mit `speed_presets` / `flow_presets`.
- **Bettnivellierung** nutzt die Panelbreite, mit Höhenwerten in jeder Kachel (bis 12 × 12 Punkte); abschaltbar mit `mesh_values: false`.
- **Größere Knöpfe** zum Antippen: Sperre, Display-Touch, Zoom und Schnellwahl.
- Eine Schrift mit gleich breiten Ziffern (Monospace nur in der G-Code-Konsole), weniger Schriftgrößen.
- Schichtansicht: Die Objektliste zum Ausschließen ist standardmäßig eingeklappt.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.2.0b2

Beta. The printer tells more: what it is doing, what went wrong, which firmware runs – and loading/unloading only when it can work.

**What the printer is doing**
- New sensor *Machine state* from Snapmaker's own `machine_state_manager`: calibration (XYZ, bed, flow, resonance), loading/unloading, firmware update, fault … with the current step (e.g. *nozzle cooling down*) and head as attributes. The card shows it in the status outside a print, e.g. "XYZ calibration · Nozzle cooling down (Head 2)".
- **Auto-off and idle-off no longer switch off during a calibration** (thanks to TheKlonko on Reddit for the report): anything the printer does outside a print counts as busy; the after-print delay starts again afterwards. During a firmware update the power is never cut, not even with `force`.

**Messages**
- New section *Messages* for the building block card: firmware errors, a fault state, a step waiting for a confirmation on the display ("Confirm at the printer") and feeder faults – or "No messages". Section cards with camera or job show them on top as before; option `alerts` for the others.

**Load / unload with checks**
- The buttons know the feeders: *Load* only when filament waits at the feeder and none is in the head, *Unload* only with filament in the head; otherwise the button is off and says why. The service `filament` refuses the same way.
- Afterwards the integration checks the head sensor and reports when the filament did not come out or in. Picking and parking a head is checked too. Errors show as a short message in the card instead of a pop-up.

**paxx12 Extended Firmware**
- Detected via its `/firmware-config/`: the card's system tab shows "paxx12 2.0.0-paxx12-24 · up to date (base 2.0.0)", the self test has its own line, the firmware update entity compares with paxx12's releases (with a note not to use the stock update). Without a login or with the config service off it is still detected, only the version is unknown.

**Also**
- Spools easier to see: larger, with a light edge so black (and on light themes white) filament stands out; same for the colour dots and the usage bars.
- Section editor: every section with a short description.
- Layer view: the object list for excluding is folded by default.

Please check: a calibration (status text, no switch-off), load/unload buttons with an empty and a loaded head, the *Messages* section, firmware line in the system tab and the self test.

### Deutsch

Beta. Der Drucker erzählt mehr: was er gerade macht, was schiefging, welche Firmware läuft – und Laden/Entladen nur, wenn es klappen kann.

**Was der Drucker gerade macht**
- Neuer Sensor *Maschinenstatus* aus Snapmakers eigenem `machine_state_manager`: Kalibrierung (XYZ, Bett, Fluss, Resonanz), Laden/Entladen, Firmware-Update, Störung … mit dem aktuellen Schritt (z. B. *Düse kühlt ab*) und Kopf als Attribute. Die Karte zeigt das außerhalb eines Drucks im Status, z. B. „XYZ-Kalibrierung · Düse kühlt ab (Kopf 2)“.
- **Auto-Aus und Leerlauf-Aus schalten nicht mehr während einer Kalibrierung ab** (danke an TheKlonko auf Reddit für die Meldung): alles, was der Drucker außerhalb eines Drucks tut, zählt als beschäftigt; die Wartezeit nach dem Druck beginnt danach neu. Während eines Firmware-Updates wird nie abgeschaltet, auch nicht mit `force`.

**Meldungen**
- Neuer Bereich *Meldungen* für die Bereichs-Karte: Firmware-Fehler, ein Störungszustand, ein Schritt, der am Display auf eine Bestätigung wartet („Am Drucker bestätigen“), und Störungen am Einzug – oder „Keine Meldungen“. Bereichs-Karten mit Kamera oder Druckauftrag zeigen sie wie bisher oben; für die anderen gibt es die Option `alerts`.

**Laden / Entladen mit Prüfung**
- Die Knöpfe kennen die Einzüge: *Laden* nur, wenn Filament am Einzug wartet und keins im Kopf ist, *Entladen* nur mit Filament im Kopf; sonst ist der Knopf aus und sagt warum. Der Dienst `filament` lehnt genauso ab.
- Danach prüft die Integration den Sensor im Kopf und meldet, wenn das Filament nicht raus- bzw. reingekommen ist. Kopf aufnehmen und ablegen wird ebenso geprüft. Fehler erscheinen als kurze Meldung in der Karte statt als Pop-up.

**paxx12 Extended Firmware**
- Erkannt über ihre `/firmware-config/`: Der System-Reiter zeigt „paxx12 2.0.0-paxx12-24 · aktuell (Basis 2.0.0)“, der Selbsttest hat eine eigene Zeile, die Firmware-Update-Entität vergleicht mit den paxx12-Releases (mit dem Hinweis, nicht das Stock-Update zu nehmen). Ohne Anmeldung oder mit ausgeschaltetem Config-Dienst wird paxx12 trotzdem erkannt, nur die Version fehlt.

**Außerdem**
- Spulen besser zu erkennen: größer und mit hellem Rand, damit schwarzes (und bei hellem Design weißes) Filament sichtbar bleibt; ebenso die Farbpunkte und die Verbrauchsbalken.
- Bereichs-Editor: jeder Bereich mit kurzer Beschreibung.
- Schichtansicht: Die Objektliste zum Ausschließen ist standardmäßig eingeklappt.

Bitte prüfen: eine Kalibrierung (Statustext, kein Abschalten), Laden/Entladen mit leerem und geladenem Kopf, den Bereich *Meldungen*, die Firmware-Zeile im System-Reiter und den Selbsttest.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.2.0b1

Beta. First part of 2.2: building blocks for your own dashboard and a lot of polish from user ideas.

**Building blocks**
- New card *Snapmaker U1 – Section* (`custom:snapmaker-u1-section-card`): single sections of the card – camera, print job, heads, bed mesh, console, maintenance … – as cards of their own, to arrange freely in a *Sections* dashboard. Pick the sections in the editor; their order counts. With one section the Home Assistant card frame is the panel itself.
- `show:` now also sets the order (`layout: scroll` and the section card); new `layout: bare` (only the sections, no head, no tabs).

**Overview**
- **Printer display on the overview** at its real size, no empty frame around it (paxx12). New option `display_place`: `overview` (default), `tab` (own tab as before) or `off`. On the overview the picture refreshes every 2 s, with touch on as fast as before.
- **Slicer preview in the running print** next to the file name and progress; the small preview on the camera image is left out when the card shows the job panel.
- **Spools show their fill level** from Spoolman (remaining / net weight, roughly: 10 % left is a thin ring), and the spool of the printing head turns slowly (off with "reduce motion").
- **Usage of the last print per head** as bars in the spool colours; tap for the details (Spoolman spool, before → after).

**Controls**
- Speed quick buttons **85 / 100 / 115 %** (was 50 / 100 / 150), flow 95 / 100 / 105 %; the current value is marked. Own values with `speed_presets` / `flow_presets`.
- **Bed mesh** uses the width of the panel with readable heights in every cell, up to 12 × 12 points; switch the numbers off with `mesh_values: false`.
- **Bigger buttons** for touch: lock, display touch, zoom buttons and quick buttons.

**Look**
- One font: numbers in the card font with even digit widths instead of monospace (monospace only in the G-code console), fewer font sizes, calmer progress figure.

Please check: section card in a sections dashboard, display on the overview, spool levels and the turning spool during a print, the usage chart after a print.

### Deutsch

Beta. Erster Teil von 2.2: Baukasten für das eigene Dashboard und viel Feinschliff aus Ideen der Nutzer.

**Baukasten**
- Neue Karte *Snapmaker U1 – Bereich* (`custom:snapmaker-u1-section-card`): einzelne Bereiche der Karte – Kamera, Druckauftrag, Köpfe, Bettnivellierung, Konsole, Wartung … – als eigene Karten, frei anzuordnen in einem *Abschnitte*-Dashboard. Bereiche im Editor wählen; die Reihenfolge zählt. Mit einem Bereich ist der Kartenrahmen von Home Assistant selbst das Panel.
- `show:` legt jetzt auch die Reihenfolge fest (`layout: scroll` und die Bereichs-Karte); neu `layout: bare` (nur die Bereiche, ohne Kopf und Reiter).

**Übersicht**
- **Druckerdisplay in der Übersicht** in echter Größe, ohne leeren Rahmen drumherum (paxx12). Neue Option `display_place`: `overview` (Standard), `tab` (eigener Reiter wie bisher) oder `off`. In der Übersicht kommt alle 2 s ein neues Bild, mit eingeschaltetem Touch so schnell wie bisher.
- **Vorschaubild des Slicers im laufenden Druck** neben Dateiname und Fortschritt; das kleine Vorschaubild auf dem Kamerabild entfällt, wenn die Karte das Druckauftrags-Panel zeigt.
- **Spulen zeigen ihren Füllstand** aus Spoolman (Rest / Nettogewicht, grob: 10 % Rest ist ein dünner Ring), und die Spule des druckenden Kopfs dreht sich langsam (aus bei „Bewegung reduzieren“).
- **Verbrauch des letzten Drucks je Kopf** als Balken in den Spulenfarben; antippen zeigt die Details (Spoolman-Spule, vorher → nachher).

**Bedienung**
- Schnellwahl Geschwindigkeit **85 / 100 / 115 %** (bisher 50 / 100 / 150), Flussrate 95 / 100 / 105 %; der aktuelle Wert ist markiert. Eigene Werte mit `speed_presets` / `flow_presets`.
- **Bettnivellierung** nutzt die Breite des Panels, mit gut lesbaren Höhenwerten in jeder Kachel bis 12 × 12 Messpunkte; die Zahlen lassen sich mit `mesh_values: false` abschalten.
- **Größere Knöpfe** zum Antippen: Sperre, Display-Touch, Zoom-Knöpfe und Schnellwahl.

**Aussehen**
- Eine Schrift: Zahlen in der Kartenschrift mit gleich breiten Ziffern statt Monospace (Monospace nur noch in der G-Code-Konsole), weniger Schriftgrößen, ruhigere Fortschrittsanzeige.

Bitte prüfen: Bereichs-Karte in einem Abschnitte-Dashboard, Display in der Übersicht, Füllstand der Spulen und die drehende Spule im Druck, die Verbrauchsgrafik nach einem Druck.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.4

Bugfix, tested as 2.1.4b1.

**Fixed in 2.1.4**
- **Printer "offline" in Home Assistant after a while with the camera in live mode** ([#11](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues/11), thanks to [@goldsam328](https://github.com/goldsam328) for the report and analysis). The camera entity's MJPEG stream never closed its connection to the printer, so every view of the camera left one open until Home Assistant had no free connection to the printer left and the status poll timed out. The connection is now closed when the viewer leaves, and the stream itself is passed through correctly.
- README: installation as clear steps with *Open in HACS* and *Add integration* buttons.

**Snapmaker U1 Card is officially in HACS!** 🎉 It is now part of the HACS default list: search for *Snapmaker U1 Card* in HACS (on Home Assistant 2026.11 and newer under *Settings → Marketplace*); no custom repository needed any more. Thanks to everyone who tested, reported bugs and contributed!

**From 2.1.3**
- **Printer display in the card (paxx12 Extended Firmware).** paxx12 mirrors the touchscreen at `/screen/`; the integration finds it by itself and the card shows it in a new tab *Display*, at most at its real size and fitted to the phone. Admins can use it from the card: hand button on, then taps and swipes go to the touchscreen; touch switches off again after a while without input. Options `display_tab` (on) and `display_camera` (off: the display as one more step of the camera switch). Thanks to [@xPlayniac](https://github.com/xPlayniac) for the pull request!
- **Camera 2 is a real camera again:** the display mirror used to show up as Camera 2.
- **Load / unload filament** from the head dialog, the firmware's own procedure (as "unload at the end of the print"): unloading asks first, moves to the discard position, heats to the filament's temperature, pulls back and cuts; loading feeds a filament waiting in the feeder. Locked during a print. New service `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`).
- **Copy from the G-code console:** *Copy* in the console head copies the whole log, the copy icon next to a command copies that command with its answer.
- One-time notification in Home Assistant about the HACS listing (not on a fresh install). README: install through the HACS search first, with an "Open in HACS" button; the custom repository stays as a fallback.
- Build and test tools updated (esbuild, eslint 10, globals, jsdom 30); `minimatch` pinned to a fixed version (security advisory in a dev dependency only).

**From 2.1.2**
- **Card no longer copied to `/config/www`.** The dashboard resource now points to the integration's own path `/snapmaker_u1_card/card/snapmaker-u1-card.js`. On the first start after the update the old `/local/snapmaker_u1_card/…` resource is moved to it, and the old copy of the card file under `/config/www/snapmaker_u1_card/` is removed (only that file; the folder only if it is empty then). Nothing else in `/config/www` is touched.
- **Your edits are kept.** The status-light blueprint and the Assist sentence files are only written when they are missing, or replaced when they are exactly a version the integration shipped earlier. A file you changed is never overwritten, even with the old `managed` line still in it.
- **Config backup:** pruning old backups in `/config/snapmaker_u1_backup/` only removes the integration's own snapshot folders, never folders you put there.

If the card shows "Custom element doesn't exist" right after a restart, reload the page once.

**From 2.1.1**
- Amounts in the card (cost estimate, history, statistics, Spoolman stock, energy and cost) use the currency set in Home Assistant (*Settings → System → General*) and the format of your language, e.g. `0,47 €`, `€0.47`, `₺700,00`. The price fields in the settings and in the card's settings dialog show the matching unit (`₺/kg`, `$/kWh` …), push notifications too.
- Price limits raised for every currency: filament up to 100 000 per kg, fixed energy price up to 1 000 per kWh (was 500 and 5).
- Turkish for the card and the integration.
- Fixed: the HACS zip contained `__pycache__` files from subfolders.

**Everything in 2.1**

**Spoolman**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold). Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`. Picking a spool for a head stays under the print heads.
- New spool with suggestions: typing in *Search filament* shows your own Spoolman filaments first, then Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the suggestions Spoolman itself uses; 1.75 mm only). A pick fills vendor, material, name, colour, net weight and empty spool weight; a catalogue entry is imported into Spoolman once and reused afterwards. Vendor and material fields suggest known names; new fields for location and, from the tab, the head to assign.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`. The catalogue needs Spoolman 0.18 or newer with internet access.

**G-code preview**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. Parsed once in the background; the last three previews are kept.

**Top cover and chamber heater**
- Top cover mode in the card and as `select.…_top_cover_mode` (idle, cool, preheat, hot), chamber target as a slider and as `number.…_top_cover_chamber_target` (`SET_PURIFIER_MODE`).
- Notification *Chamber is warm* (event `chamber_ready`, off by default) when the chamber heater (Panda Breath / DragonBreath) or the top cover reaches its target.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover; the temperature chart shows the chamber heater with its target.
- Built from the firmware without the hardware at hand: feedback from owners is welcome, ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Languages**
- Card and integration now also in Spanish, French, Italian, Portuguese and Dutch, following Home Assistant's language (regional variants use the base language, other languages get English). Push notifications, firmware messages and the self test stay German or English for now. Corrections from native speakers are welcome: `frontend/src/i18n/<language>.js` and `custom_components/snapmaker_u1_card/translations/<language>.json`.

**Fixed**
- Camera away from home (Nabu Casa): the stream through Home Assistant restarted every time the card rebuilt; the camera frame now stays in place. `debug_camera: true` logs what caused a rebuild.
- History thumbnails: a file uploaded and started straight from the slicer got no image, and images of files that dropped out of the file list were deleted. Now fetched at print start, kept while the history uses them, missing ones repaired from the file if it still exists; otherwise the printer icon instead of a broken image.
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

Update in HACS, restart Home Assistant and reload the dashboard.

### Deutsch

Bugfix, getestet als 2.1.4b1.

**Behoben in 2.1.4**
- **Drucker in Home Assistant nach einer Weile „offline“, wenn die Kamera im Live-Modus läuft** ([#11](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues/11), danke an [@goldsam328](https://github.com/goldsam328) für Meldung und Analyse). Der MJPEG-Stream der Kamera-Entität schloss seine Verbindung zum Drucker nie; jede Ansicht der Kamera ließ eine offen, bis Home Assistant keine freie Verbindung zum Drucker mehr hatte und die Statusabfrage ins Leere lief. Jetzt wird die Verbindung geschlossen, sobald die Ansicht weg ist, und der Stream selbst wird richtig durchgereicht.
- README: Installation in klaren Schritten mit Knöpfen *Open in HACS* und *Add integration*.

**Snapmaker U1 Card ist offiziell in HACS!** 🎉 Sie steht jetzt in der Standardliste von HACS: in HACS nach *Snapmaker U1 Card* suchen (ab Home Assistant 2026.11 unter *Einstellungen → Marketplace*), ein benutzerdefiniertes Repository ist nicht mehr nötig. Danke an alle, die getestet, Fehler gemeldet und mitgebaut haben!

**Aus 2.1.3**
- **Druckerdisplay in der Karte (paxx12 Extended Firmware).** paxx12 spiegelt den Touchscreen unter `/screen/`; die Integration findet das selbst, und die Karte zeigt es in einem neuen Reiter *Display*, höchstens in Originalgröße und auf dem Handy passend. Admins können es aus der Karte bedienen: Hand-Knopf an, dann gehen Tippen und Wischen an den Touchscreen; ohne Eingabe schaltet sich Touch nach einer Weile wieder aus. Optionen `display_tab` (an) und `display_camera` (aus: das Display als weiterer Schritt am Kamera-Wechselknopf). Danke an [@xPlayniac](https://github.com/xPlayniac) für den Pull Request!
- **Kamera 2 ist wieder eine echte Kamera:** Der Display-Spiegel tauchte bisher als Kamera 2 auf.
- **Filament laden / entladen** im Kopf-Dialog, mit dem Ablauf der Firmware (wie „am Druckende entladen“): Entladen fragt vorher, fährt zur Abwurfposition, heizt auf die Filamenttemperatur, zieht zurück und schneidet ab; Laden zieht ein im Einzug wartendes Filament ein. Während eines Drucks gesperrt. Neuer Dienst `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`).
- **Kopieren aus der G-Code-Konsole:** *Kopieren* im Kopf der Konsole kopiert den ganzen Verlauf, das Kopier-Symbol neben einem Befehl diesen Befehl samt Antwort.
- Einmalige Benachrichtigung in Home Assistant zur Aufnahme in HACS (nicht bei Neuinstallation). README: Installation zuerst über die HACS-Suche, mit „Open in HACS“-Knopf; das benutzerdefinierte Repository bleibt als Ausweg.
- Werkzeuge zum Bauen und Testen aktualisiert (esbuild, eslint 10, globals, jsdom 30); `minimatch` auf eine behobene Version festgelegt (Sicherheitsmeldung nur in einer Entwicklungs-Abhängigkeit).

**Aus 2.1.2**
- **Karte wird nicht mehr nach `/config/www` kopiert.** Die Dashboard-Ressource zeigt jetzt auf den eigenen Pfad der Integration `/snapmaker_u1_card/card/snapmaker-u1-card.js`. Beim ersten Start nach dem Update wird die alte Ressource `/local/snapmaker_u1_card/…` darauf umgestellt und die alte Kopie der Kartendatei unter `/config/www/snapmaker_u1_card/` gelöscht (nur diese Datei, den Ordner nur, wenn er danach leer ist). Sonst wird in `/config/www` nichts angefasst.
- **Deine Änderungen bleiben.** Der Status-Licht-Blueprint und die Assist-Satzdateien werden nur geschrieben, wenn sie fehlen, oder ersetzt, wenn sie genau einer früher ausgelieferten Version entsprechen. Eine geänderte Datei wird nie überschrieben, auch nicht mit der alten `managed`-Zeile darin.
- **Konfigurationssicherung:** Beim Aufräumen alter Sicherungen in `/config/snapmaker_u1_backup/` werden nur noch die eigenen Sicherungsordner gelöscht, nie Ordner, die du dort abgelegt hast.

Zeigt die Karte direkt nach einem Neustart „Custom element doesn't exist“, die Seite einmal neu laden.

**Aus 2.1.1**
- Beträge in der Karte (Kostenschätzung, Verlauf, Statistik, Spoolman-Bestand, Strom und Kosten) nutzen die Währung aus Home Assistant (*Einstellungen → System → Allgemein*) im Format deiner Sprache, z. B. `0,47 €`, `€0.47`, `₺700,00`. Die Preisfelder in den Einstellungen und im Einstellungsdialog der Karte zeigen die passende Einheit (`₺/kg`, `$/kWh` …), Push-Nachrichten ebenso.
- Preisgrenzen für jede Währung angehoben: Filament bis 100 000 pro kg, fester Strompreis bis 1 000 pro kWh (bisher 500 und 5).
- Türkisch für Karte und Integration.
- Behoben: Das HACS-Zip enthielt `__pycache__`-Dateien aus Unterordnern.

**Alles aus 2.1**

**Spoolman**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle). Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`. Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Neue Spule mit Vorschlägen: Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann der Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm). Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule; ein Katalog-Eintrag wird einmal in Spoolman übernommen und danach wiederverwendet. Hersteller und Material schlagen bekannte Namen vor; neu sind Ort und, im Reiter, der Kopf zum Zuordnen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang.

**G-Code-Vorschau**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Top Cover und Kammerheizung**
- Top-Cover-Modus in der Karte und als `select.…_top_cover_modus` (Leerlauf, kühlen, vorheizen, heiß), Kammer-Soll als Regler und als `number.…_top_cover_kammer_soll` (`SET_PURIFIER_MODE`).
- Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus), wenn Kammerheizung (Panda Breath / DragonBreath) oder Top Cover ihr Soll erreichen.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover; der Temperaturverlauf zeigt die Kammerheizung mit Soll.
- Nach der Firmware gebaut, ohne die Hardware selbst zu haben: Rückmeldung von Besitzern ist willkommen, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Sprachen**
- Karte und Integration jetzt auch auf Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant (regionale Varianten nutzen die Grundsprache, andere Sprachen bekommen Englisch). Push-Benachrichtigungen, Firmware-Meldungen und der Selbsttest bleiben vorerst Deutsch oder Englisch. Korrekturen von Muttersprachlern gern: `frontend/src/i18n/<sprache>.js` und `custom_components/snapmaker_u1_card/translations/<sprache>.json`.

**Behoben**
- Kamera unterwegs (Nabu Casa): Der Stream über Home Assistant startete bei jedem Neuaufbau der Karte neu; der Kamerarahmen bleibt jetzt stehen. `debug_camera: true` zeigt, was einen Neuaufbau ausgelöst hat.
- Vorschaubilder der Historie: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde, bekam kein Bild, und Bilder von Dateien, die aus der Dateiliste fielen, wurden gelöscht. Jetzt beim Druckstart geholt, behalten, solange die Historie sie nutzt, fehlende aus der Datei nachgeholt, wenn es sie noch gibt; sonst das Drucker-Symbol statt eines kaputten Bilds.
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.4b1

Beta. Fix for the live camera.

- **Fixed: printer "offline" in Home Assistant after a while with the camera in live mode** ([#11](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues/11), thanks to [@goldsam328](https://github.com/goldsam328) for the report and analysis). The camera entity's MJPEG stream never closed its connection to the printer, so every view of the camera left one open until Home Assistant had no free connection to the printer left and the status poll timed out. The connection is now closed when the viewer leaves, and the stream itself is passed through correctly.
- README: installation as clear steps with *Open in HACS* and *Add integration* buttons.

Please check: open and close the dashboard with the camera many times (and the camera entity's dialog); the printer stays online.

### Deutsch

Beta. Fix für die Live-Kamera.

- **Behoben: Drucker in Home Assistant nach einer Weile „offline“, wenn die Kamera im Live-Modus läuft** ([#11](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues/11), danke an [@goldsam328](https://github.com/goldsam328) für Meldung und Analyse). Der MJPEG-Stream der Kamera-Entität schloss seine Verbindung zum Drucker nie; jede Ansicht der Kamera ließ eine offen, bis Home Assistant keine freie Verbindung zum Drucker mehr hatte und die Statusabfrage ins Leere lief. Jetzt wird die Verbindung geschlossen, sobald die Ansicht weg ist, und der Stream selbst wird richtig durchgereicht.
- README: Installation in klaren Schritten mit Knöpfen *Open in HACS* und *Add integration*.

Bitte prüfen: Dashboard mit Kamera (und den Dialog der Kamera-Entität) oft öffnen und schließen; der Drucker bleibt online.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.3

**Snapmaker U1 Card is officially in HACS!** 🎉 It is now part of the HACS default list: search for *Snapmaker U1 Card* in HACS (on Home Assistant 2026.11 and newer under *Settings → Marketplace*); no custom repository needed any more. Thanks to everyone who tested, reported bugs and contributed! Tested as 2.1.3b1–b3.

**New in 2.1.3**
- **Printer display in the card (paxx12 Extended Firmware).** paxx12 mirrors the touchscreen at `/screen/`; the integration finds it by itself and the card shows it in a new tab *Display*, at most at its real size and fitted to the phone. Admins can use it from the card: hand button on, then taps and swipes go to the touchscreen; touch switches off again after a while without input. Options `display_tab` (on) and `display_camera` (off: the display as one more step of the camera switch). Thanks to [@xPlayniac](https://github.com/xPlayniac) for the pull request!
- **Camera 2 is a real camera again:** the display mirror used to show up as Camera 2.
- **Load / unload filament** from the head dialog, the firmware's own procedure (as "unload at the end of the print"): unloading asks first, moves to the discard position, heats to the filament's temperature, pulls back and cuts; loading feeds a filament waiting in the feeder. Locked during a print. New service `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`).
- **Copy from the G-code console:** *Copy* in the console head copies the whole log, the copy icon next to a command copies that command with its answer.
- One-time notification in Home Assistant about the HACS listing (not on a fresh install). README: install through the HACS search first, with an "Open in HACS" button; the custom repository stays as a fallback.
- Build and test tools updated (esbuild, eslint 10, globals, jsdom 30); `minimatch` pinned to a fixed version (security advisory in a dev dependency only).

**From 2.1.2**
- **Card no longer copied to `/config/www`.** The dashboard resource now points to the integration's own path `/snapmaker_u1_card/card/snapmaker-u1-card.js`. On the first start after the update the old `/local/snapmaker_u1_card/…` resource is moved to it, and the old copy of the card file under `/config/www/snapmaker_u1_card/` is removed (only that file; the folder only if it is empty then). Nothing else in `/config/www` is touched.
- **Your edits are kept.** The status-light blueprint and the Assist sentence files are only written when they are missing, or replaced when they are exactly a version the integration shipped earlier. A file you changed is never overwritten, even with the old `managed` line still in it.
- **Config backup:** pruning old backups in `/config/snapmaker_u1_backup/` only removes the integration's own snapshot folders, never folders you put there.

If the card shows "Custom element doesn't exist" right after a restart, reload the page once.

**From 2.1.1**
- Amounts in the card (cost estimate, history, statistics, Spoolman stock, energy and cost) use the currency set in Home Assistant (*Settings → System → General*) and the format of your language, e.g. `0,47 €`, `€0.47`, `₺700,00`. The price fields in the settings and in the card's settings dialog show the matching unit (`₺/kg`, `$/kWh` …), push notifications too.
- Price limits raised for every currency: filament up to 100 000 per kg, fixed energy price up to 1 000 per kWh (was 500 and 5).
- Turkish for the card and the integration.
- Fixed: the HACS zip contained `__pycache__` files from subfolders.

**Everything in 2.1**

**Spoolman**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold). Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`. Picking a spool for a head stays under the print heads.
- New spool with suggestions: typing in *Search filament* shows your own Spoolman filaments first, then Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the suggestions Spoolman itself uses; 1.75 mm only). A pick fills vendor, material, name, colour, net weight and empty spool weight; a catalogue entry is imported into Spoolman once and reused afterwards. Vendor and material fields suggest known names; new fields for location and, from the tab, the head to assign.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`. The catalogue needs Spoolman 0.18 or newer with internet access.

**G-code preview**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. Parsed once in the background; the last three previews are kept.

**Top cover and chamber heater**
- Top cover mode in the card and as `select.…_top_cover_mode` (idle, cool, preheat, hot), chamber target as a slider and as `number.…_top_cover_chamber_target` (`SET_PURIFIER_MODE`).
- Notification *Chamber is warm* (event `chamber_ready`, off by default) when the chamber heater (Panda Breath / DragonBreath) or the top cover reaches its target.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover; the temperature chart shows the chamber heater with its target.
- Built from the firmware without the hardware at hand: feedback from owners is welcome, ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Languages**
- Card and integration now also in Spanish, French, Italian, Portuguese and Dutch, following Home Assistant's language (regional variants use the base language, other languages get English). Push notifications, firmware messages and the self test stay German or English for now. Corrections from native speakers are welcome: `frontend/src/i18n/<language>.js` and `custom_components/snapmaker_u1_card/translations/<language>.json`.

**Fixed**
- Camera away from home (Nabu Casa): the stream through Home Assistant restarted every time the card rebuilt; the camera frame now stays in place. `debug_camera: true` logs what caused a rebuild.
- History thumbnails: a file uploaded and started straight from the slicer got no image, and images of files that dropped out of the file list were deleted. Now fetched at print start, kept while the history uses them, missing ones repaired from the file if it still exists; otherwise the printer icon instead of a broken image.
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

Update in HACS, restart Home Assistant and reload the dashboard.

### Deutsch

**Snapmaker U1 Card ist offiziell in HACS!** 🎉 Sie steht jetzt in der Standardliste von HACS: in HACS nach *Snapmaker U1 Card* suchen (ab Home Assistant 2026.11 unter *Einstellungen → Marketplace*), ein benutzerdefiniertes Repository ist nicht mehr nötig. Danke an alle, die getestet, Fehler gemeldet und mitgebaut haben! Getestet als 2.1.3b1–b3.

**Neu in 2.1.3**
- **Druckerdisplay in der Karte (paxx12 Extended Firmware).** paxx12 spiegelt den Touchscreen unter `/screen/`; die Integration findet das selbst, und die Karte zeigt es in einem neuen Reiter *Display*, höchstens in Originalgröße und auf dem Handy passend. Admins können es aus der Karte bedienen: Hand-Knopf an, dann gehen Tippen und Wischen an den Touchscreen; ohne Eingabe schaltet sich Touch nach einer Weile wieder aus. Optionen `display_tab` (an) und `display_camera` (aus: das Display als weiterer Schritt am Kamera-Wechselknopf). Danke an [@xPlayniac](https://github.com/xPlayniac) für den Pull Request!
- **Kamera 2 ist wieder eine echte Kamera:** Der Display-Spiegel tauchte bisher als Kamera 2 auf.
- **Filament laden / entladen** im Kopf-Dialog, mit dem Ablauf der Firmware (wie „am Druckende entladen“): Entladen fragt vorher, fährt zur Abwurfposition, heizt auf die Filamenttemperatur, zieht zurück und schneidet ab; Laden zieht ein im Einzug wartendes Filament ein. Während eines Drucks gesperrt. Neuer Dienst `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`).
- **Kopieren aus der G-Code-Konsole:** *Kopieren* im Kopf der Konsole kopiert den ganzen Verlauf, das Kopier-Symbol neben einem Befehl diesen Befehl samt Antwort.
- Einmalige Benachrichtigung in Home Assistant zur Aufnahme in HACS (nicht bei Neuinstallation). README: Installation zuerst über die HACS-Suche, mit „Open in HACS“-Knopf; das benutzerdefinierte Repository bleibt als Ausweg.
- Werkzeuge zum Bauen und Testen aktualisiert (esbuild, eslint 10, globals, jsdom 30); `minimatch` auf eine behobene Version festgelegt (Sicherheitsmeldung nur in einer Entwicklungs-Abhängigkeit).

**Aus 2.1.2**
- **Karte wird nicht mehr nach `/config/www` kopiert.** Die Dashboard-Ressource zeigt jetzt auf den eigenen Pfad der Integration `/snapmaker_u1_card/card/snapmaker-u1-card.js`. Beim ersten Start nach dem Update wird die alte Ressource `/local/snapmaker_u1_card/…` darauf umgestellt und die alte Kopie der Kartendatei unter `/config/www/snapmaker_u1_card/` gelöscht (nur diese Datei, den Ordner nur, wenn er danach leer ist). Sonst wird in `/config/www` nichts angefasst.
- **Deine Änderungen bleiben.** Der Status-Licht-Blueprint und die Assist-Satzdateien werden nur geschrieben, wenn sie fehlen, oder ersetzt, wenn sie genau einer früher ausgelieferten Version entsprechen. Eine geänderte Datei wird nie überschrieben, auch nicht mit der alten `managed`-Zeile darin.
- **Konfigurationssicherung:** Beim Aufräumen alter Sicherungen in `/config/snapmaker_u1_backup/` werden nur noch die eigenen Sicherungsordner gelöscht, nie Ordner, die du dort abgelegt hast.

Zeigt die Karte direkt nach einem Neustart „Custom element doesn't exist“, die Seite einmal neu laden.

**Aus 2.1.1**
- Beträge in der Karte (Kostenschätzung, Verlauf, Statistik, Spoolman-Bestand, Strom und Kosten) nutzen die Währung aus Home Assistant (*Einstellungen → System → Allgemein*) im Format deiner Sprache, z. B. `0,47 €`, `€0.47`, `₺700,00`. Die Preisfelder in den Einstellungen und im Einstellungsdialog der Karte zeigen die passende Einheit (`₺/kg`, `$/kWh` …), Push-Nachrichten ebenso.
- Preisgrenzen für jede Währung angehoben: Filament bis 100 000 pro kg, fester Strompreis bis 1 000 pro kWh (bisher 500 und 5).
- Türkisch für Karte und Integration.
- Behoben: Das HACS-Zip enthielt `__pycache__`-Dateien aus Unterordnern.

**Alles aus 2.1**

**Spoolman**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle). Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`. Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Neue Spule mit Vorschlägen: Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann der Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm). Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule; ein Katalog-Eintrag wird einmal in Spoolman übernommen und danach wiederverwendet. Hersteller und Material schlagen bekannte Namen vor; neu sind Ort und, im Reiter, der Kopf zum Zuordnen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang.

**G-Code-Vorschau**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Top Cover und Kammerheizung**
- Top-Cover-Modus in der Karte und als `select.…_top_cover_modus` (Leerlauf, kühlen, vorheizen, heiß), Kammer-Soll als Regler und als `number.…_top_cover_kammer_soll` (`SET_PURIFIER_MODE`).
- Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus), wenn Kammerheizung (Panda Breath / DragonBreath) oder Top Cover ihr Soll erreichen.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover; der Temperaturverlauf zeigt die Kammerheizung mit Soll.
- Nach der Firmware gebaut, ohne die Hardware selbst zu haben: Rückmeldung von Besitzern ist willkommen, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Sprachen**
- Karte und Integration jetzt auch auf Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant (regionale Varianten nutzen die Grundsprache, andere Sprachen bekommen Englisch). Push-Benachrichtigungen, Firmware-Meldungen und der Selbsttest bleiben vorerst Deutsch oder Englisch. Korrekturen von Muttersprachlern gern: `frontend/src/i18n/<sprache>.js` und `custom_components/snapmaker_u1_card/translations/<sprache>.json`.

**Behoben**
- Kamera unterwegs (Nabu Casa): Der Stream über Home Assistant startete bei jedem Neuaufbau der Karte neu; der Kamerarahmen bleibt jetzt stehen. `debug_camera: true` zeigt, was einen Neuaufbau ausgelöst hat.
- Vorschaubilder der Historie: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde, bekam kein Bild, und Bilder von Dateien, die aus der Dateiliste fielen, wurden gelöscht. Jetzt beim Druckstart geholt, behalten, solange die Historie sie nutzt, fehlende aus der Datei nachgeholt, wenn es sie noch gibt; sonst das Drucker-Symbol statt eines kaputten Bilds.
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.3b3

Beta. **Snapmaker U1 Card is officially in HACS!** 🎉 Plus loading and unloading filament from the card.

**In the HACS default list**
- The integration has been accepted into the HACS default list. New users find it by searching for *Snapmaker U1 Card* in HACS (on Home Assistant 2026.11 and newer under *Settings → Marketplace*); the custom repository is only a fallback now. README updated, with a one-click "Open in HACS" button.
- After the update Home Assistant shows this news once as a notification (not on a fresh install).

**Load / unload filament**
- Head dialog: new buttons *Load* and *Unload*. Unloading asks first, then runs the firmware's own procedure (the same as "unload at the end of the print"): move to the discard position, heat to the filament's temperature, pull back, cut. Loading feeds a filament waiting in the feeder. Progress as short messages; locked during a print.
- New service `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`) for automations.

Please check: unload one head, then load it again (with the feeder in auto mode).

### Deutsch

Beta. **Snapmaker U1 Card ist offiziell in HACS!** 🎉 Dazu Filament laden und entladen aus der Karte.

**In der Standardliste von HACS**
- Die Integration wurde in die Standardliste von HACS aufgenommen. Neue Nutzer finden sie über die Suche nach *Snapmaker U1 Card* in HACS (ab Home Assistant 2026.11 unter *Einstellungen → Marketplace*); das benutzerdefinierte Repository ist nur noch der Ausweg. README angepasst, mit „Open in HACS“-Knopf.
- Nach dem Update zeigt Home Assistant diese Nachricht einmal als Benachrichtigung (nicht bei einer Neuinstallation).

**Filament laden / entladen**
- Kopf-Dialog: neue Knöpfe *Laden* und *Entladen*. Entladen fragt vorher nach und führt dann den Ablauf der Firmware aus (derselbe wie „am Druckende entladen“): zur Abwurfposition fahren, auf die Filamenttemperatur heizen, zurückziehen, abschneiden. Laden zieht ein im Einzug wartendes Filament ein. Fortschritt als kurze Meldungen; während eines Drucks gesperrt.
- Neuer Dienst `snapmaker_u1_card.filament` (`head` 1–4, `action` `load`/`unload`) für Automationen.

Bitte prüfen: einen Kopf entladen, danach wieder laden (Einzug im Automatik-Modus).

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.3b2

Beta. Display size, copying from the console.

- **Printer display at most its real size:** on a wide dashboard the display no longer gets blown up; it shows at most at its own resolution (e.g. 480 × 320) and shrinks on a phone to the card width. Fullscreen still fills the screen.
- **Copy from the G-code console:** *Copy* in the console head copies the whole log, the small copy icon next to a command copies that command with its answer. The text can also be selected by hand.
- Test tools: jsdom 30 (Dependabot); the camera rebuild no longer relies on a `:scope` selector.

Please check: display size on PC and phone, copying in the console (over https and, if you use it, over plain http on the LAN).

### Deutsch

Beta. Displaygröße, Kopieren aus der Konsole.

- **Druckerdisplay höchstens in Originalgröße:** Auf breiten Dashboards wird das Display nicht mehr aufgeblasen; es erscheint höchstens in seiner eigenen Auflösung (z. B. 480 × 320) und passt sich auf dem Handy der Kartenbreite an. Vollbild füllt weiterhin den Bildschirm.
- **Kopieren aus der G-Code-Konsole:** *Kopieren* im Kopf der Konsole kopiert den ganzen Verlauf, das kleine Kopier-Symbol neben einem Befehl kopiert diesen Befehl samt Antwort. Der Text lässt sich auch von Hand markieren.
- Test-Werkzeuge: jsdom 30 (Dependabot); der Neuaufbau um die Kamera braucht keinen `:scope`-Selektor mehr.

Bitte prüfen: Displaygröße am PC und auf dem Handy, Kopieren in der Konsole (über https und, falls du es nutzt, über reines http im Heimnetz).

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.3b1

Beta. The printer display in the card. Thanks to [@xPlayniac](https://github.com/xPlayniac) for the pull request!

**Printer display (paxx12 Extended Firmware)**
- paxx12 mirrors the printer's touchscreen at `/screen/`. The integration detects it on its own and the card shows it in a new tab *Display*, fresh through Home Assistant (also over https and Nabu Casa).
- Admins can use the display from the card: tap the hand button, then taps and swipes on the picture go to the touchscreen. Touch switches itself off again after the control lock time without input (60 s if the lock is off). The integration only accepts touches from admins, inside the panel, to the configured printer and at most about 20 per second.
- **Camera 2 is a real camera again:** the display mirror used to show up as Camera 2; it is now never taken as a camera.
- New card options: `display_tab` (default on) and `display_camera` (default off: the display as one more step of the camera switch button). Without the mirror (stock firmware) nothing changes.
- When the display is dimmed, the first tap only wakes it (firmware behaviour).

**Also**
- Build tools updated (esbuild, eslint 10, globals); `minimatch` pinned to a fixed version (security advisory in a dev dependency only).

Please check: the tab *Display* shows up, Camera 2 is your USB camera (or gone without one), touch works with the hand button and switches off after a while.

### Deutsch

Beta. Das Druckerdisplay in der Karte. Danke an [@xPlayniac](https://github.com/xPlayniac) für den Pull Request!

**Druckerdisplay (paxx12 Extended Firmware)**
- paxx12 spiegelt den Touchscreen des Druckers unter `/screen/`. Die Integration erkennt das selbst, und die Karte zeigt es in einem neuen Reiter *Display*, frisch über Home Assistant (auch über https und Nabu Casa).
- Admins können das Display aus der Karte bedienen: Hand-Knopf antippen, dann gehen Tippen und Wischen auf dem Bild an den Touchscreen. Nach der Zeit der Bediensperre ohne Eingabe schaltet sich Touch wieder aus (60 s, wenn die Sperre aus ist). Die Integration nimmt Berührungen nur von Admins, innerhalb des Displays, an den eingerichteten Drucker und höchstens etwa 20 pro Sekunde an.
- **Kamera 2 ist wieder eine echte Kamera:** Der Display-Spiegel tauchte bisher als Kamera 2 auf; er wird jetzt nie als Kamera genommen.
- Neue Kartenoptionen: `display_tab` (Standard an) und `display_camera` (Standard aus: das Display als weiterer Schritt am Kamera-Wechselknopf). Ohne den Spiegel (Stock-Firmware) ändert sich nichts.
- Ist das Display gedimmt, weckt der erste Tipp es nur auf (Verhalten der Firmware).

**Außerdem**
- Werkzeuge zum Bauen aktualisiert (esbuild, eslint 10, globals); `minimatch` auf eine behobene Version festgelegt (Sicherheitsmeldung nur in einer Entwicklungs-Abhängigkeit).

Bitte prüfen: Der Reiter *Display* erscheint, Kamera 2 ist deine USB-Kamera (oder ohne USB-Kamera weg), Touch geht per Hand-Knopf und schaltet sich nach einer Weile wieder aus.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.2

Changes from the review for the HACS / Home Assistant Marketplace catalogue (thanks to frenck), tested as 2.1.2b1.

**New in 2.1.2**
- **Card no longer copied to `/config/www`.** The dashboard resource now points to the integration's own path `/snapmaker_u1_card/card/snapmaker-u1-card.js`. On the first start after the update the old `/local/snapmaker_u1_card/…` resource is moved to it, and the old copy of the card file under `/config/www/snapmaker_u1_card/` is removed (only that file; the folder only if it is empty then). Nothing else in `/config/www` is touched.
- **Your edits are kept.** The status-light blueprint and the Assist sentence files are only written when they are missing, or replaced when they are exactly a version the integration shipped earlier. A file you changed is never overwritten, even with the old `managed` line still in it.
- **Config backup:** pruning old backups in `/config/snapmaker_u1_backup/` only removes the integration's own snapshot folders, never folders you put there.

If the card shows "Custom element doesn't exist" right after a restart, reload the page once.

**From 2.1.1**
- Amounts in the card (cost estimate, history, statistics, Spoolman stock, energy and cost) use the currency set in Home Assistant (*Settings → System → General*) and the format of your language, e.g. `0,47 €`, `€0.47`, `₺700,00`. The price fields in the settings and in the card's settings dialog show the matching unit (`₺/kg`, `$/kWh` …), push notifications too.
- Price limits raised for every currency: filament up to 100 000 per kg, fixed energy price up to 1 000 per kWh (was 500 and 5).
- Turkish for the card and the integration.
- Fixed: the HACS zip contained `__pycache__` files from subfolders.

**Everything in 2.1**

**Spoolman**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold). Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`. Picking a spool for a head stays under the print heads.
- New spool with suggestions: typing in *Search filament* shows your own Spoolman filaments first, then Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the suggestions Spoolman itself uses; 1.75 mm only). A pick fills vendor, material, name, colour, net weight and empty spool weight; a catalogue entry is imported into Spoolman once and reused afterwards. Vendor and material fields suggest known names; new fields for location and, from the tab, the head to assign.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`. The catalogue needs Spoolman 0.18 or newer with internet access.

**G-code preview**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. Parsed once in the background; the last three previews are kept.

**Top cover and chamber heater**
- Top cover mode in the card and as `select.…_top_cover_mode` (idle, cool, preheat, hot), chamber target as a slider and as `number.…_top_cover_chamber_target` (`SET_PURIFIER_MODE`).
- Notification *Chamber is warm* (event `chamber_ready`, off by default) when the chamber heater (Panda Breath / DragonBreath) or the top cover reaches its target.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover; the temperature chart shows the chamber heater with its target.
- Built from the firmware without the hardware at hand: feedback from owners is welcome, ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Languages**
- Card and integration now also in Spanish, French, Italian, Portuguese and Dutch, following Home Assistant's language (regional variants use the base language, other languages get English). Push notifications, firmware messages and the self test stay German or English for now. Corrections from native speakers are welcome: `frontend/src/i18n/<language>.js` and `custom_components/snapmaker_u1_card/translations/<language>.json`.

**Fixed**
- Camera away from home (Nabu Casa): the stream through Home Assistant restarted every time the card rebuilt; the camera frame now stays in place. `debug_camera: true` logs what caused a rebuild.
- History thumbnails: a file uploaded and started straight from the slicer got no image, and images of files that dropped out of the file list were deleted. Now fetched at print start, kept while the history uses them, missing ones repaired from the file if it still exists; otherwise the printer icon instead of a broken image.
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

Update in HACS, restart Home Assistant and reload the dashboard.

### Deutsch

Änderungen aus der Prüfung für den Katalog von HACS / Home Assistant Marketplace (danke an frenck), getestet als 2.1.2b1.

**Neu in 2.1.2**
- **Karte wird nicht mehr nach `/config/www` kopiert.** Die Dashboard-Ressource zeigt jetzt auf den eigenen Pfad der Integration `/snapmaker_u1_card/card/snapmaker-u1-card.js`. Beim ersten Start nach dem Update wird die alte Ressource `/local/snapmaker_u1_card/…` darauf umgestellt und die alte Kopie der Kartendatei unter `/config/www/snapmaker_u1_card/` gelöscht (nur diese Datei, den Ordner nur, wenn er danach leer ist). Sonst wird in `/config/www` nichts angefasst.
- **Deine Änderungen bleiben.** Der Status-Licht-Blueprint und die Assist-Satzdateien werden nur geschrieben, wenn sie fehlen, oder ersetzt, wenn sie genau einer früher ausgelieferten Version entsprechen. Eine geänderte Datei wird nie überschrieben, auch nicht mit der alten `managed`-Zeile darin.
- **Konfigurationssicherung:** Beim Aufräumen alter Sicherungen in `/config/snapmaker_u1_backup/` werden nur noch die eigenen Sicherungsordner gelöscht, nie Ordner, die du dort abgelegt hast.

Zeigt die Karte direkt nach einem Neustart „Custom element doesn't exist“, die Seite einmal neu laden.

**Aus 2.1.1**
- Beträge in der Karte (Kostenschätzung, Verlauf, Statistik, Spoolman-Bestand, Strom und Kosten) nutzen die Währung aus Home Assistant (*Einstellungen → System → Allgemein*) im Format deiner Sprache, z. B. `0,47 €`, `€0.47`, `₺700,00`. Die Preisfelder in den Einstellungen und im Einstellungsdialog der Karte zeigen die passende Einheit (`₺/kg`, `$/kWh` …), Push-Nachrichten ebenso.
- Preisgrenzen für jede Währung angehoben: Filament bis 100 000 pro kg, fester Strompreis bis 1 000 pro kWh (bisher 500 und 5).
- Türkisch für Karte und Integration.
- Behoben: Das HACS-Zip enthielt `__pycache__`-Dateien aus Unterordnern.

**Alles aus 2.1**

**Spoolman**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle). Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`. Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Neue Spule mit Vorschlägen: Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann der Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm). Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule; ein Katalog-Eintrag wird einmal in Spoolman übernommen und danach wiederverwendet. Hersteller und Material schlagen bekannte Namen vor; neu sind Ort und, im Reiter, der Kopf zum Zuordnen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang.

**G-Code-Vorschau**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Top Cover und Kammerheizung**
- Top-Cover-Modus in der Karte und als `select.…_top_cover_modus` (Leerlauf, kühlen, vorheizen, heiß), Kammer-Soll als Regler und als `number.…_top_cover_kammer_soll` (`SET_PURIFIER_MODE`).
- Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus), wenn Kammerheizung (Panda Breath / DragonBreath) oder Top Cover ihr Soll erreichen.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover; der Temperaturverlauf zeigt die Kammerheizung mit Soll.
- Nach der Firmware gebaut, ohne die Hardware selbst zu haben: Rückmeldung von Besitzern ist willkommen, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Sprachen**
- Karte und Integration jetzt auch auf Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant (regionale Varianten nutzen die Grundsprache, andere Sprachen bekommen Englisch). Push-Benachrichtigungen, Firmware-Meldungen und der Selbsttest bleiben vorerst Deutsch oder Englisch. Korrekturen von Muttersprachlern gern: `frontend/src/i18n/<sprache>.js` und `custom_components/snapmaker_u1_card/translations/<sprache>.json`.

**Behoben**
- Kamera unterwegs (Nabu Casa): Der Stream über Home Assistant startete bei jedem Neuaufbau der Karte neu; der Kamerarahmen bleibt jetzt stehen. `debug_camera: true` zeigt, was einen Neuaufbau ausgelöst hat.
- Vorschaubilder der Historie: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde, bekam kein Bild, und Bilder von Dateien, die aus der Dateiliste fielen, wurden gelöscht. Jetzt beim Druckstart geholt, behalten, solange die Historie sie nutzt, fehlende aus der Datei nachgeholt, wenn es sie noch gibt; sonst das Drucker-Symbol statt eines kaputten Bilds.
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.2b1

Beta. Changes from the review for the HACS / Home Assistant Marketplace catalogue (thanks to frenck).

- **Card no longer copied to `/config/www`.** The dashboard resource now points to the integration's own path `/snapmaker_u1_card/card/snapmaker-u1-card.js`. On the first start after the update the old `/local/snapmaker_u1_card/…` resource is moved to it, and the old copy of the card file under `/config/www/snapmaker_u1_card/` is removed (only that file; the folder only if it is empty then). Nothing else in `/config/www` is touched.
- **Your edits are kept.** The status-light blueprint and the Assist sentence files are only written when they are missing, or replaced when they are exactly a version the integration shipped earlier. A file you changed is never overwritten, even with the old `managed` line still in it.

Please check after updating and restarting Home Assistant: the card loads, *Dashboards → Resources* lists only `/snapmaker_u1_card/card/…`, and `/config/www/snapmaker_u1_card/` is gone.

### Deutsch

Beta. Änderungen aus der Prüfung für den Katalog von HACS / Home Assistant Marketplace (danke an frenck).

- **Karte wird nicht mehr nach `/config/www` kopiert.** Die Dashboard-Ressource zeigt jetzt auf den eigenen Pfad der Integration `/snapmaker_u1_card/card/snapmaker-u1-card.js`. Beim ersten Start nach dem Update wird die alte Ressource `/local/snapmaker_u1_card/…` darauf umgestellt und die alte Kopie der Kartendatei unter `/config/www/snapmaker_u1_card/` gelöscht (nur diese Datei, den Ordner nur, wenn er danach leer ist). Sonst wird in `/config/www` nichts angefasst.
- **Deine Änderungen bleiben.** Der Status-Licht-Blueprint und die Assist-Satzdateien werden nur geschrieben, wenn sie fehlen, oder ersetzt, wenn sie genau einer früher ausgelieferten Version entsprechen. Eine geänderte Datei wird nie überschrieben, auch nicht mit der alten `managed`-Zeile darin.

Bitte nach Update und Neustart von Home Assistant prüfen: Die Karte lädt, unter *Dashboards → Ressourcen* steht nur `/snapmaker_u1_card/card/…`, und `/config/www/snapmaker_u1_card/` ist weg.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.1

Your currency instead of a fixed €, higher price limits and Turkish. Thanks to [@anilgunduzz](https://github.com/anilgunduzz) for the pull request!

**New in 2.1.1**
- Amounts in the card (cost estimate, history, statistics, Spoolman stock, energy and cost) use the currency set in Home Assistant (*Settings → System → General*) and the format of your language, e.g. `0,47 €`, `€0.47`, `₺700,00`. The price fields in the settings and in the card's settings dialog show the matching unit (`₺/kg`, `$/kWh` …), push notifications too.
- Price limits raised for every currency: filament up to 100 000 per kg, fixed energy price up to 1 000 per kWh (was 500 and 5).
- Turkish for the card and the integration.
- Fixed: the HACS zip contained `__pycache__` files from subfolders.

Note for English: amounts in euro now read `€0.47` instead of `0.47 €`.

**Everything in 2.1**

**Spoolman**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold). Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`. Picking a spool for a head stays under the print heads.
- New spool with suggestions: typing in *Search filament* shows your own Spoolman filaments first, then Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the suggestions Spoolman itself uses; 1.75 mm only). A pick fills vendor, material, name, colour, net weight and empty spool weight; a catalogue entry is imported into Spoolman once and reused afterwards. Vendor and material fields suggest known names; new fields for location and, from the tab, the head to assign.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`. The catalogue needs Spoolman 0.18 or newer with internet access.

**G-code preview**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. Parsed once in the background; the last three previews are kept.

**Top cover and chamber heater**
- Top cover mode in the card and as `select.…_top_cover_mode` (idle, cool, preheat, hot), chamber target as a slider and as `number.…_top_cover_chamber_target` (`SET_PURIFIER_MODE`).
- Notification *Chamber is warm* (event `chamber_ready`, off by default) when the chamber heater (Panda Breath / DragonBreath) or the top cover reaches its target.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover; the temperature chart shows the chamber heater with its target.
- Built from the firmware without the hardware at hand: feedback from owners is welcome, ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Languages**
- Card and integration now also in Spanish, French, Italian, Portuguese and Dutch, following Home Assistant's language (regional variants use the base language, other languages get English). Push notifications, firmware messages and the self test stay German or English for now. Corrections from native speakers are welcome: `frontend/src/i18n/<language>.js` and `custom_components/snapmaker_u1_card/translations/<language>.json`.

**Fixed**
- Camera away from home (Nabu Casa): the stream through Home Assistant restarted every time the card rebuilt; the camera frame now stays in place. `debug_camera: true` logs what caused a rebuild.
- History thumbnails: a file uploaded and started straight from the slicer got no image, and images of files that dropped out of the file list were deleted. Now fetched at print start, kept while the history uses them, missing ones repaired from the file if it still exists; otherwise the printer icon instead of a broken image.
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

Update in HACS, restart Home Assistant and reload the dashboard.

### Deutsch

Deine Währung statt fest €, höhere Preisgrenzen und Türkisch. Danke an [@anilgunduzz](https://github.com/anilgunduzz) für den Pull Request!

**Neu in 2.1.1**
- Beträge in der Karte (Kostenschätzung, Verlauf, Statistik, Spoolman-Bestand, Strom und Kosten) nutzen die Währung aus Home Assistant (*Einstellungen → System → Allgemein*) im Format deiner Sprache, z. B. `0,47 €`, `€0.47`, `₺700,00`. Die Preisfelder in den Einstellungen und im Einstellungsdialog der Karte zeigen die passende Einheit (`₺/kg`, `$/kWh` …), Push-Nachrichten ebenso.
- Preisgrenzen für jede Währung angehoben: Filament bis 100 000 pro kg, fester Strompreis bis 1 000 pro kWh (bisher 500 und 5).
- Türkisch für Karte und Integration.
- Behoben: Das HACS-Zip enthielt `__pycache__`-Dateien aus Unterordnern.

**Alles aus 2.1**

**Spoolman**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle). Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`. Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Neue Spule mit Vorschlägen: Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann der Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm). Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule; ein Katalog-Eintrag wird einmal in Spoolman übernommen und danach wiederverwendet. Hersteller und Material schlagen bekannte Namen vor; neu sind Ort und, im Reiter, der Kopf zum Zuordnen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang.

**G-Code-Vorschau**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Top Cover und Kammerheizung**
- Top-Cover-Modus in der Karte und als `select.…_top_cover_modus` (Leerlauf, kühlen, vorheizen, heiß), Kammer-Soll als Regler und als `number.…_top_cover_kammer_soll` (`SET_PURIFIER_MODE`).
- Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus), wenn Kammerheizung (Panda Breath / DragonBreath) oder Top Cover ihr Soll erreichen.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover; der Temperaturverlauf zeigt die Kammerheizung mit Soll.
- Nach der Firmware gebaut, ohne die Hardware selbst zu haben: Rückmeldung von Besitzern ist willkommen, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Sprachen**
- Karte und Integration jetzt auch auf Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant (regionale Varianten nutzen die Grundsprache, andere Sprachen bekommen Englisch). Push-Benachrichtigungen, Firmware-Meldungen und der Selbsttest bleiben vorerst Deutsch oder Englisch. Korrekturen von Muttersprachlern gern: `frontend/src/i18n/<sprache>.js` und `custom_components/snapmaker_u1_card/translations/<sprache>.json`.

**Behoben**
- Kamera unterwegs (Nabu Casa): Der Stream über Home Assistant startete bei jedem Neuaufbau der Karte neu; der Kamerarahmen bleibt jetzt stehen. `debug_camera: true` zeigt, was einen Neuaufbau ausgelöst hat.
- Vorschaubilder der Historie: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde, bekam kein Bild, und Bilder von Dateien, die aus der Dateiliste fielen, wurden gelöscht. Jetzt beim Druckstart geholt, behalten, solange die Historie sie nutzt, fehlende aus der Datei nachgeholt, wenn es sie noch gibt; sonst das Drucker-Symbol statt eines kaputten Bilds.
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.0

Spoolman in its own tab, a G-code preview with sliders, the top cover controlled from the card and five more languages. Thanks to everyone who tested the betas!

**Spoolman**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold). Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`. Picking a spool for a head stays under the print heads.
- New spool with suggestions: typing in *Search filament* shows your own Spoolman filaments first, then Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the suggestions Spoolman itself uses; 1.75 mm only). A pick fills vendor, material, name, colour, net weight and empty spool weight; a catalogue entry is imported into Spoolman once and reused afterwards. Vendor and material fields suggest known names; new fields for location and, from the tab, the head to assign.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`. The catalogue needs Spoolman 0.18 or newer with internet access.

**G-code preview**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. Parsed once in the background; the last three previews are kept.

**Top cover and chamber heater**
- Top cover mode in the card and as `select.…_top_cover_mode` (idle, cool, preheat, hot), chamber target as a slider and as `number.…_top_cover_chamber_target` (`SET_PURIFIER_MODE`).
- Notification *Chamber is warm* (event `chamber_ready`, off by default) when the chamber heater (Panda Breath / DragonBreath) or the top cover reaches its target.
- The maintenance item *Replace the air filter* counts the real filter hours of the top cover; the temperature chart shows the chamber heater with its target.
- Built from the firmware without the hardware at hand: feedback from owners is welcome, ideally with the diagnostics file. Without a top cover or chamber heater nothing of this shows up.

**Languages**
- Card and integration now also in Spanish, French, Italian, Portuguese and Dutch, following Home Assistant's language (regional variants use the base language, other languages get English). Push notifications, firmware messages and the self test stay German or English for now. Corrections from native speakers are welcome: `frontend/src/i18n/<language>.js` and `custom_components/snapmaker_u1_card/translations/<language>.json`.

**Fixed**
- Camera away from home (Nabu Casa): the stream through Home Assistant restarted every time the card rebuilt; the camera frame now stays in place. `debug_camera: true` logs what caused a rebuild.
- History thumbnails: a file uploaded and started straight from the slicer got no image, and images of files that dropped out of the file list were deleted. Now fetched at print start, kept while the history uses them, missing ones repaired from the file if it still exists; otherwise the printer icon instead of a broken image.
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

Update in HACS, restart Home Assistant and reload the dashboard.

### Deutsch

Spoolman im eigenen Reiter, eine G-Code-Vorschau mit Schiebereglern, die Top Cover aus der Karte steuern und fünf weitere Sprachen. Danke an alle, die die Betas getestet haben!

**Spoolman**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle). Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`. Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Neue Spule mit Vorschlägen: Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann der Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm). Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule; ein Katalog-Eintrag wird einmal in Spoolman übernommen und danach wiederverwendet. Hersteller und Material schlagen bekannte Namen vor; neu sind Ort und, im Reiter, der Kopf zum Zuordnen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`. Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang.

**G-Code-Vorschau**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Top Cover und Kammerheizung**
- Top-Cover-Modus in der Karte und als `select.…_top_cover_modus` (Leerlauf, kühlen, vorheizen, heiß), Kammer-Soll als Regler und als `number.…_top_cover_kammer_soll` (`SET_PURIFIER_MODE`).
- Benachrichtigung *Kammer ist warm* (Ereignis `chamber_ready`, standardmäßig aus), wenn Kammerheizung (Panda Breath / DragonBreath) oder Top Cover ihr Soll erreichen.
- Der Wartungspunkt *Luftfilter wechseln* zählt die echten Filterstunden der Top Cover; der Temperaturverlauf zeigt die Kammerheizung mit Soll.
- Nach der Firmware gebaut, ohne die Hardware selbst zu haben: Rückmeldung von Besitzern ist willkommen, am besten mit Diagnose-Datei. Ohne Top Cover oder Kammerheizung taucht davon nichts auf.

**Sprachen**
- Karte und Integration jetzt auch auf Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant (regionale Varianten nutzen die Grundsprache, andere Sprachen bekommen Englisch). Push-Benachrichtigungen, Firmware-Meldungen und der Selbsttest bleiben vorerst Deutsch oder Englisch. Korrekturen von Muttersprachlern gern: `frontend/src/i18n/<sprache>.js` und `custom_components/snapmaker_u1_card/translations/<sprache>.json`.

**Behoben**
- Kamera unterwegs (Nabu Casa): Der Stream über Home Assistant startete bei jedem Neuaufbau der Karte neu; der Kamerarahmen bleibt jetzt stehen. `debug_camera: true` zeigt, was einen Neuaufbau ausgelöst hat.
- Vorschaubilder der Historie: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde, bekam kein Bild, und Bilder von Dateien, die aus der Dateiliste fielen, wurden gelöscht. Jetzt beim Druckstart geholt, behalten, solange die Historie sie nutzt, fehlende aus der Datei nachgeholt, wenn es sie noch gibt; sonst das Drucker-Symbol statt eines kaputten Bilds.
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

In HACS aktualisieren, Home Assistant neu starten und das Dashboard neu laden.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.0b3

Beta. Five more languages. Includes everything from 2.1.0b1 and 2.1.0b2.

**Languages**
- The card and the integration (setup, settings, entities, services, notification events) now also speak Spanish, French, Italian, Portuguese and Dutch, following the language of Home Assistant. Regional variants use the base language (e.g. pt-BR → Portuguese, nl-BE → Dutch); other languages get English.
- Push notifications, firmware messages and the self test text stay German or English for now.
- Corrections from native speakers are welcome as an issue or pull request: `frontend/src/i18n/<language>.js` (card) and `custom_components/snapmaker_u1_card/translations/<language>.json` (integration).

**Fixed**
- Home Assistant's validation (hassfest) failed on a service description with angle brackets.

### Deutsch

Beta. Fünf weitere Sprachen. Enthält alles aus 2.1.0b1 und 2.1.0b2.

**Sprachen**
- Karte und Integration (Einrichtung, Einstellungen, Entitäten, Dienste, Benachrichtigungsereignisse) sprechen jetzt auch Spanisch, Französisch, Italienisch, Portugiesisch und Niederländisch, passend zur Sprache von Home Assistant. Regionale Varianten nutzen die Grundsprache (z. B. pt-BR → Portugiesisch, nl-BE → Niederländisch); andere Sprachen bekommen Englisch.
- Push-Benachrichtigungen, Firmware-Meldungen und der Text des Selbsttests bleiben vorerst Deutsch oder Englisch.
- Korrekturen von Muttersprachlern gern als Issue oder Pull Request: `frontend/src/i18n/<sprache>.js` (Karte) und `custom_components/snapmaker_u1_card/translations/<sprache>.json` (Integration).

**Behoben**
- Die Prüfung von Home Assistant (hassfest) scheiterte an einer Dienstbeschreibung mit spitzen Klammern.

⭐ [GitHub](https://github.com/Ironoxx/ha-snapmaker-u1-card) · ☕ [Ko-fi](https://ko-fi.com/ironoxx)

## 2.1.0b2

Beta. Spoolman tab, suggestions for new spools and a G-code preview with sliders. Includes everything from 2.1.0b1 (top cover mode and chamber target, chamber-warm notification, real filter hours, chamber heater in the chart, camera keeps running when the card rebuilds).

**Spoolman stock**
- New tab *Spoolman* (only with Spoolman set up): every active spool with colour, vendor, material, location, the head it is in and the remaining weight as a bar (orange below the warning threshold).
- Totals on top (spools, kg left, value from the spool prices), filter by material, search by name, vendor, location or `#ID`.

**New spool with suggestions**
- Typing in *Search filament* shows your own Spoolman filaments first, then matches from Spoolman's catalogue [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (the same suggestions Spoolman's own interface uses; 1.75 mm only, fetched once a day).
- A pick fills vendor, material, name, colour, net weight and empty spool weight. An own filament is used as it is; a catalogue entry is imported into Spoolman once (with colour, density and temperatures) and reused afterwards.
- Vendor and material fields suggest the known names. New fields: location, and in the *Spoolman* tab the head to assign (or none). Picking a spool for a head stays under the print heads.
- Service `create_spool`: new fields `filament_id`, `external_id` and `location`; `material` is optional with either ID.
- The catalogue needs Spoolman 0.18 or newer with internet access; otherwise only your own filaments are suggested.

**G-code preview with sliders**
- Layer view during a print: slider *Layer* browses the whole file (earlier layers printed, later ones pending), *Live* goes back; slider *Progress* plays the layer path by path, in the bed view with the nozzle.
- Print dialog: *G-code preview* shows any file before printing, layer by layer with the same sliders, in the colours of the heads chosen in the dialog. The file is parsed once in the background; the last three previews are kept.

**Fixed**
- History without a thumbnail: a file uploaded and started straight from the slicer (not in the file list yet) got no image, and images of files that dropped out of the list were deleted although the history still showed them. Now the image is fetched at print start, kept while the history uses it, and missing ones are taken from the file again if it still exists. Without the file the card shows the printer icon instead of a broken image.

### Deutsch

Beta. Reiter Spoolman, Vorschläge für neue Spulen und G-Code-Vorschau mit Schiebereglern. Enthält alles aus 2.1.0b1 (Top-Cover-Modus und Kammer-Soll, Meldung „Kammer ist warm“, echte Filterstunden, Kammerheizung im Verlauf, Kamera läuft beim Neuaufbau der Karte weiter).

**Spoolman-Bestand**
- Neuer Reiter *Spoolman* (nur mit eingerichtetem Spoolman): alle aktiven Spulen mit Farbe, Hersteller, Material, Ort, dem Kopf, in dem sie steckt, und dem Restgewicht als Balken (orange unter der Warnschwelle).
- Oben die Summen (Spulen, kg übrig, Wert aus den Spulenpreisen), Filter nach Material, Suche nach Name, Hersteller, Ort oder `#ID`.

**Neue Spule mit Vorschlägen**
- Beim Tippen in *Filament suchen* erscheinen zuerst deine Spoolman-Filamente, dann Treffer aus dem Spoolman-Katalog [SpoolmanDB](https://github.com/Donkie/SpoolmanDB) (dieselben Vorschläge wie in Spoolman selbst; nur 1,75 mm, einmal am Tag geladen).
- Ein Treffer füllt Hersteller, Material, Name, Farbe, Nettogewicht und Leerspule. Ein eigenes Filament wird so genommen; ein Katalog-Eintrag wird einmal in Spoolman übernommen (mit Farbe, Dichte und Temperaturen) und danach wiederverwendet.
- Hersteller und Material schlagen bekannte Namen vor. Neu: Ort, und im Reiter *Spoolman* der Kopf zum Zuordnen (oder keiner). Die Spulenwahl je Kopf bleibt unter den Druckköpfen.
- Dienst `create_spool`: neue Felder `filament_id`, `external_id` und `location`; `material` ist mit einer der IDs optional.
- Der Katalog braucht Spoolman 0.18 oder neuer mit Internetzugang; sonst werden nur deine eigenen Filamente vorgeschlagen.

**G-Code-Vorschau mit Schiebereglern**
- Schichtansicht im Druck: Regler *Schicht* blättert durch die ganze Datei (frühere Schichten gedruckt, spätere folgen), *Live* springt zurück; Regler *Fortschritt* spielt die Schicht Bahn für Bahn ab, in der Bettansicht mit Düse.
- Druckdialog: *G-Code-Vorschau* zeigt jede Datei vor dem Druck, Schicht für Schicht mit denselben Reglern, in den Farben der im Dialog gewählten Köpfe. Die Datei wird einmal im Hintergrund zerlegt; die letzten drei Vorschauen bleiben gespeichert.

**Behoben**
- Historie ohne Vorschaubild: Eine Datei, die direkt aus dem Slicer hochgeladen und gestartet wurde (noch nicht in der Dateiliste), bekam kein Bild, und Bilder von Dateien, die aus der Liste fielen, wurden gelöscht, obwohl die Historie sie noch zeigte. Jetzt wird das Bild beim Druckstart geholt, bleibt erhalten, solange die Historie es nutzt, und fehlende werden aus der Datei nachgeholt, wenn es sie noch gibt. Ohne Datei zeigt die Karte das Drucker-Symbol statt eines kaputten Bilds.

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
