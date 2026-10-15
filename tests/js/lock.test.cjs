// Control lock: nothing changes while scrolling, confirmation during a print.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
let answer = true;
const asked = [];
w.confirm = (m) => { asked.push(m); return answer; };
w.eval(src);
const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}) => { states[id] = { entity_id: id, state, attributes: attrs }; reg[id] = { entity_id: id, platform: "moonraker" }; };
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
add(`number.${P}_bed_target`, "0", { min: 0, max: 120, step: 1 });
const calls = [];
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" },
  callService: async (...a) => { calls.push(a); } });
const make = (cfg = {}) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card", ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass();
  return c;
};
const card = make();
const R = () => card.shadowRoot.getElementById("u1card");
const bedPreset = () => R().querySelector(`[data-set="number.${P}_bed_target"][data-value="55"]`);
const range = () => R().querySelector(`input[data-num="number.${P}_bed_target"]`);

// 1. Default: locked
assert.ok(bedPreset().disabled && range().disabled, "Regler gesperrt");
assert.ok(range().closest(".ctl").classList.contains("locked"));
assert.ok(R().querySelector("[data-act=home_all]").disabled, "Referenzfahrt gesperrt");
assert.strictEqual(R().querySelectorAll("[data-su1-lock]").length, 3, "Schloss an Koepfen, Bett, Bewegung");
bedPreset().click();
assert.strictEqual(calls.length, 0, "gesperrt -> kein Aufruf");

// 2. Unlock: all padlocks at once, sliders free
R().querySelector("[data-su1-lock]").click();
assert.ok(!bedPreset().disabled && !range().disabled);
assert.ok([...R().querySelectorAll("[data-su1-lock]")].every((b) => b.getAttribute("aria-pressed") === "true"));
assert.match(R().querySelector("[data-su1-lock]").textContent, /Entsperrt/);
bedPreset().click();
assert.deepEqual(calls.pop().slice(0, 3), ["number", "set_value", { entity_id: `number.${P}_bed_target`, value: 55 }]);
// Stays unlocked after a rebuild
card._renderKey = null; card.hass = hass();
assert.ok(!bedPreset().disabled, "Neuaufbau behaelt Freigabe");

// 3. Expiry: locked again
card._unlockUntil = Date.now() - 1;
card._applyLock();
assert.ok(bedPreset().disabled, "nach Ablauf gesperrt");

// 4. During a print: confirmation for the target temperature
states[`sensor.${P}_current_print_state`].state = "printing";
card.hass = hass();
R().querySelector("[data-su1-lock]").click();
answer = false;
bedPreset().click();
assert.match(asked.pop(), /Solltemperatur während des Drucks auf 55 °C ändern\?/);
assert.strictEqual(calls.length, 0, "abgelehnt");
answer = true;
bedPreset().click();
assert.strictEqual(calls.pop()[2].value, 55);

// 5. Can be disabled
const free = make({ unlock_controls: true });
const FR = free.shadowRoot.getElementById("u1card");
assert.strictEqual(FR.querySelectorAll("[data-su1-lock]").length, 0);
assert.ok(!FR.querySelector(`[data-set="number.${P}_bed_target"]`).disabled);
const off = make({ controls_lock: "off" });
assert.strictEqual(off.shadowRoot.getElementById("u1card").querySelectorAll("[data-su1-lock]").length, 0, "controls_lock: off");

// 6. Configurable duration
const t0 = Date.now();
const short = make({ controls_lock: "30" });
assert.match(short.shadowRoot.querySelector("[data-su1-lock]").title, /Regler entsperren \(30 s\)/);
short.shadowRoot.querySelector("[data-su1-lock]").click();
assert.ok(short._unlockUntil - t0 >= 30000 && short._unlockUntil - t0 < 31000, "30 s");
const five = make({ controls_lock: 300 });
five._toggleLock();
assert.ok(five._unlockUntil - Date.now() > 299000, "5 min");
const man = make({ controls_lock: "manual" });
assert.strictEqual(man.shadowRoot.querySelector("[data-su1-lock]").title, "Regler entsperren");
man._toggleLock();
assert.strictEqual(man._unlockUntil, Infinity, "bis zum erneuten Sperren");
man._touchLock();
assert.ok(!man._locked());
man._toggleLock();
assert.ok(man._locked(), "manuell wieder gesperrt");
assert.strictEqual(make({})._unlockMs(), 60000, "Standard 1 min");
// The editor offers the choice
const form = w.customElements.get("snapmaker-u1-card").getConfigForm();
assert.match(JSON.stringify(form.schema), /"controls_lock".*"manual"/);
assert.strictEqual(form.computeLabel({ name: "controls_lock" }), "Sperre für Regler");
console.log("CONTROL LOCK OK");
