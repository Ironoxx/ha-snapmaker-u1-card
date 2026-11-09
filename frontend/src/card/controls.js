/** Actions, service calls, the control lock and small reusable UI building blocks. */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { LANG, tr } from "../i18n.js";

/** Card buttons → action/target of the integration's machine_command service. */
const OWN_BUTTONS = {
  pause_print: ["pause"], resume_print: ["resume"], cancel_print: ["cancel"],
  emergency_stop: ["emergency_stop"], home_all_axes: ["home", "all"],
  home_x_axis: ["home", "x"], home_y_axis: ["home", "y"], home_z_axis: ["home", "z"],
};

// 2.2: Snapmaker machine_state_manager, main state and step (names from machine_status.py)
export const MACHINE_MAIN = {
  xyz_offset_calibrate: "XYZ-Kalibrierung", bed_leveling: "Bettnivellierung", flow_calibration: "Flusskalibrierung",
  shaper_calibrate: "Resonanzmessung", upgrading: "Firmware-Update", abnormal: "Störung",
  screws_tilt_adjust: "Bett ausrichten", auto_load: "Filament wird geladen", auto_unload: "Filament wird entladen",
  manual_load: "Filament von Hand laden", park_point_calibration: "Dock-Position kalibrieren",
  homing_origin_calibration: "Nullpunkt kalibrieren",
};
export const MACHINE_STEP = {
  homing: "Referenzfahrt", detect_plate: "Platte wird erkannt", preheat_chamber: "Kammer heizt vor",
  print_restore: "Druck wird wiederhergestellt", print_resuming: "Druck wird fortgesetzt",
  print_replenishing: "Filament wird nachgefüllt", print_switch_checking: "Kopfwechsel wird geprüft",
  print_auto_feeding: "Filament wird eingezogen", print_preextruding: "Vorextrusion",
  print_auto_unloading: "Filament wird entladen", print_bed_detecting: "Bett wird geprüft",
  manual_clean_extruder: "Düse von Hand reinigen", xyz_offset_probe: "Versatz wird gemessen",
  auto_clean_nozzle: "Düse wird gereinigt", wait_nozzle_cooling: "Düse kühlt ab",
  bed_leveling: "Bett wird vermessen", bed_preheating: "Bett heizt vor", bed_prescanning: "Bett wird vorab gescannt",
  flow_calibrating: "Fluss wird gemessen", shaper_calibrating: "Resonanz wird gemessen",
  reset_to_initial: "Ausgangsstellung", probe_reference_points: "Referenzpunkte werden gemessen",
  manual_tuning: "Schrauben von Hand einstellen", probing_adjust_verify: "Ergebnis wird geprüft",
  auto_loading: "Filament wird geladen", auto_unloading: "Filament wird entladen",
  manual_loading: "Filament von Hand laden", park_point_calibrating: "Dock-Position wird kalibriert",
  extruder_pick_verify: "Aufnahme wird geprüft", extruder_park_verify: "Ablage wird geprüft",
  homing_origin_calibrating: "Nullpunkt wird kalibriert",
};

export const ControlsMixin = (Base) => class extends Base {
  _press(name) {
    const own = this._ownControl() && OWN_BUTTONS[name];
    if (own) this._machineCommand(...own);
    else this._hass.callService("button", "press", { entity_id: `button.${this._p(name)}` });
  }

  /** Key of a machine value for an entity id of the printer (``number.<prefix>_bed_target`` → ``bed_target``). */
  _machineKey(entity) {
    const m = this._ownControl() && this._machine();
    if (!m) return null;
    const dot = entity.indexOf(".");
    const key = dot > 0 && entity.startsWith(m.pre, dot) ? entity.slice(dot + m.pre.length) : null;
    return key && Object.prototype.hasOwnProperty.call(m.values, key) ? key : null;
  }

  _setNumber(entity, value) {
    // Changing the target temperature during a print asks first (0 °C = ruined print)
    if (this._d && this._d.active && /_target$/.test(entity)
      && !confirm(tr("Solltemperatur während des Drucks auf {v} °C ändern?", { v: Number(value) }))) {
      this._busy.delete(entity);
      this._patch();
      return;
    }
    const key = this._machineKey(entity);
    if (key) this._machineCommand("set", key, Number(value));
    else this._hass.callService("number", "set_value", { entity_id: entity, value: Number(value) });
  }

  // ── Pending commands ──────────────────────────────────────────────────────
  // Pause parks the head first and the Moonraker integration polls: without
  // feedback a tap looks ignored. A pending command shows at once that it was
  // sent ("Pausiere …", light already toggled) until the printer confirms it.
  /** key: "pause" | "resume" | "cancel" | "light" | "t:<entity>"; done(d) = confirmed. */
  _pend(key, done, ms = 30000, extra = {}) {
    if (!this._pending) this._pending = new Map();
    this._pending.set(key, { done, until: Date.now() + ms, ...extra });
    this._pendTimer();
    this._rerender();
  }

  /** One timer for the earliest expiry; none while nothing waits. */
  _pendTimer() {
    clearTimeout(this._pendT);
    this._pendT = null;
    if (!this._pending || !this._pending.size) return;
    const next = Math.min(...[...this._pending.values()].map((p) => p.until));
    this._pendT = setTimeout(() => {
      this._pendT = null;
      const before = this._lastPendKey;
      if (this._settlePending()) {
        if (this._pendingKey() !== before) this._rerender();
        else { this._applyPending(); this._patch(); }
      }
      this._pendTimer();
    }, Math.max(0, next - Date.now()) + 50);
  }

  _isPending(key) {
    const p = this._pending && this._pending.get(key);
    return !!p && p.until > Date.now();
  }

  /** Drop confirmed and expired commands; true = something changed. */
  _settlePending() {
    if (!this._pending || !this._pending.size || !this._d) return false;
    const now = Date.now();
    let changed = false;
    for (const [key, p] of this._pending) {
      let ok = false;
      try { ok = p.done(this._d); } catch (e) { ok = true; }
      if (ok || p.until <= now) {
        this._pending.delete(key);
        changed = true;
        if (!ok && p.timeout) this._toast(p.timeout);
      }
    }
    if (changed && !this._pending.size) this._pendTimer();
    return changed;
  }

  /** Optimistic values while a command is on its way (light). */
  _applyPending() {
    const d = this._d;
    if (!d) return;
    const l = this._pending && this._pending.get("light");
    d.light = l && l.until > Date.now() ? l.want : d.lightReal;
  }

  _rerender() {
    this._renderKey = null;
    if (this._d) this._render();
  }

  _pendingKey() {
    this._lastPendKey = this._pending ? [...this._pending.keys()].filter((k) => k !== "light" && !k.startsWith("t:")).join(",") : "";
    return this._lastPendKey;
  }

  _spin() {
    return `<span class="su1-spin" aria-hidden="true"></span>`;
  }

  /** Pause / resume / cancel / light as buttons, with a waiting state. */
  _stageActions() {
    const d = this._d;
    const busy = (key, cls, icon, label, wait) => this._isPending(key)
      ? `<button class="${cls} grow" disabled aria-busy="true">${this._spin()}${wait}</button>`
      : `<button class="${cls} grow" data-act="${key}"><ha-icon icon="${icon}"></ha-icon>${label}</button>`;
    const out = [];
    const cancelling = this._isPending("cancel");
    if (d.printing && !cancelling) out.push(busy("pause", "filled", "mdi:pause", tr("Pause"), tr("Pausiere …")));
    if (d.paused && !cancelling) out.push(busy("resume", "filled", "mdi:play", tr("Fortsetzen"), tr("Setze fort …")));
    if (d.active) out.push(busy("cancel", "outline", "mdi:stop", tr("Abbrechen"), tr("Breche ab …")));
    out.push(`<button class="${d.light ? "on" : "outline"} grow" data-act="light" data-su1="light"><ha-icon icon="mdi:lightbulb"></ha-icon>${tr("Licht")}</button>`);
    return out.join("");
  }

  _pausePrint() {
    this._press("pause_print");
    this._pend("pause", (d) => d.paused || !d.active, 90000,
      { timeout: tr("Der Drucker hat die Pause noch nicht bestätigt.") });
  }

  _resumePrint() {
    this._press("resume_print");
    this._pend("resume", (d) => d.printing || !d.active, 90000,
      { timeout: tr("Der Drucker hat das Fortsetzen noch nicht bestätigt.") });
  }

  _cancelPrint() {
    this._press("cancel_print");
    this._pend("cancel", (d) => !d.active, 120000,
      { timeout: tr("Der Drucker hat den Abbruch noch nicht bestätigt.") });
  }

  _toggleLight() {
    const want = !this._d.light;
    const light = `light.${this._p("led_cavity_led")}`;
    if (this._machineKey(light)) this._machineCommand("switch", "led_cavity_led", want);
    else this._hass.callService("light", "toggle", { entity_id: light });
    // Patched in place: a rebuild would reconnect the camera stream
    if (!this._pending) this._pending = new Map();
    this._pending.set("light", { done: (d) => d.lightReal === want, until: Date.now() + 15000, want });
    this._pendTimer();
    this._applyPending();
    this._patch();
  }

  /** Switch toggles (heater, filter): spinner until the entity has changed. */
  _toggleEntity(id, btn) {
    const before = this._s(id);
    const key = this._machineKey(id);
    if (key && /^(output_pin|led)_/.test(key)) this._machineCommand("switch", key, before !== "on");
    else this._hass.callService(id.split(".")[0], "toggle", { entity_id: id });
    if (!this._pending) this._pending = new Map();
    this._pending.set(`t:${id}`, { done: () => this._s(id) !== before, until: Date.now() + 15000 });
    this._pendTimer();
    if (btn) btn.classList.add("pending");
  }

  /** Take the head's previous spool again (one tap, after reloading the filament). */
  async _restoreSpool(idx, spoolId) {
    this._pend(`r:${idx}`, () => {
      const sm = this._spoolman();
      return !sm || !(sm.restore || {})[String(idx)];
    }, 20000);
    try {
      await this._hass.callService(DOMAIN, "set_spool", { slot: idx + 1, spool_id: spoolId, ...this._entryData() }, undefined, false);
    } catch (err) {
      if (this._pending) this._pending.delete(`r:${idx}`);
      this._rerender();
      alert((err && (err.message || err.error)) || String(err));
    }
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
    // values from the integration without a Moonraker entity: no more-info dialog to open
    if (this._hass && !this._hass.states[entityId]) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      detail: { entityId }, bubbles: true, composed: true,
    }));
  }

  // ── Building blocks ──────────────────────────────────────────────────────
  _statusTone() {
    const d = this._d;
    if (!d.online) return "off";
    if (d.state === "error") return "error";
    const ms = this._machineState();
    if (ms && ms.main === "abnormal") return "error";
    if (ms && ms.needsUser) return "warn";
    if (ms && !d.active && ms.main !== "idle" && ms.main !== "printing") return "active";
    if (d.paused) return "warn";
    if (d.printing) return "active";
    if (d.state === "complete") return "ok";
    return "idle";
  }

  _statusLabel() {
    const d = this._d;
    if (!d.online) return tr("Offline");
    if (this._isPending("cancel")) return tr("Breche ab …");
    if (this._isPending("pause")) return tr("Pausiere …");
    if (this._isPending("resume")) return tr("Setze fort …");
    // 2.2: outside a print the firmware says what it is doing (calibration, loading …)
    const busy = !d.active && this._machineText();
    if (busy) return busy;
    return {
      printing: tr("Druckt"), standby: tr("Bereit"), complete: tr("Fertig"),
      cancelled: tr("Abgebrochen"), paused: tr("Pausiert"), error: tr("Fehler"),
    }[d.state] || d.state;
  }

  /** 2.2: "XYZ calibration · nozzle cooling down" from the machine state, or "" when idle. */
  _machineText(withStep = true) {
    const ms = this._machineState();
    if (!ms || ms.main === "idle" || ms.main === "printing") return "";
    const main = MACHINE_MAIN[ms.main] ? tr(MACHINE_MAIN[ms.main]) : ms.main;
    let step = withStep && ms.action && ms.action !== "idle" && MACHINE_STEP[ms.action] ? tr(MACHINE_STEP[ms.action]) : "";
    if (step && ms.head !== null) step += ` (${(this._d.heads[ms.head] || {}).name || `E${ms.head}`})`;
    return step && step !== main ? `${main} · ${step}` : main;
  }

  /**
   * Spool icon. fill (0–1, from Spoolman: remaining / net weight) sets how thick the
   * filament ring is, roughly – 10 % left is a thin ring on the core. spinning:
   * the head is printing right now (turns slowly, still with reduced motion off).
   */
  _spoolSvg(color, active, colors = null, fill = null, spinning = false) {
    // Multi-colour spools (silk, rainbow) as segments on the ring.
    const list = colors && colors.length > 1 ? colors : [color];
    const known = typeof fill === "number" && Number.isFinite(fill);
    const f = known ? Math.max(0, Math.min(1, fill)) : null;
    // core r 12; full spool up to r 27 (flange 28); unknown: the classic ring 12–22
    const inner = 12.5, outer = f === null ? 22 : inner + Math.max(f > 0 ? 1.6 : 0, f * 14.5);
    const r = (inner + outer) / 2, w = outer - inner;
    const C = 2 * Math.PI * r;
    const seg = C / list.length;
    const ring = w > 0 ? list.map((c, k) =>
      `<circle cx="30" cy="30" r="${r.toFixed(2)}" fill="none" stroke="${esc(c)}" stroke-width="${w.toFixed(2)}"
        stroke-dasharray="${seg.toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="${(-k * seg).toFixed(2)}"
        transform="rotate(-90 30 30)"/>`).join("") : "";
    // three holes in the hub show the turning
    const holes = [0, 120, 240].map((a) => {
      const rad = (a - 90) * Math.PI / 180;
      return `<circle cx="${(30 + 8 * Math.cos(rad)).toFixed(2)}" cy="${(30 + 8 * Math.sin(rad)).toFixed(2)}" r="1.6" fill="var(--u1-panel-highest)"/>`;
    }).join("");
    const title = f !== null ? `<title>${tr("Spule zu {p} % voll", { p: Math.round(f * 100) })}</title>` : "";
    // 2.2: a light edge around the filament, so black (and on light themes white) spools stand out
    const edge = w > 0 ? `<circle cx="30" cy="30" r="${(outer + 0.5).toFixed(2)}" fill="none" class="spool-edge" stroke-width="1.2"/>` : "";
    return `<svg class="spool${spinning ? " spin" : ""}" viewBox="0 0 60 60" ${title ? 'role="img"' : 'aria-hidden="true"'} data-fill="${f === null ? "" : Math.round(f * 100)}">
      ${title}
      <circle cx="30" cy="30" r="28" fill="var(--u1-panel)" stroke="var(--u1-outline)" stroke-width="1.5"/>
      <g class="spool-rot">
        ${ring}
        ${edge}
        ${f === null ? `<circle cx="30" cy="30" r="22" fill="none" stroke="var(--u1-on-variant)" stroke-opacity=".35" stroke-width="1"/>
        <circle cx="30" cy="30" r="19" fill="none" stroke="rgba(0,0,0,.18)" stroke-width="1.4"/>` : ""}
        <circle cx="30" cy="30" r="12" fill="var(--u1-panel)" class="spool-hub"/>
        ${holes}
        <circle cx="30" cy="30" r="4" fill="var(--u1-panel-highest)"/>
      </g>
      ${active ? `<circle cx="30" cy="30" r="28" fill="none" stroke="var(--u1-primary)" stroke-width="2.5"/>` : ""}
    </svg>`;
  }

  /** Spoolman fill level of the spool in head idx (0–1), or null. */
  _spoolFill(idx) {
    const sp = this._slotSpool(idx);
    if (!sp || sp.remaining_weight == null || !(sp.initial_weight > 0)) return null;
    return sp.remaining_weight / sp.initial_weight;
  }

  _slider(opts) {
    const { entity, label, min, max, step, value, unit, presets, dec } = opts;
    const st = this._st(entity);
    if (!st) return "";
    const mn = min ?? st.attributes.min ?? 0;
    const mx = max ?? st.attributes.max ?? 100;
    const sp = step ?? st.attributes.step ?? 1;
    const chips = (presets || []).map(
      (p) => `<button class="preset" data-set="${entity}" data-value="${p}" aria-pressed="${Number(value) === Number(p)}">${p}${unit ? " " + unit : ""}</button>`
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
