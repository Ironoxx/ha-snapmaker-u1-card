/** Visual editor: ha-form schema for both cards. */

import { SECTIONS } from "./const.js";
import { setLang, tr } from "./i18n.js";

export const SECTION_LABELS = {
  stage: "Kamera", job: "Druckauftrag", files: "Dateien", toolheads: "Druckköpfe",
  climate: "Bett & Innenraum", mesh: "Bettnivellierung", motion: "Bewegung", console: "G-Code-Konsole", system: "System & Diagnose",
  stats: "Statistik", history: "Druckhistorie", timelapse: "Zeitraffer",
  queue: "Warteschlange", charts: "Diagramme", maintenance: "Wartung", layer: "Schichtansicht",
};
export const FORM_LABELS = {
  printer_name: "Name", printer_brand: "Marke", layout: "Darstellung", hide: "Bereiche ausblenden",
  camera: "Kamera-Entität", camera_mode: "Kameramodus", hide_overlay: "Fortschritt auf dem Kamerabild ausblenden",
  state_accent: "Rahmen in der Farbe des Zustands",
  accent_color: "Akzentfarbe",
  camera_fit: "Skalierung", camera_height: "Bildhöhe (px)", refresh: "Bildrate (s)",
  stale_after: "„Bild veraltet“ ab (s)", printer_image: "Statisches Bild statt Kamera",
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
};
export const FORM_HELPERS = {
  camera: "Leer = Kamera der Integration (erkennt Stock- und angepasste Firmware), sonst die der Moonraker-Integration",
  prefix: "Nur bei mehreren Druckern nötig",
  network_tracker: "Zeigt einen Verbindungs-Chip in der Kopfzeile",
  hide: "Kopfnamen und Temperatur-Presets im YAML-Editor",
  layout: "Leer = Reiter. Tablet / Monitor: Kamera und Druckauftrag links, Reiter rechts (ab ca. 900 px Breite)",
  bed_image: "z. B. /local/u1_oben.png (Datei unter config/www). Ersetzt Platte und Köpfe in der Draufsicht.",
  bed_image_area: "Welche Druckerkoordinaten das Bild abdeckt. Leer = genau die Platte 0, 0, 270, 270. Für ein Foto des ganzen Druckers z. B. -40, -30, 310, 360.",
  layer_view: "Leer = Teil vergrößert. Umschalten geht auch direkt in der Schichtansicht.",
  emergency_stop: "Leer = anzeigen. Der Not-Halt-Button in Home Assistant bleibt in jedem Fall erhalten.",
  camera_direct: "Leer = automatisch: im Heimnetz direkt vom Drucker (weniger Verzögerung), bei https oder unterwegs über Home Assistant",
  camera_direct_url: "Leer = http://<Drucker>/webcam/?action=stream",
  camera_webrtc: "Leer = automatisch: WebRTC, wenn der Drucker es anbietet (weniger Verzögerung und Datenlast). Klappt keine direkte Verbindung (unterwegs ohne VPN), bleibt MJPEG.",
  camera_wake: "Leer = an. Bleibt das Bild stehen, schickt die Karte camera.start_monitor an den Drucker (nur solange sie sichtbar ist).",
  camera_mode: "Leer = automatisch (die Kamera-Entität der Integration erkennt Livestream oder Standbilder selbst)",
  controls_lock: "Leer = 1 min. Gesperrt sind Temperatur- und Lüfterregler, Schnellwahl, Heizungsschalter und Referenzfahrt; das Schloss öffnet sie bis zur gewählten Zeit nach der letzten Bedienung.",
  camera_height: "Leer = automatisch (Seitenverhältnis des Bildes)",
  state_accent: "Druckt, pausiert, Fehler, fertig – in den Farben deines Home-Assistant-Designs",
  accent_color: "Leer = Hauptfarbe deines Home-Assistant-Designs. Färbt Knöpfe, Regler und Hervorhebungen der Karte.",
  navigation_path: "z. B. /dashboard-drucker/0 – leer = Statusdialog",
};

export function configForm(mini) {
  // Called statically: take the language from the running HA frontend.
  try { const ha = document.querySelector("home-assistant"); if (ha && ha.hass) setLang(ha.hass); } catch (e) { /* ignore */ }
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
  const schema = mini ? [
    { name: "printer_name", selector: { text: {} } },
    { name: "accent_color", selector: { color_rgb: {} } },
    { name: "hide_filaments", selector: { boolean: {} } },
    { name: "navigation_path", selector: { text: {} } },
    advanced,
  ] : [
    { type: "grid", name: "", schema: name },
    { name: "layout", selector: { select: { mode: "dropdown", options: opts([["tabs", "Reiter"], ["scroll", "Untereinander"], ["tablet", "Tablet / Monitor"]]) } } },
    { name: "hide", selector: { select: { multiple: true, mode: "list",
      options: SECTIONS.map((sec) => ({ value: sec, label: tr(SECTION_LABELS[sec]) })) } } },
    { name: "state_accent", selector: { boolean: {} } },
    { name: "accent_color", selector: { color_rgb: {} } },
    { name: "layer_view", selector: { select: { mode: "dropdown", options: opts([["part", "Teil vergrößert"], ["bed", "Ganzes Druckbett"]]) } } },
    { name: "emergency_stop", selector: { select: { mode: "dropdown", options: opts([
      ["show", "Anzeigen, mit Rückfrage"], ["hold", "Gesichert: 1 s gedrückt halten"], ["hide", "Ausblenden"]]) } } },
    { name: "controls_lock", selector: { select: { mode: "dropdown", options: opts([
      ["off", "Aus"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"], ["manual", "Bis zum erneuten Sperren"]]) } } },
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
        ] },
        { name: "hide_overlay", selector: { boolean: {} } },
        { name: "camera_wake", selector: { boolean: {} } },
        { name: "camera_direct", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["off", "Aus (immer über Home Assistant)"]]) } } },
        { name: "camera_direct_url", selector: { text: {} } },
        { name: "camera_webrtc", selector: { select: { mode: "dropdown", options: opts([["auto", "Automatisch"], ["off", "Aus (MJPEG)"]]) } } },
        { name: "printer_image", selector: { text: {} } },
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
