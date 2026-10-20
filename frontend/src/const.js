/** Constants shared by the card modules. */

export const DOMAIN = "snapmaker_u1_card";
export const CARD_VERSION = "1.3.1";
// 1x1 GIF: assigning it reliably aborts a running MJPEG request.
export const BLANK = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

export const SUFFIX = ["", "1", "2", "3"];
export const SECTIONS = ["stage", "layer", "job", "queue", "files", "toolheads", "climate", "motion", "system",
  "maintenance", "charts", "stats", "history", "timelapse"];
// Useful while the printer is off (data comes from the integration, not the printer)
export const OFFLINE_SECTIONS = ["queue", "files", "charts", "history", "timelapse", "maintenance"];
// Tabs (layout: tabs). A tab appears when at least one of its
// sections is listed in show.
export const TABS = [
  { id: "overview", icon: "mdi:printer-3d", label: "Übersicht", sections: ["stage", "layer", "job", "toolheads"] },
  { id: "control", icon: "mdi:tune-variant", label: "Steuerung", sections: ["climate", "motion"] },
  { id: "files", icon: "mdi:file-document-multiple-outline", label: "Dateien", sections: ["queue", "files"] },
  { id: "history", icon: "mdi:history", label: "Verlauf", sections: ["charts", "history", "stats"] },
  { id: "timelapse", icon: "mdi:filmstrip", label: "Zeitraffer", sections: ["timelapse"] },
  { id: "system", icon: "mdi:chip", label: "System", sections: ["maintenance", "system"] },
];
// layout: tablet – always visible in the left column
export const TABLET_SIDE = ["stage", "job"];
export const TAB_STORE = "snapmaker-u1-card.tab";

export const RESULT = {
  complete: ["Fertig", "ok"], cancelled: ["Abgebrochen", "warn"], error: ["Fehler", "error"],
  unknown: ["Unbekannt", ""],
};

export const LAYER_PALETTE = ["#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00", "#00acc1", "#6d4c41"];
export const MAINT_LABELS = {
  plate: "Druckplatte reinigen", nozzle: "Düsen und Abstreifer reinigen", rails: "Linearführungen schmieren",
  belts: "Riemenspannung prüfen", filter: "Luftfilter wechseln", tool_changer: "Werkzeugwechsler (Firmware)",
};
export const METRICS = [
  ["prints", "Drucke"], ["hours", "Stunden"], ["filament_g", "Filament"], ["cost", "Kosten"],
];
