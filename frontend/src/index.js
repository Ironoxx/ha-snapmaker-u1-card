/**
 * Entry point: registers both cards with the frontend and the card picker.
 *
 * Built with esbuild into custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js
 * (npm run build). Do not edit
 * the built file; it is overwritten on every build.
 */

import { CARD_VERSION } from "./const.js";
import { setLang, tr } from "./i18n.js";
import { SnapmakerU1Card } from "./card/card.js";
import { SnapmakerU1MiniCard } from "./card/mini.js";

// The integration loads the card on two paths (start page and dashboard
// resource) so it is reliably there after a HA restart. Loading twice is
// therefore normal; only warn when the versions differ.
if (!customElements.get("snapmaker-u1-card")) {
  customElements.define("snapmaker-u1-card", SnapmakerU1Card);
  customElements.define("snapmaker-u1-mini-card", SnapmakerU1MiniCard);
  window.__snapmakerU1CardVersion = CARD_VERSION;
} else if (window.__snapmakerU1CardVersion !== CARD_VERSION) {
  console.warn(`snapmaker-u1-card: version ${window.__snapmakerU1CardVersion || "?"} is already loaded, ignoring ${CARD_VERSION}. Remove the old resource under Dashboards → Resources and reload.`);
}

// Card picker texts: the frontend sets <html lang> before custom cards load.
setLang({ language: document.documentElement.lang });
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "snapmaker-u1-card")) window.customCards.push({
  type: "snapmaker-u1-card",
  name: "Snapmaker U1",
  description: tr("Snapmaker U1: Kamera, geladene Filamente, Druckstart mit Filamentzuordnung, Diagnose."),
  preview: false,
});
if (!window.customCards.some((c) => c.type === "snapmaker-u1-mini-card")) window.customCards.push({
  type: "snapmaker-u1-mini-card",
  name: "Snapmaker U1 Mini",
  description: tr("Kompakt: Status, Fortschritt, Filamente und Netzschalter – ohne Kamera."),
  preview: true,
});

if (window.__snapmakerU1CardVersion === CARD_VERSION && !window.__snapmakerU1CardLogged) {
  window.__snapmakerU1CardLogged = true;
  console.info("%c SNAPMAKER-U1-CARD ", "background:#4c5c92;color:#fff;border-radius:4px", CARD_VERSION);
}
