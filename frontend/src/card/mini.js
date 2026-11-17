/** Mini card: status, progress, filaments and power switch, no camera. Same data model as the full card. */

import { configForm } from "../editor.js";
import { esc, fmtClock, fmtMin, num } from "../format.js";
import { tr } from "../i18n.js";

import { SnapmakerU1Card } from "./card.js";

export class SnapmakerU1MiniCard extends SnapmakerU1Card {
  static getConfigForm() { return configForm(true); }
  static getStubConfig() { return { type: "custom:snapmaker-u1-mini-card" }; }

  setConfig(config) {
    super.setConfig({ ...config, show: [], layout: "mini" });
    this.setAttribute("mini", "");
  }

  getCardSize() { return this._cfg && this._cfg.hide_filaments ? 1 : 2; }
  getGridOptions() { return { columns: 6, rows: "auto", min_columns: 3 }; }

  /**
   * 2.3.1: compact like Home Assistant's tile card. The icon switches the printer
   * on/off (with a power switch), the line below the name cycles through the
   * current infos every 5 s and is cut with "…" when it does not fit.
   */
  _body() {
    const d = this._d;
    const p = d.power;
    const items = this._miniItems();
    const first = items[0] || { text: "" };
    this._miniIdx = 0;
    const iconBody = `<ha-icon icon="${p && !p.on && !d.online ? "mdi:power" : "mdi:printer-3d-nozzle"}"></ha-icon>`;
    const icon = p
      ? `<button type="button" class="mini-icon" data-act="power" data-su1="miniicon" ${this._miniIconAttrs()}>${iconBody}</button>`
      : `<div class="mini-icon" data-su1="miniicon" ${this._miniIconAttrs()}>${iconBody}</div>`;
    const sm = this._spoolman();
    const fil = !this._cfg.hide_filaments && d.heads.some((h) => h.loaded || h.material !== "—") ? `
      <div class="mini-fil">${d.heads.map((h) => {
        const sp = sm ? this._slotSpool(h.idx) : null;
        const low = sp && sp.remaining_weight != null && sp.remaining_weight < (sm.low || 0);
        return `<span class="mini-slot" data-active="${h.active ? 1 : 0}" data-empty="${h.loaded ? 0 : 1}"
            title="${esc(h.name)}: ${esc(h.material)}">
          ${this._spoolSvg(h.color, h.active, h.colors, sm ? this._spoolFill(h.idx) : null, h.active && !!d.printing && !d.paused)}
          <span class="mini-mat">${esc(h.loaded ? h.material : tr("leer"))}</span>
          ${sp && sp.remaining_weight != null ? `<span class="mini-g mono" data-low="${low ? 1 : 0}">${Math.round(sp.remaining_weight)} g</span>` : ""}
        </span>`;
      }).join("")}</div>` : "";
    return `
      <div class="mini-wrap" data-tap>
        <div class="mini-tile">
          ${icon}
          <div class="mini-info">
            <div class="mini-name">${esc(this._cfg.printer_name)}</div>
            <div class="mini-sub" data-su1="minisub" data-tone="${first.tone || ""}" title="${esc(items.map((i) => i.text).join(" · "))}">${esc(first.text)}</div>
          </div>
        </div>
        ${d.online && d.active ? `<div class="mini-bar" data-tone="${d.state === "error" ? "error" : d.paused ? "warn" : ""}"><i data-su1="bar" style="width:${d.progress}%"></i></div>` : ""}
        ${fil}
      </div>`;
  }

  /** What the line under the name shows, in turn: [{text, tone}]. */
  _miniItems() {
    const d = this._d;
    if (!d) return [];
    const p = d.power;
    const watts = p && p.on && p.watts !== null && p.watts !== undefined ? num(p.watts, 0, "W") : "";
    const withW = (t) => (watts ? `${t} · ${watts}` : t);
    if (!d.online) {
      const text = p && p.shuttingDown ? tr("Drucker fährt herunter") : p && p.poweringOn ? tr("Drucker startet")
        : p && p.available && !p.on ? tr("Drucker ist aus") : tr("Drucker nicht erreichbar");
      return [{ text: withW(text), tone: p && (p.shuttingDown || p.poweringOn) ? "warn" : "" }];
    }
    const out = [];
    if (d.errors.length) out.push({ text: this._errText(d.errors[0]), tone: "error" });
    const tone = { active: "active", warn: "warn", error: "error", ok: "ok" }[this._statusTone()] || "";
    if (d.active) {
      out.push({ text: `${this._statusLabel()} · ${d.progress.toFixed(0)} % · ${fmtMin(d.remaining)}`, tone });
      if (d.filename) out.push({ text: d.filename });
      if (d.eta) out.push({ text: `${tr("Fertig um")} ${fmtClock(d.eta)}` });
      if (d.totalLayers) out.push({ text: tr("Schicht {n} / {t}", { n: d.layer, t: d.totalLayers }) });
      if (watts) out.push({ text: watts });
    } else {
      out.push({ text: withW(this._statusLabel()), tone });
      if (d.queue && d.queue.length) {
        out.push({ text: tr("Nächster: {name}", { name: d.queue[0].name || d.queue[0].file }) + (d.queue.length > 1 ? ` (+${d.queue.length - 1})` : "") });
      }
    }
    return out;
  }

  _miniIconAttrs() {
    const d = this._d;
    const p = d.power;
    const busy = p && (p.shuttingDown || p.poweringOn);
    const state = !d.online ? (busy ? "busy" : "off") : d.errors.length || d.state === "error" ? "error"
      : d.active ? (d.paused ? "paused" : "printing") : "on";
    const title = !p ? "" : !p.available ? tr("Netzschalter nicht erreichbar")
      : busy ? tr("Bitte warten") : p.on ? tr("Herunterfahren und ausschalten") : tr("Einschalten");
    return `data-state="${state}" style="--p:${d.active ? Math.round(d.progress) : 0}"${title ? ` title="${esc(title)}" aria-label="${esc(title)}"` : ""}${p && (busy || !p.available) ? " disabled" : ""}`;
  }

  /** Every second: current values in the line; every 5 s the next info (slides in). */
  _tickCamera() {
    this._miniTick = (this._miniTick || 0) + 1;
    this._miniPaint(this._miniTick % 5 === 0);
  }

  _patch() {
    super._patch();
    this._miniPaint(false);
  }

  _miniPaint(advance) {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    const sub = r && r.querySelector('[data-su1="minisub"]');
    if (!sub || !this._d) return;
    const items = this._miniItems();
    const next = advance && items.length > 1;
    if (next) this._miniIdx = ((this._miniIdx || 0) + 1) % items.length;
    if (!items.length || (this._miniIdx || 0) >= items.length) this._miniIdx = 0;
    const it = items[this._miniIdx] || { text: "" };
    sub.title = items.map((i) => i.text).join(" · ");
    if (sub.textContent !== it.text || sub.dataset.tone !== (it.tone || "")) {
      sub.textContent = it.text;
      sub.dataset.tone = it.tone || "";
      if (next) { sub.classList.remove("swap"); void sub.offsetWidth; sub.classList.add("swap"); }
    }
    const icon = r.querySelector('[data-su1="miniicon"]');
    if (icon) icon.style.setProperty("--p", String(this._d.active ? Math.round(this._d.progress) : 0));
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
