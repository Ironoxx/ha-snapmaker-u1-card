/**
 * Layer view: paths of the current layer with printed/pending state.
 *
 * 2.1: two sliders – layer (browse the whole file; "Live" goes back to the
 * printing layer) and progress within the layer (plays the paths in file
 * order). The same view previews any file in the print dialog
 * (``?file=…`` on the layer API, parsed in the background).
 */

import { DOMAIN, LAYER_PALETTE } from "../const.js";
import { esc, fixed } from "../format.js";
import { tr } from "../i18n.js";

// Snapmaker U1 build plate 270 x 270 mm; behind it the dock with the four heads
const BED_W = 270;
const BED_D = 270;
const DOCK_DEPTH = 48;
const LV_STORE = "snapmaker-u1-card.layerview";

export const LayerViewMixin = (Base) => class extends Base {
  _sectionLayer() {
    const d = this._d;
    if (!d.active || !this._entryData().config_entry_id) return "";
    const lv = this._lv;
    const head = lv && lv.data && !lv.data.missing
      ? `${tr("Schicht {n} / {t}", { n: lv.data.layer, t: d.totalLayers || lv.data.total })}${lv.data.z !== null && lv.data.z !== undefined ? ` · Z ${fixed(lv.data.z, 2)} mm` : ""}`
      : "";
    return `
      <section class="panel lv-panel">
        <div class="panel-head">
          <ha-icon icon="mdi:layers-outline"></ha-icon>
          <span class="panel-title">${tr("Schichtansicht")}</span>
          <span class="t-label" style="margin-left:auto" data-su1="lvhead">${esc(head)}</span>
          <button type="button" class="icon ghost lv-mode" data-lvmode aria-pressed="${this._lvMode() === "bed"}"
            title="${this._lvMode() === "bed" ? tr("Teil vergrößern") : tr("Ganzes Druckbett")}">
            <ha-icon icon="${this._lvMode() === "bed" ? "mdi:magnify-plus-outline" : "mdi:grid"}"></ha-icon></button>
        </div>
        <div class="lv" data-lv data-mode="${this._lvMode()}">${this._layerSvg()}</div>
        ${this._lvControls(lv)}
        <div class="lv-legend" data-su1="lvlegend">${this._layerLegend()}</div>
        <div class="lv-objects" data-su1="lvobjects">${this._objectsHtml()}</div>
      </section>`;
  }

  /** Layer and progress sliders; Live only while browsing. */
  _lvControls(lv, preview = false) {
    const v = lv && lv.data;
    if (!v || v.status !== "ready") return `<div class="lv-ctl" data-lvctl hidden></div>`;
    const first = v.first ?? 1, last = v.last ?? v.total ?? 1;
    const browsing = !preview && lv && (lv.pinned != null || lv.scrub != null);
    return `<div class="lv-ctl" data-lvctl>
        <label class="lv-range"><span>${tr("Schicht")}</span>
          <input type="range" data-lvlayer min="${first}" max="${last}" step="1" value="${v.layer ?? first}" aria-label="${tr("Schicht")}" /></label>
        <label class="lv-range"><span>${tr("Fortschritt")}</span>
          <input type="range" data-lvstep min="0" max="1000" step="1" value="${lv.scrub ?? 1000}" aria-label="${tr("Verlauf in der Schicht")}" /></label>
        ${preview ? "" : `<button type="button" class="chip sm" data-lvlive ${browsing ? "" : "hidden"}><ha-icon icon="mdi:crosshairs-gps"></ha-icon><span>${tr("Live")}</span></button>`}
      </div>`;
  }

  /**
   * File position that separates printed from pending: the progress slider,
   * else a browsed layer before (all printed) or after (all pending) the
   * printing one, else the live position. null = nothing marked (preview).
   */
  _lvPos(lv = this._lv) {
    const v = lv && lv.data;
    if (!v) return null;
    if (lv.scrub != null && v.start != null) return v.start + (v.end - v.start) * lv.scrub / 1000;
    if (lv.preview) return null;
    if (lv.pinned != null && this._d) {
      const live = this._d.layer || 1;
      if (lv.pinned < live) return Infinity;
      if (lv.pinned > live) return -Infinity;
    }
    return lv.position;
  }

  /** Colour per logical filament: head from the mapping -> loaded spool, else the file colour. */
  _toolColor(tool, lv = this._lv) {
    const c = (lv && lv.data && lv.data.colors) || {};
    const head = Array.isArray(c.map_table) ? c.map_table[tool] : undefined;
    const slot = (this._slots() || [])[head !== undefined ? head : tool];
    if (slot && slot.loaded && slot.color) return slot.color;
    if (c.file && c.file[String(tool)]) return c.file[String(tool)];
    return LAYER_PALETTE[tool % LAYER_PALETTE.length];
  }

  _layerSvg(lv = this._lv) {
    if (!lv || !lv.data) return `<div class="t-label lv-msg">${tr("Schichtansicht wird vorbereitet …")}</div>`;
    const v = lv.data;
    if (v.status === "error") return `<div class="t-label lv-msg">${esc(tr("Schichtansicht nicht verfügbar: {e}", { e: v.error || "" }))}</div>`;
    if (v.status !== "ready" || !v.bbox) return `<div class="t-label lv-msg">${tr("Schichtansicht wird vorbereitet …")}</div>`;
    const bed = this._lvMode() === "bed";
    const img = bed ? this._bedImage() : null;
    let [x0, y0, x1, y1] = bed ? [0, 0, BED_W, BED_D] : v.bbox;
    const pad = bed ? (img ? 0 : 10) : Math.max(3, (x1 - x0 + y1 - y0) * 0.03);
    // bed view: extra room behind the plate for the parked heads (or the own image)
    let top = bed && !img ? y1 + DOCK_DEPTH : y1;
    if (img) { [x0, y0, x1, top] = img.area; }
    const vb = [x0 - pad, -(top + pad), x1 - x0 + 2 * pad, top - y0 + 2 * pad].map((n) => n.toFixed(2)).join(" ");
    const pos = this._lvPos(lv);
    const ex = lv.preview ? { objects: [], excluded: [], current: null } : this._exclude();
    const excluded = new Set(ex.excluded);
    const lines = (v.segs || []).map(([tool, pts, off, obj]) => {
      const p = [];
      for (let i = 0; i < pts.length; i += 2) p.push(`${pts[i]},${-pts[i + 1]}`);
      const todo = pos !== null && pos !== undefined && off >= pos;
      const cls = [todo ? "todo" : "", obj && excluded.has(obj) ? "excl" : ""].filter(Boolean).join(" ");
      return `<polyline points="${p.join(" ")}" stroke="${esc(this._toolColor(tool, lv))}" data-o="${off}"${cls ? ` class="${cls}"` : ""}/>`;
    }).join("");
    // Object outlines (EXCLUDE_OBJECT_DEFINE): tap = exclude, only with 2+ objects
    const pick = ex.objects.length > 1;
    const outlines = ex.objects.filter((o) => Array.isArray(o.polygon) && o.polygon.length > 2).map((o) => {
      const st = excluded.has(o.name) ? "excl" : o.name === ex.current ? "cur" : "";
      const pts = o.polygon.map(([px, py]) => `${px},${-py}`).join(" ");
      return `<polygon points="${pts}" class="lv-obj ${st}${pick && !st.includes("excl") ? " pick" : ""}" data-obj="${esc(o.name)}" vector-effect="non-scaling-stroke"><title>${esc(o.label || o.name)}</title></polygon>`;
    }).join("");
    // Stroke width like a real extrusion (0.45 mm), a little bolder for very large parts
    const w = bed ? 0.7 : Math.max(0.45, Math.min(0.9, (x1 - x0) / 250));
    const ground = bed ? this._bedSvg(img) : `<rect x="${(x0 - pad).toFixed(2)}" y="${(-(y1 + pad)).toFixed(2)}" width="${(x1 - x0 + 2 * pad).toFixed(2)}" height="${(y1 - y0 + 2 * pad).toFixed(2)}" class="lv-bed"/>`;
    return `<svg viewBox="${vb}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${tr("Schichtansicht")}">
        ${ground}
        <g class="lv-paths" stroke-width="${w.toFixed(2)}">${lines}</g>
        ${bed ? this._nozzleSvg(v, pos, lv) : ""}
        ${outlines ? `<g class="lv-objs">${outlines}</g>` : ""}
        ${v.missing || !(v.segs || []).length ? `<text x="${((x0 + x1) / 2).toFixed(1)}" y="${(-(y0 + y1) / 2).toFixed(1)}" class="lv-empty">${tr("keine Bahnen")}</text>` : ""}
      </svg>`;
  }

  _layerLegend(lv = this._lv) {
    const v = lv && lv.data;
    if (!v || v.status !== "ready") return "";
    const used = [...new Set((v.segs || []).map((s) => s[0]))].sort((a, b) => a - b);
    const heads = this._d ? this._d.heads : [];
    const c = v.colors || {};
    return used.map((t) => {
      const head = Array.isArray(c.map_table) ? c.map_table[t] : t;
      const h = heads[head];
      return `<span><i style="background:${esc(this._toolColor(t, lv))}"></i>${tr("Filament {n}", { n: t + 1 })}${h ? ` → ${esc(h.name)}` : ""}</span>`;
    }).join("") + (this._lvPos(lv) !== null && this._lvPos(lv) !== undefined
      ? `<span class="lv-hint"><i class="lv-done"></i>${tr("gedruckt")}<i class="lv-todo"></i>${tr("folgt")}</span>` : "");
  }

  /** part = zoomed to the part (default), bed = whole build plate from above. */
  _lvMode() {
    if (this._lvView) return this._lvView;
    let m = null;
    try { m = window.localStorage.getItem(LV_STORE); } catch (e) { /* no storage */ }
    return m === "bed" || m === "part" ? m : (this._cfg.layer_view === "bed" ? "bed" : "part");
  }

  _toggleLvMode() {
    this._lvView = this._lvMode() === "bed" ? "part" : "bed";
    try { window.localStorage.setItem(LV_STORE, this._lvView); } catch (e) { /* no storage */ }
    const r = this.shadowRoot.getElementById("u1card");
    const btn = r && r.querySelector("[data-lvmode]");
    if (btn) {
      const bed = this._lvView === "bed";
      btn.setAttribute("aria-pressed", String(bed));
      btn.title = bed ? tr("Teil vergrößern") : tr("Ganzes Druckbett");
      btn.innerHTML = `<ha-icon icon="${bed ? "mdi:magnify-plus-outline" : "mdi:grid"}"></ha-icon>`;
    }
    const box = r && r.querySelector("[data-lv]");
    if (box) box.dataset.mode = this._lvView;
    this._paintLayer(true);
  }

  /** Stylised build plate from above: plate with grid, the four parked heads behind it. */
  /** Own background image for the bed view (bed_image + bed_image_area in printer mm). */
  _bedImage() {
    const url = typeof this._cfg.bed_image === "string" ? this._cfg.bed_image.trim() : "";
    if (!url) return null;
    let area = this._cfg.bed_image_area;
    if (typeof area === "string") area = area.split(/[\s,;]+/).map(Number);
    if (!Array.isArray(area) || area.length !== 4 || area.some((n) => !Number.isFinite(Number(n)))) area = [0, 0, BED_W, BED_D];
    area = area.map(Number);
    if (area[2] <= area[0] || area[3] <= area[1]) area = [0, 0, BED_W, BED_D];
    const op = Number(this._cfg.bed_image_opacity);
    return { url, area, opacity: Number.isFinite(op) && op > 0 && op <= 1 ? op : 1 };
  }

  _bedSvg(img) {
    if (img) {
      const [ax0, ay0, ax1, ay1] = img.area;
      const grid = this._cfg.bed_grid ? this._gridSvg() : "";
      return `<g class="lv-printer">
          <image href="${esc(img.url)}" x="${ax0}" y="${-ay1}" width="${ax1 - ax0}" height="${ay1 - ay0}"
            preserveAspectRatio="none" opacity="${img.opacity}"/>
          ${grid}
        </g>`;
    }
    const heads = (this._d && this._d.heads) || [];
    const printing = this._d && this._d.printing;
    const slotW = (BED_W - 30) / 4;
    const dock = [0, 1, 2, 3].map((i) => {
      const h = heads[i] || {};
      const x = 15 + i * slotW + 4;
      const y = -(BED_D + DOCK_DEPTH - 6);
      const away = printing && h.active;
      const color = h.loaded ? (h.color || "var(--u1-outline)") : "var(--u1-outline)";
      return `<g class="lv-head${away ? " away" : ""}${h.active ? " act" : ""}">
          <rect x="${x.toFixed(1)}" y="${y}" width="${(slotW - 8).toFixed(1)}" height="${DOCK_DEPTH - 14}" rx="4"/>
          <rect x="${(x + 4).toFixed(1)}" y="${y + DOCK_DEPTH - 22}" width="${(slotW - 16).toFixed(1)}" height="4" rx="2" style="fill:${esc(color)}" class="lv-band"/>
          <text x="${(x + (slotW - 8) / 2).toFixed(1)}" y="${y + 11}" class="lv-head-n">${i + 1}</text>
        </g>`;
    }).join("");
    return `<g class="lv-printer">
        <rect x="-6" y="${-(BED_D + DOCK_DEPTH + 4)}" width="${BED_W + 12}" height="${BED_D + DOCK_DEPTH + 10}" rx="10" class="lv-frame"/>
        <rect x="0" y="${-BED_D}" width="${BED_W}" height="${BED_D}" rx="5" class="lv-plate"/>
        ${this._gridSvg()}
        <circle cx="4" cy="-4" r="1.6" class="lv-origin"/>
        <g class="lv-dock">${dock}</g>
      </g>`;
  }

  _gridSvg() {
    const g = [];
    for (let i = 10; i < BED_W; i += 10) {
      const major = i % 50 === 0 ? " major" : "";
      g.push(`<line x1="${i}" y1="0" x2="${i}" y2="${-BED_D}" class="lv-grid${major}"/>`);
      g.push(`<line x1="0" y1="${-i}" x2="${BED_W}" y2="${-i}" class="lv-grid${major}"/>`);
    }
    return `<g>${g.join("")}</g>`;
  }

  /** Nozzle marker: end of the last printed path before the file position. */
  _nozzleAt(v, pos) {
    let best = null;
    for (const seg of v.segs || []) {
      if (seg[2] <= pos && (!best || seg[2] >= best[2])) best = seg;
    }
    if (!best || best[1].length < 2) return null;
    const n = best[1].length;
    return [best[1][n - 2], best[1][n - 1]];
  }

  _nozzleSvg(v, pos, lv = this._lv) {
    if (!Number.isFinite(pos)) return "";
    const scrub = lv && lv.scrub != null;
    if (!scrub && (lv.preview || !this._d || !this._d.printing)) return "";
    // slider: exactly at its position; live: where the animation left it
    const at = scrub ? this._nozzleAt(v, pos)
      : (this._noz && this._noz.layer === v.layer && this._noz.xy) || this._nozzleAt(v, pos);
    if (!at) return "";
    if (!scrub) this._noz = { layer: v.layer, pos, xy: at };
    const [x, y] = at;
    return `<g class="lv-gantry" transform="translate(0,${-y})"><rect x="-8" y="-3.5" width="${BED_W + 16}" height="7" rx="3.5"/></g>
      <g class="lv-nozzle" transform="translate(${x},${-y})">
        <rect x="-13" y="-9" width="26" height="18" rx="4" class="carriage"/>
        <circle r="7" class="ring"/><circle r="2.2" class="dot"/>
      </g>`;
  }

  /**
   * Move the nozzle along the paths printed between the last and the new file
   * position, spread over about the poll interval: the printer reports its
   * position every few seconds, the card plays the way in between.
   */
  _animateNozzle(v, from, to) {
    const r = this.shadowRoot.getElementById("u1card");
    const noz = r && r.querySelector(".lv-nozzle");
    const gantry = r && r.querySelector(".lv-gantry");
    if (!noz || to === null || to === undefined) return;
    const end = this._nozzleAt(v, to);
    if (!end) return;
    const start = (this._noz && this._noz.layer === v.layer && this._noz.xy) || end;
    const pts = [start];
    if (from !== null && from !== undefined && to > from) {
      for (const seg of [...(v.segs || [])].sort((a, b) => a[2] - b[2])) {
        if (seg[2] > from && seg[2] <= to) for (let i = 0; i < seg[1].length; i += 2) pts.push([seg[1][i], seg[1][i + 1]]);
      }
    }
    pts.push(end);
    this._noz = { layer: v.layer, pos: to, xy: end };
    const cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
    const total = cum[cum.length - 1];
    const place = (x, y) => {
      noz.setAttribute("transform", `translate(${x.toFixed(2)},${(-y).toFixed(2)})`);
      if (gantry) gantry.setAttribute("transform", `translate(0,${(-y).toFixed(2)})`);
    };
    if (this._nozRaf) cancelAnimationFrame(this._nozRaf);
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!total || reduced || typeof requestAnimationFrame !== "function") { place(end[0], end[1]); return; }
    const now = Date.now();
    const dur = Math.max(800, Math.min(6000, now - (this._nozAt || now - 4500)));
    this._nozAt = now;
    const t0 = performance.now();
    const step = (t) => {
      const k = Math.min(1, (t - t0) / dur);
      const d = total * k;
      let i = 1;
      while (i < cum.length - 1 && cum[i] < d) i++;
      const seg = cum[i] - cum[i - 1] || 1;
      const f = Math.max(0, Math.min(1, (d - cum[i - 1]) / seg));
      place(pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f);
      if (k < 1 && noz.isConnected) this._nozRaf = requestAnimationFrame(step);
    };
    this._nozRaf = requestAnimationFrame(step);
  }

  /** Progress slider in the bed view: nozzle and gantry straight to the slider position. */
  _placeNozzle(box, v, pos) {
    if (this._nozRaf) cancelAnimationFrame(this._nozRaf);
    const at = Number.isFinite(pos) && v ? this._nozzleAt(v, pos) : null;
    const noz = box.querySelector(".lv-nozzle"), gantry = box.querySelector(".lv-gantry");
    if (!at || !noz) return;
    noz.setAttribute("transform", `translate(${at[0].toFixed(2)},${(-at[1]).toFixed(2)})`);
    if (gantry) gantry.setAttribute("transform", `translate(0,${(-at[1]).toFixed(2)})`);
  }

  /** Exclude-object state from the last position poll. */
  _exclude() {
    const e = this._lv && this._lv.exclude;
    return { objects: (e && e.objects) || [], excluded: (e && e.excluded) || [], current: e ? e.current : null };
  }

  _objectsHtml() {
    const ex = this._exclude();
    if (ex.objects.length < 2) return "";
    const excluded = new Set(ex.excluded);
    const left = ex.objects.filter((o) => !excluded.has(o.name)).length;
    // 2.2: folded by default to save room; the open state survives the refresh
    const gone = ex.objects.length - left;
    return `<details class="obj-box" data-objbox ${this._objOpen ? "open" : ""}>
      <summary><ha-icon icon="mdi:select-remove"></ha-icon><span>${tr("Objekte ausschließen")}</span>
        <span class="t-label obj-count">${tr("{n} Objekte", { n: ex.objects.length })}${gone ? ` · ${tr("{n} ausgeschlossen", { n: gone })}` : ""}</span>
        <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon></summary>
      <div class="body"><div class="t-label">${tr("Objekte – antippen zum Ausschließen")}</div><div class="chip-row">${ex.objects.map((o) => {
      const off = excluded.has(o.name);
      const cur = !off && o.name === ex.current;
      const last = !off && left <= 1;
      return `<button type="button" class="chip obj-chip${off ? " off" : ""}${cur ? " cur" : ""}" data-obj="${esc(o.name)}"
        ${off || last ? "disabled" : ""} title="${esc(off ? tr("Ausgeschlossen") : last ? tr("Letztes Objekt") : tr("Ausschließen"))}">
        <ha-icon icon="${off ? "mdi:cancel" : cur ? "mdi:printer-3d-nozzle" : "mdi:cube-outline"}"></ha-icon>${esc(o.label || o.name)}</button>`;
    }).join("")}</div></div></details>`;
  }

  async _excludeObject(name) {
    const ex = this._exclude();
    const o = ex.objects.find((x) => x.name === name);
    if (!o || ex.excluded.includes(name)) return;
    const left = ex.objects.filter((x) => !ex.excluded.includes(x.name)).length;
    if (left <= 1) return;
    const yes = await this._confirmAction({
      icon: "mdi:select-remove", tone: "error",
      title: tr("„{n}“ ausschließen?", { n: o.label || name }),
      text: tr("Das Objekt wird ab sofort nicht mehr gedruckt, der Rest läuft weiter. Das lässt sich nicht rückgängig machen."),
      ok: tr("Ausschließen"),
    });
    if (!yes) return;
    if (await this._call("exclude_object", { name })) {
      // show it right away; the next position poll confirms it
      this._lv.exclude = { ...this._lv.exclude, excluded: [...ex.excluded, name] };
      this._paintLayer(true);
    }
  }

  /** Sliders after a repaint: (re)build when the layer range appears, else just move them (not while dragged). */
  _lvSyncCtl(host, lv, preview) {
    const ctl = host && host.querySelector("[data-lvctl]");
    if (!ctl) return;
    const v = lv && lv.data;
    if (ctl.hidden || !ctl.querySelector("[data-lvlayer]")) {
      if (v && v.status === "ready") ctl.outerHTML = this._lvControls(lv, preview);
      return;
    }
    const layer = ctl.querySelector("[data-lvlayer]"), step = ctl.querySelector("[data-lvstep]");
    const active = this.shadowRoot.activeElement;
    if (v && v.status === "ready") {
      layer.min = v.first ?? 1; layer.max = v.last ?? v.total;
      if (active !== layer) layer.value = v.layer;
    }
    if (active !== step) step.value = lv.scrub ?? 1000;
    const live = ctl.querySelector("[data-lvlive]");
    if (live) live.hidden = lv.pinned == null && lv.scrub == null;
  }

  /**
   * Slider events on a layer view host. get() returns the view state,
   * seek(n) loads layer n, paint() redraws.
   */
  _wireLvControls(host, get, seek, paint) {
    if (!host || host._lvCtlWired) return;
    host._lvCtlWired = true;
    host.addEventListener("input", (e) => {
      const t = e.target;
      if (!t || !t.dataset) return;
      const lv = get();
      if (!lv) return;
      if (t.dataset.lvstep !== undefined) {
        lv.scrub = Number(t.value) >= 1000 && !lv.preview ? null : Number(t.value);
        paint(false);
      } else if (t.dataset.lvlayer !== undefined) {
        clearTimeout(host._lvSeekTimer);
        host._lvSeekTimer = setTimeout(() => seek(Number(t.value)), 150);
      }
    });
    host.addEventListener("click", (e) => {
      if (!e.target || !e.target.closest || !e.target.closest("[data-lvlive]")) return;
      const lv = get();
      if (!lv) return;
      lv.pinned = null; lv.scrub = null;
      seek(null);
    });
  }

  /** Live view: browse to layer n (null = back to the printing layer). */
  _lvSeek(n) {
    const lv = this._lv;
    if (!lv) return;
    const live = (this._d && this._d.layer) || 1;
    lv.pinned = n === null || n === live ? null : n;
    lv.scrub = null;
    lv.layer = null;  // fetch on the next tick
    this._tickLayer();
  }

  _wireObjects(root) {
    this._wireLvControls(root, () => this._lv, (n) => this._lvSeek(n), (full) => this._paintLayer(full));
    if (!root || root._objWired) return;
    root._objWired = true;
    // toggle does not bubble: capture it on the panel (the list is replaced on every refresh)
    root.addEventListener("toggle", (e) => {
      if (e.target && e.target.matches && e.target.matches("[data-objbox]")) this._objOpen = e.target.open;
    }, true);
    root.addEventListener("click", (e) => {
      if (e.target && e.target.closest && e.target.closest("[data-lvmode]")) { this._toggleLvMode(); return; }
      const el = e.target && e.target.closest ? e.target.closest("[data-obj]") : null;
      if (!el || el.hasAttribute("disabled") || el.classList.contains("excl")) return;
      this._excludeObject(el.getAttribute("data-obj"));
    });
  }

  async _fetchLayer(query) {
    const entry = this._entryData().config_entry_id;
    const url = `/api/${DOMAIN}/layers/${entry}?${query}`;
    const h = this._hass;
    const res = typeof h.fetchWithAuth === "function"
      ? await h.fetchWithAuth(url)
      : await fetch(url, { headers: { Authorization: `Bearer ${h.auth && h.auth.data ? h.auth.data.access_token : ""}` } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  /** Reload the layer when it changes; progress within the layer every 5 s. */
  async _tickLayer(fromHass = false) {
    const d = this._d;
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-lv]");
    if (!d || !d.active || !box) { if (d && !d.active) this._lv = null; return; }
    const pane = box.closest("[data-pane]");
    if (document.hidden || !this._onScreen || (pane && pane.hidden) || this._lvBusy) return;
    const lv = this._lv || (this._lv = { layer: null, data: null, position: null });
    const want = lv.pinned ?? (d.layer || 1);
    const needLayer = lv.layer !== want || !lv.data || lv.data.status !== "ready";
    if (fromHass && !needLayer) return; // position only on the tick
    if (needLayer && lv.data && lv.data.status !== "ready" && Date.now() - (lv.at || 0) < 5000) return;
    this._lvBusy = true;
    let exChanged = false;
    try {
      if (needLayer) {
        const data = await this._fetchLayer(`layer=${want}`);
        lv.layer = want;
        lv.data = data;
        lv.at = Date.now();
      }
      if (lv.data && lv.data.status === "ready") {
        const p = await this._fetchLayer("position=1");
        lv.prevPos = lv.position;
        lv.position = typeof p.position === "number" ? p.position : null;
        if (p.exclude) {
          const key = JSON.stringify([p.exclude.excluded, p.exclude.current, (p.exclude.objects || []).length]);
          if (key !== lv.exKey) { lv.exKey = key; lv.exclude = p.exclude; exChanged = true; }
        }
        if (Number.isInteger(p.active_head)) {
          const changed = !this._liveHead || this._liveHead.idx !== p.active_head;
          this._liveHead = { idx: p.active_head, at: Date.now() };
          if (changed) { this._collect(); this._render(); }
        }
      }
    } catch (err) {
      lv.data = { status: "error", error: (err && err.message) || String(err) };
      lv.at = Date.now();
    } finally {
      this._lvBusy = false;
    }
    // The print ended while we waited for the answer (_lv was reset)
    if (this._lv !== lv) return;
    this._paintLayer(needLayer || exChanged);
  }

  _paintLayer(full) {
    const r = this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-lv]");
    if (!box) return;
    const scrubbing = this._lv.scrub != null;
    const bedNoNozzle = this._lvMode() === "bed" && ((this._d && this._d.printing) || scrubbing) && !box.querySelector(".lv-nozzle");
    if (full || !box.querySelector("svg") || bedNoNozzle) {
      if (full && this._nozRaf) cancelAnimationFrame(this._nozRaf);
      box.innerHTML = this._layerSvg();
    } else {
      const pos = this._lvPos();
      box.querySelectorAll("polyline").forEach((pl) =>
        pl.classList.toggle("todo", pos !== null && pos !== undefined && Number(pl.dataset.o) >= pos));
      const live = this._lv.pinned == null && this._lv.scrub == null;
      if (live && this._lvMode() === "bed" && this._lv.data) this._animateNozzle(this._lv.data, this._lv.prevPos, pos);
      else if (scrubbing && this._lvMode() === "bed") this._placeNozzle(box, this._lv.data, pos);
    }
    const v = this._lv.data;
    const head = r.querySelector('[data-su1="lvhead"]');
    if (head) head.textContent = v && v.status === "ready" && !v.missing
      ? `${tr("Schicht {n} / {t}", { n: v.layer, t: (this._d && this._d.totalLayers) || v.total })}${v.z !== null && v.z !== undefined ? ` · Z ${fixed(v.z, 2)} mm` : ""}${this._lv.pinned != null && this._d ? ` · ${tr("druckt {n}", { n: this._d.layer || 1 })}` : ""}` : "";
    this._lvSyncCtl(box.closest(".lv-panel"), this._lv, false);
    const leg = r.querySelector('[data-su1="lvlegend"]');
    if (leg) leg.innerHTML = this._layerLegend();
    const objs = r.querySelector('[data-su1="lvobjects"]');
    if (objs) objs.innerHTML = this._objectsHtml();
    this._wireObjects(box.closest(".lv-panel"));
  }

  // ── G-code preview in the print dialog (2.1) ─────────────────────────────
  _pvHtml(g) {
    const pv = g.pv || (g.pv = { preview: true, data: null, scrub: null, want: null });
    this._pvColors(g);
    return `<div class="pv" data-pvhost>
        <div class="lv" data-lv data-mode="${this._lvMode()}">${this._layerSvg(pv)}</div>
        ${this._lvControls(pv, true)}
        <div class="lv-legend" data-pvlegend>${this._layerLegend(pv)}</div>
        <div class="t-label" data-pvhead>${this._pvHead(pv)}</div>
      </div>`;
  }

  _pvHead(pv) {
    const v = pv && pv.data;
    return v && v.status === "ready" && !v.missing
      ? `${tr("Schicht {n} / {t}", { n: v.layer, t: v.last ?? v.total })}${v.z != null ? ` · Z ${fixed(v.z, 2)} mm` : ""}` : "";
  }

  /** Colours as chosen in the dialog: logical filament -> head -> its loaded filament. */
  _pvColors(g) {
    const v = g.pv && g.pv.data;
    if (!v || !v.colors) return;
    const table = [];
    Object.entries(g.map || {}).forEach(([fil, head]) => { table[Number(fil)] = head; });
    v.colors = { ...v.colors, map_table: table };
  }

  _pvWire(g) {
    const host = this._dlgEl && this._dlgEl.querySelector("[data-pvhost]");
    this._wireLvControls(host, () => (this._dlg === g ? g.pv : null), (n) => this._pvLoad(n), (full) => this._pvPaint(full));
  }

  /** Load layer n of the dialog's file (null = first); waits while the integration parses the file. */
  async _pvLoad(n) {
    const g = this._dlg;
    if (!g || !g.pv) return;
    const pv = g.pv;
    if (n !== null) pv.want = n;
    const seq = (pv.seq = (pv.seq || 0) + 1);
    const query = () => `file=${encodeURIComponent(g.file.path)}&layer=${pv.want ?? 1}`;
    try {
      let data = await this._fetchLayer(query());
      for (let i = 0; data.status === "parsing" && i < 120; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        if (this._dlg !== g || !g.previewOpen || pv.seq !== seq) return;
        data = await this._fetchLayer(query());
      }
      // a file counting from layer 0
      if (data.missing && pv.want == null && data.first != null) {
        pv.want = data.first;
        data = await this._fetchLayer(query());
      }
      if (this._dlg !== g || pv.seq !== seq) return;
      pv.data = data;
      pv.scrub = null;
    } catch (err) {
      pv.data = { status: "error", error: (err && err.message) || String(err) };
    }
    this._pvColors(g);
    this._pvPaint(true);
  }

  _pvPaint(full) {
    const g = this._dlg;
    const host = this._dlgEl && this._dlgEl.querySelector("[data-pvhost]");
    if (!g || !g.pv || !host) return;
    const pv = g.pv;
    const box = host.querySelector("[data-lv]");
    if (full || !box.querySelector("svg")) box.innerHTML = this._layerSvg(pv);
    else {
      const pos = this._lvPos(pv);
      box.querySelectorAll("polyline").forEach((pl) =>
        pl.classList.toggle("todo", pos !== null && Number(pl.dataset.o) >= pos));
      if (this._lvMode() === "bed") {
        if (!box.querySelector(".lv-nozzle") && pv.scrub != null) box.innerHTML = this._layerSvg(pv);
        else this._placeNozzle(box, pv.data, pos);
      }
    }
    host.querySelector("[data-pvlegend]").innerHTML = this._layerLegend(pv);
    host.querySelector("[data-pvhead]").textContent = this._pvHead(pv);
    this._lvSyncCtl(host, pv, true);
  }

  /** Load average with context: "0,50 · 13 % von 4 Kernen". */
};
