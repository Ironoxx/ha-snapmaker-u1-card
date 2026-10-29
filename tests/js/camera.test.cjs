// 1.5: own camera entity preferred, camera_mode auto, direct stream only with a live camera, hint without camera.
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
let reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
add(`camera.${P}_webcam`, "idle", { entity_picture: "/api/camera_proxy/mr?token=A", access_token: "A" });
add("sensor.snapmaker_u1_card_druckdateien", "0", { entry_id: "E1", files: [], version: "1.6.1",
  stream_url: "http://192.168.0.25/webcam/?action=stream" }, "snapmaker_u1_card", "files");
const OWN = "camera.snapmaker_u1_card_kamera";
add(OWN, "idle", { entity_picture: "/api/camera_proxy/own?token=B", access_token: "B", mode: "wake" }, "snapmaker_u1_card", "camera");

const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" }, callService: async () => {} });
const make = (cfg = {}) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card", ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass();
  c._onScreen = true;
  return c;
};

// own camera wins over the Moonraker camera; default mode auto
let card = make();
assert.strictEqual(card._ents.camera, OWN);
assert.strictEqual(card._ents.ownCamera, OWN);
assert.strictEqual(card._cfg.camera_mode, "auto");
// stock firmware (wake): no direct printer stream, the own proxy stream instead
card._stopStream(); card._tickCamera();
let src0 = card.shadowRoot.querySelector("img[data-live]").getAttribute("src");
assert.match(src0, /camera_proxy_stream\/camera\.snapmaker_u1_card_kamera\?token=B/, src0);

// live camera: direct stream allowed again
states[OWN].attributes.mode = "live";
card = make();
card._stopStream(); card._tickCamera();
assert.strictEqual(card.shadowRoot.querySelector("img[data-live]").getAttribute("src"), "http://192.168.0.25/webcam/?action=stream");

// explicitly configured camera still wins
card = make({ camera: `camera.${P}_webcam` });
assert.strictEqual(card._ents.camera, `camera.${P}_webcam`);
assert.strictEqual(card._ents.ownCamera, null);

// none: no camera frame, hint with the actions
states[OWN].attributes.mode = "none";
states[OWN].state = "unavailable";
card = make();
const R = card.shadowRoot.getElementById("u1card");
assert.ok(!R.querySelector("img[data-live]"), "no camera image");
assert.match(R.querySelector(".no-cam").textContent, /Keine Kamera erkannt/);
assert.ok(R.querySelector('.no-cam [data-act="light"]'), "light button stays");

// without own camera entity (older integration): Moonraker camera as before
delete reg[OWN]; delete states[OWN];
card = make();
assert.strictEqual(card._ents.camera, `camera.${P}_webcam`);
console.log("CAMERA OK – own entity preferred, auto, direct stream only when live, no-camera hint");
