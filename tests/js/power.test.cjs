// Netzschalter, Aus-Zustand, Druckdialog mit Auto-Ein, Verbrauch, Historie, Zeitraffer.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
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
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
const own = (id, state, attrs, tk) => add(id, state, attrs, "snapmaker_u1_card", tk);
// Drucker aus: Moonraker-Entitaeten nicht verfuegbar
add(`sensor.${P}_printer_state`, "unavailable");
add(`sensor.${P}_current_print_state`, "unavailable");
own("switch.snapmaker_u1_card_netzschalter", "off", {
  power_sensor: "sensor.steckdose_leistung", energy_sensor: "sensor.steckdose_energie",
  shutting_down: false, powering_on: false, auto_on: true, entry_id: "E1",
}, "power");
add("sensor.steckdose_leistung", "0.4", {}, "shelly");
const slots = [0, 1, 2, 3].map((i) => ({ index: i, loaded: true, type: "PLA", sub_type: i > 1 ? "Silk" : null,
  vendor: "Generic", color: ["#000000", "#FFFFFF", "#6F4C2F", "#FEE5A5"][i], colors: [], official: false }));
own("sensor.snapmaker_u1_card_filamente", "4", { slots, preferences: {}, live: false, entry_id: "E1" }, "filaments");
own("sensor.snapmaker_u1_card_druckdateien", "1", { entry_id: "E1", files: [{
  path: "nuss.gcode", name: "Nuss", modified: 1, time: 4600, weight: 12,
  filaments: [{ index: 0, type: "PLA", color: "#000000", used: true, weight: 12 }] }] }, "files");
own("sensor.snapmaker_u1_card_energie_druck", "1.234", { in_progress: false, result: "complete" }, "print_energy");
own("sensor.snapmaker_u1_card_kosten_druck", "0.47", { in_progress: false, unit_of_measurement: "€" }, "print_cost");
own("sensor.snapmaker_u1_card_druckhistorie", "2", { entry_id: "E1", prints: [
  { file: "nuss.gcode", name: "Nuss", result: "complete", ended: "2026-10-08T19:56:43+00:00", duration: 4620,
    filament_g: 12.3, energy: 1.234, switches: 0, total_cost: 0.47, energy_cost: 0.25, filament_cost: 0.22, thumb: "/t/n.png" },
  { file: "jeep.gcode", name: "Jeep", result: "cancelled", ended: "2026-10-07T18:15:20+00:00", duration: 600 },
] }, "history");
own("sensor.snapmaker_u1_card_zeitraffer", "1", { entry_id: "E1", url: "/api/snapmaker_u1_card/video/E1", videos: [
  { root: "camera", path: "Nuss_2_PLA_1h17m_20261008195643.mp4", name: "Nuss 2 PLA 1h17m",
    recorded: "2026-10-08T19:56:43", size: 17019965, poster: "Nuss_2_PLA_1h17m_20261008195643_cover.jpg",
    poster_url: "/snapmaker_u1_card/thumbs/E1/tl/abc.jpg" },
], playable: true }, "timelapses");

const calls = [], ws = [];
let startResolve;
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)),
  entities: reg,
  callService: (...a) => {
    calls.push(a);
    if (a[1] === "start_print") return new Promise((r) => { startResolve = r; });
    return Promise.resolve();
  },
  // Wie HA: zurueck kommt der DEKODIERTE Pfad (async_sign_path liefert url.path).
  callWS: async (msg) => { ws.push(msg); return { path: `${decodeURIComponent(msg.path)}?authSig=X` }; },
});

const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card" });
w.document.body.appendChild(card);
card.hass = hass();
const root = () => card.shadowRoot.getElementById("u1card");
const text = () => root().textContent.replace(/\s+/g, " ");
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  // 1. Aus-Zustand: Hinweis, Einschalten, Dateien (Auto-Ein), Historie, Zeitraffer
  assert.strictEqual(card._ents.power, "switch.snapmaker_u1_card_netzschalter");
  assert.ok(/Drucker ist aus/.test(text()), "Aus-Hinweis");
  assert.ok(root().querySelector('[data-print="nuss.gcode"]'), "Dateien bei Auto-Ein sichtbar");
  assert.ok(/Druckhistorie/.test(text()) && /Zeitraffer/.test(text()), "Historie + Zeitraffer offline");
  const chip = root().querySelector('[data-su1="pwr"]');
  assert.ok(/Aus/.test(chip.textContent), "Chip zeigt Aus");

  // 2. Druckdialog bei ausgeschaltetem Drucker
  root().querySelector('[data-print="nuss.gcode"]').click();
  const dlg = () => card.shadowRoot.querySelector("dialog.u1dlg:not(.u1video)");
  assert.ok(/wird eingeschaltet/.test(dlg().textContent), "Auto-Ein-Hinweis");
  assert.ok(/Stand vor dem Ausschalten/.test(dlg().textContent), "letzter Filamentstand markiert");
  assert.ok(dlg().querySelectorAll(".slot-btn").length === 4, "Slots aus letztem Stand");
  const conf = dlg().querySelector("[data-confirm]");
  conf.checked = true; conf.dispatchEvent(new w.Event("change"));
  const btn = () => dlg().querySelector('[data-dlg="print"]');
  assert.ok(/Einschalten & drucken/.test(btn().textContent) && !btn().disabled, "Knopf Einschalten & drucken");
  btn().click();
  await tick();
  assert.ok(/Drucker startet/.test(btn().textContent), "laeuft");
  assert.strictEqual(JSON.stringify(calls.at(-1).slice(0, 2)), JSON.stringify(["snapmaker_u1_card", "start_print"]));
  startResolve(); await tick();
  assert.ok(!dlg().hasAttribute("open"), "Dialog zu nach Start");

  // Ohne Auto-Ein: gesperrt
  states["switch.snapmaker_u1_card_netzschalter"].attributes.auto_on = false;
  card.hass = hass();
  root().querySelector('[data-act="power"]').scrollIntoView?.();
  card._openPrint("nuss.gcode");
  const c2 = dlg().querySelector("[data-confirm]");
  c2.checked = true; c2.dispatchEvent(new w.Event("change"));
  assert.ok(btn().disabled && /Bitte erst einschalten/.test(dlg().textContent), "ohne Auto-Ein gesperrt");
  card._closeDialog();
  assert.ok(!root().querySelector('[data-print="nuss.gcode"]'), "ohne Auto-Ein keine Dateien im Aus-Zustand");

  // 3. Einschalten ohne Rueckfrage
  calls.length = 0;
  root().querySelector('.offline [data-act="power"]').click();
  assert.strictEqual(JSON.stringify(calls[0].slice(0, 3)), JSON.stringify(["snapmaker_u1_card", "power_on", { config_entry_id: "E1" }]));

  // 4. Eingeschaltet + online: Watt im Chip, Ausschalten mit Rueckfrage
  states["switch.snapmaker_u1_card_netzschalter"].state = "on";
  states["sensor.steckdose_leistung"].state = "86.4";
  states[`sensor.${P}_printer_state`].state = "ready";
  states[`sensor.${P}_current_print_state`].state = "standby";
  states["sensor.snapmaker_u1_card_filamente"].attributes.live = true;
  card.hass = hass();
  assert.ok(/86 W/.test(root().querySelector('[data-su1="pwr"]').textContent), "Watt im Chip");
  const key = card._renderKey;
  states["sensor.steckdose_leistung"].state = "120";
  card.hass = hass();
  assert.strictEqual(card._renderKey, key, "Leistung ohne Neuaufbau");
  assert.ok(/120 W/.test(root().querySelector('[data-su1="pwr"]').textContent), "Watt gepatcht");
  calls.length = 0;
  confirmAnswer = false;
  root().querySelector('[data-su1="pwr"]').click();
  assert.strictEqual(calls.length, 0, "abgelehnt -> kein Aufruf");
  confirmAnswer = true;
  root().querySelector('[data-su1="pwr"]').click();
  assert.strictEqual(JSON.stringify(calls[0].slice(0, 2)), JSON.stringify(["snapmaker_u1_card", "power_off"]));
  assert.ok(/herunterfahren/.test(prompts.at(-1)));
  // Waehrend eines Drucks: Hinweis statt Ausschalten
  states[`sensor.${P}_current_print_state`].state = "printing";
  card.hass = hass();
  calls.length = 0;
  root().querySelector('[data-su1="pwr"]').click();
  assert.strictEqual(calls.length, 0);
  assert.ok(/druckt gerade/.test(prompts.at(-1)));
  // Herunterfahren: Chip gesperrt mit Status
  states[`sensor.${P}_current_print_state`].state = "standby";
  states["switch.snapmaker_u1_card_netzschalter"].attributes.shutting_down = true;
  card.hass = hass();
  const pw = root().querySelector('[data-su1="pwr"]');
  assert.ok(pw.disabled && /Fährt herunter/.test(pw.textContent), "Herunterfahren angezeigt");
  states["switch.snapmaker_u1_card_netzschalter"].attributes.shutting_down = false;
  card.hass = hass();

  // 5. Statistik: Verbrauch und Kosten
  assert.ok(/Strom letzter Druck ?1,23 kWh/.test(text()), "Strom");
  assert.ok(/Kosten letzter Druck ?0,47 €/.test(text()), "Kosten");

  // 6. Historie
  const hist = [...root().querySelectorAll(".hist")];
  assert.strictEqual(hist.length, 2);
  assert.ok(/Nuss/.test(hist[0].textContent) && /Fertig/.test(hist[0].textContent) && /0,47 €/.test(hist[0].textContent));
  assert.ok(/12 g/.test(hist[0].textContent) && /1,23 kWh/.test(hist[0].textContent));
  assert.ok(/Abgebrochen/.test(hist[1].textContent));
  assert.ok(/2 Drucke · 1,2 kWh · 0,47 €/.test(text()), "Summe");

  // 7. Zeitraffer: Vorschaubild statisch von HA (kein Proxy, keine Signatur),
  //    Player mit signierter URL
  await tick();
  const poster = root().querySelector(".tl-thumb img");
  assert.strictEqual(poster.getAttribute("src"), "/snapmaker_u1_card/thumbs/E1/tl/abc.jpg");
  assert.strictEqual(ws.length, 0, "Vorschaubilder ohne Signatur/Proxy");
  root().querySelector('[data-video="0"]').click();
  await tick(); await tick();
  const vd = card.shadowRoot.querySelector("dialog.u1video");
  const video = vd.querySelector("video");
  assert.ok(vd.hasAttribute("open") && video, "Player offen");
  assert.strictEqual(video.getAttribute("src"),
    "/api/snapmaker_u1_card/video/E1/camera/Nuss_2_PLA_1h17m_20261008195643.mp4?authSig=X");
  assert.ok(vd.querySelector("[data-dl]").getAttribute("href").endsWith(".mp4?authSig=X"), "Download-Link");
  assert.ok(ws.every((m) => m.type === "auth/sign_path" && m.expires === 3600));
  const signs = ws.length;
  vd.querySelector("[data-close]").click();
  assert.ok(!vd.hasAttribute("open") && !vd.querySelector("video"), "Player zu, Video entfernt");
  root().querySelector('[data-video="0"]').click();
  await tick(); await tick();
  assert.strictEqual(ws.length, signs, "Signaturen aus dem Cache");
  assert.strictEqual(video.getAttribute("poster"), "/snapmaker_u1_card/thumbs/E1/tl/abc.jpg");
  vd.querySelector("[data-close]").click();

  // Drucker aus: kein Abspielversuch (Proxy wuerde haengen)
  const st = states["sensor.snapmaker_u1_card_zeitraffer"];
  st.attributes = { ...st.attributes, playable: false };
  card.hass = hass();
  let alerted = "";
  w.alert = (m) => { alerted = m; };
  const before = ws.length;
  root().querySelector('[data-video="0"]').click();
  await tick();
  assert.ok(/aus oder nicht erreichbar/.test(alerted), "Hinweis statt Player");
  assert.strictEqual(ws.length, before, "keine Signatur, kein Proxy");

  // '#' im Dateinamen: Pfad muss kodiert bleiben, nur die Signatur wird angehaengt
  const signed = await card._signed("/api/snapmaker_u1_card/video/E1/camera/Teil%20%232_20260101120000.mp4");
  assert.strictEqual(signed, "/api/snapmaker_u1_card/video/E1/camera/Teil%20%232_20260101120000.mp4?authSig=X");
  console.log("STROM/HISTORIE/ZEITRAFFER OK –", calls.length, "Aufrufe,", ws.length, "Signaturen");
})().catch((e) => { console.error(e); process.exit(1); });
