/** Camera: MJPEG stream with liveness check, still image fallback, wake-up and auto height. */

import { BLANK, DOMAIN } from "../const.js";

// Image unchanged this long while visible: ask the printer to restart the camera.
const WAKE_AFTER_MS = 15000;
const WAKE_EVERY_MS = 10000;
// First frame must arrive within this time, otherwise the next source is used.
const PROVE_DIRECT_MS = 4000;
const PROVE_PROXY_MS = 6000;
// After a failed direct stream the card stays on the HA proxy this long.
const DIRECT_RETRY_MS = 10 * 60 * 1000;

export const CameraMixin = (Base) => class extends Base {
  // The camera entity stays "idle" permanently; its last_updated says nothing
  // about the picture. So frames are compared heavily downscaled: as long as
  // even the sensor noise changes, the feed is alive.
  _frameHash(img) {
    // Without a decoded image drawImage draws nothing and the hash would be the
    // one of an empty canvas; that must not count as a sign of life.
    if (!img || !img.naturalWidth) return null;
    try {
      const c = this._canvas || (this._canvas = document.createElement("canvas"));
      c.width = 32; c.height = 24;
      const ctx = c.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(img, 0, 0, 32, 24);
      const px = ctx.getImageData(0, 0, 32, 24).data;
      let h = 2166136261;
      for (let i = 0; i < px.length; i += 4) { h ^= px[i]; h = Math.imul(h, 16777619); }
      return h >>> 0;
    } catch {
      return null;
    }
  }

  _markFresh(src, target) {
    const h = this._frameHash(src);
    if (h === null) { this._lastChange = Date.now(); return; }
    if (h !== this._lastHash) { this._lastHash = h; this._lastChange = Date.now(); }
    const frame = target.closest(".frame");
    if (frame) {
      const idle = (Date.now() - this._lastChange) / 1000;
      frame.dataset.stale = idle > (this._cfg.stale_after || 90) ? "1" : "0";
    }
  }

  /** Automatic image height: aspect ratio from the real image size. */
  _fitAspect(img) {
    if (parseInt(this._cfg.camera_height, 10) || !img || !img.naturalWidth || !img.naturalHeight) return;
    const ratio = `${img.naturalWidth} / ${img.naturalHeight}`;
    if (ratio === this._camAspect) return;
    this._camAspect = ratio;
    const frame = img.closest(".frame");
    if (frame) frame.style.aspectRatio = ratio;
  }

  _tickCamera() {
    const root = this.shadowRoot?.getElementById("u1card");
    if (root) this._fitAspect(root.querySelector(".stage .frame > img"));
    const img = root?.querySelector("img[data-live]");
    if (!img) return;
    const cam = this._st(this._ents && this._ents.camera);
    if (!cam || !cam.attributes.entity_picture) return;
    const pane = img.closest("[data-pane]");
    if (document.hidden || !this._onScreen || (pane && pane.hidden)) {
      if (this._streamImg) this._stopStream();
      return;
    }

    const wantStream = this._cfg.camera_mode !== "still" && !this._preview
      && Date.now() >= this._streamFailUntil;
    if (wantStream) {
      this._tickStream(img, cam);
      return;
    }
    if (this._streamImg) this._stopStream();
    this._tickStill(img, cam);
    if (Date.now() - this._lastChange > WAKE_AFTER_MS) this._wakeCamera();
  }

  // Stock firmware stops the camera after a while unless the Snapmaker app
  // keeps calling camera.start_monitor. While the card is visible and the
  // image does not move (no stream, frozen stream, unchanged still image) it
  // asks the integration for one wake-up call, at most every 10 s. Option
  // camera_wake: false turns it off.
  _wakeCamera() {
    if (this._cfg.camera_wake === false || this._preview || !this._hass) return;
    const svc = this._hass.services && this._hass.services[DOMAIN];
    if (!svc || !svc.camera_wake || !this._d || !this._d.online) return;
    const now = Date.now();
    if (now - (this._wakeAt || 0) < WAKE_EVERY_MS) return;
    this._wakeAt = now;
    try {
      const p = this._hass.callService(DOMAIN, "camera_wake", this._entryData());
      if (p && p.catch) p.catch(() => {});
    } catch { /* service missing: nothing to do */ }
  }

  // ── Stream ────────────────────────────────────────────────────────────────
  // HA tunnels the camera entity's MJPEG stream over its own connection.
  // The access_token rotates about every 5 minutes; an already open
  // connection is not affected, so the URL is only set when (re)connecting,
  // not on every token change.
  _streamUrl(cam) {
    const token = cam.attributes.access_token;
    if (!token) return null;
    return `/api/camera_proxy_stream/${this._ents.camera}?token=${encodeURIComponent(token)}`;
  }

  /**
   * Direct MJPEG stream from the printer (option camera_direct, default auto):
   * no hop through Home Assistant, so less delay and no load on HA. Skipped
   * when the page is https (the browser blocks an http stream there) and for
   * a while after it failed, e.g. away from home; then the HA proxy is used.
   */
  _directUrl() {
    const mode = this._cfg.camera_direct;
    if (mode === false || mode === "off" || this._preview) return null;
    if (Date.now() < (this._directFailUntil || 0)) return null;
    // Own camera entity without a live stream (stock firmware, snapshots only):
    // there is no printer stream to load directly.
    if (this._ents && this._ents.ownCamera) {
      const own = this._st(this._ents.ownCamera);
      if (!own || own.attributes.mode !== "live") return null;
    }
    const custom = typeof this._cfg.camera_direct_url === "string" ? this._cfg.camera_direct_url.trim() : "";
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const url = custom || (st && st.attributes && st.attributes.stream_url);
    if (!url) return null;
    if (window.location.protocol === "https:" && /^http:/i.test(url)) return null;
    return url;
  }

  _directFailed() {
    this._directFailUntil = Date.now() + DIRECT_RETRY_MS;
    this._streamImg = null;      // next tick connects through the HA proxy
    this._streamDirect = false;
    this._streamProven = false;
  }

  _tickStream(img, cam) {
    const now = Date.now();

    if (this._streamImg !== img) {
      const direct = this._directUrl();
      const url = direct || this._streamUrl(cam);
      if (!url) { this._fallback(img, cam); return; }
      this._streamDirect = !!direct;
      // The previous image stays visible until the stream delivers its first
      // frame (the browser only swaps once the new image is there).
      this._preHash = this._frameHash(img);
      this._streamImg = img;
      this._streamProven = false;
      this._streamStart = now;
      this._lastCheck = now;
      img.onload = () => { if (this._streamImg === img) this._proveStream(); };
      img.onerror = () => {
        if (this._streamImg !== img) return;
        if (this._streamDirect) this._directFailed();
        else this._fallback(img, cam);
      };
      img.src = url;
      return;
    }

    // First frame not confirmed yet: check via image comparison whether
    // anything happened (a direct stream is cross-origin and cannot be
    // compared; it is proven by its load event). If nothing arrives in time,
    // direct falls back to the HA proxy and the proxy to still images; the
    // proxy can keep the connection open without ever sending a frame.
    if (!this._streamProven) {
      const h = this._frameHash(img);
      if (h !== null && h !== this._preHash) { this._proveStream(); return; }
      const age = now - this._streamStart;
      if (this._streamDirect) {
        if (age > PROVE_DIRECT_MS) this._directFailed();
        return;
      }
      if (age > PROVE_PROXY_MS / 2) this._wakeCamera();
      if (age > PROVE_PROXY_MS) this._fallback(img, cam);
      return;
    }

    // Liveness check on a coarse tick. If the stream hangs longer than
    // stale_after without an image change, it is rebuilt once.
    if (now - this._lastCheck < Math.max(2, this._cfg.stream_check || 10) * 1000) return;
    this._lastCheck = now;
    this._markFresh(img, img);
    if (now - this._lastChange > WAKE_AFTER_MS) this._wakeCamera();
    if ((now - this._lastChange) / 1000 > (this._cfg.stale_after || 90)) {
      this._streamImg = null;   // the next tick reconnects, the image stays
      this._lastChange = now;
    }
  }

  _proveStream() {
    this._streamProven = true;
    this._failCount = 0;
    this._lastChange = Date.now();
    this._lastHash = null;
  }

  // Drop the stream and fetch a still image right away; the request replaces
  // the stream in the same <img>, so an empty area is never shown.
  // Repeated failures extend the pause: 15 s, 30 s, 60 s ... 5 min.
  _fallback(img, cam) {
    this._streamImg = null;
    this._streamDirect = false;
    this._streamProven = false;
    if (img) { img.onload = null; img.onerror = null; }
    const wait = Math.min(15000 * 2 ** this._failCount, 300000);
    this._failCount = Math.min(this._failCount + 1, 5);
    this._streamFailUntil = Date.now() + wait;
    this._wakeCamera();
    if (img && cam) this._tickStill(img, cam, true);
  }

  _stopStream() {
    const img = this._streamImg;
    this._streamImg = null;
    this._streamProven = false;
    if (img) {
      img.onload = null;
      img.onerror = null;
      // removeAttribute("src") does not end MJPEG in every browser; open
      // connections then fill the limit of 6 per host (HTTP/1.1) and the
      // image freezes. A data: image reliably aborts the request.
      img.src = BLANK;
    }
  }

  // ── Still image (mode still or fallback) ──────────────────────────────────
  _tickStill(img, cam, force = false) {
    const now = Date.now();
    const every = Math.max(this._preview ? 10 : 1, this._cfg.refresh || 2);
    if (!force && now - this._lastStill < every * 1000) return;
    if (this._loading && !force && now - this._loadStart < 15000) return;
    this._lastStill = now;
    this._loadStart = now;

    const sep = cam.attributes.entity_picture.includes("?") ? "&" : "?";
    const url = `${cam.attributes.entity_picture}${sep}_=${Date.now()}`;

    // Double buffering: load and decode first, then swap. Setting img.src
    // directly shows nothing between dropping and finishing the load.
    this._loading = true;
    const pre = new Image();
    const done = () => { this._loading = false; };
    pre.onload = () => {
      const swap = () => { img.src = url; this._markFresh(pre, img); done(); };
      if (pre.decode) pre.decode().then(swap).catch(swap);
      else swap();
    };
    pre.onerror = () => { done(); this._wakeCamera(); };
    pre.src = url;
  }
};
