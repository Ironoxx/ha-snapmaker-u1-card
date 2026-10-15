// Funktionstest der Karte in jsdom: Autoerkennung, LED ohne Neuaufbau,
// Kamera-<img> ueberlebt Neuaufbau, Druckdialog mit Zuordnung.
const fs = require("fs");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const path = require("path");
const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open"); this.dispatchEvent(new w.Event("close"));
};
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
const observers = [];
w.IntersectionObserver = class { constructor(cb) { this.cb = cb; observers.push(this); } observe() {} disconnect() {} };
w.eval(src);

const P = "mannerhort_u1";
const reg = {};
const states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
add(`light.${P}_led_cavity_led`, "off");
add(`camera.${P}_thumbnail`, "idle", {});
add(`camera.${P}_webcam`, "idle", { entity_picture: "/api/camera_proxy/cam?token=A", access_token: "A" });
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
const slots = [
  { index: 0, loaded: true, type: "PETG", sub_type: "HF", vendor: "Snapmaker", color: "#1C1C1C", colors: ["#1C1C1C"], official: true },
  { index: 1, loaded: true, type: "PLA", sub_type: null, vendor: "Generic", color: "#ECEFF1", colors: ["#ECEFF1"], official: false },
  { index: 2, loaded: true, type: "PLA", sub_type: "Silk", vendor: "Generic", color: "#D32F2F", colors: ["#D32F2F", "#FBC02D"], official: false },
  { index: 3, loaded: false, type: null, sub_type: null, vendor: null, color: null, colors: [], official: false },
];
add("sensor.snapmaker_u1_card_filamente", "3",
  { slots, preferences: { bed_leveling: true, flow_calibration: false, timelapse: false }, entry_id: "E1" },
  "snapmaker_u1_card", "filaments");
const files = [{
  path: "sub/benchy.gcode", name: "benchy", modified: 1, time: 3600, weight: 21.4, thumb: "/snapmaker_u1_card/thumbs/E1/x.png",
  filaments: [
    { index: 0, type: "PLA", color: "#FFFFFF", name: "Generic PLA", weight: 12.0, used: true },
    { index: 1, type: "PLA", color: "#FF0000", name: "Generic PLA", weight: 9.4, used: true },
    { index: 2, type: "PETG", color: "#000000", name: "x", weight: 0, used: false },
  ],
}];
add("sensor.snapmaker_u1_card_druckdateien", "1", { files, entry_id: "E1" }, "snapmaker_u1_card", "files");
add("sensor.snapmaker_u1_card_werkzeugwechsel", "12345", {
  heads: [0, 1, 2, 3].map((i) => ({ index: i, switches: [6000, 4000, 2000, 345][i], retries: 0, errors: 0, since_maintenance: [23000, 10, 10, 10][i] })),
  maintenance_threshold: 25100,
}, "snapmaker_u1_card", "tool_changes");
add("sensor.snapmaker_u1_card_werkzeugwechsel_druck", "87",
  { in_progress: false, file: "a.gcode", result: "complete", last_switches: 87 }, "snapmaker_u1_card", "tool_changes_print");

const calls = [];
let failNext = null;
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)),
  entities: reg,
  callService: async (...a) => { calls.push(a); if (failNext) { const e = failNext; failNext = null; throw e; } },
});

const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card" });
w.document.body.appendChild(card);
card.hass = hass();
const root = () => card.shadowRoot.getElementById("u1card");

// 1. Autoerkennung
assert.strictEqual(card._ents.prefix, P, "Praefix");
assert.strictEqual(card._ents.camera, `camera.${P}_webcam`, "Kamera");
assert.strictEqual(card._ents.filaments, "sensor.snapmaker_u1_card_filamente");
assert.strictEqual(card._ents.files, "sensor.snapmaker_u1_card_druckdateien");

// 2. Live-Filamente in den Koepfen
const mats = [...root().querySelectorAll(".head-mat")].map((e) => e.textContent);
assert.deepStrictEqual(mats, ["PETG HF", "PLA", "PLA Silk", "Leer"], "Materialien");
assert.ok(root().querySelector(".rfid"), "RFID-Badge");
assert.strictEqual(root().querySelectorAll(".spool")[2].querySelectorAll('circle[stroke-dasharray]').length, 2, "Mehrfarbenring");

// 2b. Werkzeugwechsel in der Statistik
const txt = () => [...root().querySelectorAll(".row")].map((r) => `${r.querySelector(".k").textContent} ${r.querySelector(".v").textContent}`).join(" | ").replace(/\s+/g, " ");
assert.ok(/Werkzeugwechsel gesamt 12\.345/.test(txt()), "Wechsel gesamt");
assert.ok(/Wechsel letzter Druck 87 \(fertig\)/.test(txt()), "Wechsel letzter Druck");
assert.ok(/Wechsel je Kopf 1: 6\.000 · 2: 4\.000 · 3: 2\.000 · 4: 345/.test(txt()), "je Kopf");
assert.ok(/Seit Wartung \(max\.\) 23\.000 \/ 25\.100/.test(txt()), "Wartung");
// Laufender Druck: Beschriftung wechselt, Zahl wird gepatcht
states["sensor.snapmaker_u1_card_werkzeugwechsel_druck"] = { entity_id: "x", state: "3", attributes: { in_progress: true, file: "b.gcode" } };
card.hass = hass();
assert.ok(/Wechsel aktueller Druck 3/.test(txt()), "aktueller Druck");
const k2 = card._renderKey;
states["sensor.snapmaker_u1_card_werkzeugwechsel_druck"].state = "4";
states["sensor.snapmaker_u1_card_werkzeugwechsel"].state = "12346";
card.hass = hass();
assert.strictEqual(card._renderKey, k2, "Zaehler ohne Neuaufbau");
assert.ok(/Wechsel aktueller Druck 4/.test(txt()) && /12\.346/.test(txt()), "gepatcht");

// 3. LED: kein Neuaufbau, Kamerabild bleibt dasselbe Element
const img = root().querySelector("img[data-live]");
img.setAttribute("src", "/api/camera_proxy_stream/x");
const key = card._renderKey;
states[`light.${P}_led_cavity_led`].state = "on";
card.hass = hass();
assert.strictEqual(card._renderKey, key, "LED darf keinen Neuaufbau ausloesen");
assert.ok(root().querySelector('[data-su1="light"]').classList.contains("on"), "Licht-Knopf gepatcht");

// 4. Strukturwechsel: Bild-Element wird uebernommen, nicht neu verbunden
states["sensor.snapmaker_u1_card_druckdateien"].attributes.files = [...files, { ...files[0], path: "b.gcode", name: "b", modified: 2 }];
card.hass = hass();
assert.notStrictEqual(card._renderKey, key, "Neuaufbau erwartet");
assert.strictEqual(root().querySelector("img[data-live]"), img, "img-Element muss erhalten bleiben");
assert.strictEqual(img.getAttribute("src"), "/api/camera_proxy_stream/x", "Stream nicht neu gesetzt");
states["sensor.snapmaker_u1_card_druckdateien"].attributes.files = files;
card.hass = hass();

// 4b. Kein Stream im Bearbeitungsmodus und ausserhalb des Bildbereichs
const live = () => root().querySelector("img[data-live]");
const isStream = () => /camera_proxy_stream/.test(live().getAttribute("src") || "");
card._stopStream(); card._streamFailUntil = 0;
card._tickCamera();
assert.ok(isStream(), "Stream startet normal");
card.preview = true;
assert.ok(!isStream(), "Bearbeitungsmodus beendet Stream");
card._tickCamera();
assert.ok(!isStream(), "kein Stream im Bearbeitungsmodus");
card.editMode = false;
card._tickCamera();
assert.ok(isStream(), "Stream nach Bearbeitungsmodus wieder an");
observers.at(-1).cb([{ isIntersecting: false }]);
assert.ok(!isStream(), "weggescrollt beendet Stream");
card._tickCamera();
assert.ok(!isStream(), "kein Stream ausserhalb des Bildbereichs");
observers.at(-1).cb([{ isIntersecting: true }]);
assert.ok(isStream(), "sichtbar: Stream wieder an");

// 5. Druckdialog
root().querySelector('[data-print="sub/benchy.gcode"]').click();
const dlg = () => card.shadowRoot.querySelector("dialog.u1dlg");
assert.ok(dlg() && dlg().hasAttribute("open"), "Dialog offen");
assert.strictEqual(dlg().querySelectorAll(".map-row").length, 2, "nur genutzte Filamente");
// Vorschlag: weiss PLA -> Slot 1 (weisses PLA), rot PLA -> Slot 2 (rotes Silk-PLA)
assert.deepStrictEqual({ ...card._dlg.map }, { 0: 1, 1: 2 }, "Vorschlag");
const printBtn = () => dlg().querySelector('[data-dlg="print"]');
assert.ok(printBtn().disabled, "ohne Bestaetigung gesperrt");
// Filament 2 von Hand auf Slot 0 (PETG) -> Warnung, aber erlaubt
dlg().querySelector('[data-map="1"][data-slot="0"]').click();
assert.ok(/Material weicht ab/.test(dlg().textContent), "Warnung Materialabweichung");
// Leerer Slot blockiert
dlg().querySelector('[data-map="1"][data-slot="3"]').click();
const conf = dlg().querySelector("[data-confirm]");
conf.checked = true; conf.dispatchEvent(new w.Event("change"));
assert.ok(printBtn().disabled, "leerer Slot muss blockieren");
dlg().querySelector('[data-map="1"][data-slot="2"]').click();
assert.ok(!printBtn().disabled, "jetzt freigegeben");
// Fehlerpfad
failNext = { message: "Printer is busy, cannot start print" };
printBtn().click();
return new Promise((r) => setTimeout(r, 0)).then(async () => {
  assert.ok(/Printer is busy/.test(dlg().textContent), "Fehler im Dialog");
  const [dom_, svc, data, target, notify] = calls.at(-1);
  assert.strictEqual(dom_, "snapmaker_u1_card"); assert.strictEqual(svc, "start_print");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(data)), {
    filename: "sub/benchy.gcode", bed_leveling: true, flow_calibration: false, timelapse: false,
    config_entry_id: "E1", mapping: { 0: 1, 1: 2 },
  });
  assert.strictEqual(notify, false, "kein doppelter Toast");
  // Erfolgspfad
  printBtn().click();
  await new Promise((r) => setTimeout(r, 0));
  assert.ok(!dlg().hasAttribute("open"), "Dialog nach Erfolg zu");
  assert.strictEqual(card._dlg, null);
  console.log("ALLE TESTS OK –", calls.length, "Dienstaufrufe");
});
