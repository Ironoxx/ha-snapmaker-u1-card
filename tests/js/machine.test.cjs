// Machine controls: flow slider, bed mesh heatmap, top cover panel, G-code console and picking/parking heads.
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
w.confirm = () => true;
w.alert = () => {};
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
add(`number.${P}_speed_factor`, "100", { min: 10, max: 200, step: 1 });
for (let i = 0; i < 4; i++) add(`number.${P}_extruder${["", "1", "2", "3"][i]}_target`, "0", { min: 0, max: 300, step: 1 });
const slot = (i, loaded) => ({ index: i, loaded, type: loaded ? "PLA" : null, sub_type: null, vendor: "Generic",
  color: loaded ? "#FF0000" : null, colors: [], official: false, rfid: null });
own("sensor.snapmaker_u1_card_filaments", "2", { slots: [slot(0, true), slot(1, true), slot(2, false), slot(3, false)],
  preferences: {}, entry_id: "E1", head_states: ["parked", "active", "parked", "parked"] }, "filaments");
own("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [] }, "files");
own("number.snapmaker_u1_card_flow", "100", { min: 50, max: 150, step: 1 }, "flow_factor");
own("sensor.snapmaker_u1_card_bed_mesh_spread", "0.2", {
  profile: "default", mesh_min: [5, 5], mesh_max: [265, 265], rows: 3, cols: 3,
  matrix: [[0.1, 0.05, -0.02], [0.0, -0.04, -0.1], [0.08, 0.02, -0.06]], min: -0.1, max: 0.1, mean: 0.0,
}, "bed_mesh");

let lang = "de";
const calls = [];
let reply = { response: { script: "M105", ok: true, error: null, responses: ["ok T0:21.0 /0.0"] } };
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: { ...reg },
  locale: { language: lang }, language: lang,
  callService: async (...a) => { calls.push(a); if (a[1] === "send_gcode") { if (reply instanceof Error) throw reply; return reply; } return {}; },
});
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", controls_lock: "off" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const D = () => card.shadowRoot.getElementById("u1dlg");
const flush = () => new Promise((r) => setTimeout(r, 0));
const plain = (v) => JSON.parse(JSON.stringify(v));

(async () => {
  // 1. Flow slider next to speed, own entity
  const flow = R().querySelector('input[data-num="number.snapmaker_u1_card_flow"]');
  assert.ok(flow, "Flussrate-Regler");
  assert.strictEqual(flow.min, "50");
  assert.ok(R().querySelector('[data-set="number.snapmaker_u1_card_flow"][data-value="95"]'), "Voreinstellung 95 %");

  // 2. Bed mesh: one cell per point, front row at the bottom, values in the cells
  const svg = R().querySelector(".mesh-svg");
  assert.ok(svg, "Heatmap");
  const vals = [...svg.querySelectorAll(".mesh-val")].map((t) => t.textContent);
  assert.strictEqual(vals.length, 9);
  // Row 0 (front, Y min) is drawn last at the bottom: its first value has the largest y
  const ys = [...svg.querySelectorAll(".mesh-val")].map((t) => parseFloat(t.getAttribute("y")));
  assert.ok(ys[0] > ys[8], "vorne unten");
  assert.deepStrictEqual(vals.slice(0, 3), ["+0.10", "+0.05", "−0.02"]);
  assert.ok(R().textContent.includes("0,200") || R().textContent.includes("0.200"), "Spanne");
  // Without mesh: hint instead of the heatmap
  const keep = states["sensor.snapmaker_u1_card_bed_mesh_spread"];
  states["sensor.snapmaker_u1_card_bed_mesh_spread"] = { ...keep, state: "unknown", attributes: {} };
  card.hass = hass();
  assert.ok(!R().querySelector(".mesh-svg") && R().textContent.includes("Kein Höhenprofil"), "Hinweis ohne Mesh");
  states["sensor.snapmaker_u1_card_bed_mesh_spread"] = keep;
  card.hass = hass();

  // 3. No top cover entity: no panel; with one: mode, filter hours and fan sliders
  assert.ok(!R().textContent.includes("Top Cover"), "kein Top-Cover-Panel ohne Abdeckung");
  own("sensor.snapmaker_u1_card_top_cover", "cool", { exhaust: 60, inner: 0, inner_rpm: 2411, filter_hours: 2.0, desired_temp: 42 }, "top_cover");
  own("number.snapmaker_u1_card_top_cover_exhaust_fan", "60", { min: 0, max: 100, step: 5 }, "top_cover_exhaust");
  own("number.snapmaker_u1_card_top_cover_circulation_fan", "0", { min: 0, max: 100, step: 5 }, "top_cover_inner");
  card.hass = hass();
  assert.ok(R().textContent.includes("Top Cover") && R().textContent.includes("Kammer kühlen"), "Top-Cover-Panel");
  assert.ok(R().querySelector('input[data-num="number.snapmaker_u1_card_top_cover_exhaust_fan"]'), "Abluftregler");
  assert.ok(R().querySelector('[data-su1="cvfilter"]').textContent.includes("2,0") || R().querySelector('[data-su1="cvfilter"]').textContent.includes("2.0"));
  // Cover unplugged: panel disappears again
  states["sensor.snapmaker_u1_card_top_cover"].state = "unavailable";
  card.hass = hass();
  assert.ok(!R().querySelector('[data-su1="cvmode"]'), "Panel weg ohne Abdeckung");

  // 4. Console: send, show the printer's answer, arrow key history
  const inp = R().querySelector("[data-conin]");
  inp.value = "M105";
  R().querySelector("[data-conform]").dispatchEvent(new w.Event("submit", { cancelable: true }));
  await flush(); await flush();
  const sent = calls.find((c) => c[1] === "send_gcode");
  assert.deepStrictEqual(plain(sent[2]), { script: "M105", config_entry_id: "E1" });
  assert.strictEqual(sent[5], true, "Antwort angefordert");
  assert.ok(R().querySelector("[data-conlog]").textContent.includes("ok T0:21.0"), "Antwort sichtbar");
  // Refusal (e.g. locked during a print) appears as an error line
  reply = new Error("Während des Drucks gesperrt: G28");
  inp.value = "G28";
  R().querySelector("[data-conform]").dispatchEvent(new w.Event("submit", { cancelable: true }));
  await flush(); await flush();
  assert.ok(R().querySelector(".con-err").textContent.includes("G28"), "Fehler sichtbar");
  inp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowUp" }));
  assert.strictEqual(inp.value, "G28");
  inp.dispatchEvent(new w.KeyboardEvent("keydown", { key: "ArrowUp" }));
  assert.strictEqual(inp.value, "M105");
  // The log survives a rebuild
  states[`sensor.${P}_current_print_state`].state = "printing";
  card.hass = hass();
  assert.ok(R().querySelector("[data-conlog]").textContent.includes("M105"), "Verlauf bleibt");
  assert.ok(R().textContent.includes("Während des Drucks nur Feineinstellungen"), "Hinweis im Druck");
  states[`sensor.${P}_current_print_state`].state = "standby";
  card.hass = hass();

  // 5. Head dialog: head 2 is on the carriage -> park, head 1 in the dock -> pick
  card._openHeadInfo(1);
  let btn = D().querySelector("[data-headchange]");
  assert.strictEqual(btn.dataset.headchange, "park");
  assert.ok(D().textContent.includes("Auf dem Schlitten"));
  btn.click();
  await flush(); await flush();
  let tc = calls.filter((c) => c[1] === "tool_change").pop();
  assert.deepStrictEqual(plain(tc[2]), { head: 2, action: "park", config_entry_id: "E1" });
  card._openHeadInfo(0);
  btn = D().querySelector("[data-headchange]");
  assert.strictEqual(btn.dataset.headchange, "pick");
  btn.click();
  await flush(); await flush();
  tc = calls.filter((c) => c[1] === "tool_change").pop();
  assert.deepStrictEqual(plain(tc[2]), { head: 1, action: "pick", config_entry_id: "E1" });
  // During a print: locked
  states[`sensor.${P}_current_print_state`].state = "printing";
  card.hass = hass();
  card._openHeadInfo(0);
  assert.ok(D().querySelector("[data-headchange]").disabled, "Kopfwechsel im Druck gesperrt");
  states[`sensor.${P}_current_print_state`].state = "standby";

  // 6. English
  lang = "en";
  card.hass = hass();
  const text = R().textContent;
  for (const de of ["Flussrate", "Bettnivellierung", "G-Code-Konsole", "Höchster (mm)"]) assert.ok(!text.includes(de), `Deutsch übrig: ${de}`);
  assert.ok(text.includes("G-code console") && text.includes("Flow"), "Englisch");

  console.log("MACHINE OK – flow, bed mesh, top cover, console, head change, English");
})().catch((e) => { console.error(e); process.exit(1); });
