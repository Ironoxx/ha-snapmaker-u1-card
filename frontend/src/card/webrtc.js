/**
 * Camera over WebRTC (paxx12 Extended Firmware, camera-streamer protocol).
 *
 * Lower delay and far less data than MJPEG. The printer sends no CORS
 * headers, so the few signalling messages go through the integration
 * (/api/snapmaker_u1_card/webrtc/<entry>); the video flows directly between
 * browser and printer. That works at home and over a VPN; where no direct
 * path exists (away without VPN) the connection fails and the card stays on
 * MJPEG for a while. Option camera_webrtc: "auto" (default) | "off".
 */

import { DOMAIN } from "../const.js";

const RTC_CONNECT_MS = 8000;          // first frame must arrive by then
const RTC_RETRY_MS = 10 * 60 * 1000;  // after a failure: MJPEG for this long

export const WebrtcMixin = (Base) => class extends Base {
  _rtcWanted() {
    const v = this._cfg.camera_webrtc;
    if (v === false || v === "off" || this._preview) return false;
    if (this._cfg.camera_mode === "still" || this._cfg.printer_image) return false;
    if (typeof window.RTCPeerConnection !== "function") return false;
    if (this._ents && this._ents.camAlt) return false; // second camera: MJPEG
    if (Date.now() < (this._rtcFailUntil || 0)) return false;
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    return !!(st && st.attributes && st.attributes.webrtc && st.attributes.entry_id);
  }

  /** Called from the camera tick. true = WebRTC is showing the picture. */
  _tickRtc(frame, img) {
    if (!this._rtcWanted()) { this._stopRtc(); return false; }
    const rtc = this._rtc;
    if (!rtc) { this._startRtc(frame, img); return false; }
    // The card was rebuilt: take the running video into the new frame
    if (rtc.video.parentNode !== frame) {
      frame.insertBefore(rtc.video, img.nextSibling);
      if (rtc.playing) frame.classList.add("rtc-on");
      const p = rtc.video.play && rtc.video.play();
      if (p && p.catch) p.catch(() => {});
    }
    rtc.video.style.objectFit = img.style.objectFit;
    if (!rtc.playing) {
      if (Date.now() - rtc.started > RTC_CONNECT_MS) this._rtcFailed("timeout");
      return false;
    }
    // Liveness: the video clock must move
    const t = rtc.video.currentTime;
    if (t !== rtc.lastTime) { rtc.lastTime = t; this._lastChange = Date.now(); }
    frame.dataset.stale = (Date.now() - this._lastChange) / 1000 > (this._cfg.stale_after || 90) ? "1" : "0";
    if (Date.now() - this._lastChange > 15000) { this._rtcFailed("frozen"); return false; }
    return true;
  }

  async _rtcSignal(body) {
    const st = this._st(this._ents.files);
    return this._hass.callApi("POST", `${DOMAIN}/webrtc/${st.attributes.entry_id}`, body);
  }

  _startRtc(frame, img) {
    const video = document.createElement("video");
    video.dataset.rtc = "";
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("aria-label", img.getAttribute("alt") || "");
    video.style.objectFit = img.style.objectFit;
    const rtc = this._rtc = { video, pc: null, playing: false, started: Date.now(), lastTime: -1, id: null };
    frame.insertBefore(video, img.nextSibling);
    video.addEventListener("playing", () => {
      if (this._rtc !== rtc) return;
      rtc.playing = true;
      this._lastChange = Date.now();
      frame.classList.add("rtc-on");
      if (video.videoWidth && video.videoHeight && !parseInt(this._cfg.camera_height, 10)) {
        const ratio = `${video.videoWidth} / ${video.videoHeight}`;
        if (ratio !== this._camAspect) { this._camAspect = ratio; frame.style.aspectRatio = ratio; }
      }
      // MJPEG is no longer needed while WebRTC runs (saves the printer's CPU and the network)
      if (this._streamImg) this._stopStream();
      if (this._applyZoom) this._applyZoom();
    });
    this._connectRtc(rtc).catch((err) => { if (this._rtc === rtc) this._rtcFailed(err); });
  }

  async _connectRtc(rtc) {
    const offer = await this._rtcSignal({ type: "request", iceServers: [] });
    if (this._rtc !== rtc) return;
    if (!offer || !offer.sdp) throw new Error("no offer");
    rtc.id = offer.id;
    const pc = rtc.pc = new RTCPeerConnection({ iceServers: offer.iceServers || [] });
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.ontrack = (e) => { if (e.streams && e.streams[0]) rtc.video.srcObject = e.streams[0]; };
    pc.ondatachannel = (e) => {
      if (e.channel && e.channel.label === "keepalive") e.channel.onmessage = () => { try { e.channel.send("pong"); } catch (x) { /* closed */ } };
    };
    pc.onicecandidate = (e) => {
      if (e.candidate && rtc.id != null && this._rtc === rtc) {
        this._rtcSignal({ type: "remote_candidate", id: rtc.id, candidates: [e.candidate.toJSON ? e.candidate.toJSON() : e.candidate] })
          .catch(() => {});
      }
    };
    pc.onconnectionstatechange = () => {
      if (this._rtc !== rtc) return;
      if (pc.connectionState === "failed" || pc.connectionState === "closed") this._rtcFailed(pc.connectionState);
    };
    await pc.setRemoteDescription({ type: offer.type || "offer", sdp: offer.sdp });
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    if (this._rtc !== rtc) return;
    await this._rtcSignal({ type: "answer", id: rtc.id, sdp: pc.localDescription.sdp });
  }

  _rtcFailed(why) {
    if (this._cfg.debug_camera) console.info("snapmaker-u1-card: WebRTC off,", why);
    this._rtcFailUntil = Date.now() + RTC_RETRY_MS;
    this._stopRtc();
  }

  _stopRtc() {
    const rtc = this._rtc;
    if (!rtc) return;
    this._rtc = null;
    try { if (rtc.pc) rtc.pc.close(); } catch (e) { /* already closed */ }
    try { rtc.video.srcObject = null; } catch (e) { /* ignore */ }
    const frame = rtc.video.closest(".frame");
    if (frame) frame.classList.remove("rtc-on");
    rtc.video.remove();
  }
};
