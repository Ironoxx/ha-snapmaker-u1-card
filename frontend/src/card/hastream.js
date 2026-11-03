/**
 * Camera through Home Assistant's own streaming (2.0): RTSP (paxx12, H.264)
 * played with HA's <ha-camera-stream> – WebRTC via HA (also over Nabu Casa,
 * with its relay servers), else HLS.
 *
 * Used when the direct WebRTC to the printer is not possible (away from home
 * without VPN, Nabu Casa) and the camera entity offers a stream (RTSP). Far
 * less data than MJPEG through the HA proxy, so it is smooth away from home.
 * Without RTSP (stock firmware) nothing changes. Option camera_ha_stream:
 * "auto" (default) | "off".
 */

const HS_CONNECT_MS = 15000;           // first frame by then, else MJPEG
const HS_RETRY_MS = 10 * 60 * 1000;    // after a failure: MJPEG for this long

/** Nabu Casa remote access: a direct connection to the printer can never work there. */
export function remoteCloud() {
  return /\.ui\.nabu\.casa$/i.test(window.location.hostname || "");
}

export const HaStreamMixin = (Base) => class extends Base {
  _hsWanted(cam) {
    const v = this._cfg.camera_ha_stream;
    if (v === false || v === "off" || this._preview) return false;
    if (this._cfg.camera_mode === "still" || this._cfg.printer_image) return false;
    if (Date.now() < (this._hsFailUntil || 0)) return false;
    // CameraEntityFeature.STREAM (2): the integration found RTSP
    return !!(cam && (Number(cam.attributes.supported_features) & 2));
  }

  /** HA's stream element is loaded lazily by the frontend; a picture-entity card pulls it in. */
  async _hsLoad(camId) {
    if (customElements.get("ha-camera-stream")) return true;
    try {
      const helpers = window.loadCardHelpers && await window.loadCardHelpers();
      if (helpers) {
        const card = await helpers.createCardElement({ type: "picture-entity", entity: camId, camera_view: "live" });
        if (card) card.hass = this._hass;
      }
    } catch (e) { /* not available */ }
    await Promise.race([customElements.whenDefined("ha-camera-stream"), new Promise((r) => setTimeout(r, 5000))]);
    return !!customElements.get("ha-camera-stream");
  }

  /** Called from the camera tick when direct WebRTC is not in use. true = HA stream shows the picture. */
  _tickHaStream(frame, img, cam) {
    if (!this._hsWanted(cam)) { this._stopHaStream(); return false; }
    let hs = this._hs;
    if (hs && hs.cam !== this._ents.camera) { this._stopHaStream(); hs = null; }
    if (!hs) { this._startHaStream(frame, img, cam); return false; }
    if (!hs.el) return false;   // still loading the element
    hs.el.hass = this._hass;
    if (hs.el.parentNode !== frame) {
      frame.insertBefore(hs.el, img.nextSibling);
      if (hs.playing) frame.classList.add("rtc-on");
    }
    if (!hs.playing) {
      if (Date.now() - hs.started > HS_CONNECT_MS) this._hsFailed("timeout");
      return false;
    }
    // Liveness: the inner video's clock must move (open shadow roots)
    const video = this._hsVideo(hs.el);
    if (video) {
      const t = video.currentTime;
      if (t !== hs.lastTime) { hs.lastTime = t; this._lastChange = Date.now(); }
      if (Date.now() - this._lastChange > 20000) { this._hsFailed("frozen"); return false; }
    }
    return true;
  }

  _hsVideo(el) {
    const player = el.shadowRoot && el.shadowRoot.querySelector("ha-web-rtc-player, ha-hls-player");
    return (player && player.shadowRoot && player.shadowRoot.querySelector("video")) || null;
  }

  _startHaStream(frame, img, cam) {
    const hs = this._hs = { el: null, cam: this._ents.camera, playing: false, started: Date.now(), lastTime: -1 };
    this._hsLoad(this._ents.camera).then((ok) => {
      if (this._hs !== hs) return;
      if (!ok) { this._hsFailed("no ha-camera-stream"); return; }
      const el = document.createElement("ha-camera-stream");
      el.dataset.hastream = "";
      el.hass = this._hass;
      el.stateObj = this._st(this._ents.camera) || cam;
      el.muted = true;
      el.controls = false;
      el.fitMode = img.style.objectFit === "cover" ? "cover" : "contain";
      // both HA players fire "load" with the first frame
      el.addEventListener("load", () => {
        if (this._hs !== hs) return;
        hs.playing = true;
        this._lastChange = Date.now();
        const f = el.closest(".frame");
        if (f) f.classList.add("rtc-on");
        if (this._streamImg) this._stopStream();
        if (this._applyZoom) this._applyZoom();
      });
      hs.el = el;
      hs.started = Date.now();
      const f = this.shadowRoot && this.shadowRoot.querySelector(".stage .frame");
      const live = f && f.querySelector("img[data-live]");
      if (f && live) f.insertBefore(el, live.nextSibling);
    });
  }

  _hsFailed(why) {
    if (this._cfg.debug_camera) console.info("snapmaker-u1-card: HA stream off,", why);
    this._hsFailUntil = Date.now() + HS_RETRY_MS;
    this._stopHaStream();
  }

  _stopHaStream() {
    const hs = this._hs;
    if (!hs) return;
    this._hs = null;
    if (hs.el) {
      const frame = hs.el.closest(".frame");
      if (frame && !(this._rtc && this._rtc.playing)) frame.classList.remove("rtc-on");
      hs.el.remove();
    }
  }
};
