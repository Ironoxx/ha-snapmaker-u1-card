/** Constants shared by the card modules. */

export const DOMAIN = "snapmaker_u1_card";
export const CARD_VERSION = "2.1.2";
// 1x1 GIF: assigning it reliably aborts a running MJPEG request.
export const BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

export const SUFFIX = ["", "1", "2", "3"];
export const SECTIONS = ["stage", "display", "layer", "job", "queue", "files", "toolheads", "climate", "mesh", "motion", "console", "system",
  "maintenance", "charts", "stats", "history", "timelapse", "spools"];
// Useful while the printer is off (data comes from the integration, not the printer)
export const OFFLINE_SECTIONS = ["queue", "files", "charts", "history", "timelapse", "maintenance", "spools"];
// Tabs (layout: tabs). A tab appears when at least one of its
// sections is listed in show.
export const TABS = [
  { id: "overview", icon: "mdi:printer-3d", label: "Übersicht", sections: ["stage", "layer", "job", "toolheads"] },
  // only with paxx12's display mirror (left out in _layout otherwise)
  { id: "display", icon: "mdi:monitor-screenshot", label: "Display", sections: ["display"] },
  { id: "control", icon: "mdi:tune-variant", label: "Steuerung", sections: ["climate", "mesh", "motion", "console"] },
  { id: "files", icon: "mdi:file-document-multiple-outline", label: "Dateien", sections: ["queue", "files"] },
  // only with Spoolman (the section renders nothing otherwise and is left out in _layout)
  { id: "spoolman", icon: "mdi:package-variant-closed", label: "Spoolman", sections: ["spools"] },
  { id: "history", icon: "mdi:history", label: "Verlauf", sections: ["charts", "history", "stats"] },
  { id: "timelapse", icon: "mdi:filmstrip", label: "Zeitraffer", sections: ["timelapse"] },
  { id: "system", icon: "mdi:chip", label: "System", sections: ["maintenance", "system"] },
];
// layout: tablet – always visible in the left column
// Tablet: always visible on the left; the heads fill the space under the job
export const TABLET_SIDE = ["stage", "job", "toolheads"];
export const TAB_STORE = "snapmaker-u1-card.tab";

export const RESULT = {
  complete: ["Fertig", "ok"], cancelled: ["Abgebrochen", "warn"], error: ["Fehler", "error"],
  unknown: ["Unbekannt", ""],
};

export const LAYER_PALETTE = ["#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00", "#00acc1", "#6d4c41"];
export const MAINT_LABELS = {
  plate: "Druckplatte reinigen", nozzle: "Düsen und Abstreifer reinigen", rails: "Linearführungen reinigen und schmieren",
  belts: "Riemen prüfen", filter: "Luftfilter wechseln", tool_changer: "Werkzeugwechsler (Firmware)",
  carbon_rods: "X-Carbonstangen reinigen", lead_screws: "Z-Spindeln und Muttern schmieren",
  coupling: "Stahlstifte und Kugeln der Kopfaufnahme", pogo: "Pogo-Kontakte der Köpfe reinigen",
};
export const METRICS = [
  ["prints", "Drucke"], ["hours", "Stunden"], ["filament_g", "Filament"], ["cost", "Kosten"],
];
