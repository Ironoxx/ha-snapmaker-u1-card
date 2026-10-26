// WebRTC camera (paxx12): signalling through the integration, video over MJPEG, fallback, zoom, accent colour.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };
w.setInterval = () => 0;

// Minimal RTCPeerConnection: records what the card does
const pcs = [];
w.RTCPeerConnection = class {
  constructor(cfg) { this.cfg = cfg; this.connectionState = "new"; this.transceivers = []; pcs.push(this); }
  addTransceiver(kind, opts) { this.transceivers.push([kind, opts]); }
  async setRemoteDescription(d) { this.remote = d; }
  async createAnswer() { return { type: "answer", sdp: "v=0 answer" }; }
  async setLocalDescription(d) { this.localDescription = d; }
  close() { this.connectionState = "closed"; this.closed = true; }
};
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
add("sensor.snapmaker_u1_card_files", "0", { entry_id: "E1", files: [], version: "x",
  stream_url: "http://192.168.0.25/webcam/stream.mjpg", webrtc: true }, "snapmaker_u1_card", "files");
const OWN = "camera.snapmaker_u1_card_camera";
add(OWN, "idle", { entity_picture: "/api/camera_proxy/own?token=B", access_token: "B", mode: "live" }, "snapmaker_u1_card", "camera");

const api = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" }, callService: async () => {},
  callApi: async (method, p, body) => {
    api.push([method, p, body]);
    if (body.type === "request") return { type: "offer", id: "pc1", sdp: "v=0 offer", iceServers: [] };
    return {};
  },
});
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
  const video = frame().querySelector("video[data-rtc]");
  assert.ok(video, "video element added");
  // MJPEG keeps running while WebRTC connects
  assert.ok(card._streamImg, "MJPEG meanwhile");
  await tick(); await tick(); await tick();
  assert.deepStrictEqual(api.map((a) => [a[0], a[1], a[2].type]), [
    ["POST", "snapmaker_u1_card/webrtc/E1", "request"], ["POST", "snapmaker_u1_card/webrtc/E1", "answer"]]);
  assert.strictEqual(api[1][2].id, "pc1");
  assert.strictEqual(api[1][2].sdp, "v=0 answer");
  const pc = pcs[0];
  assert.strictEqual(JSON.stringify(pc.transceivers[0]), JSON.stringify(["video", { direction: "recvonly" }]));
  assert.strictEqual(pc.remote.sdp, "v=0 offer");
  // ICE candidates of the browser go to the printer
  pc.onicecandidate({ candidate: { toJSON: () => ({ candidate: "candidate:1", sdpMid: "0" }) } });
  await tick();
  assert.strictEqual(api[2][2].type, "remote_candidate");
  assert.strictEqual(JSON.stringify(api[2][2].candidates), JSON.stringify([{ candidate: "candidate:1", sdpMid: "0" }]));

  // plays: video visible, MJPEG stopped
  Object.defineProperty(video, "videoWidth", { value: 1280 });
  Object.defineProperty(video, "videoHeight", { value: 720 });
  video.dispatchEvent(new w.Event("playing"));
  assert.ok(frame().classList.contains("rtc-on"));
  assert.strictEqual(card._streamImg, null, "MJPEG stopped while WebRTC plays");
  assert.strictEqual(frame().style.aspectRatio, "1280 / 720");
  assert.strictEqual(card._tickRtc(frame(), frame().querySelector("img[data-live]")), true);

  // rebuild of the card: the same video moves into the new frame
  card._renderKey = null; card._render();
  card._tickCamera();
  assert.strictEqual(frame().querySelector("video[data-rtc]"), video, "same video after a rebuild");
  assert.ok(frame().classList.contains("rtc-on"));
  // zoom applies to the video too
  Object.assign(card._zoom, { s: 2, x: 0, y: 0 });
  card._applyZoom();
  assert.match(video.style.transform, /scale\(2\)/);

  // connection fails: back to MJPEG, no new attempt for a while
  pc.connectionState = "failed";
  pc.onconnectionstatechange();
  assert.ok(pc.closed && !frame().querySelector("video[data-rtc]"));
  card._tickCamera();
  assert.ok(card._streamImg, "MJPEG again");
  assert.ok(!frame().querySelector("video[data-rtc]"), "no retry right away");
  assert.strictEqual(pcs.length, 1);

  // timeout without a frame
  card = make();
  card._tickCamera();
  card._rtc.started = Date.now() - 9000;
  card._tickCamera();
  assert.strictEqual(card._rtc, null, "timeout -> off");

  // option off, no WebRTC from the printer, second camera: no WebRTC
  const before = pcs.length;
  card = make({ camera_webrtc: "off" }); card._tickCamera();
  assert.ok(!card.shadowRoot.querySelector("video[data-rtc]"));
  states["sensor.snapmaker_u1_card_files"].attributes.webrtc = false;
  card = make(); card._tickCamera();
  assert.ok(!card.shadowRoot.querySelector("video[data-rtc]"));
  await tick();
  assert.strictEqual(pcs.length, before);

  // hidden page stops the connection
  states["sensor.snapmaker_u1_card_files"].attributes.webrtc = true;
  card = make(); card._tickCamera();
  assert.ok(card._rtc);
  card._onScreen = false; card._tickCamera();
  assert.strictEqual(card._rtc, null, "off screen -> closed");

  // accent colour: variables on the card, readable text colour
  card = make({ accent_color: [255, 193, 7] });
  assert.strictEqual(card.style.getPropertyValue("--u1-primary"), "rgb(255, 193, 7)");
  assert.strictEqual(card.style.getPropertyValue("--u1-on-primary"), "#111318");
  card = make({ accent_color: "#1565c0" });
  assert.strictEqual(card.style.getPropertyValue("--u1-on-primary"), "#ffffff");
  card.setConfig({ type: "custom:snapmaker-u1-card" });
  assert.strictEqual(card.style.getPropertyValue("--u1-primary"), "", "removed again");
  const mini = w.document.createElement("snapmaker-u1-mini-card");
  mini.setConfig({ type: "custom:snapmaker-u1-mini-card", accent_color: [0, 200, 83] });
  assert.strictEqual(mini.style.getPropertyValue("--u1-primary"), "rgb(0, 200, 83)");
  const form = w.customElements.get("snapmaker-u1-card").getConfigForm();
  assert.match(JSON.stringify(form.schema), /"accent_color".*"color_rgb"/);
  assert.match(JSON.stringify(form.schema), /"camera_webrtc"/);

  console.log("WEBRTC OK – signalling via HA, MJPEG meanwhile, rebuild, zoom, fallback, timeout, off, accent colour");
  process.exit(0);
})().catch((e) => { console.error(e); process.exit(1); });
