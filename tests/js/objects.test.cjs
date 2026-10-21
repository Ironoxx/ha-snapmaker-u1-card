// Exclude object: outlines in the layer view, chips, confirmation, service call, faded paths.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
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
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "printing");
add(`sensor.${P}_current_layer`, "1");
add(`sensor.${P}_total_layer`, "3");
add("sensor.snapmaker_u1_card_druckdateien", "0", { files: [], entry_id: "E1" }, "snapmaker_u1_card", "files");

const A = "Teil_id_0_copy_0", B = "Teil_id_0_copy_1";
let exclude = {
  objects: [
    { name: A, label: "Teil (1)", center: [20, 20], polygon: [[10, 10], [30, 10], [30, 30], [10, 30]] },
    { name: B, label: "Teil (2)", center: [50, 50], polygon: [[40, 40], [60, 40], [60, 60], [40, 60]] },
  ],
  excluded: [], current: A,
};
const calls = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" },
  callService: async (...a) => { calls.push(a); },
  fetchWithAuth: async (url) => {
    const q = new URL(url, "http://x").searchParams;
    const body = q.get("position") ? { status: "ready", position: 100, layer: 1, exclude }
      : { status: "ready", file: "a.gcode", layer: 1, total: 3, z: 0.2, bbox: [10, 10, 60, 60], tools: [0],
        start: 0, end: 900, segs: [[0, [10, 10, 30, 30], 50, A], [0, [40, 40, 60, 60], 60, B]], colors: {} };
    return { ok: true, status: 200, json: async () => body };
  },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card" });
w.document.body.appendChild(card);
const R = () => card.shadowRoot.getElementById("u1card");
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  card.hass = hass();
  card._onScreen = true;
  await card._tickLayer(); await tick();
  const polys = R().querySelectorAll(".lv-objs polygon");
  assert.strictEqual(polys.length, 2, "outlines drawn");
  assert.ok(polys[0].classList.contains("cur") && polys[1].classList.contains("pick"));
  const chips = R().querySelectorAll(".obj-chip");
  assert.deepStrictEqual([...chips].map((c) => c.textContent.trim()), ["Teil (1)", "Teil (2)"]);

  // tap the outline -> confirmation -> cancel: nothing happens
  polys[1].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await tick();
  let dlg = card.shadowRoot.querySelector("dialog.u1confirm");
  assert.ok(dlg && dlg.hasAttribute("open"));
  assert.match(dlg.textContent, /„Teil \(2\)“ ausschließen\?/);
  dlg.querySelector('[data-cf="no"]').click();
  await tick();
  assert.strictEqual(calls.length, 0);

  // chip -> confirm -> service call, path faded, chip struck through
  R().querySelector(`.obj-chip[data-obj="${B}"]`).click();
  await tick();
  card.shadowRoot.querySelector("dialog.u1confirm [data-cf=\"yes\"]").click();
  await tick(); await tick();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(calls[0].slice(0, 3))),
    ["snapmaker_u1_card", "exclude_object", { name: B, config_entry_id: "E1" }]);
  const lines = R().querySelectorAll("[data-lv] polyline");
  assert.ok(!lines[0].classList.contains("excl") && lines[1].classList.contains("excl"), "excluded path faded");
  const b = R().querySelector(`.obj-chip[data-obj="${B}"]`);
  assert.ok(b.classList.contains("off") && b.disabled);
  // the last remaining object cannot be excluded
  assert.ok(R().querySelector(`.obj-chip[data-obj="${A}"]`).disabled, "last object locked, bed view");

  // one object only: no list, no clickable outline
  exclude = { objects: [exclude.objects[0]], excluded: [], current: A };
  card._lv.at = 0; card._lv.exKey = null;
  await card._tickLayer(); await tick();
  assert.strictEqual(R().querySelector("[data-su1=\"lvobjects\"]").innerHTML, "");
  assert.ok(!R().querySelector(".lv-objs polygon.pick"));
  // bed view: plate, dock with four heads, toggle back and forth (remembered)
  assert.ok(!R().querySelector(".lv-plate"), "part view by default");
  R().querySelector("[data-lvmode]").click();
  await tick();
  assert.ok(R().querySelector(".lv-plate"), "plate drawn");
  assert.strictEqual(R().querySelectorAll(".lv-dock .lv-head").length, 4);
  assert.strictEqual(R().querySelector("[data-lv]").dataset.mode, "bed");
  assert.strictEqual(w.localStorage.getItem("snapmaker-u1-card.layerview"), "bed");
  assert.match(R().querySelector("svg").getAttribute("viewBox"), /^-10\.00 /);
  R().querySelector("[data-lvmode]").click();
  await tick();
  assert.ok(!R().querySelector(".lv-plate"), "back to the part");
  console.log("OBJECTS OK – outlines, chips, confirmation, exclude call, last object locked, bed view");
})().catch((e) => { console.error(e); process.exit(1); });
