/** Visual editor: ha-form schema for both cards. */

import { SECTIONS } from "./const.js";
import { setLang, tr } from "./i18n.js";

export const SECTION_LABELS = {
  stage: "Kamera", job: "Druckauftrag", files: "Dateien", toolheads: "Druckköpfe",
  climate: "Bett & Innenraum", motion: "Bewegung", system: "System & Diagnose",
  stats: "Statistik", history: "Druckhistorie", timelapse: "Zeitraffer",
  queue: "Warteschlange", charts: "Diagramme", maintenance: "Wartung", layer: "Schichtansicht",
};
export const FORM_LABELS = {
  printer_name: "Name", printer_brand: "Marke", layout: "Darstellung", hide: "Bereiche ausblenden",
  camera: "Kamera-Entität", camera_mode: "Kameramodus", hide_overlay: "Fortschritt auf dem Kamerabild ausblenden",
  state_accent: "Rahmen in der Farbe des Zustands",
  camera_fit: "Skalierung", camera_height: "Bildhöhe (px)", refresh: "Bildrate (s)",
  stale_after: "„Bild veraltet“ ab (s)", printer_image: "Statisches Bild statt Kamera",
  prefix: "Moonraker-Präfix", network_tracker: "WLAN-Tracker", files_limit: "Angezeigte Dateien",
  navigation_path: "Beim Antippen öffnen", hide_filaments: "Filamente ausblenden",
  unlock_controls: "Regler nicht sperren",
  controls_lock: "Sperre für Regler",
};
export const FORM_HELPERS = {
  camera: "Leer = automatisch erkannt",
  prefix: "Nur bei mehreren Druckern nötig",
  network_tracker: "Zeigt einen Verbindungs-Chip in der Kopfzeile",
  hide: "Kopfnamen und Temperatur-Presets im YAML-Editor",
  layout: "Leer = Reiter",
  camera_mode: "Leer = Livestream",
  controls_lock: "Leer = 1 min. Gesperrt sind Temperatur- und Lüfterregler, Schnellwahl, Heizungsschalter und Referenzfahrt; das Schloss öffnet sie bis zur gewählten Zeit nach der letzten Bedienung.",
  camera_height: "Leer = automatisch (Seitenverhältnis des Bildes)",
  state_accent: "Druckt, pausiert, Fehler, fertig – in den Farben deines Home-Assistant-Designs",
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
    { name: "hide_filaments", selector: { boolean: {} } },
    { name: "navigation_path", selector: { text: {} } },
    advanced,
  ] : [
    { type: "grid", name: "", schema: name },
    { name: "layout", selector: { select: { mode: "dropdown", options: opts([["tabs", "Reiter"], ["scroll", "Untereinander"]]) } } },
    { name: "hide", selector: { select: { multiple: true, mode: "list",
      options: SECTIONS.map((sec) => ({ value: sec, label: tr(SECTION_LABELS[sec]) })) } } },
    { name: "state_accent", selector: { boolean: {} } },
    { name: "controls_lock", selector: { select: { mode: "dropdown", options: opts([
      ["off", "Aus"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"], ["manual", "Bis zum erneuten Sperren"]]) } } },
    {
      type: "expandable", name: "camera_group", flatten: true, title: tr("Kamera"), icon: "mdi:cctv",
      schema: [
        { name: "camera", selector: { entity: { domain: "camera" } } },
        { type: "grid", name: "", schema: [
          { name: "camera_mode", selector: { select: { mode: "dropdown", options: opts([["stream", "Livestream"], ["still", "Einzelbilder"]]) } } },
          { name: "camera_fit", selector: { select: { mode: "dropdown", options: opts([["contain", "Einpassen"], ["cover", "Füllen"], ["fill", "Strecken"]]) } } },
          { name: "camera_height", selector: { number: { min: 120, max: 900, step: 10, mode: "box" } } },
          { name: "refresh", selector: { number: { min: 1, max: 60, mode: "box" } } },
          { name: "stale_after", selector: { number: { min: 10, max: 3600, mode: "box" } } },
        ] },
        { name: "hide_overlay", selector: { boolean: {} } },
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
