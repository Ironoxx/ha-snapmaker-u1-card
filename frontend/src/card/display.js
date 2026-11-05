/**
 * Printer display (paxx12 mirror, see screen.py), only when the integration found it.
 * display_tab: own tab (default on). display_camera: one more step of the camera switch.
 * Touch: admins only, switched on with the hand button, off again after the control
 * lock time without input ("off" = 60 s, so it is never left open for good).
 */

import { DOMAIN } from "../const.js";
import { tr } from "../i18n.js";

const POLL_MS = 700;        // picture rate while idle
const POLL_TOUCH_MS = 200;  // picture rate right after a touch
const TOUCH_FAST_MS = 2500; // how long the fast rate lasts
const MOVE_EVERY_MS = 60;   // throttle for move events
const LOAD_TIMEOUT_MS = 5000;
const TOUCH_IDLE_OFF_S = 60; // controls_lock "off": the display still switches touch off

export const DisplayMixin = (Base) => class extends Base {
  /** {width, height} of the panel, or null without a display mirror. */
  _screenInfo() {
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const s = st && st.attributes && st.attributes.screen;
    return s && s.width > 0 && s.height > 0 && this._entryData().config_entry_id ? s : null;
  }

  _displayTab() {
    return this._cfg.display_tab !== false && !!this._screenInfo();
  }

  /** The display as additional "camera" of the stage (only the card's own cameras). */
  _displayAsCamera() {
    return this._cfg.display_camera === true && !this._cfg.camera && !this._cfg.printer_image && !!this._screenInfo();
  }

  _camSwitchable() {
    return this._hasCamera2() || this._displayAsCamera();
  }

  /**
   * At most the panel's own size (no upscaling on a wide dashboard), smaller on a
   * phone: as wide as the card allows, and never taller than maxH.
   */
  _displaySize(s, maxH) {
    return `aspect-ratio:${s.width} / ${s.height};max-width:min(${s.width}px, calc(${maxH} * ${s.width} / ${s.height}))`;
  }

  _sectionDisplay() {
    const s = this._screenInfo();
    if (!s) return "";
    return `
      <section class="panel span2 display">
        <div class="panel-head">
          <ha-icon icon="mdi:monitor-screenshot"></ha-icon>
          <span class="panel-title">${tr("Druckerdisplay")}</span>
          ${this._displayTouchBtn()}
        </div>
        <div class="display-frame" data-display style="${this._displaySize(s, "70vh")}">
          <img data-display-img alt="${tr("Druckerdisplay")}" draggable="false" />
        </div>
        <div class="t-label" data-display-hint>${this._displayHint()}</div>
      </section>`;
  }

  /** Stage showing the display (display_camera): no camera overlays, same buttons. */
  _stageDisplay() {
    const s = this._screenInfo();
    const full = document.fullscreenEnabled || document.webkitFullscreenEnabled;
    const hand = this._isAdmin() ? `<button type="button" class="zoom-btn" data-display-touch aria-pressed="${this._displayTouchOn()}"
        title="${this._displayTouchTitle()}" aria-label="${this._displayTouchTitle()}"><ha-icon icon="mdi:gesture-tap"></ha-icon></button>` : "";
    return `
      <section class="panel stage span2">
        <div class="display-frame stage-display" data-display
             style="${this._displaySize(s, `${parseInt(this._cfg.camera_max_height, 10) || 520}px`)}">
          <img data-display-img alt="${tr("Druckerdisplay")}" draggable="false" />
          <div class="zoom-ctl">
            ${hand}
            ${full ? `<button type="button" class="zoom-btn" data-display-full title="${tr("Vollbild")}" aria-label="${tr("Vollbild")}"><ha-icon icon="mdi:fullscreen"></ha-icon></button>` : ""}
            <button type="button" class="zoom-btn" data-camswitch title="${tr("Kamera wechseln")}" aria-label="${tr("Kamera wechseln")}" aria-pressed="true"><ha-icon icon="mdi:camera-switch-outline"></ha-icon></button>
          </div>
        </div>
        <div class="stage-actions">${this._stageActions()}</div>
      </section>`;
  }

  // ── Touch on/off (hand button) ─────────────────────────────────────────
  _displayIdleMs() {
    const m = this._lockMode();
    if (m === "manual") return Infinity;
    return (m === "off" ? TOUCH_IDLE_OFF_S : m) * 1000;
  }

  _displayTouchOn() {
    return this._isAdmin() && this._dispUntil > Date.now();
  }

  _displayTouchTitle() {
    return this._displayTouchOn() ? tr("Bedienung ausschalten") : tr("Display bedienen");
  }

  _displayTouchLabel() {
    return this._displayTouchOn() ? tr("Bedienung an") : tr("Bedienen");
  }

  _displayTouchBtn() {
    if (!this._isAdmin()) return "";
    return `<button type="button" class="chip sm lock-btn" data-display-touch aria-pressed="${this._displayTouchOn()}" style="margin-left:auto"
        title="${this._displayTouchTitle()}">
        <ha-icon icon="mdi:gesture-tap"></ha-icon><span>${this._displayTouchLabel()}</span>
      </button>`;
  }

  _displayHint() {
    if (!this._isAdmin()) return tr("Nur Admins können das Display bedienen.");
    if (!this._displayTouchOn()) return tr("Zum Bedienen die Hand antippen.");
    const ms = this._displayIdleMs();
    return ms === Infinity ? tr("Tippen und Wischen gehen an das Display.")
      : tr("Tippen und Wischen gehen an das Display. Aus nach {n} s ohne Bedienung.", { n: Math.round(ms / 1000) });
  }

  _toggleDisplayTouch() {
    this._dispUntil = this._displayTouchOn() ? 0 : Date.now() + this._displayIdleMs();
    this._dispDown = null;
    this._applyDisplayTouch();
  }

  /** Update buttons, hints and frames in place (no rebuild: the picture stays). */
  _applyDisplayTouch() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    if (!r) return;
    const on = this._displayTouchOn();
    r.querySelectorAll("[data-display-touch]").forEach((b) => {
      b.setAttribute("aria-pressed", String(on));
      b.title = this._displayTouchTitle();
      if (b.hasAttribute("aria-label")) b.setAttribute("aria-label", b.title);
      const label = b.querySelector("span");
      if (label) label.textContent = this._displayTouchLabel();
    });
    r.querySelectorAll("[data-display-hint]").forEach((h) => { h.textContent = this._displayHint(); });
    r.querySelectorAll("[data-display]").forEach((f) => f.classList.toggle("touch", on));
  }

  // ── Picture ────────────────────────────────────────────────────────────
  /** Called every second by the card: switch touch off when idle, keep the picture going. */
  _tickDisplay() {
    if (this._dispUntil && Date.now() > this._dispUntil) {
      this._dispUntil = 0;
      this._dispDown = null;
      this._applyDisplayTouch();
    }
    if (!this._dispTimer) this._pollDisplay();
  }

  /** Display pictures on screen right now (tab and/or stage). */
  _displayImgs() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    if (!r || !this._onScreen || document.hidden || !this.isConnected) return [];
    return [...r.querySelectorAll("img[data-display-img]")].filter((img) => {
      const pane = img.closest("[data-pane]");
      return !(pane && pane.hidden);
    });
  }

  _pollDisplay() {
    this._dispTimer = null;
    const imgs = this._displayImgs();
    const h = this._hass;
    if (!imgs.length || !h || typeof h.fetchWithAuth !== "function") return; // the card tick starts it again
    const now = Date.now();
    const every = now - (this._dispTouchAt || 0) < TOUCH_FAST_MS ? POLL_TOUCH_MS : POLL_MS;
    this._dispTimer = setTimeout(() => this._pollDisplay(), every);
    if (this._dispLoading && now - this._dispLoadStart < LOAD_TIMEOUT_MS) return;
    this._dispLoading = true;
    this._dispLoadStart = now;
    h.fetchWithAuth(`/api/${DOMAIN}/screen/${this._entryData().config_entry_id}/snapshot`)
      .then((res) => (res.ok ? res.blob() : null))
      .then((blob) => { if (blob) this._showDisplay(imgs.filter((i) => i.isConnected), blob); })
      .catch(() => {})
      .finally(() => { this._dispLoading = false; });
  }

  // Decode first, then swap: the old picture stays until the new one is ready.
  _showDisplay(imgs, blob) {
    if (!imgs.length) return;
    const url = URL.createObjectURL(blob);
    const pre = new Image();
    pre.onload = () => {
      const old = this._dispUrl;
      imgs.forEach((img) => { img.src = url; });
      this._dispUrl = url;
      if (old) URL.revokeObjectURL(old);
    };
    pre.onerror = () => URL.revokeObjectURL(url);
    pre.src = url;
  }

  // ── Touch ──────────────────────────────────────────────────────────────
  _wireDisplay(r) {
    r.querySelectorAll("[data-display-touch]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._toggleDisplayTouch(); }));
    r.querySelectorAll("[data-display-full]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._fullscreen(b.closest("[data-display]")); }));
    r.querySelectorAll("[data-display]").forEach((frame) => {
      frame.classList.toggle("touch", this._displayTouchOn());
      frame.addEventListener("pointerdown", (e) => this._displayPointer("down", e, frame));
      frame.addEventListener("pointermove", (e) => this._displayPointer("move", e, frame));
      frame.addEventListener("pointerup", (e) => this._displayPointer("up", e, frame));
      frame.addEventListener("pointercancel", (e) => this._displayPointer("up", e, frame));
    });
  }

  /** Panel pixel under the pointer, or null outside the picture. */
  _displayPoint(e, img) {
    const s = this._screenInfo();
    const nw = img.naturalWidth || (s && s.width), nh = img.naturalHeight || (s && s.height);
    if (!nw || !nh) return null;
    const r = img.getBoundingClientRect();
    const scale = Math.min(r.width / nw, r.height / nh);
    if (!(scale > 0)) return null;
    const x = Math.floor((e.clientX - r.left - (r.width - nw * scale) / 2) / scale);
    const y = Math.floor((e.clientY - r.top - (r.height - nh * scale) / 2) / scale);
    return x >= 0 && y >= 0 && x < nw && y < nh ? { x, y } : null;
  }

  _displaySend(a, p) {
    this._dispTouchAt = Date.now();
    this._dispUntil = Date.now() + this._displayIdleMs(); // interaction keeps touch on
    // Keep the order: a move must never overtake its down or up.
    this._dispQueue = (this._dispQueue || Promise.resolve())
      .then(() => this._hass.callApi("POST", `${DOMAIN}/screen/${this._entryData().config_entry_id}/touch`,
        { a, x: p.x, y: p.y }))
      .catch(() => {});
    if (!this._dispTimer) this._pollDisplay();
  }

  _displayPointer(kind, e, frame) {
    if (!this._displayTouchOn()) { this._dispDown = null; return; }
    const img = frame.querySelector("img[data-display-img]");
    const d = this._dispDown;
    if (kind === "down") {
      if (e.target && e.target.closest && e.target.closest("button")) return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      const p = img && this._displayPoint(e, img);
      if (!p) return;
      e.preventDefault();
      try { frame.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      this._dispDown = { id: e.pointerId, p, at: 0 };
      this._displaySend("down", p);
      return;
    }
    if (!d || d.id !== e.pointerId) return;
    // Outside the picture: keep the last point instead of dropping the gesture
    const p = (img && this._displayPoint(e, img)) || d.p;
    if (kind === "move") {
      const now = Date.now();
      if (now - d.at < MOVE_EVERY_MS || (p.x === d.p.x && p.y === d.p.y)) return;
      d.at = now;
      d.p = p;
      this._displaySend("move", p);
      return;
    }
    this._dispDown = null;
    this._displaySend("up", p);
  }
};
