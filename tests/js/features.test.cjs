// Queue, pause at layer, reprint, upload, messages,
// charts, maintenance, timelapse archive, in German and English.
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
  { key: "lead_screws", interval_m: 3, remaining_d: 41.6, progress: 54, due: false, done_at: 1 },
  { key: "tool_changer", interval: 25100, used: 23000, remaining: 2100, progress: 92, due: false, firmware: true },
] }, "maintenance");
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
  // 1. Plain-language message on top, on every tab
  assert.match(text(R().querySelector(".alerts")), /Vorladen: kein Filament erkannt \(Kopf 2\) Filament bis zum Anschlag/);
  tab("system");
  assert.ok(R().querySelector(".alerts"), "Meldung auch im System-Reiter");

  // 2. Maintenance
  const m = text(R().querySelector(".m-list"));
  assert.match(m, /Druckplatte reinigen 31 \/ 30 h · fällig/);
  assert.match(m, /Linearführungen reinigen und schmieren 250 \/ 300 h · noch 50 h/);
  assert.match(m, /Z-Spindeln und Muttern schmieren alle 3 Monate · noch 42 Tage/);
  assert.match(m, /Werkzeugwechsler \(Firmware\) 23\.000 \/ 25\.100 Wechsel/);
  assert.strictEqual(R().querySelectorAll("[data-maint]").length, 3, "Firmware-Zaehler ohne Erledigt-Knopf");
  assert.strictEqual(R().querySelector('.m-item[data-due="1"] .track').dataset.tone, "error");
  R().querySelector('[data-maint="plate"]').click();
  await tick();
  assert.match(prompts.pop(), /„Druckplatte reinigen“ als erledigt markieren\?/);
  assert.deepEqual(calls.pop().slice(0, 3), ["snapmaker_u1_card", "maintenance_done", { item: "plate", config_entry_id: "E1" }]);

  // 3. Charts
  tab("history");
  assert.strictEqual(R().querySelectorAll(".chart .bar").length, 12);
  assert.ok(R().querySelector(".bar-fail"), "Abgebrochene gestapelt");
  assert.match(text(R().querySelector(".chart").parentElement), /Erfolgsquote\s*94,3 %.*Druckstunden\s*123 h.*Filament\s*3,20 kg.*Strom\s*41,5 kWh/);
  assert.match(text(R().querySelector(".chart").parentElement), /Am häufigsten: box ×9/);
  R().querySelector('[data-metric="hours"]').click();
  assert.strictEqual(R().querySelector('[data-metric="hours"]').classList.contains("sel"), true);
  assert.ok(!R().querySelector(".bar-fail"), "Stunden ohne Stapel");
  assert.match(R().querySelectorAll(".chart .bar")[11].title, /16,5 h/);
  assert.ok(R().querySelector('[data-metric="cost"]'), "Kosten-Chip, da Kosten vorhanden");
  // The metric survives a rebuild
  card._renderKey = null; card.hass = hass();
  assert.ok(R().querySelector('[data-metric="hours"]').classList.contains("sel"));

  // 4. History: reprint with the old mapping, options, pause; error text
  assert.strictEqual(R().querySelectorAll("[data-reprint]").length, 1, "nur, wenn die Datei noch da ist");
  assert.match(text(R().querySelector(".hist-list")), /Pause vor 12/);
  assert.match(text(R().querySelector(".hist-list")), /Spaghetti erkannt/);
  R().querySelector("[data-reprint]").click();
  let dl = D();
  assert.ok(dl && dl.hasAttribute("open"), "Dialog offen");
  const pressed = [...dl.querySelectorAll('.slot-btn[aria-pressed="true"]')].map((b) => `${b.dataset.map}>${b.dataset.slot}`);
  assert.deepEqual(pressed, ["0>2", "1>0"], "alte Zuordnung");
  assert.strictEqual(dl.querySelector("[data-pause]").value, "12");
  assert.ok(dl.querySelector('[data-pref="timelapse"]').checked, "Zeitraffer wie damals");
  assert.match(text(dl), /hält vor Schicht 12 an/);

  // 5. Validate the pause input
  const pin = dl.querySelector("[data-pause]");
  pin.value = "3, 60"; pin.dispatchEvent(new w.Event("change"));
  dl = D();
  assert.match(text(dl), /Die Datei hat nur 50 Schichten/);
  assert.ok(dl.querySelector('[data-dlg="queue"]').disabled);
  dl.querySelector("[data-pause]").value = "x"; dl.querySelector("[data-pause]").dispatchEvent(new w.Event("change"));
  assert.match(text(D()), /ganze Zahlen ab 1/);
  D().querySelector("[data-pause]").value = "20 5,20"; D().querySelector("[data-pause]").dispatchEvent(new w.Event("change"));
  dl = D();
  assert.match(text(dl), /vor Schicht 5, 20 an/);
  // Print: confirmation required; queue: not
  assert.ok(dl.querySelector('[data-dlg="print"]').disabled);
  dl.querySelector('[data-dlg="queue"]').click();
  await tick(); await tick();
  const q = calls.pop();
  assert.strictEqual(q[1], "queue_add");
  assert.deepEqual(q[2].pause_layers, [5, 20]);
  assert.deepEqual(q[2].mapping, { 0: 2, 1: 0 });
  assert.strictEqual(q[2].timelapse, true);
  assert.ok(!D() || !D().hasAttribute("open"), "Dialog zu");

  // 6. Start a print with pauses
  tab("files");
  R().querySelector('[data-print="box.gcode"]').click();
  dl = D();
  dl.querySelector("[data-pause]").value = "7"; dl.querySelector("[data-pause]").dispatchEvent(new w.Event("change"));
  D().querySelector("[data-confirm]").click();
  D().querySelector('[data-dlg="print"]').click();
  await tick(); await tick();
  const sp = calls.pop();
  assert.strictEqual(sp[1], "start_print");
  assert.deepEqual(sp[2].pause_layers, [7]);

  // 7. Queue in the files tab
  const qtext = text(R().querySelector(".q-list"));
  assert.match(qtext, /1 Box Pause vor 5, 9.*2 Teil/);
  assert.strictEqual(R().querySelector('[data-q="start"]').dataset.job, "j1");
  assert.strictEqual(R().querySelectorAll('[data-q="move"]').length, 1, "nur Folgeauftraege nach oben");
  R().querySelector('[data-q="move"]').click(); await tick();
  assert.deepEqual(calls.pop()[2], { job_id: "j2", position: 0, config_entry_id: "E1" });
  R().querySelectorAll('[data-q="remove"]')[1].click(); await tick();
  assert.deepEqual(calls.pop().slice(1, 3), ["queue_remove", { job_id: "j2", config_entry_id: "E1" }]);
  confirmAnswer = false;
  R().querySelector('[data-q="start"]').click(); await tick();
  assert.match(prompts.pop(), /Box starten\? Druckbett ist leer/);
  assert.notStrictEqual(calls.length && calls[calls.length - 1][1], "queue_start", "abgelehnt -> kein Start");
  confirmAnswer = true;
  R().querySelector('[data-q="start"]').click(); await tick(); await tick();
  assert.strictEqual(calls.pop()[1], "queue_start");

  // 8. During a print: files visible, dialog offers the queue only, start blocked
  states[`sensor.${P}_current_print_state`].state = "printing";
  card.hass = hass();
  tab("files");
  assert.ok(R().querySelector('[data-q="start"]').disabled, "Start gesperrt waehrend Druck");
  assert.match(text(R()), /Antippen, um einen Auftrag in die Warteschlange/);
  R().querySelector('[data-print="box.gcode"]').click();
  dl = D();
  D().querySelector("[data-confirm]").click();
  assert.ok(D().querySelector('[data-dlg="print"]').disabled, "Drucken gesperrt");
  assert.ok(!D().querySelector('[data-dlg="queue"]').disabled, "Warteschlange frei");
  D().querySelector('[data-dlg="cancel"]').click();
  states[`sensor.${P}_current_print_state`].state = "standby";
  card.hass = hass();

  // 9. Upload
  tab("files");
  const input = R().querySelector("input[data-upload]");
  const file = new w.File(["G28\n"], "Neu.gcode");
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  input.dispatchEvent(new w.Event("change"));
  const x = xhrs.pop();
  assert.strictEqual(x.url, "/api/snapmaker_u1_card/upload/E1");
  assert.strictEqual(x.headers.Authorization, "Bearer TOKEN");
  assert.ok(x.body instanceof w.FormData && x.body.get("file").name === "Neu.gcode");
  x.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 });
  assert.match(text(R().querySelector(".upl")), /Neu\.gcode 50 %/);
  x.status = 200; x.responseText = JSON.stringify({ file: "Neu.gcode" }); x.onload();
  assert.match(text(R().querySelector(".upl")), /fertig/);
  assert.ok(!D() || !D().hasAttribute("open"), "Datei noch nicht in der Liste");
  states["sensor.snapmaker_u1_card_druckdateien"].attributes.files = [...files, { path: "Neu.gcode", name: "Neu", modified: 5, filaments: [] }];
  card.hass = hass();
  assert.ok(D() && D().hasAttribute("open") && /Neu/.test(D().querySelector(".dlg-title").textContent), "Dialog fuer neue Datei");
  D().querySelector('[data-dlg="cancel"]').click();
  // error from the server
  const input2 = R().querySelector("input[data-upload]");
  Object.defineProperty(input2, "files", { value: [file], configurable: true });
  input2.dispatchEvent(new w.Event("change"));
  const x2 = xhrs.pop();
  x2.status = 413; x2.responseText = JSON.stringify({ message: "Datei zu gross." }); x2.onload();
  assert.match(text(R().querySelector(".dlg-error")), /Neu\.gcode: Datei zu gross/);
  // wrong file extension
  const bad = new w.File(["x"], "a.stl");
  Object.defineProperty(R().querySelector("input[data-upload]"), "files", { value: [bad], configurable: true });
  R().querySelector("input[data-upload]").dispatchEvent(new w.Event("change"));
  assert.match(prompts.pop(), /Nur \.gcode/);

  // 10. Timelapse archive
  tab("timelapse");
  assert.match(text(R().querySelector(".arch-head")), /Gesichert in Medien \(2\)/);
  assert.match(text(R().querySelector('[data-archive="0"]')), /Nuss 2 PLA 1h17m/);
  assert.match(text(R()), /Auf dem Drucker bleiben die 5 neuesten/);
  R().querySelector('[data-archive="0"]').click();
  await tick(); await tick();
  assert.deepEqual(ws.pop(), { type: "media_source/resolve_media", media_content_id: states["sensor.snapmaker_u1_card_zeitraffer"].attributes.archive.videos[0].media_id, expires: 3600 });
  const vid = card.shadowRoot.querySelector("dialog.u1video video");
  assert.ok(vid && vid.getAttribute("src").includes("authSig=Y"), "Video aus Medienquelle");
  card.shadowRoot.querySelector("dialog.u1video").close();
  R().querySelector('[data-act="backup"]').click(); await tick();
  assert.strictEqual(calls.pop()[1], "backup_timelapses");
  states["sensor.snapmaker_u1_card_zeitraffer"].attributes.archive.cleanup = "not_supported";
  card.hass = hass();
  assert.match(text(R()), /von der Firmware nicht unterstützt/);

  // 11. Mini card: message and next job
  const mini = w.document.createElement("snapmaker-u1-mini-card");
  mini.setConfig({ type: "custom:snapmaker-u1-mini-card" });
  w.document.body.appendChild(mini);
  mini.hass = hass();
  const mt = text(mini.shadowRoot.getElementById("u1card"));
  assert.match(mt, /Vorladen: kein Filament erkannt/);
  assert.match(mt, /Nächster: Box \(\+1\)/);

  // 12. English: no German leftovers in any tab, the dialog and the mini card
  lang = "en";
  card._up = null; // The server error message comes from the German part
  const GERMAN = /[äöüÄÖÜß]|\b(Druck|Drucke|Drucker|Datei|Dateien|Schicht|Schichten|Restzeit|Fertig|fertig|Bereit|Abbrechen|Licht|Kopf|Leer|Spule|Verlauf|Steuerung|Zeitraffer|Wartung|Warteschlange|Aufträge|Meldung|Starten|Entfernen|Erledigt|Stunden|Kosten|Strom|und|oder|nicht|noch|keine?|vor|nach)\b/;
  const scan = (root, what) => {
    const t = text(root);
    const titles = [...root.querySelectorAll("[title],[aria-label],[placeholder]")]
      .map((e) => e.getAttribute("title") || e.getAttribute("aria-label") || e.getAttribute("placeholder")).join(" ");
    const all = `${t} ${titles}`.replace(/Box|Teil|Nuss|Generic|Weg|Spaghetti erkannt\. Druck prüfen\./g, "");
    const hit = all.match(GERMAN);
    assert.ok(!hit, `${what}: "${hit && hit[0]}" … ${hit ? all.slice(Math.max(0, hit.index - 60), hit.index + 60) : ""}`);
  };
  card._renderKey = null; card.hass = hass();
  for (const t of ["overview", "control", "files", "history", "timelapse", "system"]) { tab(t); scan(R(), `EN ${t}`); }
  tab("files");
  R().querySelector('[data-print="box.gcode"]').click();
  D().querySelector("[data-pause]").value = "99"; D().querySelector("[data-pause]").dispatchEvent(new w.Event("change"));
  scan(D(), "EN Dialog");
  assert.match(text(D()), /The file only has 50 layers/);
  D().querySelector('[data-dlg="cancel"]').click();
  mini._renderKey = null; mini.hass = hass();
  scan(mini.shadowRoot.getElementById("u1card"), "EN Mini");
  tab("history");
  assert.match(text(R().querySelector(".chart").parentElement), /Success rate\s*94\.3 %/);

  console.log("FEATURES OK – queue, pause at layer, upload, messages, charts, maintenance, archive");
})().catch((e) => { console.error(e); process.exit(1); });
