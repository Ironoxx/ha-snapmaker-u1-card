// Schichtansicht: Laden je Schicht, Farbe ueber Zuordnung, Fortschritt in der Schicht.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
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
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, i === 0 ? "230" : "215", { min: 0, max: 300 });
const slots = [0, 1, 2, 3].map((i) => ({ index: i, loaded: i !== 1, type: "PLA", color: ["#111111", null, "#FF0000", "#00FF00"][i], colors: [] }));
add("sensor.snapmaker_u1_card_filamente", "3", { slots, entry_id: "E1", active_head: 2 }, "snapmaker_u1_card", "filaments");
add("sensor.snapmaker_u1_card_druckdateien", "0", { files: [], entry_id: "E1" }, "snapmaker_u1_card", "files");

let status = "parsing";
let liveHead = 2;
const requests = [];
const layer = (n) => ({
  status: "ready", file: "a.gcode", layer: n, total: 3, z: 0.2 * n, bbox: [10, 10, 60, 60], tools: [0, 1],
  start: 100, end: 900,
  segs: [[0, [10, 10, 20, 10, 20, 20], 150], [0, [50, 50, 60, 50], 400], [1, [60, 50, 60, 60], 700]],
  // Filament 1 -> Kopf 3 (rot), Filament 2 -> Kopf 2 (leer -> Dateifarbe)
  colors: { file: { 0: "#0000FF", 1: "#ABCDEF" }, map_table: [2, 1, 0, 3] },
});
let lang = "de";
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: lang },
  callService: async () => {},
  fetchWithAuth: async (url) => {
    requests.push(url);
    const q = new URL(url, "http://x").searchParams;
    const body = q.get("position") ? { status, position: 450, layer: 1, active_head: liveHead }
      : status === "ready" ? layer(Number(q.get("layer"))) : { status, file: "a.gcode" };
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
  await tick(); await tick();
  // Aktiver Kopf von der Firmware, nicht der heisseste (E0 hat 230 °C Soll)
  assert.match(R().querySelector(".hud-head").textContent, /Kopf 3/, "Firmware-Kopf statt Heuristik");
  assert.ok(R().querySelector(".lv-panel"), "Panel im Uebersicht-Reiter");
  assert.match(R().querySelector("[data-lv]").textContent, /wird vorbereitet/);
  assert.strictEqual(requests.length, 1);
  // Erneut innerhalb von 5 s: keine weitere Anfrage
  card.hass = hass(); await tick();
  assert.strictEqual(requests.length, 1, "nicht im Sekundentakt nachfragen");

  status = "ready";
  card._lv.at = 0;
  await card._tickLayer(); await tick();
  const lines = R().querySelectorAll("[data-lv] polyline");
  assert.strictEqual(lines.length, 3);
  assert.strictEqual(lines[0].getAttribute("stroke"), "#FF0000", "Kopf 3 geladen: Spulenfarbe");
  assert.strictEqual(lines[2].getAttribute("stroke"), "#ABCDEF", "Kopf 2 leer: Dateifarbe");
  assert.strictEqual(lines[0].getAttribute("points"), "10,-10 20,-10 20,-20", "Y gespiegelt");
  // Position 450: erste zwei gedruckt, dritte folgt
  assert.deepEqual([...lines].map((l) => l.classList.contains("todo")), [false, false, true]);
  // Kopfwechsel kommt mit der Position (alle 5 s), schneller als der Sensor
  liveHead = 3;
  await card._tickLayer(); await tick();
  assert.match(R().querySelector(".hud-head").textContent, /Kopf 4/, "Live-Kopf aus der Position");
  assert.match(R().querySelector('[data-su1="lvhead"]').textContent, /Schicht 1 \/ 3 · Z 0,20 mm/);
  assert.match(R().querySelector(".lv-legend").textContent, /Filament 1 → Kopf 3.*Filament 2 → Kopf 2.*gedruckt.*folgt/);

  // Neue Schicht -> Nachladen; Neuaufbau behaelt das Bild
  states[`sensor.${P}_current_layer`].state = "2";
  card.hass = hass(); await tick(); await tick(); await tick();
  assert.ok(requests.some((u) => /layer=2/.test(u)));
  assert.match(R().querySelector('[data-su1="lvhead"]').textContent, /Schicht 2 \/ 3/);
  card._renderKey = null; card.hass = hass(); await tick();
  assert.strictEqual(R().querySelectorAll("[data-lv] polyline").length, 3, "nach Neuaufbau noch da");

  // Anderer Reiter: keine Anfragen
  const before = requests.length;
  R().querySelector('[data-tab="history"]').click();
  await card._tickLayer(); await tick();
  assert.strictEqual(requests.length, before, "verborgen -> nichts laden");
  R().querySelector('[data-tab="overview"]').click();

  // Englisch
  lang = "en"; card._renderKey = null; card.hass = hass(); await tick();
  assert.match(R().querySelector(".lv-panel").textContent, /Layer view.*Layer 2 \/ 3 · Z 0\.40 mm/s);
  assert.match(R().querySelector(".lv-legend").textContent, /printed.*to do/);

  // Druck vorbei: Panel weg, Zustand verworfen
  states[`sensor.${P}_current_print_state`].state = "complete";
  card.hass = hass(); await tick();
  assert.ok(!R().querySelector(".lv-panel"));
  console.log("SCHICHTANSICHT OK");
})().catch((e) => { console.error(e); process.exit(1); });
