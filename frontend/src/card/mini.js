/** Mini card: status, progress, filaments and power switch, no camera. Same data model as the full card. */

import { configForm } from "../editor.js";
import { esc, fmtClock, fmtMin } from "../format.js";
import { tr } from "../i18n.js";

import { SnapmakerU1Card } from "./card.js";

export class SnapmakerU1MiniCard extends SnapmakerU1Card {
  static getConfigForm() { return configForm(true); }
  static getStubConfig() { return { type: "custom:snapmaker-u1-mini-card" }; }

  setConfig(config) {
    super.setConfig({ ...config, show: [], layout: "mini" });
  }

  getCardSize() { return 3; }
  getGridOptions() { return { columns: 6, rows: "auto", min_columns: 3 }; }
  _tickCamera() { /* no camera */ }

  _body() {
    const d = this._d;
    const p = d.power;
    const tone = this._statusTone();
    const off = !d.online && p && p.available && !p.on;
    const sub = !d.online
      ? (p && p.shuttingDown ? tr("Drucker fährt herunter") : p && p.poweringOn ? tr("Drucker startet")
        : off ? tr("Drucker ist aus") : tr("Drucker nicht erreichbar"))
      : null;
    const job = d.online && d.active ? `
      <div class="mini-job">
        <div class="mini-file" data-su1="file">${esc(d.filename || "—")}</div>
        <div class="mini-prog">
          <div class="track" data-tone="${d.state === "error" ? "error" : d.paused ? "warn" : ""}"><i data-su1="bar" style="width:${d.progress}%"></i></div>
          <span class="mono"><span data-su1="opct">${d.progress.toFixed(0)}</span> %</span>
        </div>
        <div class="mini-meta t-label">
          <span><ha-icon icon="mdi:timer-sand"></ha-icon><span data-su1="remain">${fmtMin(d.remaining)}</span></span>
          <span><ha-icon icon="mdi:flag-checkered"></ha-icon><span data-su1="eta">${fmtClock(d.eta)}</span></span>
          <span><ha-icon icon="mdi:layers-triple-outline"></ha-icon><span data-su1="layer">${d.layer} / ${d.totalLayers}</span></span>
        </div>
      </div>` : "";
    const sm = this._spoolman();
    const fil = !this._cfg.hide_filaments && d.heads.some((h) => h.loaded || h.material !== "—") ? `
      <div class="mini-fil">${d.heads.map((h) => {
        const sp = sm ? this._slotSpool(h.idx) : null;
        const low = sp && sp.remaining_weight != null && sp.remaining_weight < (sm.low || 0);
        return `<span class="mini-slot" data-active="${h.active ? 1 : 0}" data-empty="${h.loaded ? 0 : 1}"
            title="${esc(h.name)}: ${esc(h.material)}">
          ${this._spoolSvg(h.color, h.active, h.colors)}
          <span class="mini-mat">${esc(h.loaded ? h.material : tr("leer"))}</span>
          ${sp && sp.remaining_weight != null ? `<span class="mini-g mono" data-low="${low ? 1 : 0}">${Math.round(sp.remaining_weight)} g</span>` : ""}
        </span>`;
      }).join("")}</div>` : "";
    return `
      <div class="mini-wrap" data-tap>
        <div class="mini-top">
          <div class="head-icon" data-tone="${tone === "error" ? "error" : ""}">
            <ha-icon icon="mdi:printer-3d-nozzle"></ha-icon>
          </div>
          <div class="head-text">
            <div class="t-title">${esc(this._cfg.printer_name)}</div>
            <div class="t-label mini-status">${sub ? esc(sub) : `<span class="chip sm ${d.printing ? "live" : ""}" data-tone="${{ active: "active", warn: "warn", error: "error", ok: "ok" }[tone] || ""}"><span class="dot"></span><span data-su1="status">${this._statusLabel()}</span></span>`}</div>
          </div>
          ${p ? this._powerChip() : ""}
        </div>
        ${d.online && d.errors.length ? `<div class="mini-err"><ha-icon icon="mdi:alert"></ha-icon><span>${esc(this._errText(d.errors[0]))}</span></div>` : ""}
        ${job}
        ${fil}
        ${d.queue && d.queue.length && !d.active ? `<div class="t-label mini-q"><ha-icon icon="mdi:tray-full"></ha-icon>${tr("Nächster: {name}", { name: d.queue[0].name || d.queue[0].file })}${d.queue.length > 1 ? ` (+${d.queue.length - 1})` : ""}</div>` : ""}
      </div>`;
  }

  _wire() {
    super._wire();
    const r = this.shadowRoot.getElementById("u1card");
    const wrap = r && r.querySelector("[data-tap]");
    if (!wrap) return;
    wrap.addEventListener("click", (e) => {
      if (e.composedPath().some((el) => el.tagName === "BUTTON")) return;
      const path = this._cfg.navigation_path;
      if (path) {
        window.history.pushState(null, "", path);
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      } else {
        this._more(`sensor.${this._p("printer_state")}`);
      }
    });
  }
}
