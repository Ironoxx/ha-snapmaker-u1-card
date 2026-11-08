// Printer display (paxx12 mirror): own tab only when found, admin-only touch with the
// hand button, off again after the lock time, pixel mapping and touch order.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.URL.createObjectURL = () => "blob:display";
w.URL.revokeObjectURL = () => {};
w.eval(src);

const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => {
  states[id] = { entity_id: id, state, attributes: attrs };
  reg[id] = { entity_id: id, platform, translation_key: tk };
};
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
const FILES = "sensor.snapmaker_u1_card_druckdateien";
add(FILES, "0", { entry_id: "E1", files: [], version: "2.1.2", screen: null }, "snapmaker_u1_card", "files");

let fetched = [], posted = [];
const hass = (admin = true) => ({
  states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" },
  user: { is_admin: admin },
  callService: async () => {},
  callApi: async (method, p, body) => { posted.push([method, p, body]); return { ok: true }; },
  fetchWithAuth: async (url) => { fetched.push(url); return { ok: true, blob: async () => new w.Blob(["png"]) }; },
});
const made = [];
const make = (cfg = {}, admin = true) => {
  const c = w.document.createElement("snapmaker-u1-card");
  made.push(c);
  c.setConfig({ type: "custom:snapmaker-u1-card", ...cfg });
  w.document.body.appendChild(c);
  c.hass = hass(admin);
  c._onScreen = true;
  return c;
};
const $ = (c, sel) => c.shadowRoot.querySelector(sel);
// Picture 480x320 in a 960x320 frame: 240 px bars left and right
const fakeImage = (img) => {
  Object.defineProperty(img, "naturalWidth", { value: 480, configurable: true });
  Object.defineProperty(img, "naturalHeight", { value: 320, configurable: true });
  img.getBoundingClientRect = () => ({ left: 0, top: 0, width: 960, height: 320 });
};
const ev = (x, y) => ({ clientX: x, clientY: y, pointerId: 1, pointerType: "touch", button: 0, preventDefault() {} });

(async () => {
  // without a display mirror: no tab, no section
  let card = make();
  assert.ok(!$(card, '[data-tab="display"]'), "no display tab");
  assert.ok(!$(card, "section.display"));

  // mirror found: on the overview (2.2), panel aspect ratio, no camera involved
  states[FILES].attributes.screen = { width: 480, height: 320 };
  card = make();
  assert.ok(!$(card, '[data-tab="display"]'), "no own tab by default");
  assert.ok($(card, '[data-pane="overview"] section.display'), "display on the overview");
  assert.match($(card, "[data-display]").getAttribute("style"), /aspect-ratio:480 \/ 320/);
  assert.match($(card, "[data-display]").getAttribute("style"), /width:480px;max-width:min\(100%, calc\(70vh \* 480 \/ 320\)\)/, "höchstens Originalgröße");
  // display_place: tab -> own tab as before
  assert.ok($(make({ display_place: "tab" }), '[data-tab="display"]'), "own tab");
  assert.ok($(make({ display_tab: true }), '[data-tab="display"]'), "old option display_tab: true");
  card._tickDisplay();
  await new Promise((r) => setTimeout(r, 0));
  assert.deepStrictEqual(fetched.slice(0, 1), ["/api/snapmaker_u1_card/screen/E1/snapshot"]);

  // touch is off until the hand button is pressed
  const frame = $(card, "[data-display]");
  const img = $(card, "img[data-display-img]");
  fakeImage(img);
  card._displayPointer("down", ev(340, 50), frame);
  await card._dispQueue;
  assert.deepStrictEqual(posted, [], "no touch while off");
  assert.match($(card, "[data-display-hint]").textContent, /Hand antippen/);
  $(card, "[data-display-touch]").click();
  assert.strictEqual($(card, "[data-display-touch]").getAttribute("aria-pressed"), "true");
  assert.ok(frame.classList.contains("touch"));
  assert.match($(card, "[data-display-hint]").textContent, /Aus nach 60 s/);

  // down/move/up in panel pixels, in order; a down in the letterbox is ignored
  card._displayPointer("down", ev(100, 50), frame);
  card._displayPointer("down", ev(340, 50), frame);
  card._displayPointer("move", ev(360, 60), frame);
  card._displayPointer("move", ev(361, 60), frame); // throttled
  card._displayPointer("up", ev(900, 60), frame);   // outside: last point
  await card._dispQueue;
  assert.deepStrictEqual(posted.map(([m, p, b]) => [m, p, b.a, b.x, b.y]), [
    ["POST", "snapmaker_u1_card/screen/E1/touch", "down", 100, 50],
    ["POST", "snapmaker_u1_card/screen/E1/touch", "move", 120, 60],
    ["POST", "snapmaker_u1_card/screen/E1/touch", "up", 120, 60],
  ]);

  // idle: off again after the lock time, the button follows
  card._dispUntil = Date.now() - 1;
  card._tickDisplay();
  assert.strictEqual(card._displayTouchOn(), false);
  assert.strictEqual($(card, "[data-display-touch]").getAttribute("aria-pressed"), "false");
  assert.ok(!$(card, "[data-display]").classList.contains("touch"));
  // the button works again after it was replaced
  $(card, "[data-display-touch]").click();
  assert.strictEqual(card._displayTouchOn(), true);

  // the lock time comes from controls_lock; "off" still switches the display off
  assert.strictEqual(make({ controls_lock: "30" })._displayIdleMs(), 30000);
  assert.strictEqual(make({ controls_lock: "manual" })._displayIdleMs(), Infinity);
  assert.strictEqual(make({ controls_lock: "off" })._displayIdleMs(), 60000);

  // not an admin: picture yes, no hand button, no touch
  card = make({}, false);
  assert.ok($(card, "section.display"));
  assert.ok(!$(card, "[data-display-touch]"));
  assert.match($(card, "[data-display-hint]").textContent, /Nur Admins/);
  card._dispUntil = Date.now() + 60000;
  assert.strictEqual(card._displayTouchOn(), false);

  // hide: display removes it like any other section
  card = make({ hide: ["display"] });
  assert.ok(!$(card, "section.display"));

  // display_tab: false (old) / display_place: off -> not shown
  card = make({ display_tab: false });
  assert.ok(!$(card, "section.display"));
  assert.ok(!$(make({ display_place: "off" }), "section.display"));
  // without display_camera: no camera switch (no second camera here)
  assert.ok(!$(card, "[data-camswitch]"));

  // display_camera: the switch button cycles printer camera -> display -> printer camera
  card = make({ display_camera: true, display_tab: false, layout: "tablet" });
  assert.ok($(card, "[data-camswitch]"), "switch button for the display");
  $(card, "[data-camswitch]").click();
  assert.ok($(card, "section.stage [data-display]"), "display on the stage");
  assert.ok(!$(card, "section.stage img[data-live]"), "no camera image");
  assert.ok($(card, "section.stage [data-display-touch]"), "hand button on the stage");
  // touch on the stage like in the tab
  posted = [];
  const sframe = $(card, "section.stage [data-display]");
  fakeImage($(card, "section.stage img[data-display-img]"));
  $(card, "section.stage [data-display-touch]").click();
  card._displayPointer("down", ev(340, 50), sframe);
  card._displayPointer("up", ev(340, 50), sframe);
  await card._dispQueue;
  assert.deepStrictEqual(posted.map(([, , b]) => [b.a, b.x, b.y]), [["down", 100, 50], ["up", 100, 50]]);
  $(card, "[data-camswitch]").click();
  assert.ok(!$(card, "section.stage [data-display]"), "back to the camera");

  // with a USB camera: printer camera -> USB camera -> display -> printer camera
  add("camera.snapmaker_u1_card_kamera_2", "idle", { entity_picture: "/api/camera_proxy/two?token=B", mode: "live" },
    "snapmaker_u1_card", "camera2");
  card = make({ display_camera: true });
  const step = () => { $(card, "[data-camswitch]").click(); return card._camDisplay ? "display" : card._camAlt ? "usb" : "main"; };
  assert.deepStrictEqual([step(), step(), step()], ["usb", "display", "main"]);

  // tablet layout with tab and stage both on the display: one picture loop serves both
  card = make({ display_camera: true, layout: "tablet" });
  step(); step(); // -> display on the stage
  card._selectTab("overview"); // 2.2: the display section sits on the overview
  assert.strictEqual(card._displayImgs().length, 2);

  // removed from the page: the picture loop stops (no timer left behind)
  made.forEach((c) => c.remove());
  assert.ok(made.every((c) => !c._dispTimer));

  console.log("DISPLAY OK – on the overview when found (or own tab), admin touch with hand button, idle off, lock time, pixel mapping, touch order, display_tab, display_camera cycle");
})().catch((err) => { console.error(err); process.exit(1); });
