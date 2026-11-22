// Validate localized cards; regional variants use their base language, Traditional Chinese falls back to English.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.HTMLCanvasElement.prototype.getContext = () => null;
w.setInterval = () => 0;
// 2.4.0b3: other languages come as files from the integration's static path – served from disk here
const fetched = [];
const FRONT = path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend");
w.fetch = async (url) => {
  fetched.push(url);
  const m = String(url).match(/^\/snapmaker_u1_card\/card\/(i18n\/[\w.]+\.json)$/);
  if (!m || !fs.existsSync(path.join(FRONT, m[1]))) return { ok: false, status: 404 };
  const body = fs.readFileSync(path.join(FRONT, m[1]), "utf8");
  return { ok: true, status: 200, json: async () => JSON.parse(body) };
};
w.eval(src);
const tick = () => new Promise((r) => setTimeout(r, 0));

const states = { "sensor.u1_printer_state": { entity_id: "sensor.u1_printer_state", state: "ready", attributes: {} } };
const entities = { "sensor.u1_printer_state": { entity_id: "sensor.u1_printer_state", platform: "moonraker" } };
// the card redraws by itself once the table has arrived
const tabs = async (lang) => {
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card" });
  w.document.body.appendChild(c);
  c.hass = { states, entities, locale: { language: lang }, callService: async () => {} };
  for (let i = 0; i < 5; i++) await tick();
  const out = [...c.shadowRoot.querySelectorAll("[data-tab]")].map((b) => b.textContent.trim());
  c.remove();
  return out;
};
(async () => {
// German and English are in the bundle: no download
assert.strictEqual((await tabs("de"))[0], "Übersicht");
assert.strictEqual((await tabs("en"))[0], "Overview");
assert.deepStrictEqual(fetched, [], "de/en ohne Nachladen");
assert.strictEqual((await tabs("es"))[0], "Resumen");
assert.strictEqual((await tabs("fr"))[0], "Aperçu");
assert.strictEqual((await tabs("it"))[0], "Panoramica");
assert.strictEqual((await tabs("nl"))[0], "Overzicht");
assert.strictEqual((await tabs("pt"))[0], "Visão geral");
assert.strictEqual((await tabs("pt-BR"))[0], "Visão geral", "Region -> Grundsprache");
assert.strictEqual((await tabs("tr"))[0], "Genel Bakış");
assert.strictEqual((await tabs("zh-Hans"))[0], "概览");
assert.strictEqual((await tabs("zh-CN"))[0], "概览");
assert.strictEqual((await tabs("zh"))[0], "概览");
assert.strictEqual((await tabs("zh-Hant"))[0], "Overview", "Traditional Chinese -> English");
assert.strictEqual((await tabs("zh-TW"))[0], "Overview", "Traditional region -> English");
assert.strictEqual((await tabs("sv"))[0], "Overview", "unknown -> English");
// one download per language, hashed file names, nothing for unknown/Traditional
assert.ok(fetched.every((u) => /^\/snapmaker_u1_card\/card\/i18n\/(es|fr|it|nl|pt|tr|zh)\.[0-9a-f]{8}\.json$/.test(u)), fetched.join());
assert.strictEqual(fetched.length, 7, fetched.join());


// every language table has exactly the keys of the English one, with the same placeholders
const i18n = fs.readFileSync(path.join(__dirname, "../../frontend/src/i18n.js"), "utf8");
const enSrc = i18n.slice(i18n.indexOf("export const EN = ") + "export const EN = ".length, i18n.lastIndexOf("};") + 1);
const EN = eval(`(${enSrc})`);
const ph = (s) => (s.match(/\{\w+\}/g) || []).sort().join();
for (const lang of ["es", "fr", "it", "nl", "pt", "tr", "zh"]) {
  const t = fs.readFileSync(path.join(__dirname, `../../frontend/src/i18n/${lang}.js`), "utf8");
  const table = eval(`(${t.slice(t.indexOf("{"), t.lastIndexOf("}") + 1)})`);
  const missing = Object.keys(EN).filter((k) => !(k in table));
  assert.deepStrictEqual(missing, [], `${lang}: fehlende Texte`);
  for (const [k, v] of Object.entries(table)) assert.strictEqual(ph(v), ph(EN[k] ?? k), `${lang}: Platzhalter in ${k}`);
}

// Critical printer actions and terminology reviewed against the German source and English reference.
const zhText = fs.readFileSync(path.join(__dirname, "../../frontend/src/i18n/zh.js"), "utf8");
const ZH = eval(`(${zhText.slice(zhText.indexOf("{"), zhText.lastIndexOf("}") + 1)})`);
for (const [source, expected] of [
  ["Referenzfahrt", "归零"],
  ["Spanne (mm)", "跨度（mm）"],
  ["Aufnahme wird geprüft", "正在检查打印头拾取状态"],
  ["Meldungen", "消息"],
  ["Licht", "照明"],
  ["Einzug {head}: Störung", "进料器 {head}：故障"],
  ["Druck wirklich abbrechen?", "确定要取消打印吗？"],
  ["Der Drucker antwortet nicht. Trotzdem ausschalten?", "打印机无响应。仍要关机并断电吗？"],
  ["Der Drucker ist aus. Er wird eingeschaltet und startet den Druck, sobald er bereit ist (ca. 1–2 min).", "打印机当前已关机；系统会先自动开机，待打印机就绪后开始打印（约 1–2 分钟）。"],
  ["Rand (Brim)", "外扩边（Brim）"],
  ["nur vom Bett", "仅接触打印平台"],
  ["Der laufende Druck lässt sich danach nicht fortsetzen.", "当前打印无法继续。"],
  ["Druck abbrechen", "取消打印"],
]) assert.strictEqual(ZH[source], expected, `reviewed translation: ${source}`);

// Amounts use Home Assistant's currency (hass.config.currency), not a fixed €
const cost = (lang, currency) => {
  const st = {
    ...states,
    "sensor.u1_kosten_druck": { entity_id: "sensor.u1_kosten_druck", state: "700", attributes: { unit_of_measurement: currency } },
  };
  const en = { ...entities, "sensor.u1_kosten_druck": { entity_id: "sensor.u1_kosten_druck", platform: "snapmaker_u1_card", translation_key: "print_cost" } };
  const c = w.document.createElement("snapmaker-u1-card");
  c.setConfig({ type: "custom:snapmaker-u1-card" });
  w.document.body.appendChild(c);
  c.hass = { states: st, entities: en, locale: { language: lang }, config: { currency }, callService: async () => {} };
  const btn = c.shadowRoot.querySelector('[data-tab="system"]');
  if (btn) btn.click();
  const out = c.shadowRoot.textContent;
  c.remove();
  return out;
};
assert.match(cost("tr", "TRY"), /₺700,00/, "TRY in Turkish");
assert.match(cost("de", "EUR"), /700,00\s€/, "EUR in German");
console.log("I18N OK – de en es fr it nl pt tr zh-Hans, loaded on demand, regional/Traditional fallback, complete tables, placeholders, currency");
})().catch((e) => { console.error(e); process.exit(1); });
