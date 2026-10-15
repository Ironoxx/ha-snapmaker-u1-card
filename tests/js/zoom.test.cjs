// Kamera-Zoom und Systemlast-Anzeige.
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

// Systemlast eingeordnet
assert.match(R().querySelector('[data-su1="sys"]').textContent, /0,50 · 13 % von 4 Kernen/);
assert.match(R().textContent, /Systemlast \(Ø 1 min\)/);

// Zoom per Knopf
assert.ok(frame().querySelector('[data-zoom="out"]').hidden, "Minus erst beim Zoomen");
frame().querySelector('[data-zoom="in"]').click();
assert.match(img().style.transform, /scale\(1\.6\)/);
assert.ok(frame().classList.contains("zoomed"));
assert.strictEqual(frame().querySelector(".zoom-badge").textContent, "1,6×");
assert.ok(!frame().querySelector('[data-zoom="out"]').hidden);
// Mitte bleibt Mitte: translate = 200 - 200*1.6 = -120, 150 - 150*1.6 = -90
assert.match(img().style.transform, /translate\(-120px, -90px\)/);
// Mausrad ohne Strg scrollt nur die Seite? Bei Zoom > 1 wird gezoomt
const wheel = (dy, ctrl) => { const e = new w.WheelEvent("wheel", { deltaY: dy, ctrlKey: ctrl, clientX: 0, clientY: 0, cancelable: true }); frame().dispatchEvent(e); return e.defaultPrevented; };
assert.ok(wheel(100, false), "gezoomt: Rad zoomt");
// Neuaufbau behaelt den Zoom
const t = img().style.transform;
card._renderKey = null; card.hass = hass();
assert.strictEqual(img().style.transform, t, "Zoom ueberlebt Neuaufbau");
// Doppelklick setzt zurueck
frame().dispatchEvent(new w.MouseEvent("dblclick", { clientX: 10, clientY: 10, bubbles: true }));
assert.strictEqual(img().style.transform, "");
assert.ok(!frame().classList.contains("zoomed"));
// Ungezoomt: Rad ohne Strg nicht abfangen (Seite scrollt)
assert.ok(!wheel(100, false), "ungezoomt: Seite scrollt");
assert.ok(wheel(-100, true), "Strg+Rad zoomt");
// Rand: nicht ueber das Bild hinaus schieben
card._zoom.x = 500; card._applyZoom();
assert.match(img().style.transform, /translate\(0px/);
console.log("ZOOM OK");
