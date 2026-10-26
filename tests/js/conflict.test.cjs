// Another integration (kbaker827/ha-snapmaker-u1) registered "snapmaker-u1-card" first:
// this card must stay usable under its own name and say so.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { JSDOM } = require("jsdom");

const src = fs.readFileSync(process.argv[2] || path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8");
const dom = new JSDOM(`<!doctype html><body></body>`, { url: "http://ha.local/lovelace/0", runScripts: "outside-only" });
const w = dom.window;
const warnings = [];
w.console.warn = (m) => warnings.push(String(m));
w.console.info = () => {};
w.eval(`customElements.define("snapmaker-u1-card", class Other extends HTMLElement {});
        window.customCards = [{ type: "snapmaker-u1-card", name: "Other U1 card" }];`);
w.eval(src);

assert.strictEqual(w.customElements.get("snapmaker-u1-card").name, "Other", "fremde Karte bleibt");
assert.ok(w.customElements.get("snapmaker-u1-card-ironoxx"), "eigener Name registriert");
assert.ok(w.customElements.get("snapmaker-u1-mini-card"), "Mini-Karte registriert");
assert.ok(warnings.some((m) => m.includes("custom:snapmaker-u1-card-ironoxx")), "Hinweis in der Konsole");
assert.ok(w.customCards.some((c) => c.type === "snapmaker-u1-card-ironoxx"), "Kartenauswahl zeigt den eigenen Namen");
// The alias renders the full card
const card = w.document.createElement("snapmaker-u1-card-ironoxx");
card.setConfig({ type: "custom:snapmaker-u1-card-ironoxx" });
assert.strictEqual(typeof card.getCardSize, "function");
console.log("CONFLICT OK – own card name next to kbaker827's card");
