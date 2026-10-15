/** Formatting helpers (numbers, dates, HTML escaping) and thumbnail backgrounds. */

import { LOCALE } from "./i18n.js";

export const fmtEuro = (v) => (v === null || v === undefined || Number.isNaN(v) ? "—"
  : `${Number(v).toLocaleString(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`);
// ── Background for thumbnails ──────────────────────────────────────────────
// A black part disappears on a dark grey background (and a white one on a
// light one). Measure the average brightness of the opaque pixels and recolour
// the frame if needed. The result is cached per URL.
export const THUMB_TONES = new Map();
export const THUMB_BOXES = ".file-thumb, .dlg-thumb, .hist-thumb, .thumb";
export function thumbTone(img) {
  const key = img.currentSrc || img.src;
  if (THUMB_TONES.has(key)) return THUMB_TONES.get(key);
  let tone = "";
  try {
    const c = document.createElement("canvas");
    c.width = c.height = 32;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    if (!ctx) return "";
    ctx.drawImage(img, 0, 0, 32, 32);
    const px = ctx.getImageData(0, 0, 32, 32).data;
    let sum = 0, n = 0, opaque = 0;
    for (let i = 0; i < px.length; i += 4) {
      const a = px[i + 3] / 255;
      if (a < 0.5) continue;
      opaque++;
      sum += (0.2126 * px[i] + 0.7152 * px[i + 1] + 0.0722 * px[i + 2]) / 255;
      n++;
    }
    // Without transparency the image shows its own background: do nothing
    if (n && opaque < (px.length / 4) * 0.97) {
      const lum = sum / n;
      tone = lum < 0.3 ? "dark" : lum > 0.8 ? "light" : "";
    }
  } catch (e) { tone = ""; /* foreign source without CORS: keep the default */ }
  THUMB_TONES.set(key, tone);
  return tone;
}
export function toneThumb(img) {
  if (!img || img.tagName !== "IMG") return;
  const box = img.closest(THUMB_BOXES);
  if (!box) return;
  const tone = thumbTone(img);
  if (tone) box.dataset.toneBg = tone; else delete box.dataset.toneBg;
}

export const fmtDate = (iso) => {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleString(LOCALE, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
};

/** "Nuss_2_PLA_1h17m_20261008195643.mp4" -> "Nuss 2 PLA 1h17m" */
export const archiveName = (file) => String(file).replace(/\.\w+$/, "").replace(/_\d{14}$/, "").replace(/_/g, " ");
export const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

export function fmtMin(min) {
  if (min === null || min === undefined || min <= 0) return "—";
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h} h ${m} min` : `${m} min`;
}

export function fmtClock(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  const t = d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });
  return sameDay ? t : `${d.toLocaleDateString(LOCALE, { weekday: "short" })} ${t}`;
}

/** Number with fixed decimals in the format of the HA language (comma in German). */
export function fixed(v, dec = 0) {
  return Number(v).toLocaleString(LOCALE, { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: false });
}

export function num(v, dec = 0, unit = "") {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${fixed(v, dec)}${unit ? " " + unit : ""}`;
}

export const fmtInt = (v) => (v === null || v === undefined || Number.isNaN(v)
  ? "—" : Math.round(v).toLocaleString(LOCALE));

export const esc = (s) =>
  String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
