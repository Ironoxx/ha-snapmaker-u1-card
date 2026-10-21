// 1.3.0: emergency stop modes and confirm dialog, tablet layout, camera wake-up, version notice.
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
let nativeConfirm = 0;
w.confirm = () => { nativeConfirm++; return true; };
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "printing");
add(`sensor.${P}_filename`, "teil.gcode");
add(`camera.${P}_webcam`, "idle", { entity_picture: "/api/camera_proxy/cam?token=A", access_token: "A" });
add("sensor.snapmaker_u1_card_druckdateien", "0", { entry_id: "E1", files: [], version: "1.4.2" }, "snapmaker_u1_card", "files");

add("switch.snapmaker_u1_card_fortschritt", "off", { targets: ["notify.mobile_app_handy"], sent_today: 4, budget: 150 },
  "snapmaker_u1_card", "live_notify");
const calls = [];
const ws = [];
const hass = () => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg,
  callWS: async (m) => { ws.push(m); return { path: `${m.path}?authSig=X` }; },
  services: { snapmaker_u1_card: { camera_wake: {} } },
  locale: { language: "de" }, language: "de",
  callService: async (...a) => { calls.push(a); },
});
const make = (cfg = {}) => {
  const card = w.document.createElement("snapmaker-u1-card");
  card.setConfig({ type: "custom:snapmaker-u1-card", ...cfg });
  w.document.body.appendChild(card);
  card.hass = hass();
  return card;
};
const flush = () => new Promise((r) => setTimeout(r, 0));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const pressed = (name) => calls.some((c) => c[0] === "button" && c[2].entity_id === `button.${P}_${name}`);

(async () => {
  // 1. Default: emergency stop visible, own dialog instead of window.confirm
  let card = make();
  let R = card.shadowRoot.getElementById("u1card");
  let btn = R.querySelector("[data-estop]");
  assert.ok(btn && btn.dataset.estop === "show", "emergency stop shown by default");
  btn.click();
  let dlg = card.shadowRoot.querySelector("dialog.u1confirm");
  assert.ok(dlg && dlg.hasAttribute("open"), "confirm dialog open");
  assert.match(dlg.textContent, /Not-Halt auslösen\?/);
  dlg.querySelector('[data-cf="no"]').click();
  await flush();
  assert.ok(!pressed("emergency_stop"), "cancel does not trigger");
  assert.ok(!dlg.hasAttribute("open"), "dialog closed");
  btn.click();
  dlg.querySelector('[data-cf="yes"]').click();
  await flush();
  assert.ok(pressed("emergency_stop"), "OK triggers");
  // Backdrop click = cancel
  calls.length = 0;
  btn.click();
  dlg.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await flush();
  assert.ok(!pressed("emergency_stop"), "backdrop cancels");
  assert.strictEqual(nativeConfirm, 0, "no window.confirm");

  // Cancel print uses the same dialog
  const cancel = R.querySelector('[data-act="cancel"]');
  assert.ok(cancel, "cancel button while printing");
  {
    cancel.click();
    dlg = card.shadowRoot.querySelector("dialog.u1confirm");
    assert.match(dlg.textContent, /Druck wirklich abbrechen\?/);
    dlg.querySelector('[data-cf="yes"]').click();
    await flush();
    assert.ok(pressed("cancel_print"), "cancel print after confirm");
    assert.strictEqual(nativeConfirm, 0);
  }

  // 2. Hidden
  card = make({ emergency_stop: "hide" });
  R = card.shadowRoot.getElementById("u1card");
  assert.ok(!R.querySelector("[data-estop]") && !R.querySelector(".danger-zone"), "hidden");

  // 3. Hold: short press does nothing, 1 s hold triggers without a dialog
  calls.length = 0;
  card = make({ emergency_stop: "hold" });
  R = card.shadowRoot.getElementById("u1card");
  btn = R.querySelector('[data-estop="hold"]');
  assert.ok(btn, "hold button");
  btn.dispatchEvent(new w.Event("pointerdown"));
  await sleep(300);
  btn.dispatchEvent(new w.Event("pointerup"));
  await sleep(900);
  assert.ok(!pressed("emergency_stop"), "short press ignored");
  btn.dispatchEvent(new w.Event("pointerdown"));
  assert.ok(btn.classList.contains("holding"));
  await sleep(1100);
  assert.ok(pressed("emergency_stop"), "hold triggers");
  assert.ok(!card.shadowRoot.querySelector("dialog.u1confirm[open]"), "no dialog in hold mode");

  // 4. Tablet layout: camera and job in the side column, rest as tabs
  card = make({ layout: "tablet" });
  R = card.shadowRoot.getElementById("u1card");
  const side = R.querySelector(".tablet-side");
  assert.ok(side && side.querySelector(".stage"), "camera in the side column");
  assert.ok(!R.querySelector(".tablet-main .stage"), "camera not in the tabs");
  assert.ok(R.querySelector(".tablet-main [data-tab]"), "tabs in the main column");
  const tabs = [...R.querySelectorAll(".tablet-main [data-tab]")].map((t) => t.dataset.tab);
  assert.ok(tabs.includes("overview"), "toolheads keep the overview tab");

  // 5. Camera wake-up: rate limited, only with the service present
  calls.length = 0;
  card._wakeCamera();
  card._wakeCamera();
  const wakes = calls.filter((c) => c[1] === "camera_wake");
  assert.strictEqual(wakes.length, 1, "one call within 10 s");
  assert.deepStrictEqual(JSON.parse(JSON.stringify(wakes[0][2])), { config_entry_id: "E1" });
  card = make({ camera_wake: false });
  calls.length = 0;
  card._wakeCamera();
  assert.ok(!calls.some((c) => c[1] === "camera_wake"), "camera_wake: false");

  // 6. Version notice: integration newer → reload hint; older → restart hint
  assert.ok(!card.shadowRoot.querySelector("[data-reload]"), "no notice when equal");
  states["sensor.snapmaker_u1_card_druckdateien"].attributes.version = "9.0.0";
  card = make();
  R = card.shadowRoot.getElementById("u1card");
  assert.match(R.textContent, /Veraltete Karte im Browser-Cache/);
  assert.ok(R.querySelector("[data-reload]"), "reload button");
  states["sensor.snapmaker_u1_card_druckdateien"].attributes.version = "1.0.0";
  card = make();
  R = card.shadowRoot.getElementById("u1card");
  assert.match(R.textContent, /Neustart von Home Assistant nötig/);
  assert.ok(!R.querySelector("[data-reload]"));

  // 7. Direct stream: printer URL on an http page, HA proxy after an error
  states["sensor.snapmaker_u1_card_druckdateien"].attributes.version = "1.4.2";
  states["sensor.snapmaker_u1_card_druckdateien"].attributes.stream_url = "http://192.168.0.25/webcam/?action=stream";
  card = make();
  card._onScreen = true;
  const live = () => card.shadowRoot.querySelector("img[data-live]");
  card._stopStream();
  card._tickCamera();
  assert.strictEqual(live().getAttribute("src"), "http://192.168.0.25/webcam/?action=stream", "direct stream first");
  live().onerror();
  card._tickCamera();
  assert.match(live().getAttribute("src"), /camera_proxy_stream/, "proxy after a failed direct stream");
  card._stopStream();
  card._tickCamera();
  assert.match(live().getAttribute("src"), /camera_proxy_stream/, "stays on the proxy for a while");
  // No first frame in time: proxy as well
  card._directFailUntil = 0;
  card._stopStream();
  card._tickCamera();
  assert.ok(card._streamDirect);
  card._streamStart -= 5000;
  card._tickCamera();
  card._tickCamera();
  assert.match(live().getAttribute("src"), /camera_proxy_stream/, "timeout falls back to the proxy");
  // camera_direct: off
  card = make({ camera_direct: "off" });
  card._onScreen = true;
  card._stopStream();
  card._tickCamera();
  assert.match(card.shadowRoot.querySelector("img[data-live]").getAttribute("src"), /camera_proxy_stream/, "off: proxy");
  // Own URL
  card = make({ camera_direct_url: "http://u1.lan:8080/stream" });
  card._onScreen = true;
  card._stopStream();
  card._tickCamera();
  assert.strictEqual(card.shadowRoot.querySelector("img[data-live]").getAttribute("src"), "http://u1.lan:8080/stream");

  // 8. Progress notification switch in the system tab; G-code download
  card = make();
  R = card.shadowRoot.getElementById("u1card");
  const ln = R.querySelector("[data-livenotify]");
  assert.ok(ln && ln.getAttribute("aria-pressed") === "false", "switch shown");
  assert.match(ln.closest(".row").textContent, /Heute 4 von 150/);
  calls.length = 0;
  ln.click();
  assert.deepStrictEqual(JSON.parse(JSON.stringify(calls[0])), ["switch", "toggle", { entity_id: "switch.snapmaker_u1_card_fortschritt" }]);
  card._dlg = { file: { path: "sub/Teil 1.gcode", name: "Teil 1" } };
  let clicked = null;
  w.HTMLAnchorElement.prototype.click = function () { clicked = { href: this.getAttribute("href"), download: this.download }; };
  await card._downloadFile();
  assert.strictEqual(ws[0].path, "/api/snapmaker_u1_card/gcode/E1/sub/Teil%201.gcode");
  assert.deepStrictEqual(clicked, { href: "/api/snapmaker_u1_card/gcode/E1/sub/Teil%201.gcode?authSig=X", download: "Teil 1.gcode" });

  console.log("SAFETY OK – emergency stop modes, confirm dialog, tablet layout, camera wake, version notice, direct stream, progress switch, download");
})().catch((e) => { console.error(e); process.exit(1); });
