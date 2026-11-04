// 2.1: Spanish, French, Italian, Portuguese and Dutch; regional variants use the base
// language, unknown languages English; missing entries fall back to English.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
w.eval(src);

const states = { "sensor.u1_printer_state": { entity_id: "sensor.u1_printer_state", state: "ready", attributes: {} } };
const entities = { "sensor.u1_printer_state": { entity_id: "sensor.u1_printer_state", platform: "moonraker" } };
const tabs = (lang) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card" });
  w.document.body.appendChild(c);
  c.hass = { states, entities, locale: { language: lang }, callService: async () => {} };
  const out = [...c.shadowRoot.querySelectorAll("[data-tab]")].map((b) => b.textContent.trim());
  c.remove();
  return out;
};
assert.strictEqual(tabs("de")[0], "Übersicht");
assert.strictEqual(tabs("en")[0], "Overview");
assert.strictEqual(tabs("es")[0], "Resumen");
assert.strictEqual(tabs("fr")[0], "Aperçu");
assert.strictEqual(tabs("it")[0], "Panoramica");
assert.strictEqual(tabs("nl")[0], "Overzicht");
assert.strictEqual(tabs("pt")[0], "Visão geral");
assert.strictEqual(tabs("pt-BR")[0], "Visão geral", "Region -> Grundsprache");
assert.strictEqual(tabs("sv")[0], "Overview", "unbekannt -> Englisch");

// every language table has exactly the keys of the English one, with the same placeholders
const i18n = fs.readFileSync(path.join(__dirname, "../../frontend/src/i18n.js"), "utf8");
const enSrc = i18n.slice(i18n.indexOf("export const EN = ") + "export const EN = ".length, i18n.lastIndexOf("};") + 1);
const EN = eval(`(${enSrc})`);
const ph = (s) => (s.match(/\{\w+\}/g) || []).sort().join();
for (const lang of ["es", "fr", "it", "nl", "pt"]) {
  const t = fs.readFileSync(path.join(__dirname, `../../frontend/src/i18n/${lang}.js`), "utf8");
  const table = eval(`(${t.slice(t.indexOf("{"), t.lastIndexOf("}") + 1)})`);
  const missing = Object.keys(EN).filter((k) => !(k in table));
  assert.deepStrictEqual(missing, [], `${lang}: fehlende Texte`);
  for (const [k, v] of Object.entries(table)) assert.strictEqual(ph(v), ph(EN[k] ?? k), `${lang}: Platzhalter in ${k}`);
}
console.log("I18N OK – de en es fr it nl pt, regional variants, fallback, complete tables");
