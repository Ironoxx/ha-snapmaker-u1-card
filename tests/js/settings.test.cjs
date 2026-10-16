// Head details (RFID data, editing the filament), printer settings in the system tab and the state accent.
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
add(`sensor.${P}_current_print_state`, "standby");
add(`camera.${P}_webcam`, "idle", { entity_picture: "/api/camera_proxy/cam?token=A", access_token: "A" });
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
const RFID = { official: true, vendor: "Snapmaker", manufacturer: "Polymaker", sku: 900001, weight_g: 1000, length_m: 330,
  diameter_mm: 1.75, nozzle_temp: [190, 230], first_layer_temp: 220, other_layer_temp: 210, bed_temp: 60,
  drying_temp: 55, drying_time_h: 8, manufactured: "2025-08-12" };
const slots = [
  { index: 0, loaded: true, type: "PLA", sub_type: "Matte", vendor: "Snapmaker", color: "#1C1C1C", colors: ["#1C1C1C"], official: true, rfid: RFID },
  { index: 1, loaded: true, type: "PETG", sub_type: null, vendor: "Generic", color: "#ECEFF1", colors: ["#ECEFF1"], official: false, rfid: null },
  { index: 2, loaded: false, type: null, sub_type: null, vendor: null, color: null, colors: [], official: false, rfid: null },
  { index: 3, loaded: false, type: null, sub_type: null, vendor: null, color: null, colors: [], official: false, rfid: null },
];
const prefs = { bed_leveling: false, flow_calibration: false, timelapse: false, auto_replenish: true,
  replenish_ignore_color: false, entangle_detect: true, end_led_off: false, entangle_sensitivity: "medium" };
own("sensor.snapmaker_u1_card_filamente", "2", { slots, preferences: prefs, entry_id: "E1" }, "filaments");
own("sensor.snapmaker_u1_card_druckdateien", "0", { entry_id: "E1", files: [] }, "files");

let lang = "de";
const calls = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg,
  locale: { language: lang }, language: lang,
  callService: async (...a) => { calls.push(a); },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const D = () => card.shadowRoot.getElementById("u1dlg");
const flush = () => new Promise((r) => setTimeout(r, 0));
// Objects from the jsdom realm: compare as plain JSON
const plain = (v) => JSON.parse(JSON.stringify(v));

(async () => {
  // 1. Printer settings in the system tab
  const chip = (k) => R().querySelector(`[data-prefset="${k}"]`);
  assert.strictEqual(chip("auto_replenish").getAttribute("aria-pressed"), "true");
  assert.strictEqual(chip("end_led_off").getAttribute("aria-pressed"), "false");
  assert.ok(R().querySelector('[data-prefsen="medium"]').classList.contains("sel"), "sensitivity shown with detection on");
  chip("auto_replenish").click();
  await flush();
  assert.deepStrictEqual(plain(calls.pop().slice(0, 3)), ["snapmaker_u1_card", "set_preference",
    { preference: "auto_replenish", value: false, config_entry_id: "E1" }]);
  R().querySelector('[data-prefsen="high"]').click();
  await flush();
  assert.strictEqual(calls.pop()[2].value, "high");
  // A changed preference rebuilds the row
  states["sensor.snapmaker_u1_card_filamente"].attributes.preferences = { ...prefs, entangle_detect: false };
  card.hass = hass();
  assert.ok(!R().querySelector("[data-prefsen]"), "no sensitivity without detection");
  // Old firmware without these fields: no settings block
  states["sensor.snapmaker_u1_card_filamente"].attributes.preferences = { bed_leveling: false };
  card.hass = hass();
  assert.ok(!R().querySelector("[data-prefset]"), "hidden on old firmware");
  states["sensor.snapmaker_u1_card_filamente"].attributes.preferences = prefs;
  card.hass = hass();

  // Camera: state in the corner, no dimmed overlay while idle; visible edit button
  const camState = R().querySelector(".cam-state");
  assert.ok(camState && /Bereit/.test(camState.textContent), "state pill on the camera");
  assert.strictEqual(R().querySelector(".frame").dataset.dim, "0", "idle camera not dimmed");
  assert.ok(!R().querySelector(".frame .overlay"), "no idle overlay");
  assert.match(R().querySelector('[data-headinfo="0"]').textContent, /Filament/);

  // 2. Head details with RFID data
  R().querySelector('[data-headinfo="0"]').click();
  const dlg = D().querySelector("dialog.u1head");
  assert.ok(dlg && dlg.hasAttribute("open"), "dialog open");
  const text = dlg.textContent.replace(/\s+/g, " ");
  assert.match(text, /Spulengewicht\s*1000 g/);
  assert.match(text, /Düsentemperatur\s*190–230 °C/);
  assert.match(text, /Trocknen\s*55 °C · 8 h/);
  assert.match(text, /SKU\s*900001/);
  assert.ok(dlg.querySelector('input[name="force"]'), "force option for an official spool");
  // Submit: set_filament with the form values
  const form = dlg.querySelector("[data-headform]");
  form.querySelector('select[name="type"]').value = "PETG";
  form.querySelector('input[name="sub_type"]').value = " HF ";
  form.querySelector('input[name="color"]').value = "#ff0000";
  form.querySelector('input[name="force"]').checked = true;
  form.dispatchEvent(new w.Event("submit", { cancelable: true }));
  await flush();
  const call = calls.pop();
  assert.deepStrictEqual(plain(call.slice(0, 3)), ["snapmaker_u1_card", "set_filament", {
    slot: 1, type: "PETG", sub_type: "HF", vendor: "Snapmaker", color: "#ff0000", force: true, config_entry_id: "E1" }]);
  assert.ok(!dlg.hasAttribute("open"), "closes after success");

  // Head without tag: no RFID block, no force option
  R().querySelector('[data-headinfo="1"]').click();
  assert.ok(!/Spulengewicht/.test(D().querySelector("dialog.u1head").textContent));
  assert.ok(!D().querySelector('dialog.u1head input[name="force"]'));

  // 3. During a print: form disabled; state accent on the frame
  states[`sensor.${P}_current_print_state`].state = "printing";
  card.hass = hass();
  assert.strictEqual(R().dataset.accent, "active", "accent while printing");
  assert.strictEqual(R().querySelector(".cam-state").dataset.tone, "active");
  R().querySelector('[data-headinfo="1"]').click();
  assert.ok(D().querySelector('dialog.u1head button[type="submit"]').disabled, "no editing during a print");
  states[`sensor.${P}_current_print_state`].state = "paused";
  card.hass = hass();
  assert.strictEqual(R().dataset.accent, "warn");
  card.setConfig({ type: "custom:snapmaker-u1-card", state_accent: false });
  card.hass = hass();
  assert.ok(!R().dataset.accent, "accent can be turned off");
  states[`sensor.${P}_current_print_state`].state = "standby";

  // 4. English: no German leftovers in the new parts
  lang = "en";
  card.setConfig({ type: "custom:snapmaker-u1-card" });
  card.hass = hass();
  const GERMAN = /[äöüÄÖÜß]|\b(Drucker|Kopf|Spule|Farbe|Hersteller|Unterart|Übernehmen|Einstellungen|Empfindlichkeit|Niedrig|Mittel|Hoch|nachfüllen|Licht|und|oder|nicht)\b/;
  const sys = [...R().querySelectorAll(".rows")].map((e) => e.textContent).join(" ");
  R().querySelector('[data-headinfo="0"]').click();
  const dlgText = D().querySelector("dialog.u1head").textContent;
  const all = (sys + " " + dlgText).replace(/\s+/g, " ").replace(/Snapmaker|Polymaker|Matte/g, "");
  const m = all.match(GERMAN);
  assert.ok(!m, `German leftover "${m && m[0]}" in: ${all.slice(Math.max(0, (m && m.index) - 60), (m && m.index) + 60)}`);
  assert.match(all, /Spool weight\s*1000 g/);
  console.log("SETTINGS OK – printer settings, head details, filament edit, state accent, English");
})().catch((e) => { console.error(e); process.exit(1); });
