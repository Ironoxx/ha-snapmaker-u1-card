// 2.0: settings of the integration in the card – admins only, fields from the websocket, save only changed sections.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/lovelace/0", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.confirm = () => true;
if (!w.CSS) w.CSS = {};
w.CSS.escape = w.CSS.escape || ((v) => String(v).replace(/["\\]/g, "\\$&"));
w.eval(src);

const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add("sensor.snapmaker_u1_printer_state", "ready");
add("sensor.snapmaker_u1_current_print_state", "standby");
add("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [] }, "snapmaker_u1_card", "files");
add("switch.drucker", "on", { friendly_name: "Drucker-Steckdose" }, "shelly");
add("sensor.drucker_leistung", "85", { friendly_name: "Leistung", device_class: "power", unit_of_measurement: "W" }, "shelly");
add("sensor.temperatur", "21", { device_class: "temperature" }, "x");

const META = {
  title: "Snapmaker U1 (192.168.0.25)", spoolman: true, spoolman_prices: { PLA: 18 },
  sections: {
    power: { name: "Strom und Verbrauch", description: "Jeder Schalter geht" },
    filament: { name: "Filamentpreise", description: "" },
    notify: { name: "Benachrichtigungen", description: "" },
    maintenance: { name: "Wartung", description: "" },
  },
  fields: [
    { key: "power_switch", section: "power", type: "entity", domains: ["switch", "light", "input_boolean"], label: "Netzschalter", help: "Für den Ein/Aus-Knopf" },
    { key: "power_sensor", section: "power", type: "entity", domains: ["sensor"], device_class: "power", label: "Leistung", help: "" },
    { key: "auto_off", section: "power", type: "boolean", required: true, default: false, label: "Auto-Aus", help: "" },
    { key: "auto_off_temp", section: "power", type: "number", required: true, default: 50, min: 30, max: 100, step: 1, unit: "°C", label: "Temp", help: "" },
    { key: "price_pla", section: "filament", type: "number", min: 0, max: 500, step: 0.01, unit: "€/kg", label: "PLA", help: "" },
    { key: "price_petg", section: "filament", type: "number", min: 0, max: 500, step: 0.01, unit: "€/kg", label: "PETG", help: "" },
    { key: "notify_events", section: "notify", type: "select", multiple: true, required: true, options: ["complete", "error"], option_labels: { complete: "Fertig", error: "Fehler" }, label: "Ereignisse", help: "" },
    { key: "maint_plate", section: "maintenance", type: "number", required: true, default: 30, min: 0, max: 5000, unit: "h", label: "Druckplatte reinigen (Druckstunden)" },
    { key: "maint_m_plate", section: "maintenance", type: "number", required: true, default: 1, min: 0, max: 36, unit: "mo", label: "Druckplatte reinigen (Monate)" },
  ],
  values: { power: { power_switch: "switch.drucker", auto_off: true, auto_off_temp: 50 }, filament: { price_petg: 25 },
    notify: { notify_events: ["complete"] }, maintenance: {} },
};

const ws = [];
let admin = true;
let setReply = { changed: true };
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" }, language: "de",
  user: { is_admin: admin }, callService: async () => ({}),
  callWS: async (m) => {
    ws.push(JSON.parse(JSON.stringify(m)));
    if (m.type.endsWith("/get")) return JSON.parse(JSON.stringify(META));
    if (setReply instanceof Error) throw setReply;
    return setReply;
  },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", layout: "stack" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const D = () => card.shadowRoot.querySelector("dialog.u1settings");
const tick = () => new Promise((r) => setTimeout(r, 0));
const toasts = [];
card.addEventListener("hass-notification", (e) => toasts.push(e.detail.message));

(async () => {
  // 1. Button only for admins
  assert.ok(R().querySelector("[data-act=settings]"), "Knopf fuer Admins");
  admin = false; card._renderKey = null; card.hass = hass();
  assert.ok(!R().querySelector("[data-act=settings]"), "kein Knopf ohne Admin");
  admin = true; card._renderKey = null; card.hass = hass();

  // 2. Opens, loads fields with entry and language
  R().querySelector("[data-act=settings]").click();
  await tick(); await tick();
  assert.deepStrictEqual(ws[0], { type: "snapmaker_u1_card/settings/get", language: "de", entry_id: "E1" });
  assert.ok(D().hasAttribute("open"));
  const secs = [...D().querySelectorAll("details.cfg-sec")].map((d) => d.dataset.sec);
  assert.deepStrictEqual(secs, ["power", "filament", "notify", "maintenance"]);
  // summaries
  assert.match(D().querySelector('[data-sec="power"] summary').textContent, /Drucker-Steckdose · Auto-Aus/);
  assert.match(D().querySelector('[data-sec="filament"] summary').textContent, /Spoolman: 1 Material · PETG 25,00/);
  // entity with current value, datalist filtered by device class
  assert.match(D().querySelector('[data-now="power.power_switch"]').textContent, /Drucker-Steckdose: an/);
  const dl = [...D().querySelectorAll("#dl-power_sensor option")].map((o) => o.value);
  assert.deepStrictEqual(dl, ["sensor.drucker_leistung"]);
  // Spoolman price as hint at PLA
  const pla = D().querySelector('[data-set="filament.price_pla"]');
  assert.strictEqual(pla.placeholder, "18,00");
  assert.match(pla.closest(".cfg-ctl").textContent, /Spoolman: 18,00 €\/kg – hat Vorrang/);
  // maintenance as a table: hours and months
  const mrow = D().querySelectorAll(".cfg-maint")[1];
  assert.match(mrow.textContent, /Druckplatte reinigen/);
  assert.ok(!/Druckstunden\)/.test(mrow.textContent));
  assert.strictEqual(mrow.querySelectorAll("input").length, 2);
  assert.ok(D().querySelector("[data-save]").disabled, "nichts geaendert");

  // 3. Change: power sensor, auto-off temp, PETG cleared, event added
  const set = (sel, v) => { const el = D().querySelector(sel); if (el.type === "checkbox") el.checked = v; else el.value = v; el.dispatchEvent(new w.Event("change", { bubbles: true })); };
  set('[data-set="power.power_sensor"]', "sensor.drucker_leistung");
  assert.match(D().querySelector('[data-now="power.power_sensor"]').textContent, /Leistung: 85 W/);
  set('[data-set="power.auto_off_temp"]', "45");
  set('[data-set="filament.price_petg"]', "");
  set('[data-set="notify.notify_events"] input[value="error"]', true);
  assert.ok(!D().querySelector("[data-save]").disabled);
  assert.ok(D().querySelector('[data-sec="power"] .cfg-dot'), "Abschnitt markiert");
  D().querySelector("[data-save]").click();
  await tick();
  const sent = ws.at(-1);
  assert.strictEqual(sent.type, "snapmaker_u1_card/settings/set");
  assert.deepStrictEqual(Object.keys(sent.values).sort(), ["filament", "notify", "power"], "nur geaenderte Abschnitte");
  assert.deepStrictEqual(sent.values.power, { power_switch: "switch.drucker", auto_off: true, auto_off_temp: 45, power_sensor: "sensor.drucker_leistung" });
  assert.deepStrictEqual(sent.values.filament, { price_petg: null });
  assert.deepStrictEqual(sent.values.notify.notify_events, ["complete", "error"]);
  assert.ok(!D().hasAttribute("open"), "zu nach dem Speichern");
  assert.ok(toasts.some((t) => /gespeichert/.test(t)));

  // 4. Validation error stays in the dialog
  setReply = Object.assign(new Error("Automatisches Ein/Aus braucht einen Netzschalter."), { code: "auto_needs_switch" });
  R().querySelector("[data-act=settings]").click();
  await tick(); await tick();
  set('[data-set="power.power_switch"]', "");
  D().querySelector("[data-save]").click();
  await tick();
  assert.ok(D().hasAttribute("open"));
  assert.match(D().querySelector(".cfg-foot .dlg-error").textContent, /Netzschalter/);
  // discard
  D().querySelector("[data-discard]").click();
  assert.strictEqual(D().querySelector('[data-set="power.power_switch"]').value, "switch.drucker");
  assert.ok(D().querySelector("[data-save]").disabled);

  console.log("SETTINGS DIALOG OK – admin only, fields, context, save changed sections, errors, discard");
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
