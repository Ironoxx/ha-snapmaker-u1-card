/**
 * Minimal QR code encoder (2.4, spool labels) – no external library, no CDN.
 *
 * Byte mode, error correction level M, versions 1–10 (up to 213 bytes, plenty
 * for a Spoolman link). Follows ISO/IEC 18004: Reed–Solomon over GF(256) with
 * the polynomial 0x11d, block interleaving, function patterns, the eight masks
 * scored with the four penalty rules, BCH-coded format and version info.
 * Checked during development by decoding versions 1–10 with every mask in
 * OpenCV's QR decoder; the JS tests guard size, finder patterns and limits.
 *
 * qrMatrix(text) -> boolean[][] (true = dark), qrSvg(text, opts) -> SVG string.
 */

// Level M per version: [EC codewords per block, [blocks, data codewords per block], ...]
const BLOCKS_M = [
  null,
  [10, [1, 16]], [16, [1, 28]], [26, [1, 44]], [18, [2, 32]], [24, [2, 43]],
  [16, [4, 27]], [18, [4, 31]], [22, [2, 38], [2, 39]], [22, [3, 36], [2, 37]], [26, [4, 43], [1, 44]],
];
const ALIGN = [null, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]];
const MAX_VERSION = 10;

// GF(256) log/antilog tables for Reed–Solomon
const EXP = new Uint8Array(512);
const LOG = new Uint8Array(256);
(() => {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x; LOG[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= 0x11d;
  }
  for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
})();
const mul = (a, b) => (a && b ? EXP[LOG[a] + LOG[b]] : 0);

/** Reed–Solomon EC codewords for one data block. */
function rsEncode(data, ecLen) {
  // generator polynomial (x - a^0)(x - a^1)...(x - a^(ecLen-1)), highest degree first
  let gen = [1];
  for (let i = 0; i < ecLen; i++) {
    const next = new Array(gen.length + 1).fill(0);
    gen.forEach((c, j) => { next[j] ^= c; next[j + 1] ^= mul(c, EXP[i]); });
    gen = next;
  }
  const rem = new Array(ecLen).fill(0);
  data.forEach((d) => {
    const factor = d ^ rem.shift();
    rem.push(0);
    for (let j = 0; j < ecLen; j++) rem[j] ^= mul(gen[j + 1], factor);
  });
  return rem;
}

function dataCapacity(version) {
  const [, ...groups] = BLOCKS_M[version];
  return groups.reduce((n, [b, d]) => n + b * d, 0);
}

/** Data bit stream (mode, length, bytes, terminator, padding) as codewords. */
function encodeData(bytes, version) {
  const bits = [];
  const put = (value, len) => { for (let i = len - 1; i >= 0; i--) bits.push((value >>> i) & 1); };
  put(0b0100, 4); // byte mode
  put(bytes.length, version < 10 ? 8 : 16);
  bytes.forEach((b) => put(b, 8));
  const cap = dataCapacity(version) * 8;
  put(0, Math.min(4, cap - bits.length));
  while (bits.length % 8) bits.push(0);
  const out = [];
  for (let i = 0; i < bits.length; i += 8) out.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
  for (let pad = 0xec; out.length < cap / 8; pad ^= 0xec ^ 0x11) out.push(pad);
  return out;
}

/** Split into blocks, add EC, interleave. */
function codewords(data, version) {
  const [ecLen, ...groups] = BLOCKS_M[version];
  const blocks = [];
  let pos = 0;
  groups.forEach(([count, len]) => {
    for (let i = 0; i < count; i++) { blocks.push(data.slice(pos, pos + len)); pos += len; }
  });
  const ecs = blocks.map((b) => rsEncode(b, ecLen));
  const out = [];
  const maxLen = Math.max(...blocks.map((b) => b.length));
  for (let i = 0; i < maxLen; i++) blocks.forEach((b) => { if (i < b.length) out.push(b[i]); });
  for (let i = 0; i < ecLen; i++) ecs.forEach((e) => out.push(e[i]));
  return out;
}

/** BCH code for format (15,5) and version (18,6) information. */
function bch(value, poly, polyBits) {
  let v = value << (polyBits - 1);
  for (let i = 31 - Math.clz32(v); i >= polyBits - 1; i--) if ((v >>> i) & 1) v ^= poly << (i - polyBits + 1);
  return (value << (polyBits - 1)) | v;
}

const MASKS = [
  (r, c) => (r + c) % 2 === 0,
  (r) => r % 2 === 0,
  (r, c) => c % 3 === 0,
  (r, c) => (r + c) % 3 === 0,
  (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
  (r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
  (r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
  (r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
];

/** Empty matrix with every function pattern; ``fn`` marks the reserved modules. */
function base(version) {
  const size = version * 4 + 17;
  const m = Array.from({ length: size }, () => new Array(size).fill(false));
  const fn = Array.from({ length: size }, () => new Array(size).fill(false));
  const set = (r, c, dark) => { m[r][c] = dark; fn[r][c] = true; };
  // finder patterns with separators
  [[0, 0], [0, size - 7], [size - 7, 0]].forEach(([r0, c0]) => {
    for (let r = -1; r <= 7; r++) for (let c = -1; c <= 7; c++) {
      const rr = r0 + r, cc = c0 + c;
      if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue;
      const ring = Math.max(Math.abs(r - 3), Math.abs(c - 3));
      set(rr, cc, r >= 0 && r <= 6 && c >= 0 && c <= 6 && ring !== 2);
    }
  });
  // alignment patterns (not over the finders)
  const al = ALIGN[version];
  al.forEach((r) => al.forEach((c) => {
    if (fn[r][c]) return;
    for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++)
      set(r + dr, c + dc, Math.max(Math.abs(dr), Math.abs(dc)) !== 1);
  }));
  // timing patterns
  for (let i = 8; i < size - 8; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
  // dark module and the reserved format areas
  set(size - 8, 8, true);
  for (let i = 0; i < 9; i++) { if (!fn[8][i]) set(8, i, false); if (!fn[i][8]) set(i, 8, false); }
  for (let i = 0; i < 8; i++) { set(8, size - 1 - i, false); if (!fn[size - 1 - i][8]) set(size - 1 - i, 8, false); }
  // version information (7+)
  if (version >= 7) {
    const v = bch(version, 0x1f25, 13);
    for (let i = 0; i < 18; i++) {
      const dark = ((v >>> i) & 1) === 1;
      const a = Math.floor(i / 3), b = (i % 3) + size - 11;
      set(a, b, dark); set(b, a, dark);
    }
  }
  return { m, fn, size };
}

/** Place the codewords in the zig-zag order, upwards and downwards in column pairs. */
function place(m, fn, size, cw) {
  let bit = 0;
  const total = cw.length * 8;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5; // skip the vertical timing column
    for (let v = 0; v < size; v++) {
      const upward = ((right + 1) & 2) === 0;
      const r = upward ? size - 1 - v : v;
      for (let j = 0; j < 2; j++) {
        const c = right - j;
        if (fn[r][c]) continue;
        m[r][c] = bit < total ? ((cw[bit >>> 3] >>> (7 - (bit & 7))) & 1) === 1 : false;
        bit++;
      }
    }
  }
}

function drawFormat(m, size, mask) {
  const data = (0b00 << 3) | mask; // level M = 00
  const f = bch(data, 0x537, 11) ^ 0x5412;
  const bitAt = (i) => ((f >>> i) & 1) === 1;
  // first copy around the top left finder (column 8 downwards, then row 8 to the left)
  for (let i = 0; i <= 5; i++) m[i][8] = bitAt(i);
  m[7][8] = bitAt(6); m[8][8] = bitAt(7); m[8][7] = bitAt(8);
  for (let i = 9; i < 15; i++) m[8][14 - i] = bitAt(i);
  // second copy: row 8 on the right, column 8 at the bottom
  for (let i = 0; i < 8; i++) m[8][size - 1 - i] = bitAt(i);
  for (let i = 8; i < 15; i++) m[size - 15 + i][8] = bitAt(i);
  m[size - 8][8] = true; // always dark
}

/** Penalty score of a finished matrix (rules N1–N4). */
function penalty(m, size) {
  let score = 0;
  const lines = (get) => {
    for (let a = 0; a < size; a++) {
      let run = 1;
      for (let b = 1; b <= size; b++) {
        if (b < size && get(a, b) === get(a, b - 1)) run++;
        else { if (run >= 5) score += run - 2; run = 1; }
      }
      // 1:1:3:1:1 finder-like pattern with 4 light modules on one side
      for (let b = 0; b + 10 < size; b++) {
        const p = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0].every((v, k) => get(a, b + k) === !!v);
        const q = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1].every((v, k) => get(a, b + k) === !!v);
        if (p) score += 40;
        if (q) score += 40;
      }
    }
  };
  lines((a, b) => m[a][b]);
  lines((a, b) => m[b][a]);
  for (let r = 0; r < size - 1; r++) for (let c = 0; c < size - 1; c++) {
    const v = m[r][c];
    if (v === m[r][c + 1] && v === m[r + 1][c] && v === m[r + 1][c + 1]) score += 3;
  }
  let dark = 0;
  m.forEach((row) => row.forEach((v) => { if (v) dark++; }));
  score += Math.floor(Math.abs(dark * 20 - size * size * 10) / (size * size)) * 10;
  return score;
}

/**
 * QR matrix for ``text`` (UTF-8). ``mask`` forces a mask (tests); otherwise the
 * one with the lowest penalty. Throws for texts longer than version 10 holds.
 */
export function qrMatrix(text, mask = null) {
  const bytes = Array.from(new TextEncoder().encode(String(text)));
  let version = 1;
  const fits = (v) => 4 + (v < 10 ? 8 : 16) + bytes.length * 8 <= dataCapacity(v) * 8;
  while (version <= MAX_VERSION && !fits(version)) version++;
  if (version > MAX_VERSION) throw new Error("QR: text too long");
  const cw = codewords(encodeData(bytes, version), version);
  let best = null;
  (mask === null ? [0, 1, 2, 3, 4, 5, 6, 7] : [mask]).forEach((k) => {
    const { m, fn, size } = base(version);
    place(m, fn, size, cw);
    for (let r = 0; r < size; r++) for (let c = 0; c < size; c++) if (!fn[r][c] && MASKS[k](r, c)) m[r][c] = !m[r][c];
    drawFormat(m, size, k);
    const score = mask === null ? penalty(m, size) : 0;
    if (!best || score < best.score) best = { m, score };
  });
  return best.m;
}

/** QR code as an SVG string; ``size`` in CSS units, ``quiet`` = margin in modules (spec: 4). */
export function qrSvg(text, { size = "100%", quiet = 4 } = {}) {
  const m = qrMatrix(text);
  const n = m.length + quiet * 2;
  let path = "";
  m.forEach((row, r) => row.forEach((dark, c) => { if (dark) path += `M${c + quiet} ${r + quiet}h1v1h-1z`; }));
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${n} ${n}" width="${size}" height="${size}" shape-rendering="crispEdges">`
    + `<rect width="${n}" height="${n}" fill="#fff"/><path d="${path}" fill="#000"/></svg>`;
}
