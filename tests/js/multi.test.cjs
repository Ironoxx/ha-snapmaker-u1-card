// 2.4.1 (#19): several U1 – each card shows one printer (option device), never a mix;
// the editor offers the printers with their address.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.eval(src);

const reg = {}, states = {};
const own = (id, state, attrs, tk, dev) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform: "snapmaker_u1_card", translation_key: tk, device_id: dev };
};
// printer 1 was set up first; its entities come first in the registry
const printer = (n, dev, entry, file) => {
  own(`sensor.u1_${n}_druckdateien`, "1", { entry_id: entry, files: [{ path: file, name: file.replace(".gcode", ""), modified: 1, filaments: [] }] }, "files", dev);
  own(`sensor.u1_${n}_filamente`, "4", { entry_id: entry, preferences: {}, slots: [0, 1, 2, 3].map((i) => ({ index: i, loaded: true, type: n === 1 ? "PLA" : "PETG", colors: [] })) }, "filaments", dev);
  own(`sensor.u1_${n}_warteschlange`, "0", { entry_id: entry, jobs: [] }, "queue", dev);
};
printer(1, "dev1", "E1", "eins.gcode");
printer(2, "dev2", "E2", "zwei.gcode");
const devices = {
  dev1: { id: "dev1", name: "Snapmaker U1 (192.168.1.50)", name_by_user: null, configuration_url: "http://192.168.1.50" },
  dev2: { id: "dev2", name: "Snapmaker U1 Card", name_by_user: "Werkstatt", configuration_url: "http://192.168.1.51" },
};
const calls = [];
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, devices, user: { is_admin: true },
  callService: async (...a) => { calls.push(a); }, callWS: async () => ({}) });

const make = (cfg) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card", show: ["files"], ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass();
  return c;
};

(async () => {
  // without device: the first printer, all of its entities
  const a = make({});
  assert.strictEqual(a._ents.files, "sensor.u1_1_druckdateien");
  assert.strictEqual(a._ents.filaments, "sensor.u1_1_filamente");
  assert.strictEqual(a._entryData().config_entry_id, "E1");
  // device: only that printer
  const b = make({ device: "dev2" });
  assert.deepStrictEqual([b._ents.files, b._ents.filaments, b._ents.queue],
    ["sensor.u1_2_druckdateien", "sensor.u1_2_filamente", "sensor.u1_2_warteschlange"]);
  assert.strictEqual(b._entryData().config_entry_id, "E2", "Dienste gehen an den gewählten Drucker");
  assert.deepStrictEqual(b._d.files.map((f) => f.path), ["zwei.gcode"], "nur Dateien des zweiten Druckers");
  // a registry where printer 2 comes first for one key must still not mix
  delete reg["sensor.u1_1_warteschlange"];
  const c = make({});
  assert.strictEqual(c._ents.queue, null, "keine Warteschlange vom anderen Drucker");
  // mini card follows the same option
  const m = w.document.createElement("snapmaker-u1-mini-card");
  m.setConfig({ type: "custom:snapmaker-u1-mini-card", device: "dev2" });
  w.document.body.appendChild(m);
  m.hass = hass();
  assert.strictEqual(m._ents.filaments, "sensor.u1_2_filamente");

  // editor: printer choice with address, only with more than one printer
  const ha = w.document.createElement("home-assistant");
  ha.hass = hass();
  w.document.body.appendChild(ha);
  const Card = w.customElements.get("snapmaker-u1-card");
  const form = Card.getConfigForm();
  const dev = form.schema.find((s) => s.name === "device");
  assert.ok(dev && dev.selector.select, "Druckerwahl im Editor");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(dev.selector.select.options.map((o) => o.label))), ["Snapmaker U1 (192.168.1.50)", "Werkstatt · 192.168.1.51"], "Adresse nur, wenn sie nicht schon im Namen steht");
  assert.strictEqual(form.computeLabel({ name: "device" }), "Drucker");
  assert.ok(w.customElements.get("snapmaker-u1-mini-card").getConfigForm().schema.some((s) => s.name === "device"));
  assert.ok(w.customElements.get("snapmaker-u1-section-card").getConfigForm().schema.some((s) => s.name === "device"));
  // one printer: no choice offered
  for (const id of Object.keys(reg)) if (reg[id].device_id === "dev2") delete reg[id];
  ha.hass = hass();
  assert.ok(!Card.getConfigForm().schema.some((s) => s.name === "device"), "ein Drucker: keine Auswahl");
  console.log("MULTI PRINTER OK");
})().catch((e) => { console.error(e); process.exit(1); });
