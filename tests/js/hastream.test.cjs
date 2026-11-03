// 2.0: away from home (Nabu Casa) the camera plays RTSP through Home Assistant (ha-camera-stream)
// instead of MJPEG through the proxy; no direct WebRTC attempt there; fallback and option off.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "https://abcdef.ui.nabu.casa/lovelace/0", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };
w.setInterval = () => 0;
let pcs = 0;
w.RTCPeerConnection = class { constructor() { pcs++; } };
// HA's stream element (normally loaded by the frontend)
// counts detaches: HA's real player closes its stream session on disconnect
w.eval(`customElements.define("ha-camera-stream", class extends HTMLElement {
  disconnectedCallback() { window.__hsGone = (window.__hsGone || 0) + 1; } })`);
w.eval(src);

const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add("sensor.snapmaker_u1_printer_state", "ready");
add("sensor.snapmaker_u1_current_print_state", "standby");
add("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [], webrtc: true,
  stream_url: "http://192.168.0.25/webcam/stream.mjpg" }, "snapmaker_u1_card", "files");
const CAM = "camera.snapmaker_u1_card_camera";
add(CAM, "streaming", { entity_picture: "/api/camera_proxy/x?token=T", access_token: "T", mode: "live",
  supported_features: 2 }, "snapmaker_u1_card", "camera");
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" },
  callService: async () => ({}), callApi: async () => ({}) });
const make = (cfg = {}) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card", ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass();
  c._onScreen = true;
  return c;
};
const tick = () => new Promise((r) => setTimeout(r, 0));

(async () => {
  let card = make();
  const frame = () => card.shadowRoot.querySelector(".stage .frame");
  card._tickCamera();
  await tick(); await tick();
  assert.strictEqual(pcs, 0, "Nabu Casa: kein direkter WebRTC-Versuch");
  const el = frame().querySelector("ha-camera-stream[data-hastream]");
  assert.ok(el, "HA-Stream-Element eingesetzt");
  assert.strictEqual(el.stateObj.entity_id, CAM);
  assert.strictEqual(el.muted, true);
  assert.strictEqual(el.controls, false);
  assert.ok(card._streamImg, "MJPEG bis zum ersten Bild");
  // first frame
  el.dispatchEvent(new w.Event("load"));
  assert.ok(frame().classList.contains("rtc-on"));
  assert.strictEqual(card._streamImg, null, "MJPEG gestoppt");
  card._tickCamera();
  assert.strictEqual(card._tickHaStream(frame(), frame().querySelector("img[data-live]"), card._st(CAM)), true);
  // rebuild: same element moves into the new frame
  card._renderKey = null; card._render();
  card._tickCamera();
  assert.strictEqual(frame().querySelector("[data-hastream]"), el, "gleiches Element nach Neuaufbau");
  assert.ok(!w.__hsGone, "Stream-Element bleibt beim Neuaufbau im Dokument (keine neue Sitzung)");
  assert.ok(frame().classList.contains("rtc-on"), "rtc-on bleibt");
  assert.ok(frame().querySelector('[data-zoom="in"]'), "Zoom-Knöpfe neu aufgebaut");
  // a structural change around the camera (pause overlay) also keeps it
  states["sensor.snapmaker_u1_current_print_state"].state = "paused"; card.hass = hass();
  assert.strictEqual(frame().querySelector("[data-hastream]"), el);
  assert.ok(frame().querySelector(".overlay"), "Pause-Overlay im alten Rahmen");
  assert.ok(!w.__hsGone, "auch bei Pause kein Abbau");
  states["sensor.snapmaker_u1_current_print_state"].state = "standby"; card.hass = hass();
  // hidden page stops it
  card._onScreen = false; card._tickCamera();
  assert.ok(!card._hs && !frame().querySelector("[data-hastream]"), "aus bei verdeckter Karte");

  // no first frame in time: MJPEG for a while
  card = make();
  card._tickCamera(); await tick(); await tick();
  card._hs.started = Date.now() - 20000;
  card._tickCamera();
  assert.ok(!card._hs && card._hsFailUntil > Date.now(), "Zeitüberschreitung -> MJPEG");

  // option off, camera without RTSP: never
  card = make({ camera_ha_stream: "off" }); card._tickCamera(); await tick(); await tick();
  assert.ok(!card.shadowRoot.querySelector("[data-hastream]"));
  states[CAM].attributes.supported_features = 0;
  card = make(); card._tickCamera(); await tick(); await tick();
  assert.ok(!card.shadowRoot.querySelector("[data-hastream]"), "ohne RTSP (Stock-Firmware) wie bisher");
  assert.match(JSON.stringify(w.customElements.get("snapmaker-u1-card").getConfigForm().schema), /"camera_ha_stream"/);

  console.log("HA STREAM OK – Nabu Casa without direct WebRTC, RTSP via HA, MJPEG meanwhile, rebuild, timeout, off, no RTSP");
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
