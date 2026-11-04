// Spools from Spoolman: display per head, selection, warning in the print dialog.
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

const calls = [], ws = [];
const SUGGEST = [
  { key: "f:9", source: "own", filament_id: 9, vendor: "Generic", name: "PLA Silk Bronze", material: "PLA", color: "#6f4c2f", colors: ["#6f4c2f"], weight: 1000 },
  { key: "x:pm", source: "db", external_id: "polymaker_pla_black", vendor: "Polymaker", name: "PolyTerra PLA Black", material: "PLA", color: "#1a1a1a", colors: ["#1a1a1a"], weight: 1000, spool_weight: 140 },
];
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg,
  callService: async (...a) => { calls.push(JSON.parse(JSON.stringify(a))); },
  callWS: async (m) => { ws.push(m); return m.type.endsWith("/catalog")
    ? { vendors: ["Generic", "Polymaker"], materials: ["PETG", "PLA"], catalog: 1 } : { items: SUGGEST }; } });
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", show: ["toolheads", "files"] });
w.document.body.appendChild(card);
card.hass = hass();
const root = () => card.shadowRoot.getElementById("u1card");
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  // 1. Spool per head
  const lines = [...root().querySelectorAll(".spool-line")];
  assert.strictEqual(lines.length, 3, "drei geladene Koepfe mit Spule, leerer Kopf ohne Zeile");
  assert.ok(/#1 PLA Schwarz/.test(lines[0].textContent) && /650 g/.test(lines[0].textContent));
  assert.strictEqual(lines[0].querySelector(".spool-track i").style.width, "65%");
  assert.strictEqual(lines[1].dataset.low, "1", "60 g < 100 g Warnschwelle");
  assert.ok(/manuell/.test(lines[2].title), "manuell gewaehlt im Tooltip");

  // 2. Selection: matching first, PETG last, used spool marked
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
  // automatic = without spool_id; none = 0
  root().querySelectorAll(".spool-line")[1].click();
  dlg().querySelector('[data-pick="auto"]').click(); await tick();
  assert.deepStrictEqual(calls.at(-1)[2], { slot: 2, config_entry_id: "E1" });
  root().querySelectorAll(".spool-line")[1].click();
  dlg().querySelector('[data-pick="0"]').click(); await tick();
  assert.deepStrictEqual(calls.at(-1)[2], { slot: 2, spool_id: 0, config_entry_id: "E1" });

  // 2b. Unknown spool: create one in Spoolman, prefilled from the head
  root().querySelectorAll(".spool-line")[0].click();
  dlg().querySelector("[data-newspool]").click();
  const nf = dlg().querySelector("[data-newspoolform]");
  assert.ok(nf, "Formular");
  assert.strictEqual(nf.elements.material.value, "PLA");
  assert.strictEqual(nf.elements.weight.value, "1000");
  nf.elements.vendor.value = "Sunlu";
  nf.elements.price.value = "18.5";
  nf.dispatchEvent(new w.Event("submit", { cancelable: true }));
  await tick();
  const cs = calls.at(-1);
  assert.strictEqual(cs[1], "create_spool");
  assert.strictEqual(cs[5], true, "mit Antwort");
  assert.deepStrictEqual(cs[2], { slot: 1, vendor: "Sunlu", material: "PLA", name: "PLA", color: "#000000",
    weight: 1000, price: 18.5, config_entry_id: "E1" });
  // back to the list
  root().querySelectorAll(".spool-line")[0].click();
  dlg().querySelector("[data-newspool]").click();
  dlg().querySelector("[data-back]").click();
  assert.ok(dlg().querySelector("[data-pick]"), "zurueck zur Liste");
  dlg().close();

  // 2c. Stock: all spools, totals, filter by material and text, where each spool is
  root().querySelector("[data-spoolstock]").click();
  const rows = () => [...dlg().querySelectorAll("[data-stock]")];
  assert.strictEqual(rows().length, 4);
  assert.ok(/4 Spulen · 2\.1 kg/.test(dlg().querySelector("[data-stocksum]").textContent));
  assert.ok(/steckt in/.test(rows().find((r) => r.dataset.stock === "4").textContent), "Kopf der Spule");
  assert.strictEqual(rows().find((r) => r.dataset.stock === "3").dataset.low, "1", "unter der Warnschwelle");
  dlg().querySelector('[data-stockmat="PETG"]').click();
  assert.deepStrictEqual(rows().map((r) => r.dataset.stock), ["6"]);
  dlg().querySelector('[data-stockmat=""]').click();
  card._openSpoolStock({ material: "", text: "regal" });
  assert.deepStrictEqual(rows().map((r) => r.dataset.stock), ["4"], "Suche im Ort");
  card._openSpoolStock({ material: "", text: "" });

  // 2d. New spool from the stock: suggestions, a catalogue pick, head chosen in the form
  dlg().querySelector("[data-stocknew]").click();
  await tick();
  const f2 = dlg().querySelector("[data-newspoolform]");
  assert.strictEqual(f2.querySelectorAll("#u1-vendors option").length, 2, "Herstellervorschläge");
  f2.elements.q.value = "pla";
  card._suggestTimer = null;
  f2.elements.q.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 300)); await tick();
  assert.strictEqual(ws.at(-1).type, "snapmaker_u1_card/spoolman/suggest");
  assert.strictEqual(ws.at(-1).query, "pla");
  const sug = [...f2.querySelectorAll("[data-sug]")];
  assert.strictEqual(sug.length, 2);
  assert.ok(/Katalog/.test(sug[1].textContent));
  sug[1].click();
  assert.strictEqual(f2.elements.vendor.value, "Polymaker");
  assert.strictEqual(f2.elements.spool_weight.value, "140");
  assert.ok(!f2.querySelector("[data-picked]").hidden);
  f2.elements.slot.value = "4";
  f2.elements.location.value = "Trockenbox";
  f2.dispatchEvent(new w.Event("submit", { cancelable: true }));
  await tick();
  assert.deepStrictEqual(calls.at(-1)[2], { vendor: "Polymaker", material: "PLA", color: "#1a1a1a", weight: 1000,
    spool_weight: 140, config_entry_id: "E1", name: "PolyTerra PLA Black", location: "Trockenbox", slot: 4,
    external_id: "polymaker_pla_black" });
  // own filament: by ID; editing the name drops the pick
  dlg().querySelector("[data-stocknew]").click(); await tick();
  const f3 = dlg().querySelector("[data-newspoolform]");
  f3.elements.q.value = "silk"; f3.elements.q.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 300)); await tick();
  f3.querySelector('[data-sug="0"]').click();
  f3.dispatchEvent(new w.Event("submit", { cancelable: true })); await tick();
  assert.strictEqual(calls.at(-1)[2].filament_id, 9);
  assert.ok(!("slot" in calls.at(-1)[2]), "keinem Kopf");
  dlg().querySelector("[data-stocknew]").click(); await tick();
  const f4 = dlg().querySelector("[data-newspoolform]");
  f4.elements.q.value = "silk"; f4.elements.q.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 300)); await tick();
  f4.querySelector('[data-sug="0"]').click();
  f4.elements.name.value = "PLA Silk Kupfer"; f4.elements.name.dispatchEvent(new w.Event("input"));
  f4.dispatchEvent(new w.Event("submit", { cancelable: true })); await tick();
  assert.ok(!("filament_id" in calls.at(-1)[2]) && calls.at(-1)[2].name === "PLA Silk Kupfer");
  dlg().close();

  // 3. Print dialog: white PLA (80 g) on head 2 with 60 g -> warning, remainder on the button
  root().querySelector('[data-print="teil.gcode"]').click();
  const pd = card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)");
  assert.ok(/Spule #3 hat noch 60 g, gebraucht werden ca\. 80 g/.test(pd.textContent), pd.textContent.replace(/\s+/g, " "));
  assert.ok(pd.querySelector(".slot-rest"), "Restgewicht an den Kopf-Knoepfen");
  // both filaments on head 1 (650 g): no warning
  pd.querySelector('[data-map="0"][data-slot="0"]').click();
  assert.ok(!/gebraucht werden/.test(card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)").textContent));
  pd.close && card.shadowRoot.querySelector("dialog.u1dlg:not(.u1spool)").close();

  // 4. Without Spoolman: none of it
  delete states["sensor.u1c_filamente"].attributes.spoolman;
  card.hass = hass();
  assert.strictEqual(root().querySelectorAll(".spool-line").length, 0);
  console.log("SPOOLMAN OK –", calls.length, "service calls");
})().catch((e) => { console.error(e); process.exit(1); });
