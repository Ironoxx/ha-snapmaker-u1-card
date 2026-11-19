// 2.4.0b2 Spoolman tab: spool details, archive/restore/delete (admin), empty-spool shortcut,
// archived spools on demand, labels with QR code, more fields in the new-spool form.
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
// label window: capture what would be printed
const opened = [];
w.open = () => { const doc = { html: "", open() {}, write(h) { this.html += h; }, close() {} }; opened.push(doc); return { document: doc }; };
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
  { index: 0, loaded: true, type: "PLA", sub_type: null, vendor: "Generic", color: "#000000", colors: ["#000000"],
    rfid: { nozzle_temp: [210, 230], bed_temp: 60 } },
  { index: 1, loaded: false, type: null, colors: [] }, { index: 2, loaded: false, type: null, colors: [] },
  { index: 3, loaded: false, type: null, colors: [] },
];
const spools = [
  { id: 1, name: "PLA Schwarz", vendor: "Generic", material: "PLA", color: "#000000", remaining_weight: 650, initial_weight: 1000,
    extruder_temp: 215, bed_temp: 60, lot_nr: "L7", location: "Regal" },
  { id: 5, name: "PETG Rest", vendor: "Sunlu", material: "PETG", color: "#00ff00", remaining_weight: 0, initial_weight: 1000 },
  { id: 6, name: "PETG Rot", vendor: "Snapmaker", material: "PETG", color: "#D32F2F", remaining_weight: 1000, initial_weight: 1000 },
];
add("sensor.u1c_filamente", "1", { slots, preferences: {}, entry_id: "E1",
  spoolman: { online: true, error: null, url: "http://sm:7912/", low: 100, deduct: true, pending: [],
    slots: { 0: { ...spools[0], manual: true }, 1: null, 2: null, 3: null }, spools } }, "snapmaker_u1_card", "filaments");

const calls = [], ws = [];
let admin = true;
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, user: { is_admin: admin },
  callService: async (...a) => { calls.push(JSON.parse(JSON.stringify(a))); return { response: { spool_id: 99 } }; },
  callWS: async (m) => { ws.push(m); if (m.type.endsWith("/archived")) return { spools: [
    { id: 7, name: "PLA alt", vendor: "Generic", material: "PLA", color: "#111111", remaining_weight: 10, initial_weight: 1000, archived: true }] };
    return m.type.endsWith("/catalog") ? { vendors: [], materials: [] } : { items: [
      { key: "f:9", source: "own", filament_id: 9, vendor: "Generic", name: "PLA Silk", material: "PLA", extruder_temp: 220, bed_temp: 55, density: 1.24 }] }; } });
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", show: ["toolheads", "spools"] });
w.document.body.appendChild(card);
card.hass = hass();
const root = () => card.shadowRoot.getElementById("u1card");
const sec = () => root().querySelector("[data-spools]");
const dlg = () => card.shadowRoot.querySelector("dialog.u1spool");
const row = (id) => sec().querySelector(`[data-stock="${id}"]`);
const tick = () => new Promise((r) => setTimeout(r, 0));
const text = (el) => el.textContent.replace(/\s+/g, " ");
// last service call without the entry ID (only sent when it is known)
const last = () => { const c = calls.at(-1); const d = { ...c[2] }; delete d.config_entry_id; return [c[1], d]; };

(async () => {
  // 1. Empty spool in no head: archive shortcut right in the list (no detail dialog)
  assert.ok(row(5).querySelector("[data-emptyarch]"), "leere Spule bietet Archivieren an");
  assert.ok(!row(1).querySelector("[data-emptyarch]") && !row(6).querySelector("[data-emptyarch]"));
  row(5).querySelector("[data-emptyarch]").click(); await tick();
  assert.deepStrictEqual(last(), ["spool_archive", { spool_id: 5, archived: true }]);
  assert.ok(!dlg() || !dlg().hasAttribute("open"), "kein Dialog dafür");

  // 2. Details of a spool in a head: data, label, archive/delete disabled with a hint
  row(1).click();
  const d1 = text(dlg());
  assert.match(d1, /#1 PLA Schwarz/);
  assert.match(d1, /Düse ?215 °C/); assert.match(d1, /Bett ?60 °C/); assert.match(d1, /Charge ?L7/); assert.match(d1, /Ort ?Regal/);
  assert.match(d1, /erst die Zuordnung im Druckkopf lösen/);
  assert.ok(dlg().querySelector("[data-archive]").disabled && dlg().querySelector("[data-delete]").disabled);

  // 3. Label: QR code with the Spoolman link (trailing slash dropped), printed from a new window
  dlg().querySelector("[data-label]").click();
  const html = opened.at(-1).html;
  assert.ok(/<svg[^>]+viewBox="0 0 33 33"/.test(html), "27 Byte Link: Version 3 (29 Module) + 2 x 2 Ruhezone");
  assert.match(html, /#1<\/div>/); assert.match(html, /PLA Schwarz/); assert.match(html, /Düse 215 °C · Bett 60 °C/);
  assert.match(html, /window\.print/);

  // 4. Free spool: archive from the details; delete only for admins, with a second step
  row(6).click();
  dlg().querySelector("[data-delete]").click();
  assert.match(text(dlg()), /endgültig löschen\? Spoolman löscht auch ihren Verbrauch/);
  dlg().querySelector("[data-cancel]").click();
  assert.ok(dlg().querySelector("[data-archive]"), "zurück zu den Details");
  dlg().querySelector("[data-delete]").click();
  dlg().querySelector("[data-confirm]").click(); await tick();
  assert.deepStrictEqual(last(), ["spool_delete", { spool_id: 6 }]);
  admin = false; card.hass = hass();
  row(6).click();
  assert.ok(!dlg().querySelector("[data-delete]"), "kein Löschen ohne Admin");
  dlg().querySelector("[data-archive]").click(); await tick();
  assert.deepStrictEqual(last(), ["spool_archive", { spool_id: 6, archived: true }]);

  // 5. Archived: loaded on demand only, restore from the details
  assert.ok(!ws.some((m) => m.type.endsWith("/archived")), "nicht im normalen Ablauf");
  sec().querySelector("[data-stockarch]").click(); await tick(); await tick();
  assert.strictEqual(ws.at(-1).type, "snapmaker_u1_card/spoolman/archived");
  assert.ok(sec().querySelector("[data-activelist]").hidden && !sec().querySelector("[data-archlist]").hidden);
  assert.match(text(sec().querySelector("[data-stocksum]")), /1 Spulen/);
  row(7).click();
  assert.match(text(dlg()), /archiviert/);
  dlg().querySelector("[data-restore]").click(); await tick();
  assert.deepStrictEqual(last(), ["spool_archive", { spool_id: 7, archived: false }]);
  assert.ok(!row(7), "aus der Archivliste entfernt");
  // labels for the list on show (archived list now empty)
  sec().querySelector("[data-stockarch]").click(); await tick();
  const before = opened.length;
  sec().querySelector("[data-stocklabels]").click();
  assert.strictEqual(opened.length, before + 1);
  assert.strictEqual((opened.at(-1).html.match(/class="lbl"/g) || []).length, 3, "alle angezeigten Spulen");

  // 6. New spool for head 1: RFID temperatures prefilled; picked filament fills "more details"; extra fields sent
  sec().querySelector("[data-stocknew]").click(); await tick();
  const f = dlg().querySelector("[data-newspoolform]");
  assert.ok(f.querySelector("details.more-fields") && !f.querySelector("details.more-fields").open, "eingeklappt");
  f.elements.q.value = "silk"; f.elements.q.dispatchEvent(new w.Event("input"));
  await new Promise((r) => setTimeout(r, 300)); await tick();
  f.querySelector('[data-sug="0"]').click();
  assert.strictEqual(f.elements.extruder_temp.value, "220");
  assert.strictEqual(f.elements.density.value, "1.24");
  f.elements.lot_nr.value = "B12"; f.elements.comment.value = "  Trockenbox  "; f.elements.remaining.value = "800";
  f.elements.article_number.value = "";
  f.dispatchEvent(new w.Event("submit", { cancelable: true })); await tick();
  const data = calls.at(-1)[2];
  assert.strictEqual(calls.at(-1)[1], "create_spool");
  assert.strictEqual(data.extruder_temp, 220); assert.strictEqual(data.bed_temp, 55); assert.strictEqual(data.density, 1.24);
  assert.strictEqual(data.remaining, 800); assert.strictEqual(data.lot_nr, "B12"); assert.strictEqual(data.comment, "Trockenbox");
  assert.ok(!("article_number" in data) && !("diameter" in data), "leere Felder nicht gesendet");
  dlg().close();
  // from a head: the tag's temperatures prefilled
  card._newSpoolForm(card._spoolDialog(), 0);
  const fh = dlg().querySelector("[data-newspoolform]");
  assert.strictEqual(fh.elements.extruder_temp.value, "210"); assert.strictEqual(fh.elements.bed_temp.value, "60");
  console.log("SPOOLSTOCK OK –", calls.length, "service calls,", opened.length, "label pages");
})().catch((e) => { console.error(e); process.exit(1); });
