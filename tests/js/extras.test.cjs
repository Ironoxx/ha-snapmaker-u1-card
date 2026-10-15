// Cost before printing, config backup, automatic image height.
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
own("sensor.snapmaker_u1_card_filamente", "3", { slots, preferences: { bed_leveling: false }, entry_id: "E1" }, "filaments");
const files = [{ path: "box.gcode", name: "Box", modified: 1, time: 3600, weight: 20, layers: 50,
  cost: { filament: 0.4, energy_kwh: 0.25, energy: 0.08, total: 0.48 },
  filaments: [{ index: 0, type: "PLA", color: "#D32F2F", used: true, weight: 12 }, { index: 1, type: "PLA", color: "#000000", used: true, weight: 8 }] }];
own("sensor.snapmaker_u1_card_druckdateien", "1", { entry_id: "E1", files }, "files");
own("sensor.snapmaker_u1_card_druckhistorie", "1", { entry_id: "E1", prints: [
  { file: "box.gcode", source: "box.gcode", name: "Box", result: "complete", ended: "2026-10-08T19:56:43+00:00", duration: 3600,
    mapping: { 0: 2, 1: 0 }, options: { timelapse: true }, pause_layers: [12] },
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
  top_files: [{ file: "sub/box.gcode", count: 9 }] }, "statistics");
own("sensor.snapmaker_u1_card_wartung", "1", { entry_id: "E1", items: [
  { key: "plate", interval_h: 30, used_h: 31, remaining_h: -1, progress: 103, due: true, done_at: null },
  { key: "rails", interval_h: 300, used_h: 250, remaining_h: 50, progress: 83, due: false, done_at: "2026-01-01T00:00:00+00:00" },
  { key: "tool_changer", interval: 25100, used: 23000, remaining: 2100, progress: 92, due: false, firmware: true },
], config_backup: { enabled: true, snapshot: "2026-10-12_030000", saved_at: "2026-10-12T03:00:00+00:00", status: "saved", files: 14, folder: "snapmaker_u1_backup/192.168.1.50" } }, "maintenance");
own("binary_sensor.snapmaker_u1_card_live_verbindung", "on", { connected_since: "2026-10-13T06:00:00+00:00", poll_interval_s: 30, entry_id: "E1" }, "live");
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
  callService: async (...a) => { calls.push(a); return {}; },
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
  // 1. Cost in the start dialog
  tab("files");
  R().querySelector('[data-print="box.gcode"]').click();
  const t = text(D());
  assert.match(t, /≈ 0,48 €/);
  assert.match(text(D().querySelector("[data-cost]")), /Geschätzt: Filament 0,40 € · Strom 0,08 € \(0,25 kWh\)/);
  D().close();

  // 2. Config backup in the system tab
  tab("system");
  const b = R().querySelector("[data-backup]");
  assert.ok(b, "Sicherungszeile");
  assert.match(text(b), /Drucker-Konfiguration gesichert .*12\.10\..*14 Dateien/);
  b.querySelector('[data-act="backup_config"]').click();
  await tick();
  assert.deepEqual(calls.pop().slice(0, 3), ["snapmaker_u1_card", "backup_config", { config_entry_id: "E1" }]);

  // 3. Automatic image height: aspect ratio from the image
  tab("overview");
  const frame = R().querySelector(".stage .frame");
  assert.match(frame.getAttribute("style"), /aspect-ratio:\s*16 \/ 9/);
  assert.match(frame.getAttribute("style"), /max-height:\s*520px/);
  const img = frame.querySelector("img[data-live]");
  Object.defineProperty(img, "naturalWidth", { value: 1280 });
  Object.defineProperty(img, "naturalHeight", { value: 960 });
  card._fitAspect(img);
  assert.strictEqual(card._camAspect, "1280 / 960");
  assert.match(frame.style.aspectRatio, /1280 \/ 960|4 \/ 3/);
  card._renderKey = null; card.hass = hass();
  assert.match(R().querySelector(".stage .frame").getAttribute("style"), /1280 \/ 960/, "bleibt nach Neuaufbau");
  // a fixed height stays fixed
  const fixedCard = w.document.createElement("snapmaker-u1-card");
  fixedCard.setConfig({ type: "custom:snapmaker-u1-card", camera_height: 300 });
  w.document.body.appendChild(fixedCard); fixedCard.hass = hass();
  const ff = fixedCard.shadowRoot.querySelector(".stage .frame");
  assert.match(ff.getAttribute("style"), /height:300px/);
  fixedCard._fitAspect(Object.assign(ff.querySelector("img[data-live]"), {}));
  assert.ok(!fixedCard._camAspect);

  // 4. Live connection in the system tab, updated without a rebuild
  tab("system");
  assert.match(text(R().querySelector('[data-su1="live"]')), /● verbunden · seit 13\.10\./);
  states["binary_sensor.snapmaker_u1_card_live_verbindung"].state = "off";
  states["binary_sensor.snapmaker_u1_card_live_verbindung"].attributes = { poll_interval_s: 10 };
  card.hass = hass();
  assert.match(text(R().querySelector('[data-su1="live"]')), /getrennt · Abfrage alle 10 s/);

  // 5. Thumbnail: dark part -> light background, light -> dark, no transparency -> nothing
  const fake = (rgb, alphaOpaque) => {
    const data = new Uint8ClampedArray(32 * 32 * 4);
    for (let i = 0; i < 32 * 32; i++) {
      const on = i < alphaOpaque;
      data.set(on ? [...rgb, 255] : [0, 0, 0, 0], i * 4);
    }
    return { drawImage() {}, getImageData: () => ({ data }) };
  };
  const probe = (src, ctx) => {
    w.HTMLCanvasElement.prototype.getContext = () => ctx;
    const box = w.document.createElement("span"); box.className = "file-thumb";
    const im = w.document.createElement("img"); im.src = src; box.appendChild(im);
    card.shadowRoot.appendChild(box);
    im.dispatchEvent(new w.Event("load"));
    box.remove();
    return box.dataset.toneBg;
  };
  assert.strictEqual(probe("/t/schwarz.png", fake([20, 20, 22], 300)), "dark");
  assert.strictEqual(probe("/t/weiss.png", fake([245, 245, 245], 300)), "light");
  assert.strictEqual(probe("/t/gruen.png", fake([60, 160, 90], 300)), undefined);
  assert.strictEqual(probe("/t/voll.png", fake([10, 10, 10], 1024)), undefined, "ohne Transparenz unveraendert");
  assert.strictEqual(probe("/t/schwarz.png", null), "dark", "Ergebnis je Adresse gemerkt");
  w.HTMLCanvasElement.prototype.getContext = () => null;

  // 6. English
  lang = "en"; card._renderKey = null; card.hass = hass();
  tab("files");
  R().querySelector('[data-print="box.gcode"]').click();
  assert.match(text(D().querySelector("[data-cost]")), /Estimated: Filament 0\.40 € · Energy 0\.08 €/);
  D().close();
  tab("system");
  assert.match(text(R().querySelector("[data-backup]")), /Printer configuration backed up .*14 files/);
  assert.match(text(R().querySelector('[data-su1="live"]')), /disconnected · polling every 10 s/);

  console.log("EXTRAS OK – cost, config backup, image height, live connection, thumbnail background");
})().catch((e) => { console.error(e); process.exit(1); });
