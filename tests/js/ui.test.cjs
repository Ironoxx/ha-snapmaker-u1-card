// 5.2: Reiter, Overlay auf der Kamera, Mini-Karte, visueller Editor, Englisch.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/lovelace/0", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new w.Event("close")); };
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
const own = (id, state, attrs, tk) => add(id, state, attrs, "snapmaker_u1_card", tk);
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "printing");
add(`sensor.${P}_filename`, "nuss.gcode");
add(`sensor.${P}_progress`, "42.4");
add(`sensor.${P}_current_layer`, "57");
add(`sensor.${P}_total_layer`, "130");
add(`sensor.${P}_print_time_left`, "1.25");
add(`sensor.${P}_print_eta`, "2026-10-12T18:30:00+00:00");
add(`light.${P}_led_cavity_led`, "on");
add(`camera.${P}_webcam`, "idle", { entity_picture: "/api/camera_proxy/cam?token=A", access_token: "A" });
for (let i = 0; i < 4; i++) {
  const sfx = ["", "1", "2", "3"][i];
  add(`number.${P}_extruder${sfx}_target`, i === 1 ? "220" : "0", { min: 0, max: 300, step: 1 });
  add(`sensor.${P}_extruder${sfx}_temperature`, i === 1 ? "219" : "30");
  add(`sensor.${P}_extruder${sfx}_power`, i === 1 ? "40" : "0");
}
add(`number.${P}_bed_target`, "60", { min: 0, max: 120, step: 1 });
const slots = [0, 1, 2, 3].map((i) => ({ index: i, loaded: i < 3, type: i < 3 ? "PLA" : null, sub_type: null,
  vendor: "Generic", color: ["#000000", "#D32F2F", "#FFFFFF", null][i], colors: [], official: false }));
own("sensor.snapmaker_u1_card_filamente", "3", { slots, preferences: {}, entry_id: "E1",
  spoolman: { online: true, low: 100, slots: { 1: { id: 7, name: "Rot", remaining_weight: 80, initial_weight: 1000, manual: false } } } }, "filaments");
own("sensor.snapmaker_u1_card_druckdateien", "0", { entry_id: "E1", files: [] }, "files");
own("switch.snapmaker_u1_card_netzschalter", "on", { power_sensor: "sensor.pw", auto_on: true, entry_id: "E1" }, "power");
add("sensor.pw", "112", {}, "shelly");
own("sensor.snapmaker_u1_card_druckhistorie", "0", { entry_id: "E1", prints: [] }, "history");
own("sensor.snapmaker_u1_card_zeitraffer", "0", { entry_id: "E1", videos: [], playable: true }, "timelapses");

let lang = "de";
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg,
  locale: { language: lang }, language: lang,
  callService: async () => {}, callWS: async (m) => ({ path: `${m.path}?authSig=X` }),
});

const make = (tag, cfg = {}) => {
  const el = w.document.createElement(tag);
  el.setConfig({ type: `custom:${tag}`, ...cfg });
  w.document.body.appendChild(el);
  el.hass = hass();
  return el;
};
const R = (el) => el.shadowRoot.getElementById("u1card");

// 1. Reiter: Standard, Uebersicht aktiv, Wechsel nur per hidden (kein Neuaufbau)
const card = make("snapmaker-u1-card");
let r = R(card);
const tabs = [...r.querySelectorAll("[data-tab]")].map((b) => b.dataset.tab);
assert.deepStrictEqual(tabs, ["overview", "control", "files", "history", "timelapse", "system"], "Reiter");
const visible = () => [...r.querySelectorAll("[data-pane]")].filter((p) => !p.hidden).map((p) => p.dataset.pane);
assert.deepStrictEqual(visible(), ["overview"]);
const live = r.querySelector("img[data-live]");
r.querySelector('[data-tab="history"]').click();
assert.deepStrictEqual(visible(), ["history"]);
assert.strictEqual(r.querySelector('[data-tab="history"]').getAttribute("aria-selected"), "true");
assert.strictEqual(r.querySelector("img[data-live]"), live, "Kamera-<img> bleibt erhalten");
assert.strictEqual(card._streamImg, null, "kein Stream bei verborgener Bildflaeche");
// Neuaufbau behaelt den Reiter
card._renderKey = null; card.hass = hass(); r = R(card);
assert.deepStrictEqual(visible(), ["history"], "Reiter ueberlebt Neuaufbau");
r.querySelector('[data-tab="overview"]').click();

// 2. Overlay auf der Kamera, gepatcht
const hud = r.querySelector(".hud");
assert.ok(hud, "Overlay");
assert.match(hud.textContent.replace(/\s+/g, " "), /42 ?% .*57 \/ 130 .*1 h 15 min/);
assert.match(hud.querySelector(".hud-head").textContent, /Kopf 2 · PLA/, "aktiver Kopf");
states[`sensor.${P}_progress`].state = "43.6";
const key = card._renderKey;
card.hass = hass();
assert.strictEqual(card._renderKey, key, "kein Neuaufbau");
assert.strictEqual(r.querySelector('[data-su1="opct"]').textContent, "44");
assert.strictEqual(r.querySelector('[data-su1="obar"]').style.width, "43.6%");
const noHud = make("snapmaker-u1-card", { camera_overlay: false });
assert.ok(!R(noHud).querySelector(".hud"), "Overlay abschaltbar");
assert.ok(!R(make("snapmaker-u1-card", { hide_overlay: true })).querySelector(".hud"), "hide_overlay");
const hid = make("snapmaker-u1-card", { hide: ["system", "maintenance", "timelapse"] });
assert.deepStrictEqual([...R(hid).querySelectorAll("[data-tab]")].map((b) => b.dataset.tab), ["overview", "control", "files", "history"], "hide");

// 3. layout: scroll = alles untereinander, keine Reiter
const scroll = make("snapmaker-u1-card", { layout: "scroll" });
assert.ok(!R(scroll).querySelector(".tabs"));
assert.strictEqual(R(scroll).querySelectorAll(".layout").length, 1);
assert.ok(R(scroll).querySelector(".hud"));

// 4. show begrenzt: ein Reiter => keine Leiste
const single = make("snapmaker-u1-card", { show: ["stage", "job"] });
assert.ok(!R(single).querySelector(".tabs"), "ein Reiter ohne Leiste");

// 5. Mini-Karte
const mini = make("snapmaker-u1-mini-card");
const mt = R(mini).textContent.replace(/\s+/g, " ");
assert.match(mt, /nuss/);
assert.match(mt, /Druckt/);
assert.match(mt, /44 %/);
assert.match(mt, /80 g/, "Spoolman-Rest");
assert.strictEqual(R(mini).querySelector(".mini-g").dataset.low, "1", "Restwarnung");
assert.ok(!R(mini).querySelector("img[data-live]"), "keine Kamera");
assert.ok(R(mini).querySelector('[data-act="power"]'), "Netzschalter");
assert.strictEqual(mini.getCardSize(), 3);
let more = null;
mini.addEventListener("hass-more-info", (e) => { more = e.detail.entityId; });
R(mini).querySelector(".mini-file").click();
assert.strictEqual(more, `sensor.${P}_printer_state`, "Antippen = Statusdialog");
const miniNav = make("snapmaker-u1-mini-card", { navigation_path: "/drucker/0" });
let nav = 0;
w.addEventListener("location-changed", () => { nav++; });
R(miniNav).querySelector(".mini-file").click();
assert.strictEqual(nav, 1);
assert.strictEqual(w.location.pathname, "/drucker/0");

// 6. Visueller Editor
const C = w.customElements.get("snapmaker-u1-card");
const M = w.customElements.get("snapmaker-u1-mini-card");
assert.strictEqual(C.getConfigElement, undefined, "alter Editor entfernt");
const form = C.getConfigForm();
const names = JSON.stringify(form.schema);
for (const n of ["layout", "hide", "hide_overlay", "camera_mode", "prefix"]) assert.ok(names.includes(`"${n}"`), n);
assert.strictEqual(form.computeLabel({ name: "layout" }), "Darstellung");
assert.strictEqual(form.computeLabel({ name: "unbekannt" }), undefined);
assert.ok(JSON.stringify(M.getConfigForm().schema).includes("navigation_path"));
assert.ok(JSON.stringify(M.getConfigForm().schema).includes("hide_filaments"));
const miniHide = make("snapmaker-u1-mini-card", { hide_filaments: true });
assert.ok(!R(miniHide).querySelector(".mini-fil"), "Filamente ausblendbar");
// Mini patcht Prozent ohne Neuaufbau
states[`sensor.${P}_progress`].state = "50.2"; mini.hass = hass();
assert.match(R(mini).textContent.replace(/\s+/g, " "), /50 %/);
states[`sensor.${P}_progress`].state = "43.6";
assert.ok(w.customCards.some((c) => c.type === "snapmaker-u1-mini-card"), "Kartenauswahl");

// 7. Englisch: keine deutschen Reste
lang = "en";
const GERMAN = /[äöüÄÖÜß]|\b(Druck|Drucker|Datei|Dateien|Schicht|Restzeit|Fertig|Bereit|Abbrechen|Licht|Kopf|Köpfe|Leer|Spule|Verlauf|Steuerung|Übersicht|Zeitraffer|Heizung|Lüfter|Geladen|und|oder|nicht|noch|keine?)\b/;
const check = (el, what) => {
  el._renderKey = null; el.hass = hass();
  const t = R(el).textContent.replace(/\s+/g, " ");
  const titles = [...R(el).querySelectorAll("[title],[aria-label]")].map((e) => e.title || e.getAttribute("aria-label")).join(" ");
  const m = (t + " " + titles).replace(/nuss|Generic/g, "").match(GERMAN);
  assert.ok(!m, `${what}: deutscher Rest "${m && m[0]}" in: ${(t + titles).slice(Math.max(0, (m && m.index) - 60), (m && m.index) + 60)}`);
};
for (const tab of ["overview", "control", "files", "history", "timelapse", "system"]) {
  card._tab = tab; check(card, `Reiter ${tab}`);
}
check(mini, "Mini");
assert.match(R(card).textContent, /Overview/);
const fe = C.getConfigForm();
assert.strictEqual(fe.computeLabel({ name: "layout" }), "Layout");
assert.match(JSON.stringify(fe.schema), /"Tabs"/);
// Drucker aus, englisch
states[`sensor.${P}_printer_state`].state = "unavailable";
states[`sensor.${P}_current_print_state`].state = "unavailable";
states["switch.snapmaker_u1_card_netzschalter"].state = "off";
check(card, "aus");
check(mini, "Mini aus");
assert.match(R(card).textContent, /Printer is off/);

console.log("UI 5.2 OK – Reiter, Overlay, Mini-Karte, Editor, Englisch");
