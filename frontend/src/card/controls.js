/** Actions, service calls, the control lock and small reusable UI building blocks. */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { LANG, tr } from "../i18n.js";

export const ControlsMixin = (Base) => class extends Base {
  _press(name) {
    this._hass.callService("button", "press", { entity_id: `button.${this._p(name)}` });
  }

  _setNumber(entity, value) {
    // Changing the target temperature during a print asks first (0 °C = ruined print)
    if (this._d && this._d.active && /_target$/.test(entity)
      && !confirm(tr("Solltemperatur während des Drucks auf {v} °C ändern?", { v: Number(value) }))) {
      this._busy.delete(entity);
      this._patch();
      return;
    }
    this._hass.callService("number", "set_value", { entity_id: entity, value: Number(value) });
  }

  // ── Control lock ────────────────────────────────────────────────────────
  // On a phone it is easy to brush a slider while scrolling. So sliders,
  // presets, heater switches and homing are locked until the padlock is
  // tapped; they lock again 60 s after the last interaction.
  /**
   * controls_lock: "off" | seconds ("30", "60", "120", "300") | "manual"
   * (stays open until locked again). Legacy: unlock_controls: true = "off".
   */
  _lockMode() {
    if (this._cfg.unlock_controls) return "off";
    const v = this._cfg.controls_lock;
    if (v === undefined || v === null || v === "") return 60;
    if (v === false || v === "off") return "off";
    if (v === "manual") return "manual";
    const n = parseInt(v, 10);
    return n > 0 ? n : 60;
  }

  _unlockMs() {
    const m = this._lockMode();
    return m === "manual" ? Infinity : m * 1000;
  }

  _unlockTitle() {
    const m = this._lockMode();
    return m === "manual" ? tr("Regler entsperren") : tr("Regler entsperren ({n} s)", { n: m });
  }

  _locked() {
    return this._lockMode() !== "off" && !(this._unlockUntil > Date.now());
  }

  _lockBtn() {
    if (this._lockMode() === "off") return "";
    const locked = this._locked();
    return `<button type="button" class="chip sm lock-btn" data-act="lock" data-su1-lock aria-pressed="${!locked}"
        title="${locked ? this._unlockTitle() : tr("Regler sperren")}" style="margin-left:auto">
        <ha-icon icon="${locked ? "mdi:lock" : "mdi:lock-open-variant"}"></ha-icon><span>${locked ? tr("Gesperrt") : tr("Entsperrt")}</span>
      </button>`;
  }

  _toggleLock() {
    this._unlockUntil = this._locked() ? Date.now() + this._unlockMs() : 0;
    this._applyLock();
  }

  _touchLock() {
    if (!this._locked()) this._unlockUntil = Date.now() + this._unlockMs();
  }

  _applyLock() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    if (!r) return;
    const locked = this._locked();
    r.querySelectorAll("[data-lockable]").forEach((el) => {
      el.classList.toggle("locked", locked);
      const ctrls = el.matches("button, input") ? [el] : el.querySelectorAll("button, input");
      ctrls.forEach((c) => { c.disabled = locked; });
    });
    r.querySelectorAll("[data-su1-lock]").forEach((b) => {
      b.setAttribute("aria-pressed", String(!locked));
      b.title = locked ? this._unlockTitle() : tr("Regler sperren");
      b.innerHTML = `<ha-icon icon="${locked ? "mdi:lock" : "mdi:lock-open-variant"}"></ha-icon><span>${locked ? tr("Gesperrt") : tr("Entsperrt")}</span>`;
    });
  }

  _more(entityId) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      detail: { entityId }, bubbles: true, composed: true,
    }));
  }

  // ── Building blocks ──────────────────────────────────────────────────────
  _statusTone() {
    const d = this._d;
    if (!d.online) return "off";
    if (d.state === "error") return "error";
    if (d.paused) return "warn";
    if (d.printing) return "active";
    if (d.state === "complete") return "ok";
    return "idle";
  }

  _statusLabel() {
    const d = this._d;
    if (!d.online) return tr("Offline");
    return {
      printing: tr("Druckt"), standby: tr("Bereit"), complete: tr("Fertig"),
      cancelled: tr("Abgebrochen"), paused: tr("Pausiert"), error: tr("Fehler"),
    }[d.state] || d.state;
  }

  _spoolSvg(color, active, colors = null) {
    // Multi-colour spools (silk, rainbow) as segments on the ring.
    const list = colors && colors.length > 1 ? colors : [color];
    const C = 2 * Math.PI * 17;
    const seg = C / list.length;
    const ring = list.map((c, k) =>
      `<circle cx="30" cy="30" r="17" fill="none" stroke="${esc(c)}" stroke-width="10"
        stroke-dasharray="${seg.toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="${(-k * seg).toFixed(2)}"
        transform="rotate(-90 30 30)"/>`).join("");
    return `<svg class="spool" viewBox="0 0 60 60" aria-hidden="true">
      <circle cx="30" cy="30" r="28" fill="var(--u1-panel)" stroke="var(--u1-outline)" stroke-width="1.5"/>
      ${ring}
      <circle cx="30" cy="30" r="22" fill="none" stroke="var(--u1-on-variant)" stroke-opacity=".35" stroke-width="1"/>
      <circle cx="30" cy="30" r="19" fill="none" stroke="rgba(0,0,0,.18)" stroke-width="1.4"/>
      <circle cx="30" cy="30" r="12" fill="var(--u1-panel)"/>
      <circle cx="30" cy="30" r="5" fill="var(--u1-panel-highest)"/>
      ${active ? `<circle cx="30" cy="30" r="28" fill="none" stroke="var(--u1-primary)" stroke-width="2.5"/>` : ""}
    </svg>`;
  }

  _slider(opts) {
    const { entity, label, min, max, step, value, unit, presets, dec } = opts;
    const st = this._st(entity);
    if (!st) return "";
    const mn = min ?? st.attributes.min ?? 0;
    const mx = max ?? st.attributes.max ?? 100;
    const sp = step ?? st.attributes.step ?? 1;
    const chips = (presets || []).map(
      (p) => `<button class="preset" data-set="${entity}" data-value="${p}">${p}${unit ? " " + unit : ""}</button>`
    ).join("");
    return `
      <div class="ctl" data-lockable>
        <div class="ctl-row">
          <span class="t-label">${esc(label)}</span>
          <span class="ctl-val" data-su1="n:${entity}">${num(value, dec ?? 0, unit)}</span>
        </div>
        <input type="range" min="${mn}" max="${mx}" step="${sp}" value="${value}"
               data-num="${entity}" data-unit="${esc(unit || "")}" data-dec="${dec ?? 0}"
               aria-label="${esc(label)}" />
        ${chips ? `<div class="presets">${chips}</div>` : ""}
      </div>`;
  }

  _stat(k, v, cls = "", hint = "") {
    const t = hint ? ` title="${esc(hint)}"` : ` title="${esc(k)}"`;
    return `<div class="stat"${t}><div class="k" lang="${LANG}">${esc(k)}</div><div class="v ${cls}">${v}</div></div>`;
  }

  _row(k, v, entity, title) {
    const attr = (entity ? ` data-more="${entity}" style="cursor:pointer"` : "") + (title ? ` title="${esc(title)}"` : "");
    return `<div class="row"${attr}><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`;
  }

  _loadText() {
    const d = this._d;
    if (d.sysLoad === null || d.sysLoad === undefined) return "—";
    const fst = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const cores = fst && fst.attributes && fst.attributes.cpu_count;
    return cores ? `${num(d.sysLoad, 2)} · ${tr("{p} % von {n} Kernen", { p: Math.round((d.sysLoad / cores) * 100), n: cores })}`
      : num(d.sysLoad, 2);
  }

  _toast(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  /** Call an integration service; errors are shown instead of swallowed. */
  async _call(service, data) {
    try {
      await this._hass.callService(DOMAIN, service, { ...data, ...this._entryData() }, undefined, false);
      return true;
    } catch (err) {
      alert((err && (err.message || err.error)) || String(err));
      return false;
    }
  }

  _reprint(idx) {
    const h = (this._d.history || [])[idx];
    if (!h) return;
    this._openPrint(h.source || h.file, { mapping: h.mapping, options: h.options, pause_layers: h.pause_layers });
  }
};
