// 2.2: building block card (snapmaker-u1-section-card), spool fill level and turning
// spool, usage of the last print per head, slicer preview in the job panel.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.eval(src);

const P = "u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
const slots = [
  { index: 0, loaded: true, type: "PLA", vendor: "Generic", color: "#000000", colors: ["#000000"] },
  { index: 1, loaded: true, type: "PLA", vendor: "Generic", color: "#FFFFFF", colors: ["#FFFFFF"] },
  { index: 2, loaded: false, type: null, vendor: null, color: null, colors: [] },
  { index: 3, loaded: false, type: null, vendor: null, color: null, colors: [] },
];
const spools = [
  { id: 1, name: "PLA Schwarz", vendor: "Generic", material: "PLA", color: "#000000", remaining_weight: 650, initial_weight: 1000 },
  { id: 3, name: "PLA Weiss", vendor: "Generic", material: "PLA", color: "#FFFFFF", remaining_weight: 100, initial_weight: 1000 },
];
add("sensor.u1c_filamente", "2", { slots, preferences: {}, entry_id: "E1",
  spoolman: { online: true, error: null, url: "http://sm:7912", low: 50, deduct: true, pending: [], spools,
    slots: { 0: { ...spools[0], manual: false }, 1: { ...spools[1], manual: false }, 2: null, 3: null } } },
"snapmaker_u1_card", "filaments");
add("sensor.u1c_druckdateien", "0", { entry_id: "E1", files: [] }, "snapmaker_u1_card", "files");
add("sensor.u1c_druckhistorie", "1", { entry_id: "E1", prints: [{
  file: "drache.gcode", name: "Drache", result: "complete", ended: "2026-11-07T10:00:00+00:00", duration: 3600,
  filament_g: 50, map_table: [1, 0],
  filaments: [{ index: 0, type: "PLA", color: "#FFFFFF", weight: 40, used: true }, { index: 1, type: "PLA", color: "#000000", weight: 10, used: true }],
  spools: [{ slot: 1, spool_id: 3, grams: 40, before: 140, after: 100, booked: true }],
}] }, "snapmaker_u1_card", "history");

const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" },
  callService: async () => {} });
const make = (type, cfg) => {
  const c = w.document.createElement(type);
  c.setConfig({ type: `custom:${type}`, ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass();
  return c;
};
const R = (c) => c.shadowRoot.getElementById("u1card");

// 1. Building block card: picker entry, stub, only the chosen sections in their order
const entry = w.customCards.find((c) => c.type === "snapmaker-u1-section-card");
assert.ok(entry && /Bereich/.test(entry.name), "Eintrag im Karten-Picker");
const Section = w.customElements.get("snapmaker-u1-section-card");
assert.deepStrictEqual(JSON.parse(JSON.stringify(Section.getStubConfig())), { type: "custom:snapmaker-u1-section-card", show: ["job"] });
assert.ok(Section.getConfigForm().schema.some((f) => f.name === "show"), "Editor: Bereiche wählen");
let card = make("snapmaker-u1-section-card", { show: ["toolheads", "job", "toolheads"] });
assert.strictEqual(card._cfg.layout, "bare");
assert.ok(!R(card).querySelector("[data-tab]"), "keine Reiter");
assert.ok(!R(card).querySelector(".head"), "kein Kopf");
const panels = [...R(card).querySelectorAll(".layout.bare > .panel")];
assert.strictEqual(panels.length, 2, "doppelte Bereiche nur einmal");
assert.ok(/Druckköpfe/.test(panels[0].textContent) && /Letzter Druck/.test(panels[1].textContent), "Reihenfolge aus show");
assert.ok(!card.hasAttribute("bare-one"));
card = make("snapmaker-u1-section-card", {});
assert.deepStrictEqual([...card._cfg.show], ["job"], "Standard: Druckauftrag");
assert.ok(card.hasAttribute("bare-one"), "ein Bereich: HA-Kartenrahmen ist das Panel");
// the full card keeps head and tabs; layout scroll follows the order of show
card = make("snapmaker-u1-card", { layout: "scroll", show: ["toolheads", "job"] });
const order = [...R(card).querySelectorAll(".layout > .panel")].map((p) => p.textContent);
assert.ok(/Druckköpfe/.test(order[0]), "scroll: Reihenfolge aus show");

// 2. Spool fill from Spoolman (remaining / net weight), unknown without Spoolman spool
card = make("snapmaker-u1-card", { show: ["toolheads"] });
const fills = [...R(card).querySelectorAll(".head-card svg.spool")].map((s) => s.dataset.fill);
assert.deepStrictEqual(fills, ["65", "10", "", ""]);
assert.ok(!R(card).querySelector("svg.spool.spin"), "nichts dreht sich ohne Druck");
// printing on head 1: its spool turns
states[`sensor.${P}_current_print_state`].state = "printing";
card.hass = hass();
card._d.heads.forEach((h) => { h.active = h.idx === 0; });
card._renderKey = null; card._render();
assert.strictEqual(R(card).querySelectorAll("svg.spool.spin").length, 1, "aktiver Kopf dreht");
states[`sensor.${P}_current_print_state`].state = "standby";

// 3. Usage of the last print per head: bars by weight, details on tap
card = make("snapmaker-u1-card", { show: ["job"] });
const chart = R(card).querySelector("[data-usage]");
assert.ok(chart, "Verbrauchsgrafik");
const rows = [...chart.querySelectorAll(".use-row")].map((r) => r.textContent.replace(/\s+/g, " ").trim());
// logical filament 0 -> head 2 (map_table), 40 g first
assert.ok(/^Kopf 2|^T1|2/.test(rows[0]) && /40 g/.test(rows[0]), rows[0]);
assert.ok(/10 g/.test(rows[1]));
assert.ok(chart.querySelector(".use-detail").hidden, "Details zu");
chart.click();
assert.strictEqual(chart.getAttribute("aria-expanded"), "true");
assert.ok(!chart.querySelector(".use-detail").hidden);
assert.ok(/#3/.test(chart.textContent) && /140 g → 100 g/.test(chart.textContent), "Spoolman vorher → nachher");

console.log("BLOCKS OK – section card, order of show, spool fill and turning, usage of the last print");
