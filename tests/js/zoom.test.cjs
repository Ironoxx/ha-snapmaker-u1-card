// Camera zoom and system load display.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
Object.defineProperty(w.HTMLElement.prototype, "clientWidth", { get() { return this.classList && this.classList.contains("frame") ? 400 : 0; } });
Object.defineProperty(w.HTMLElement.prototype, "clientHeight", { get() { return this.classList && this.classList.contains("frame") ? 300 : 0; } });
w.eval(src);
const P = "snapmaker_u1";
const reg = {}, states = {};
const add = (id, state, attrs = {}, platform = "moonraker", tk) => { states[id] = { entity_id: id, state, attributes: attrs }; reg[id] = { entity_id: id, platform, translation_key: tk }; };
add(`sensor.${P}_printer_state`, "ready");
add(`sensor.${P}_current_print_state`, "standby");
add(`sensor.${P}_system_load`, "0.5");
add(`camera.${P}_webcam`, "idle", {});
add("sensor.snapmaker_u1_card_filamente", "0", { slots: [], entry_id: "E1", cpu_count: 4 }, "snapmaker_u1_card", "filaments");
const hass = () => ({ states: JSON.parse(JSON.stringify(states)), entities: reg, locale: { language: "de" }, callService: async () => {} });
const card = w.document.createElement("snapmaker-u1-card");
card.setConfig({ type: "custom:snapmaker-u1-card", layout: "scroll" });
w.document.body.appendChild(card);
card.hass = hass();
const R = () => card.shadowRoot.getElementById("u1card");
const frame = () => R().querySelector(".stage .frame");
const img = () => frame().querySelector("img");

// System load with context
assert.match(R().querySelector('[data-su1="sys"]').textContent, /0,50 · 13 % von 4 Kernen/);
assert.match(R().textContent, /Systemlast \(Ø 1 min\)/);

// Zoom via buttons
assert.ok(frame().querySelector('[data-zoom="out"]').hidden, "Minus erst beim Zoomen");
frame().querySelector('[data-zoom="in"]').click();
assert.match(img().style.transform, /scale\(1\.6\)/);
assert.ok(frame().classList.contains("zoomed"));
assert.strictEqual(frame().querySelector(".zoom-badge").textContent, "1,6×");
assert.ok(!frame().querySelector('[data-zoom="out"]').hidden);
// The centre stays the centre: translate = 200 - 200*1.6 = -120, 150 - 150*1.6 = -90
assert.match(img().style.transform, /translate\(-120px, -90px\)/);
// Mouse wheel without Ctrl only scrolls the page? With zoom > 1 it zooms
const wheel = (dy, ctrl) => { const e = new w.WheelEvent("wheel", { deltaY: dy, ctrlKey: ctrl, clientX: 0, clientY: 0, cancelable: true }); frame().dispatchEvent(e); return e.defaultPrevented; };
assert.ok(wheel(100, false), "gezoomt: Rad zoomt");
// A rebuild keeps the zoom
const t = img().style.transform;
card._renderKey = null; card.hass = hass();
assert.strictEqual(img().style.transform, t, "Zoom ueberlebt Neuaufbau");
// Double click resets
frame().dispatchEvent(new w.MouseEvent("dblclick", { clientX: 10, clientY: 10, bubbles: true }));
assert.strictEqual(img().style.transform, "");
assert.ok(!frame().classList.contains("zoomed"));
// Not zoomed: do not capture the wheel without Ctrl (page scrolls)
assert.ok(!wheel(100, false), "ungezoomt: Seite scrollt");
assert.ok(wheel(-100, true), "Strg+Rad zoomt");
// Edge: do not pan beyond the image
card._zoom.x = 500; card._applyZoom();
assert.match(img().style.transform, /translate\(0px/);
// Back to 1x after the idle time (default 60 s) and when the page is left
const timers = [];
w.setTimeout = (fn, ms) => { timers.push({ fn, ms }); return timers.length; };
w.clearTimeout = () => {};
card._zoom.x = 0; frame().querySelector('[data-zoom="in"]').click();
assert.ok(frame().classList.contains("zoomed"));
const t1 = timers[timers.length - 1];
assert.strictEqual(t1.ms, 60000, "60 s Standard");
t1.fn();
assert.ok(!frame().classList.contains("zoomed"), "nach Zeit zurueck");
frame().querySelector('[data-zoom="in"]').click();
Object.defineProperty(w.document, "hidden", { value: true, configurable: true });
w.document.dispatchEvent(new w.Event("visibilitychange"));
assert.ok(!frame().classList.contains("zoomed"), "Seite verlassen -> zurueck");
Object.defineProperty(w.document, "hidden", { value: false, configurable: true });
// option: 0 = never, other value in seconds
card.setConfig({ type: "custom:snapmaker-u1-card", layout: "scroll", camera_zoom_reset: 0 });
card.hass = hass();
timers.length = 0;
frame().querySelector('[data-zoom="in"]').click();
assert.strictEqual(timers.filter((t) => t.ms >= 1000).length, 0, "0 = nie");
card.setConfig({ type: "custom:snapmaker-u1-card", layout: "scroll", camera_zoom_reset: 15 });
card.hass = hass();
frame().querySelector('[data-zoom="in"]').click();
assert.ok(timers.some((t) => t.ms === 15000), "eigene Zeit");
assert.match(JSON.stringify(w.customElements.get("snapmaker-u1-card").getConfigForm().schema), /camera_zoom_reset/);
console.log("ZOOM OK – incl. reset after idle time and on leaving");
process.exit(0);
