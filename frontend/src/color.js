/** Colour helpers and the filament mapping suggestion (same logic as parsing.suggest_mapping). */

export function hexRgb(c) {
  const m = /^#?([0-9a-f]{6})/i.exec(c || "");
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function colorDistance(a, b) {
  const x = hexRgb(a), y = hexRgb(b);
  if (!x || !y) return 765;
  const rm = (x[0] + y[0]) / 2;
  const dr = x[0] - y[0], dg = x[1] - y[1], db = x[2] - y[2];
  return Math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db);
}

/** Black or white, whichever is readable on the colour. */
export function onColor(c) {
  const x = hexRgb(c);
  if (!x) return "#fff";
  const lum = (0.299 * x[0] + 0.587 * x[1] + 0.114 * x[2]) / 255;
  return lum > 0.6 ? "#1b1b1f" : "#fff";
}

export function suggestMapping(filaments, slots) {
  const loaded = slots.filter((s) => s.loaded);
  const taken = new Set();
  const map = {};
  filaments.filter((f) => f.used).forEach((f) => {
    if (!loaded.length) { map[f.index] = f.index % 4; return; }
    const same = (s) => !!(f.type && s.type && f.type.toUpperCase() === s.type.toUpperCase());
    const score = (s) => [same(s) ? 0 : 1, colorDistance(f.color, s.color), taken.has(s.index) ? 1 : 0];
    let best = loaded[0], bs = score(best);
    for (const s of loaded.slice(1)) {
      const sc = score(s);
      if (sc[0] < bs[0] || (sc[0] === bs[0] && (sc[1] < bs[1] || (sc[1] === bs[1] && sc[2] < bs[2])))) {
        best = s; bs = sc;
      }
    }
    map[f.index] = best.index;
    taken.add(best.index);
  });
  return map;
}
