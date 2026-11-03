// 2.0: the card without the Moonraker integration – values from the integration's machine sensor,
// controls through the machine_command service. Moonraker entities, if present, are only the fallback.
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
w.setTimeout = () => 0;
w.confirm = () => true;
w.alert = () => {};
w.eval(src);

const reg = {}, states = {};
const own = (id, state, attrs, tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform: "snapmaker_u1_card", translation_key: tk };
};
const values = {
  printer_state: "ready", current_print_state: "printing", progress: 42.5, filename: "dog.gcode",
  current_layer: 12, total_layer: 80, print_duration: 30,
  bed_temperature: 60.2, bed_target: 60, extruder_temperature: 219.6, extruder_target: 220,
  extruder1_temperature: 25, extruder1_target: 0, cavity_temp: 31.4,
  fan_speed: 50, speed_factor: 100, led_cavity_led: "off", output_pin_e0_heat_sw: "off",
};
const attrs = {
  bed_target: { min: 0, max: 120, step: 1, unit_of_measurement: "°C" },
  extruder_target: { min: 0, max: 300, step: 1, unit_of_measurement: "°C" },
  extruder1_target: { min: 0, max: 300, step: 1, unit_of_measurement: "°C" },
  speed_factor: { min: 10, max: 300, step: 1, unit_of_measurement: "%" },
  fan_speed: { min: 0, max: 100, step: 1, unit_of_measurement: "%" },
  led_cavity_led: { brightness: 0 },
};
own("sensor.snapmaker_u1_card_printer_values", "ready", { values, attrs, entry_id: "E1" }, "machine");
const slot = (i) => ({ index: i, loaded: i < 2, type: i < 2 ? "PLA" : null, sub_type: null, vendor: "Generic",
  color: "#FF0000", colors: [], official: false, rfid: null });
own("sensor.snapmaker_u1_card_filaments", "2", { slots: [0, 1, 2, 3].map(slot), preferences: {}, entry_id: "E1" }, "filaments");
own("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [] }, "files");

const calls = [];
let services = { snapmaker_u1_card: { machine_command: {} } };
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: { ...reg }, services,
  locale: { language: "de" }, language: "de",
  callService: async (...a) => { calls.push(a); return {}; },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", controls_lock: "off", layout: "stack" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const last = () => calls[calls.length - 1];
const plain = (v) => JSON.parse(JSON.stringify(v));

// 1. Values come from the machine sensor (no Moonraker entity exists)
const d = card._d;
assert.ok(d.online, "online ohne Moonraker-Integration");
assert.ok(d.active, "Druck aktiv");
assert.strictEqual(Math.round(d.progress), 43);
assert.strictEqual(d.layer, 12);
assert.ok(!/nicht erreichbar/.test(R().textContent), "kein Offline-Hinweis");
assert.ok(R().textContent.includes("dog"), "Dateiname");
const bed = card._st("number.snapmaker_u1_card_bed_target") || card._st("number.snapmaker_u1_bed_target");
assert.strictEqual(bed.state, "60");
assert.strictEqual(bed.attributes.max, 120, "Regler-Bereich aus attrs");
assert.strictEqual(card._st("sensor.snapmaker_u1_bed_target"), card._st("sensor.snapmaker_u1_bed_target"), "stabiles Objekt");
assert.strictEqual(card._st("sensor.snapmaker_u1_nothing"), undefined, "unbekannter Schlüssel");

// 2. Controls go to machine_command
R().querySelector("[data-act=pause]").click();
assert.deepStrictEqual(plain(last()), ["snapmaker_u1_card", "machine_command", { action: "pause", config_entry_id: "E1" }]);
card._setNumber("number.snapmaker_u1_bed_target", "65");
assert.deepStrictEqual(plain(last()), ["snapmaker_u1_card", "machine_command",
  { action: "set", target: "bed_target", value: 65, config_entry_id: "E1" }]);
card._press("home_x_axis");
assert.deepStrictEqual(plain(last()).slice(2), [{ action: "home", target: "x", config_entry_id: "E1" }]);
card._toggleLight();
assert.deepStrictEqual(plain(last()).slice(2), [{ action: "switch", target: "led_cavity_led", value: true, config_entry_id: "E1" }]);
card._toggleEntity("switch.snapmaker_u1_output_pin_e0_heat_sw");
assert.deepStrictEqual(plain(last()).slice(2), [{ action: "switch", target: "output_pin_e0_heat_sw", value: true, config_entry_id: "E1" }]);
// a slider from the machine values is rendered
assert.ok(R().querySelector('input[data-num="number.snapmaker_u1_extruder_target"]'), "Düsen-Regler");

// 3. Own values beat a Moonraker entity of the same name
states["sensor.snapmaker_u1_printer_state"] = { entity_id: "sensor.snapmaker_u1_printer_state", state: "shutdown", attributes: {} };
reg["sensor.snapmaker_u1_printer_state"] = { entity_id: "sensor.snapmaker_u1_printer_state", platform: "moonraker" };
card.hass = hass();
assert.strictEqual(card._st("sensor.snapmaker_u1_printer_state").state, "ready", "eigene Werte zuerst");

// 4. Machine sensor unavailable (printer off): falls back to the Moonraker entities
states["sensor.snapmaker_u1_card_printer_values"] = { entity_id: "sensor.snapmaker_u1_card_printer_values", state: "unavailable", attributes: {} };
card.hass = hass();
assert.strictEqual(card._st("sensor.snapmaker_u1_printer_state").state, "shutdown", "Rückfall Moonraker");

// 5. Older backend without the service: old entity services
states["sensor.snapmaker_u1_card_printer_values"] = { entity_id: "sensor.snapmaker_u1_card_printer_values", state: "ready", attributes: { values, attrs, entry_id: "E1" } };
services = {};
card.hass = hass();
card._press("cancel_print");
assert.deepStrictEqual(plain(last()), ["button", "press", { entity_id: "button.snapmaker_u1_cancel_print" }]);

// 6. Stepper temperatures appear once the motors are on (null before): the row is added
const sys = () => card.shadowRoot.querySelector("[data-su1=stepx]");
card.setConfig({ type: "custom:snapmaker-u1-card", controls_lock: "off", layout: "stack" });
card.hass = hass();
assert.ok(!sys(), "keine Zeile ohne Wert");
values.stepper_x_temp = 41;
values.stepper_y_temp = 39;
card.hass = hass();
assert.ok(sys() && /41/.test(sys().textContent), "Zeile erscheint nach Referenzfahrt");
values.cpu_temp = 48.3;
card.hass = hass();
assert.match(card.shadowRoot.querySelector("[data-su1=cputemp]").textContent, /48,3/, "CPU-Temperatur im System-Reiter");
delete values.stepper_x_temp; delete values.stepper_y_temp;
card.hass = hass();
assert.ok(!sys(), "Motoren aus: Zeile weg");

console.log("STANDALONE OK – values from the integration, machine_command, priority, fallback");
process.exit(0);
