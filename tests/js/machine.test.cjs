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
let settingsReply = { response: { settings: { layer_height: 0.2, first_layer_height: 0.25, walls: 3, top_layers: 5,
  bottom_layers: 3, infill: 15, infill_pattern: "gyroid", support: true, support_type: "tree(auto)", support_build_plate_only: true,
  brim: "auto_brim", brim_width: 5, plate: "Textured PEI Plate", nozzle_temp: [220, 250], nozzle_temp_first: [225, 250],
  bed_temp: [65, 70], bed_temp_first: [65, 70], profile: "0.20mm Standard @Snapmaker U1" } } };
let reply = { response: { script: "M105", ok: true, error: null, responses: ["ok T0:21.0 /0.0"] } };
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: { ...reg },
  locale: { language: lang }, language: lang,
  callService: async (...a) => { calls.push(a); if (a[1] === "file_settings") return settingsReply; if (a[1] === "send_gcode" || a[1] === "weigh_spool") { if (reply instanceof Error) throw reply; return reply; } return {}; },
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

  // 5b. Nozzle per head: shown in the head dialog, mismatch warned in the print dialog
  const fil = states["sensor.snapmaker_u1_card_filaments"].attributes;
  fil.slots[0].nozzle = { diameter: 0.4, type: "standard" };
  fil.slots[1].nozzle = { diameter: 0.6, type: "high_flow" };
  states["sensor.snapmaker_u1_card_files"].attributes.files = [{ path: "teil.gcode", name: "teil", modified: 1,
    filaments: [{ index: 0, type: "PLA", color: "#FF0000", used: true, weight: 5, nozzle: 0.4 },
                { index: 1, type: "PLA", color: "#FF0000", used: true, weight: 5, nozzle: 0.4 }] }];
  card.hass = hass();
  card._openHeadInfo(1);
  assert.ok(D().textContent.includes("Düse 0.6 mm") && D().textContent.includes("High Flow"), "Düse im Kopf-Dialog");
  D().querySelector("dialog.u1head").removeAttribute("open");
  card._openPrint("teil.gcode");
  card._dlg.map = { 0: 0, 1: 1 };
  card._renderDialog();
  assert.ok(D().textContent.includes("Düse passt nicht: Datei 0.4 mm, Kopf 0.6 mm"), "Düsenwarnung");
  // 5b'. Slicer settings of the file (inspector)
  await flush(); await flush();
  assert.ok(calls.some((c) => c[1] === "file_settings" && c[2].path === "teil.gcode" && c[5] === true), "file_settings mit Antwort");
  const set = D().querySelector("[data-settings]");
  assert.ok(set, "Einstellungsbereich");
  const st = set.textContent.replace(/\s+/g, " ");
  assert.ok(st.includes("Schichthöhe") && st.includes("0,20 mm · erste 0,25 mm"), st);
  assert.ok(st.includes("3 Wände · oben 5 · unten 3") && st.includes("15 % · Gyroid"), st);
  assert.ok(st.includes("an · Baum (automatisch) · nur vom Bett") && st.includes("Textured PEI Plate"), st);
  assert.ok(st.includes("Düse 220 (225) °C · Bett 65 °C") && st.includes("Düse 250 °C · Bett 70 °C"), st);
  assert.match(set.querySelector("summary").textContent, /0,20 mm · 15 % · Stützen/);
  // stays open across a re-render, cached for the next opening
  set.open = true; set.dispatchEvent(new w.Event("toggle"));
  card._renderDialog();
  assert.ok(D().querySelector("[data-settings]").open);
  card._closeDialog();
  const n = calls.filter((c) => c[1] === "file_settings").length;
  card._openPrint("teil.gcode");
  assert.strictEqual(calls.filter((c) => c[1] === "file_settings").length, n, "aus dem Cache");
  assert.ok(D().querySelector("[data-settings]").textContent.includes("Gyroid"));
  card._closeDialog();

  // 5c. Spoolman: weigh form in the head dialog, before -> after in the history
  fil.spoolman = { online: true, slots: { 0: { id: 5, name: "Black", remaining_weight: 270, spool_weight: 200, manual: true } },
    spools: [], external_booking: true, books: false, spoollink: true };
  card.hass = hass();
  card._openHeadInfo(0);
  const wf = D().querySelector("[data-weigh]");
  assert.ok(wf && D().textContent.includes("200 g werden abgezogen"), "Wiegen mit Leerspule");
  assert.ok(D().textContent.includes("Den Verbrauch bucht Moonraker"), "Hinweis: Moonraker bucht");
  reply = { response: { spool_id: 5, remaining_weight: 542, before: 270 } };
  wf.querySelector("[name=weight]").value = "742";
  wf.dispatchEvent(new w.Event("submit", { cancelable: true }));
  await flush(); await flush();
  const wcall = calls.filter((c) => c[1] === "weigh_spool").pop();
  assert.deepStrictEqual(plain(wcall[2]), { slot: 1, weight: 742, gross: true, config_entry_id: "E1" });
  // spool picker: no "automatic" with SpoolLink
  card._openSpoolPicker(0);
  assert.ok(!D().querySelector('[data-pick="auto"]') && D().textContent.includes("SpoolLink"), "SpoolLink-Auswahl");
  D().querySelector("dialog.u1spool").removeAttribute("open");
  own("sensor.snapmaker_u1_card_print_history", "1", { prints: [{ name: "Teil", file: "teil.gcode", ended: "2026-10-26T10:00:00",
    result: "complete", spools: [{ slot: 0, spool_id: 5, grams: 90, booked: "moonraker", before: 550, after: 460 }] }] }, "history");
  card.hass = hass();
  card._selectTab("history");
  assert.ok(R().textContent.includes("#5 550 g → 460 g"), "vorher/nachher in der Historie");
  card._selectTab("control");

  // 5d. Second camera: switch button, swaps the camera entity
  own("camera.snapmaker_u1_card_camera_2", "idle", { entity_picture: "/api/camera_proxy/camera.snapmaker_u1_card_camera_2?token=B",
    access_token: "B", mode: "live" }, "camera2");
  card.hass = hass();
  card._selectTab("overview");
  const sw = R().querySelector("[data-camswitch]");
  assert.ok(sw, "Kamera-Umschalter");
  sw.click();
  assert.strictEqual(card._ents.camera, "camera.snapmaker_u1_card_camera_2");
  R().querySelector("[data-camswitch]").click();
  assert.notStrictEqual(card._ents.camera, "camera.snapmaker_u1_card_camera_2");
  card._selectTab("control");

  // 5e. Chamber heater panel (DragonBreath), only with the entity
  assert.ok(!R().textContent.includes("Kammerheizung"), "kein Panel ohne Heizung");
  own("sensor.snapmaker_u1_card_chamber_heater", "41.3", { target: 50, power: 62, filter: false, label: "DragonBreath", min: 0, max: 75 }, "chamber_heater");
  own("number.snapmaker_u1_card_chamber_heater_target", "50", { min: 0, max: 75, step: 1 }, "chamber_target");
  own("switch.snapmaker_u1_card_chamber_heater_filter", "off", {}, "chamber_filter");
  card.hass = hass();
  card._selectTab("control");
  assert.ok(R().textContent.includes("Kammerheizung") && R().textContent.includes("DragonBreath"), "Panel");
  assert.ok(R().querySelector('input[data-num="number.snapmaker_u1_card_chamber_heater_target"]'), "Regler");
  R().querySelector('[data-toggle="switch.snapmaker_u1_card_chamber_heater_filter"]').click();
  assert.deepStrictEqual(plain(calls.pop().slice(0, 3)), ["switch", "toggle", { entity_id: "switch.snapmaker_u1_card_chamber_heater_filter" }]);

  // 6. English
  lang = "en";
  card.hass = hass();
  const text = R().textContent;
  for (const de of ["Flussrate", "Bettnivellierung", "G-Code-Konsole", "Höchster (mm)", "Kammerheizung", "Heizleistung", "Kamera wechseln"]) assert.ok(!text.includes(de), `Deutsch übrig: ${de}`);
  assert.ok(text.includes("G-code console") && text.includes("Flow"), "Englisch");

  console.log("MACHINE OK – flow, bed mesh, top cover, console, head change, English");
})().catch((e) => { console.error(e); process.exit(1); });
