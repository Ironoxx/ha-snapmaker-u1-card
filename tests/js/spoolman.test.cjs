// Spulen aus Spoolman: Anzeige je Kopf, Auswahl, Warnung im Druckdialog.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new w.Event("close")); };
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
  { index: 0, loaded: true, type: "PLA", sub_type: null, vendor: "Generic", color: "#000000", colors: ["#000000"] },
  { index: 1, loaded: true, type: "PLA", sub_type: null, vendor: "Generic", color: "#FFFFFF", colors: ["#FFFFFF"] },
  { index: 2, loaded: true, type: "PLA", sub_type: "Silk", vendor: "Generic", color: "#6F4C2F", colors: ["#6F4C2F"] },
  { index: 3, loaded: false, type: null, sub_type: null, vendor: null, color: null, colors: [] },
];
const spools = [
  { id: 1, name: "PLA Schwarz", vendor: "Generic", material: "PLA", color: "#000000", remaining_weight: 650, initial_weight: 1000 },
  { id: 3, name: "PLA Weiss", vendor: "Generic", material: "PLA", color: "#FFFFFF", remaining_weight: 60, initial_weight: 1000 },
  { id: 4, name: "PLA Silk Bronze", vendor: "Generic", material: "PLA", color: "#6F4C2F", remaining_weight: 400, initial_weight: 1000, location: "Regal" },
  { id: 6, name: "PETG Rot", vendor: "Snapmaker", material: "PETG", color: "#D32F2F", remaining_weight: 1000, initial_weight: 1000 },
];
const sm = (slotMap) => ({ online: true, error: null, url: "http://sm:7912", low: 100, deduct: true, pending: [],
  slots: slotMap, spools });
add("sensor.u1c_filamente", "3", { slots, preferences: {}, entry_id: "E1",
  spoolman: sm({ 0: { ...spools[0], manual: false }, 1: { ...spools[1], manual: false }, 2: { ...spools[2], manual: true }, 3: null }) },
  "snapmaker_u1_card", "filaments");
add("sensor.u1c_druckdateien", "1", { entry_id: "E1", files: [{
  path: "teil.gcode", name: "Teil", modified: 1, time: 600, weight: 90,
  filaments: [{ index: 0, type: "PLA", color: "#FFFFFF", weight: 80, used: true }, { index: 1, type: "PLA", color: "#000000", weight: 10, used: true }],
}] }, "snapmaker_u1_card", "files");

const calls = [];
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg,
  callService: async (...a) => { calls.push(JSON.parse(JSON.stringify(a))); } });
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", show: ["toolheads", "files"] });
w.document.body.appendChild(card);
card.hass = hass();
const root = () => card.shadowRoot.getElementById("u1card");
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  // 1. Spule je Kopf
  const lines = [...root().querySelectorAll(".spool-line")];
  assert.strictEqual(lines.length, 3, "drei geladene Koepfe mit Spule, leerer Kopf ohne Zeile");
  assert.ok(/#1 PLA Schwarz/.test(lines[0].textContent) && /650 g/.test(lines[0].textContent));
  assert.strictEqual(lines[0].querySelector(".spool-track i").style.width, "65%");
  assert.strictEqual(lines[1].dataset.low, "1", "60 g < 100 g Warnschwelle");
  assert.ok(/manuell/.test(lines[2].title), "manuell gewaehlt im Tooltip");

  // 2. Auswahl: passende zuerst, PETG zuletzt, belegte Spule markiert
  lines[0].click();
  const dlg = () => card.shadowRoot.querySelector("dialog.u1spool");
  assert.ok(dlg().hasAttribute("open"));
  const opts = [...dlg().querySelectorAll("[data-pick]")].map((b) => b.dataset.pick);
  assert.deepStrictEqual(opts, ["auto", "0", "1", "4", "3", "6"], "Reihenfolge: Material, dann Farbe");
  assert.ok(/steckt in Kopf 2/.test(dlg().querySelector('[data-pick="3"]').textContent));
  assert.strictEqual(dlg().querySelector('[data-pick="1"]').getAttribute("aria-pressed"), "true");
  dlg().querySelector('[data-pick="4"]').click();
  await tick();
  assert.deepStrictEqual(calls.at(-1), ["snapmaker_u1_card", "set_spool", { slot: 1, spool_id: 4, config_entry_id: "E1" }, null, false]);
  assert.ok(!dlg().hasAttribute("open"), "Dialog zu nach Erfolg");
  // automatisch = ohne spool_id; keine = 0
  root().querySelectorAll(".spool-line")[1].click();
  dlg().querySelector('[data-pick="auto"]').click(); await tick();
  assert.deepStrictEqual(calls.at(-1)[2], { slot: 2, config_entry_id: "E1" });
  root().querySelectorAll(".spool-line")[1].click();
  dlg().querySelector('[data-pick="0"]').click(); await tick();
  assert.deepStrictEqual(calls.at(-1)[2], { slot: 2, spool_id: 0, config_entry_id: "E1" });

  // 3. Druckdialog: weisses PLA (80 g) auf Kopf 2 mit 60 g -> Warnung, Rest am Knopf
  root().querySelector('[data-print="teil.gcode"]').click();
  const pd = card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)");
  assert.ok(/Spule #3 hat noch 60 g, gebraucht werden ca\. 80 g/.test(pd.textContent), pd.textContent.replace(/\s+/g, " "));
  assert.ok(pd.querySelector(".slot-rest"), "Restgewicht an den Kopf-Knoepfen");
  // beide Filamente auf Kopf 1 (650 g): keine Warnung
  pd.querySelector('[data-map="0"][data-slot="0"]').click();
  assert.ok(!/gebraucht werden/.test(card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)").textContent));
  pd.close && card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)").close();

  // 4. Ohne Spoolman: nichts davon
  delete states["sensor.u1c_filamente"].attributes.spoolman;
  card.hass = hass();
  assert.strictEqual(root().querySelectorAll(".spool-line").length, 0);
  console.log("SPOOLMAN OK –", calls.length, "Dienstaufrufe");
})().catch((e) => { console.error(e); process.exit(1); });
