// Feedback for commands: pause/resume/cancel show a waiting state, the light toggles at once,
// switches pulse until confirmed, and the live print state beats the Moonraker integration.
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
const timers = [];
w.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
w.confirm = () => true;
w.alert = () => {};
const toasts = [];
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
add(`light.${P}_led_cavity_led`, "off");
add(`switch.${P}_output_pin_e0_heat_sw`, "off");
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
const slot = (i) => ({ index: i, loaded: true, type: "PLA", sub_type: null, vendor: "Generic",
  color: "#FF0000", colors: [], official: false, rfid: null });
own("sensor.snapmaker_u1_card_filaments", "4", { slots: [0, 1, 2, 3].map(slot), preferences: {}, entry_id: "E1",
  live: true, print_state: "printing" }, "filaments");
own("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [] }, "files");

const calls = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: { ...reg },
  locale: { language: "de" }, language: "de",
  callService: async (...a) => { calls.push(a); return {}; },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", controls_lock: "off", layout: "stack" });
w.document.body.appendChild(card);
card.addEventListener("hass-notification", (e) => toasts.push(e.detail.message));
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const pressed = (name) => calls.some((c) => c[0] === "button" && c[2].entity_id === `button.${P}_${name}`);

// 1. Pause: button turns into "Pausiere …" at once, status too
R().querySelector("[data-act=pause]").click();
assert.ok(pressed("pause_print"), "Pause gesendet");
const wait = R().querySelector("button[aria-busy=true]");
assert.ok(wait && wait.disabled && /Pausiere/.test(wait.textContent), "Pause wartet sichtbar");
assert.ok(!R().querySelector("[data-act=pause]"), "kein zweites Pausieren");
assert.match(R().querySelector("[data-su1=camstate], [data-su1=status]").textContent, /Pausiere/);
// Another poll without change keeps the waiting state
card.hass = hass();
assert.ok(R().querySelector("button[aria-busy=true]"), "wartet weiter");

// 2. The live state (integration) confirms before the Moonraker sensor does
states["sensor.snapmaker_u1_card_filaments"].attributes.print_state = "paused";
card.hass = hass();
assert.ok(!R().querySelector("button[aria-busy=true]"), "bestaetigt -> kein Warten");
assert.ok(R().querySelector("[data-act=resume]"), "Fortsetzen da, obwohl Moonraker noch printing meldet");
assert.match(R().querySelector("[data-su1=camstate], [data-su1=status]").textContent, /Pausiert/);

// 3. Resume, not confirmed in time: hint instead of a silent nothing
R().querySelector("[data-act=resume]").click();
assert.ok(pressed("resume_print"));
assert.match(R().querySelector("button[aria-busy=true]").textContent, /Setze fort/);
card._pending.get("resume").until = Date.now() - 1;
timers.splice(0).forEach((t) => t.fn());
assert.ok(!R().querySelector("button[aria-busy=true]"), "Ablauf beendet Warten");
assert.ok(toasts.some((m) => /Fortsetzen noch nicht/.test(m)), "Hinweis nach Ablauf");

// 4. Light: toggles in the card at once, stays until HA confirms
const light = () => R().querySelector("[data-su1=light]");
assert.ok(!light().classList.contains("on"));
const img = R().querySelector("img[data-live]");
light().click();
assert.ok(calls.some((c) => c[0] === "light" && c[1] === "toggle"));
assert.ok(light().classList.contains("on"), "Licht sofort an");
card.hass = hass(); // poll still says off
assert.ok(light().classList.contains("on"), "bleibt an bis bestaetigt");
assert.strictEqual(R().querySelector("img[data-live]"), img, "kein Neuaufbau (Kamera bleibt)");
states[`light.${P}_led_cavity_led`].state = "on";
card.hass = hass();
assert.ok(light().classList.contains("on") && !card._pending.has("light"));
// Not confirmed: falls back to the real state
light().click();
assert.ok(!light().classList.contains("on"), "sofort aus");
card._pending.get("light").until = Date.now() - 1;
card.hass = hass();
assert.ok(light().classList.contains("on"), "nicht bestaetigt -> echter Zustand");

// 5. Switches pulse until the entity has changed
const sw = () => R().querySelector(`[data-toggle="switch.${P}_output_pin_e0_heat_sw"]`);
if (sw()) {
  sw().click();
  assert.ok(sw().classList.contains("pending"), "Schalter wartet");
  card.hass = hass();
  assert.ok(sw().classList.contains("pending"));
  states[`switch.${P}_output_pin_e0_heat_sw`].state = "on";
  card.hass = hass();
  assert.ok(!sw().classList.contains("pending"), "bestaetigt");
}

// 6. Cancel: waiting state, pause/resume hidden
states["sensor.snapmaker_u1_card_filaments"].attributes.print_state = "printing";
card.hass = hass();
card._cancelPrint();
assert.ok(pressed("cancel_print"));
assert.match(R().querySelector("button[aria-busy=true]").textContent, /Breche ab/);
assert.ok(!R().querySelector("[data-act=pause]"), "kein Pause waehrend Abbruch");
states["sensor.snapmaker_u1_card_filaments"].attributes.print_state = "cancelled";
card.hass = hass();
assert.ok(!R().querySelector("button[aria-busy=true]"));

// 7. Without the live subscription the Moonraker sensor counts
states["sensor.snapmaker_u1_card_filaments"].attributes.live = false;
states["sensor.snapmaker_u1_card_filaments"].attributes.print_state = null;
states[`sensor.${P}_current_print_state`].state = "paused";
card.hass = hass();
assert.ok(R().querySelector("[data-act=resume]"), "Fallback Moonraker");

// 8. Spool restore: head reloaded without spool -> "Wieder #5 …?", one tap
states["sensor.snapmaker_u1_card_filaments"].attributes.spoolman = {
  online: true, spoollink: true, low: 100, slots: { 0: null, 1: null, 2: null, 3: null },
  spools: [{ id: 5, name: "PLA Black", vendor: "GEEETECH", material: "PLA", color: "#000000", remaining_weight: 800 }],
  restore: { 0: { id: 5, name: "PLA Black", vendor: "GEEETECH", material: "PLA", color: "#000000" } },
};
card.hass = hass();
const rb = R().querySelector("[data-spoolrestore='0']");
assert.ok(rb && /Wieder #5 GEEETECH PLA Black\?/.test(rb.textContent), "Vorschlag sichtbar");
assert.ok(R().querySelector(".spool-restore [data-spoolpick='0']"), "andere Spule waehlbar");
rb.click();
assert.ok(calls.some((c) => c[1] === "set_spool" && c[2].slot === 1 && c[2].spool_id === 5), "set_spool gesendet");
assert.ok(R().querySelector("[data-spoolrestore='0']").disabled, "wartet");
states["sensor.snapmaker_u1_card_filaments"].attributes.spoolman.restore = {};
states["sensor.snapmaker_u1_card_filaments"].attributes.spoolman.slots[0] = { id: 5, name: "PLA Black", manual: true, remaining_weight: 800, initial_weight: 1000 };
card.hass = hass();
assert.ok(!R().querySelector("[data-spoolrestore]"), "uebernommen");

console.log("FEEDBACK OK – pause, resume, cancel, light, switches, live state, spool restore");
process.exit(0);
