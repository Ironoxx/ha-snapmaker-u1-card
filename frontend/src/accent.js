/** Own accent colour for the card (option accent_color), instead of the theme's primary colour. */

/** "#3366ff", "3366ff", [51, 102, 255] or "rgb(…)"-free input -> [r, g, b] or null. */
export function parseColor(value) {
  if (Array.isArray(value) && value.length === 3 && value.every((v) => Number.isFinite(Number(v)))) {
    return value.map((v) => Math.max(0, Math.min(255, Math.round(Number(v)))));
  }
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(value || "").trim());
  if (!m) return null;
  const hex = m[1].length === 3 ? m[1].replace(/./g, (c) => c + c) : m[1];
  return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
}

const lum = ([r, g, b]) => {
  const ch = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b);
};

/** CSS variables for the accent colour; {} = keep the theme's colours. */
export function accentVars(value) {
  const rgb = parseColor(value);
  if (!rgb) return {};
  const col = `rgb(${rgb.join(", ")})`;
  const dark = lum(rgb) > 0.4; // light accent -> dark text on it
  return {
    "--u1-primary": col,
    "--u1-on-primary": dark ? "#111318" : "#ffffff",
    "--u1-primary-container": `color-mix(in srgb, ${col} 32%, var(--u1-surface))`,
    "--u1-on-primary-container": "var(--u1-on)",
  };
}

/** Set (or clear) the accent variables on the card element. */
export function applyAccent(el, value) {
  const vars = accentVars(value);
  for (const k of ["--u1-primary", "--u1-on-primary", "--u1-primary-container", "--u1-on-primary-container"]) {
    if (vars[k]) el.style.setProperty(k, vars[k]);
    else el.style.removeProperty(k);
  }
}
