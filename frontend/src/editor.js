/** Visual editor: ha-form schema for both cards. */

import { DOMAIN, SECTIONS } from "./const.js";
import { setLang, tr } from "./i18n.js";

export const SECTION_LABELS = {
  stage: "Kamera", job: "Druckauftrag", files: "Dateien", toolheads: "Druckköpfe",
  climate: "Bett & Innenraum", mesh: "Bettnivellierung", motion: "Bewegung", console: "G-Code-Konsole", system: "System & Diagnose",
  stats: "Statistik", history: "Druckhistorie", timelapse: "Zeitraffer",
  queue: "Warteschlange", charts: "Diagramme", maintenance: "Wartung", layer: "Schichtansicht",
  spools: "Spoolman-Bestand", display: "Druckerdisplay", messages: "Meldungen",
};
// 2.2: short description per section for the building block editor (native select)
export const SECTION_DESC = {
  stage: "Kamerabild mit Fortschritt und Not-Halt", display: "Touchscreen des Druckers (paxx12)",
  layer: "aktuelle Schicht, Objekte ausschließen", job: "laufender oder letzter Druck mit Vorschaubild",
  queue: "Druckaufträge in der Warteschlange", files: "Druckdateien, Druck starten",
  toolheads: "Köpfe, Filamente, Düsentemperaturen", climate: "Bett, Innenraum, Lüfter, Temperaturverlauf",
  mesh: "Heatmap mit Höhenwerten", motion: "Position, Tempo, Fluss, Referenzfahrt",
  console: "G-Code senden, Antworten kopieren", system: "Firmware, Verbindung, Auslastung, Selbsttest",
  maintenance: "fällige Wartung", charts: "Diagramme der letzten 12 Monate", stats: "Drucke, Zeiten, Kopfwechsel",
  history: "letzte Drucke mit Kosten", timelapse: "Zeitraffer-Videos", spools: "alle Spulen aus Spoolman",
  messages: "Fehler und Hinweise des Druckers",
};
export const FORM_LABELS = {
  printer_name: "Name", printer_brand: "Marke", layout: "Darstellung", hide: "Bereiche ausblenden",
  camera: "Kamera-Entität", camera_mode: "Kameramodus", hide_overlay: "Fortschritt auf dem Kamerabild ausblenden",
  state_accent: "Rahmen in der Farbe des Zustands",
  accent_color: "Akzentfarbe",
  camera_fit: "Skalierung", camera_height: "Bildhöhe (px)", refresh: "Bildrate (s)",
  stale_after: "„Bild veraltet“ ab (s)", printer_image: "Statisches Bild statt Kamera",
  device: "Drucker",
  prefix: "Moonraker-Präfix", network_tracker: "WLAN-Tracker", files_limit: "Angezeigte Dateien",
  navigation_path: "Beim Antippen öffnen", hide_filaments: "Filamente ausblenden",
  unlock_controls: "Regler nicht sperren",
  controls_lock: "Sperre für Regler",
  emergency_stop: "Not-Halt",
  layer_view: "Schichtansicht",
  bed_image: "Eigenes Hintergrundbild",
  bed_image_area: "Bildbereich in mm (x0, y0, x1, y1)",
  bed_image_opacity: "Deckkraft",
  bed_grid: "Raster über dem Bild",
  camera_wake: "Kamera bei stehendem Bild wecken",
  camera_direct: "Direktstream vom Drucker",
  camera_direct_url: "Adresse des Direktstreams",
  camera_webrtc: "WebRTC (paxx12-Firmware)",
  camera_ha_stream: "Unterwegs: RTSP über Home Assistant",
  camera_zoom_reset: "Zoom zurücksetzen nach (s)",
  display_place: "Druckerdisplay",
  display_camera: "Druckerdisplay als zusätzliche Kamera",
  mesh_values: "Höhenwerte in der Bettnivellierung",
  exclude_objects: "Objekte ausschließen in der Schichtansicht",
  show: "Bereiche",
  alerts: "Meldungen des Druckers oben anzeigen",
  clock: "Uhr in der Kopfzeile",
  buttons: "Eigene Knöpfe (bis zu 4)",
  light_entities: "Weitere Lampen mit dem Licht-Knopf",
};
export const FORM_HELPERS = {
  camera: "Leer = Kamera der Integration (erkennt Stock- und angepasste Firmware), sonst die der Moonraker-Integration",
  device: "Leer = der erste eingerichtete Drucker. Bei mehreren U1 hier wählen, welchen diese Karte zeigt.",
  prefix: "Nur für Entitäten der Moonraker-Integration. Den Drucker wählst du oben unter „Drucker“.",
  network_tracker: "Zeigt einen Verbindungs-Chip in der Kopfzeile",
  hide: "Kopfnamen und Temperatur-Presets im YAML-Editor",
  layout: "Leer = Reiter. Tablet / Monitor: Kamera, Druckauftrag und Druckköpfe links, Reiter rechts (ab ca. 900 px Breite)",
  bed_image: "z. B. /local/u1_oben.png (Datei unter config/www). Ersetzt Platte und Köpfe in der Draufsicht.",
  bed_image_area: "Welche Druckerkoordinaten das Bild abdeckt. Leer = genau die Platte 0, 0, 270, 270. Für ein Foto des ganzen Druckers z. B. -40, -30, 310, 360.",
  layer_view: "Leer = Teil vergrößert. Umschalten geht auch direkt in der Schichtansicht.",
  emergency_stop: "Leer = anzeigen. Der Not-Halt-Button in Home Assistant bleibt in jedem Fall erhalten.",
  camera_direct: "Leer = automatisch: im Heimnetz direkt vom Drucker (weniger Verzögerung), bei https oder unterwegs über Home Assistant",
  camera_direct_url: "Leer = http://<Drucker>/webcam/?action=stream",
  camera_webrtc: "Leer = automatisch: WebRTC, wenn der Drucker es anbietet (weniger Verzögerung und Datenlast). Klappt keine direkte Verbindung (unterwegs ohne VPN), bleibt MJPEG.",
  camera_ha_stream: "Leer = automatisch: Ist keine direkte Verbindung zum Drucker möglich (z. B. Nabu Casa), spielt Home Assistant den RTSP-Stream ab – flüssiger und viel weniger Daten als MJPEG. Nur mit RTSP (paxx12).",
  camera_zoom_reset: "Leer = 60 s ohne Bedienung, 0 = nie. Beim Verlassen der Seite oder Wegscrollen geht der Zoom immer zurück.",
  display_place: "Leer = in der Übersicht, in seiner echten Größe. Nur mit dem Display-Spiegel der paxx12-Firmware.",
  mesh_values: "Leer = an. Zeigt in jeder Kachel die gemessene Höhe (bis 12 × 12 Messpunkte).",
  exclude_objects: "Leer = an. Aus: keine Objektliste und keine Umrisse in der Schichtansicht – hilft bei Drucken mit sehr vielen Teilen.",
  show: "Welche Bereiche diese Karte zeigt, in dieser Reihenfolge. Mehrere Karten lassen sich im Abschnitte-Dashboard frei anordnen.",
  alerts: "Leer = nur mit Kamera oder Druckauftrag. Für alle Meldungen an einem Ort gibt es den Bereich „Meldungen“.",
  display_camera: "Der Knopf „Kamera wechseln“ zeigt dann auch das Display. Nur mit dem Display-Spiegel der paxx12-Firmware.",
  camera_wake: "Leer = an. Bleibt das Bild stehen, schickt die Karte camera.start_monitor an den Drucker (nur solange sie sichtbar ist).",
  camera_mode: "Leer = automatisch (die Kamera-Entität der Integration erkennt Livestream oder Standbilder selbst)",
  controls_lock: "Leer = 1 min. Gesperrt sind Temperatur- und Lüfterregler, Schnellwahl, Heizungsschalter und Referenzfahrt; das Schloss öffnet sie bis zur gewählten Zeit nach der letzten Bedienung.",
  camera_height: "Leer = automatisch (Seitenverhältnis des Bildes)",
  state_accent: "Druckt, pausiert, Fehler, fertig – in den Farben deines Home-Assistant-Designs",
  accent_color: "Leer = Hauptfarbe deines Home-Assistant-Designs. Färbt Knöpfe, Regler und Hervorhebungen der Karte.",
  navigation_path: "z. B. /dashboard-drucker/0 – leer = Statusdialog",
  clock: "Stunden und Minuten im Zeitformat von Home Assistant, rechts in der Kopfzeile. Auf schmalen Karten ausgeblendet.",
  buttons: "Neben dem Licht-Knopf, mit den Aktionen von Home Assistant (navigieren, Aktion/Skript, Details, URL). Je Knopf wählbar: vor, während oder nach dem Druck.",
  light_entities: "Leer = nur das Innenlicht. Z. B. eine WLED-Leiste, die mit dem Licht-Knopf an- und ausgeht.",
};

/** 2.4 (#16): one own button in the editor (Home Assistant's native object/action selectors). */
export function buttonFields(opts) {
  return {
    name: { label: tr("Name"), selector: { text: {} } },
    icon: { label: tr("Symbol"), selector: { icon: {} } },
    show: { label: tr("Anzeigen"), selector: { select: { multiple: true, mode: "list", options: opts([
      ["idle", "Vor dem Druck"], ["printing", "Während des Drucks"], ["finished", "Nach dem Druck (fertig)"]]) } } },
    tap_action: { label: tr("Aktion beim Antippen"), selector: { ui_action: {} } },
    hold_action: { label: tr("Aktion beim Halten"), selector: { ui_action: {} } },
  };
}

/**
 * 2.4.1 (#19): the printer this card shows, as a native select with the device name (since
 * 2.4.2 named after the printer) and its address (configuration_url) when the name lacks it;
 * without hass at hand HA's device picker (filtered to the integration).
 * Value = device ID; empty = the first printer (as before 2.4.1).
 */
export function deviceField(hass) {
  const ids = new Set(Object.values((hass && hass.entities) || {})
    .filter((e) => e.platform === DOMAIN && e.device_id).map((e) => e.device_id));
  const devs = [...ids].map((id) => (hass.devices || {})[id]).filter(Boolean);
  if (!devs.length) return { name: "device", selector: { device: { integration: DOMAIN } } };
  const host = (d) => { try { return new URL(d.configuration_url).host; } catch (e) { return ""; } };
  // 2.4.2: devices are named after the printer; the address only when the name lacks it
  const label = (d) => { const n = d.name_by_user || d.name || "", h = host(d); return h && !n.includes(h) ? [n, h].filter(Boolean).join(" · ") : n; };
  return { name: "device", selector: { select: { mode: "dropdown", options: devs.map((d) => ({ value: d.id, label: label(d) })) } } };
}

/** Form of the card editor: mini = true for the mini card, "section" for the building block card. */
export function configForm(mini) {
  const section = mini === "section";
  if (section) mini = false;
  // Called statically: take the language from the running HA frontend.
  let hass = null;
  try { const ha = document.querySelector("home-assistant"); hass = ha && ha.hass; if (hass) setLang(hass); } catch (e) { /* ignore */ }
  // only offered when there is something to choose (or HA could not be asked)
  const devCount = new Set(Object.values((hass && hass.entities) || {})
    .filter((e) => e.platform === DOMAIN && e.device_id).map((e) => e.device_id)).size;
  const device = !hass || devCount > 1 ? [deviceField(hass)] : [];
  const opts = (list) => list.map(([value, label]) => ({ value, label: tr(label) }));
  const name = [
    { name: "printer_name", selector: { text: {} } },
    { name: "printer_brand", selector: { text: {} } },
  ];
  const advanced = {
    type: "expandable", name: "advanced", flatten: true, title: tr("Erweitert"), icon: "mdi:cog-outline",
    schema: [
      { name: "prefix", selector: { text: {} } },
      ...(mini ? [] : [
        { name: "network_tracker", selector: { entity: { domain: "device_tracker" } } },
        { name: "files_limit", selector: { number: { min: 1, max: 100, mode: "box" } } },
      ]),
    ],
  };
  if (section) {
    return {
      schema: [
        ...device,
        { name: "show", required: true, selector: { select: { multiple: true, mode: "list", reorder: true,
          options: SECTIONS.map((sec) => ({ value: sec, label: `${tr(SECTION_LABELS[sec])} – ${tr(SECTION_DESC[sec])}` })) } } },
        { name: "alerts", selector: { boolean: {} } },
        { name: "accent_color", selector: { color_rgb: {} } },
        { name: "controls_lock", selector: { select: { mode: "dropdown", options: opts([
          ["off", "Aus"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"], ["manual", "Bis zum erneuten Sperren"]]) } } },
        { name: "mesh_values", selector: { boolean: {} } },
        { name: "emergency_stop", selector: { select: { mode: "dropdown", options: opts([
          ["show", "Anzeigen, mit Rückfrage"], ["hold", "Gesichert: 1 s gedrückt halten"], ["hide", "Ausblenden"]]) } } },
        advanced,
      ],
      computeLabel: (s) => (FORM_LABELS[s.name] ? tr(FORM_LABELS[s.name]) : undefined),
      computeHelper: (s) => (FORM_HELPERS[s.name] ? tr(FORM_HELPERS[s.name]) : undefined),
    };
  }
  const schema = mini ? [
    ...device,
    { name: "printer_name", selector: { text: {} } },
    { name: "accent_color", selector: { color_rgb: {} } },
    { name: "hide_filaments", selector: { boolean: {} } },
    { name: "navigation_path", selector: { text: {} } },
    advanced,
  ] : [
    ...device,
    { type: "grid", name: "", schema: name },
    { name: "layout", selector: { select: { mode: "dropdown", options: opts([["tabs", "Reiter"], ["scroll", "Untereinander"], ["tablet", "Tablet / Monitor"]]) } } },
    { name: "hide", selector: { select: { multiple: true, mode: "list",
      options: SECTIONS.map((sec) => ({ value: sec, label: tr(SECTION_LABELS[sec]) })) } } },
    { name: "state_accent", selector: { boolean: {} } },
    { name: "accent_color", selector: { color_rgb: {} } },
    { name: "clock", selector: { boolean: {} } },
    { name: "buttons", selector: { object: { multiple: true, label_field: "name", fields: buttonFields(opts) } } },
    { name: "light_entities", selector: { entity: { multiple: true, domain: ["light", "switch"] } } },
    { name: "layer_view", selector: { select: { mode: "dropdown", options: opts([["part", "Teil vergrößert"], ["bed", "Ganzes Druckbett"]]) } } },
    { name: "emergency_stop", selector: { select: { mode: "dropdown", options: opts([
      ["show", "Anzeigen, mit Rückfrage"], ["hold", "Gesichert: 1 s gedrückt halten"], ["hide", "Ausblenden"]]) } } },
    { name: "controls_lock", selector: { select: { mode: "dropdown", options: opts([
      ["off", "Aus"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"], ["manual", "Bis zum erneuten Sperren"]]) } } },
    { name: "mesh_values", selector: { boolean: {} } },
    { name: "exclude_objects", selector: { boolean: {} } },
    {
      type: "expandable", name: "bed_group", flatten: true, title: tr("Draufsicht"), icon: "mdi:grid",
      schema: [
        { name: "bed_image", selector: { text: {} } },
        { name: "bed_image_area", selector: { text: {} } },
        { type: "grid", name: "", schema: [
          { name: "bed_image_opacity", selector: { number: { min: 0.1, max: 1, step: 0.05, mode: "box" } } },
          { name: "bed_grid", selector: { boolean: {} } },
        ] },
      ],
    },
    {
      type: "expandable", name: "camera_group", flatten: true, title: tr("Kamera"), icon: "mdi:cctv",
      schema: [
        { name: "camera", selector: { entity: { domain: "camera" } } },
        { type: "grid", name: "", schema: [
          { name: "camera_mode", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["stream", "Livestream"], ["still", "Einzelbilder"]]) } } },
          { name: "camera_fit", selector: { select: { mode: "dropdown", options: opts([["contain", "Einpassen"], ["cover", "Füllen"], ["fill", "Strecken"]]) } } },
          { name: "camera_height", selector: { number: { min: 120, max: 900, step: 10, mode: "box" } } },
          { name: "refresh", selector: { number: { min: 1, max: 60, mode: "box" } } },
          { name: "stale_after", selector: { number: { min: 10, max: 3600, mode: "box" } } },
          { name: "camera_zoom_reset", selector: { number: { min: 0, max: 3600, mode: "box" } } },
        ] },
        { name: "hide_overlay", selector: { boolean: {} } },
        { name: "camera_wake", selector: { boolean: {} } },
        { name: "camera_direct", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["off", "Aus (immer über Home Assistant)"]]) } } },
        { name: "camera_direct_url", selector: { text: {} } },
        { name: "camera_webrtc", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["off", "Aus (MJPEG)"]]) } } },
        { name: "camera_ha_stream", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["off", "Aus (MJPEG)"]]) } } },
        { name: "printer_image", selector: { text: {} } },
        { type: "grid", name: "", schema: [
          { name: "display_place", selector: { select: { mode: "dropdown", options: opts([["overview", "In der Übersicht"], ["tab", "Eigener Reiter"], ["off", "Aus"]]) } } },
          { name: "display_camera", selector: { boolean: {} } },
        ] },
      ],
    },
    advanced,
  ];
  return {
    schema,
    computeLabel: (s) => (FORM_LABELS[s.name] ? tr(FORM_LABELS[s.name]) : undefined),
    computeHelper: (s) => (FORM_HELPERS[s.name] ? tr(FORM_HELPERS[s.name]) : undefined),
  };
}
