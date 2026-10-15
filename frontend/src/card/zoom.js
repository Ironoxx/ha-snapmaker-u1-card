/** Camera zoom and pan (pinch, drag, double tap, Ctrl+wheel) and fullscreen. */

import { clamp, fixed } from "../format.js";

export const ZoomMixin = (Base) => class extends Base {
  // Two fingers zoom, one finger pans (only when zoomed, otherwise the page
  // scrolls as usual), double tap/click toggles 1x <-> 2.5x, Ctrl+mouse
  // wheel zooms on the desktop. The overlay stays unzoomed.
  _wireZoom(r) {
    const frame = r.querySelector(".stage .frame");
    if (!frame) return;
    const z = this._zoom || (this._zoom = { s: 1, x: 0, y: 0 });
    const img = () => frame.querySelector("img");
    const apply = () => {
      const w = frame.clientWidth || 1, h = frame.clientHeight || 1;
      z.s = clamp(z.s, 1, 6);
      z.x = clamp(z.x, w * (1 - z.s), 0);
      z.y = clamp(z.y, h * (1 - z.s), 0);
      const el = img();
      if (el) {
        el.style.transformOrigin = "0 0";
        el.style.transform = z.s > 1 ? `translate(${z.x}px, ${z.y}px) scale(${z.s})` : "";
      }
      frame.classList.toggle("zoomed", z.s > 1);
      const badge = frame.querySelector(".zoom-badge");
      if (badge) { badge.hidden = z.s <= 1; badge.textContent = `${fixed(z.s, 1)}×`; }
      const out = frame.querySelector('[data-zoom="out"]');
      if (out) out.hidden = z.s <= 1;
    };
    const zoomAt = (factor, px, py) => {
      const ns = clamp(z.s * factor, 1, 6);
      z.x = px - (px - z.x) * (ns / z.s);
      z.y = py - (py - z.y) * (ns / z.s);
      z.s = ns;
      if (ns === 1) { z.x = 0; z.y = 0; }
      apply();
    };
    this._applyZoom = apply;
    apply();
    if (frame._zoomWired) return;
    frame._zoomWired = true;
    const local = (e) => { const b = frame.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top]; };
    frame.querySelectorAll("[data-zoom]").forEach((b) => b.addEventListener("click", (e) => {
      e.stopPropagation();
      const w = frame.clientWidth, h = frame.clientHeight;
      if (b.dataset.zoom === "in") zoomAt(1.6, w / 2, h / 2);
      else if (b.dataset.zoom === "out") zoomAt(1 / 1.6, w / 2, h / 2);
      else this._fullscreen(frame);
    }));
    let lastType = "mouse";
    frame.addEventListener("dblclick", (e) => {
      if (lastType === "touch") return; // touch: own double tap below
      const [px, py] = local(e);
      if (z.s > 1) { z.s = 1; z.x = 0; z.y = 0; apply(); } else zoomAt(2.5, px, py);
    });
    frame.addEventListener("wheel", (e) => {
      if (!e.ctrlKey && z.s <= 1) return; // normal page scrolling
      e.preventDefault();
      const [px, py] = local(e);
      zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, px, py);
    }, { passive: false });
    const pts = new Map();
    let pinch = null, pan = null, lastTap = 0;
    frame.addEventListener("pointerdown", (e) => {
      lastType = e.pointerType || "mouse";
      if (e.target.closest("button")) return;
      // Mouse: only the left button pans. Right keeps the context menu,
      // middle keeps scrolling. preventDefault stops the browser from
      // grabbing the image for drag & drop (which would end panning at once).
      if (e.pointerType === "mouse") {
        if (e.button !== 0) return;
        if (z.s > 1) e.preventDefault();
      }
      pts.set(e.pointerId, local(e));
      if (pts.size === 2) {
        const [a, b] = [...pts.values()];
        pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]) || 1, s: z.s, cx: (a[0] + b[0]) / 2, cy: (a[1] + b[1]) / 2, x: z.x, y: z.y };
        pan = null;
        try { frame.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      } else if (pts.size === 1 && z.s > 1) {
        pan = { px: e.clientX, py: e.clientY, x: z.x, y: z.y };
        try { frame.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      }
      // double tap on touch (dblclick is unreliable there)
      if (e.pointerType === "touch" && pts.size === 1) {
        const now = Date.now();
        if (now - lastTap < 300) {
          const [px, py] = local(e);
          if (z.s > 1) { z.s = 1; z.x = 0; z.y = 0; apply(); } else zoomAt(2.5, px, py);
          lastTap = 0;
        } else lastTap = now;
      }
    });
    frame.addEventListener("pointermove", (e) => {
      if (!pts.has(e.pointerId)) return;
      pts.set(e.pointerId, local(e));
      if (pinch && pts.size === 2) {
        const [a, b] = [...pts.values()];
        const ns = clamp(pinch.s * ((Math.hypot(a[0] - b[0], a[1] - b[1]) || 1) / pinch.d), 1, 6);
        const cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
        z.x = cx - (pinch.cx - pinch.x) * (ns / pinch.s);
        z.y = cy - (pinch.cy - pinch.y) * (ns / pinch.s);
        z.s = ns;
        if (ns === 1) { z.x = 0; z.y = 0; }
        apply();
      } else if (pan) {
        z.x = pan.x + (e.clientX - pan.px);
        z.y = pan.y + (e.clientY - pan.py);
        apply();
      }
    });
    const end = (e) => {
      pts.delete(e.pointerId);
      if (pts.size < 2) pinch = null;
      if (!pts.size) pan = null;
    };
    frame.addEventListener("pointerup", end);
    frame.addEventListener("pointercancel", end);
  }

  _fullscreen(el) {
    const doc = document;
    if (doc.fullscreenElement || doc.webkitFullscreenElement) {
      (doc.exitFullscreen || doc.webkitExitFullscreen).call(doc);
      return;
    }
    const req = el.requestFullscreen || el.webkitRequestFullscreen;
    if (req) Promise.resolve(req.call(el)).catch(() => {});
  }
};
