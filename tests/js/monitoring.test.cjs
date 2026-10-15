// Temperature chart, file management, result photo, remaining time, spool runout, firmware, self test, material stats.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/lovelace/0", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new w.Event("close")); };
w.HTMLMediaElement.prototype.pause = () => {};
w.HTMLMediaElement.prototype.load = () => {};
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
let confirmAnswer = true;
const prompts = [];
w.confirm = (m) => { prompts.push(m); return confirmAnswer; };
w.alert = (m) => prompts.push(m);
// XHR fake for the upload
const xhrs = [];
w.XMLHttpRequest = class {
  constructor() { this.headers = {}; this.upload = {}; xhrs.push(this); }
  open(method, url) { this.method = method; this.url = url; }
  setRequestHeader(k, v) { this.headers[k] = v; }
  send(body) { this.body = body; }
};
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
const own = (id, state, attrs, tk) => add(id, state, attrs, "snapmaker_u1_card", tk);
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
add(`camera.${P}_webcam`, "idle", {});
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
const slots = [0, 1, 2, 3].map((i) => ({ index: i, loaded: i < 3, type: i < 3 ? "PLA" : null, sub_type: null,
  vendor: "Generic", color: ["#000000", "#D32F2F", "#FFFFFF", null][i], colors: [], official: false }));
own("sensor.snapmaker_u1_card_filamente", "3", { slots, preferences: { bed_leveling: false }, entry_id: "E1",
  runout: { 1: { minutes: 25, takeover: 2 } },
  spoolman: { online: true, low: 100, slots: { 1: { id: 7, name: "Rot", remaining_weight: 80, initial_weight: 1000, manual: false } } } }, "filaments");
const files = [{ path: "box.gcode", name: "Box", modified: 1, time: 3600, weight: 20, layers: 50,
  cost: { filament: 0.4, energy_kwh: 0.25, energy: 0.08, total: 0.48 },
  filaments: [{ index: 0, type: "PLA", color: "#D32F2F", used: true, weight: 12 }, { index: 1, type: "PLA", color: "#000000", used: true, weight: 8 }] }];
own("sensor.snapmaker_u1_card_druckdateien", "1", { entry_id: "E1", files, all: [
  { path: "box.gcode", modified: 1 }, { path: "halter/klein.gcode", modified: 0 }, { path: "halter/gross.gcode", modified: 0 },
  { path: "deko/stern.gcode", modified: 0 }] }, "files");
own("sensor.snapmaker_u1_card_druckhistorie", "1", { entry_id: "E1", prints: [
  { file: "box.gcode", source: "box.gcode", name: "Box", result: "complete", ended: "2026-10-08T19:56:43+00:00", duration: 3600,
    mapping: { 0: 2, 1: 0 }, options: { timelapse: true }, pause_layers: [12], photo: "/snapmaker_u1_card/thumbs/E1/results/x.jpg" },
  { file: "weg.gcode", name: "Weg", result: "error", ended: "2026-10-07T19:56:43+00:00", error: "Spaghetti erkannt. Druck prüfen." },
] }, "history");
own("sensor.snapmaker_u1_card_warteschlange", "2", { entry_id: "E1", jobs: [
  { id: "j1", file: "box.gcode", name: "Box", mapping: { 0: 1 }, timelapse: true, pause_layers: [5, 9] },
  { id: "j2", file: "teil.gcode", name: "Teil" },
] }, "queue");
const months = Array.from({ length: 12 }, (_, i) => ({ month: `2026-${String(i < 2 ? 11 + i : i - 1).padStart(2, "0")}`,
  prints: i, failed: i % 3 === 0 ? 1 : 0, hours: i * 1.5, filament_g: i * 100, energy: null, cost: i === 11 ? 2.5 : null }));
months.forEach((m, i) => { m.month = `${i < 2 ? 2025 : 2026}-${String(i < 2 ? 11 + i : i - 1).padStart(2, "0")}`; });
own("sensor.snapmaker_u1_card_druckstunden", "123.4", { entry_id: "E1", months,
  totals: { prints: 70, completed: 66, failed: 4, success_rate: 94.3, hours: 120.5, hours_total: 123.4, filament_kg: 3.2, energy: 41.5, cost: 22.1 },
  top_files: [{ file: "sub/box.gcode", count: 9 }],
  materials: [{ type: "PLA", grams: 3200, prints: 60, ok: 57, failed: 3, cost: 64, success_rate: 95 },
    { type: "PETG", grams: 450, prints: 10, ok: 9, failed: 1, cost: null, success_rate: 90 }],
  colors: [{ type: "PLA", color: "#000000", grams: 1800 }] }, "statistics");
own("sensor.snapmaker_u1_card_wartung", "1", { entry_id: "E1", items: [
  { key: "plate", interval_h: 30, used_h: 31, remaining_h: -1, progress: 103, due: true, done_at: null },
  { key: "rails", interval_h: 300, used_h: 250, remaining_h: 50, progress: 83, due: false, done_at: "2026-01-01T00:00:00+00:00" },
  { key: "tool_changer", interval: 25100, used: 23000, remaining: 2100, progress: 92, due: false, firmware: true },
], config_backup: { enabled: true, snapshot: "2026-10-12_030000", saved_at: "2026-10-12T03:00:00+00:00", status: "saved", files: 14, folder: "snapmaker_u1_backup/192.168.1.50" } }, "maintenance");
own("binary_sensor.snapmaker_u1_card_live_verbindung", "on", { connected_since: "2026-10-13T06:00:00+00:00", poll_interval_s: 30, entry_id: "E1" }, "live");
own("sensor.snapmaker_u1_card_restzeit", "42.5", {}, "remaining");
own("sensor.snapmaker_u1_card_fertig_um", "2026-10-13T18:30:00+00:00", {}, "finish");
own("update.snapmaker_u1_card_firmware", "on", { installed_version: "1.6.0", latest_version: "2.0.0" }, "firmware");
own("sensor.snapmaker_u1_card_meldungen", "1", { errors: [
  { key: "0525-0001-0013", id: 525, index: 1, code: 13, level: 1, known: true, message: "preload fail: no_filament",
    text: { de: "Vorladen: kein Filament erkannt (Kopf 2)", en: "Preload: no filament detected (head 2)" },
    hint: { de: "Filament bis zum Anschlag einführen.", en: "Insert the filament until it stops." } },
] }, "errors");
own("sensor.snapmaker_u1_card_zeitraffer", "0", { entry_id: "E1", url: "/api/snapmaker_u1_card/video/E1", videos: [], playable: true,
  archive: { count: 2, keep: 5, cleanup: "ok", busy: false, last_backup: 1760000000, errors: [], folder: "/media/snapmaker_u1",
    videos: [{ file: "Nuss_2_PLA_1h17m_20261008195643.mp4", size: 17000000, modified: 1760000000,
      media_id: "media-source://media_source/local/snapmaker_u1/Nuss_2_PLA_1h17m_20261008195643.mp4",
      poster: "x.jpg", poster_url: "/snapmaker_u1_card/thumbs/E1/archive/Nuss.jpg" }] } }, "timelapses");

let lang = "de";
const calls = [], ws = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: lang }, language: lang,
  auth: { data: { access_token: "TOKEN" }, expired: false },
  callService: async (...a) => { calls.push(a);
    if (a[1] === "file_details") return { response: { file: { path: a[2].path, name: "klein", filaments: [], time: 60 } } };
    if (a[1] === "self_test") return { response: { ok: false, checks: [{ key: "printer", ok: true, detail: "Moonraker erreichbar" }, { key: "camera", ok: null, detail: "Keine Kamera" }, { key: "storage", ok: false, detail: "300 MiB frei" }] } };
    return {}; },
  callWS: async (m) => { ws.push(m); return { url: "/media/local/snapmaker_u1/x.mp4?authSig=Y", mime_type: "video/mp4" }; },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const D = () => card.shadowRoot.querySelector("dialog.u1dlg:not(.u1video)");
const text = (el) => el.textContent.replace(/\s+/g, " ");
const tab = (id) => R().querySelector(`[data-tab="${id}"]`).click();
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  // 1. Remaining/finish time from our own sensors
  assert.strictEqual(card._d.remaining, 42.5 * 60);
  assert.strictEqual(card._d.eta, "2026-10-13T18:30:00+00:00");

  // 2. Spool runout: hint on the head, with takeover
  tab("overview");
  const ro = R().querySelector('[data-runout="1"]');
  assert.ok(ro, "Hinweis am Kopf 2");
  assert.match(text(ro), /leer in ~25 min · Kopf 3 übernimmt/);

  // 3. Files: search, folders, loading an older file
  tab("files");
  const search = R().querySelector("[data-fsearch]");
  assert.match(search.placeholder, /4 Dateien/);
  search.value = "klein"; search.dispatchEvent(new w.Event("input"));
  assert.ok(R().querySelector('[data-print="box.gcode"]').hidden, "Box ausgeblendet");
  const more = R().querySelectorAll("[data-fopen]");
  assert.deepEqual([...more].map((b) => b.dataset.fopen), ["halter/klein.gcode"]);
  more[0].click(); await tick(); await tick();
  assert.deepEqual(calls.find((c) => c[1] === "file_details")[2], { path: "halter/klein.gcode", config_entry_id: "E1" });
  assert.ok(D() && D().hasAttribute("open"), "Druckdialog fuer aeltere Datei");
  assert.match(text(D().querySelector(".dlg-title")), /klein/);
  D().close();
  search.value = ""; search.dispatchEvent(new w.Event("input"));
  const chips = [...R().querySelectorAll("[data-ffolder]")].map((b) => b.dataset.ffolder);
  assert.deepEqual(chips, ["", "deko", "halter"]);
  R().querySelector('[data-ffolder="halter"]').click();
  assert.ok(R().querySelector('[data-print="box.gcode"]').hidden);
  assert.strictEqual(R().querySelectorAll("[data-fopen]").length, 2, "Ordner zeigt aeltere Dateien");
  R().querySelector('[data-ffolder=""]').click();
  // Sorting by name survives a rebuild
  R().querySelector("[data-fsort]").value = "name"; R().querySelector("[data-fsort]").dispatchEvent(new w.Event("change"));
  card._renderKey = null; card.hass = hass();
  assert.strictEqual(R().querySelector("[data-fsort]").value, "name");

  // 4. Rename / delete in the dialog
  R().querySelector('[data-print="box.gcode"]').click();
  w.prompt = () => "teile/box2";
  D().querySelector('[data-dlg="rename"]').click(); await tick();
  assert.deepEqual(calls.pop().slice(1, 3), ["move_file", { source: "box.gcode", dest: "teile/box2", config_entry_id: "E1" }]);
  R().querySelector('[data-print="box.gcode"]').click();
  D().querySelector('[data-dlg="delete"]').click(); await tick();
  assert.match(prompts.pop(), /„Box“ vom Drucker löschen\?/);
  assert.deepEqual(calls.pop().slice(1, 3), ["delete_file", { path: "box.gcode", config_entry_id: "E1" }]);

  // 5. Temperature chart
  tab("control");
  card._temps = { step: 5, series: {
    extruder: { temperatures: [30, 120, 210, 219], targets: [220, 220, 220, 220] },
    extruder1: { temperatures: [30, 30, 30, 30], targets: [0, 0, 0, 0] },
    heater_bed: { temperatures: [25, 40, 58, 60], targets: [60, 60, 60, 60] } } };
  const tc = R().querySelector("[data-tchart]");
  tc.innerHTML = card._tempSvg();
  assert.strictEqual(tc.querySelectorAll("polyline").length, 4, "Kopf 1 + Bett, je Ist und Soll; kalter Kopf 2 ausgelassen");
  assert.match(text(tc.querySelector(".tlegend")), /Kopf 1 219 °C.*Bett 60 °C/);
  card._temps = null;
  assert.match(card._tempSvg(), /Lädt/);
  card._temps = { step: 5, series: {} };
  assert.match(card._tempSvg(), /Noch keine Daten/);
  card._temps = { step: 5, series: {}, offline: true };
  assert.match(card._tempSvg(), /nicht erreichbar/);

  // 6. History: result photo
  tab("history");
  const ph = R().querySelector("img.hist-photo");
  assert.ok(ph && ph.dataset.photo.endsWith("/results/x.jpg"));
  let opened = null; w.open = (u) => { opened = u; };
  ph.click();
  assert.strictEqual(opened, null, "kein neues Fenster");
  const pd = card.shadowRoot.querySelector("dialog.u1photo");
  assert.ok(pd && pd.hasAttribute("open"), "Vergroesserung im Dialog");
  assert.ok(pd.querySelector("img").src.endsWith("/results/x.jpg"));
  pd.click();
  assert.ok(!pd.hasAttribute("open"), "Antippen schliesst");

  // 7. Material statistics
  const mt = R().querySelector(".mat-table");
  assert.ok(mt);
  const cells = [...mt.querySelectorAll("tbody tr")].map((tr) => [...tr.children].map((td) => td.textContent.trim()).join("|"));
  assert.deepEqual(cells, ["PLA|60|3,20 kg|64,00 €|95 %", "PETG|10|450 g|—|90 %"]);
  assert.match(text(R().querySelector(".colors")), /PLA 1800 g/);

  // 8. System: firmware and self test
  tab("system");
  assert.match(text(R().querySelector('[data-su1="fw"]')), /1\.6\.0 → 2\.0\.0 verfügbar/);
  R().querySelector('[data-act="selftest"]').click(); await tick(); await tick();
  const stx = text(R().querySelector("[data-selftest]"));
  assert.strictEqual(stx, "✓Moonraker erreichbar!Keine Kamera✗300 MiB frei");

  // 9. English
  lang = "en"; card._renderKey = null; card.hass = hass();
  tab("files");
  assert.match(R().querySelector("[data-fsearch]").placeholder, /Search \(4 files\)/);
  tab("system");
  assert.match(text(R().querySelector('[data-su1="fw"]')), /available/);
  console.log("MONITORING OK – temperatures, files, photo, remaining time, spool, firmware, self test, materials");
})().catch((e) => { console.error(e); process.exit(1); });
