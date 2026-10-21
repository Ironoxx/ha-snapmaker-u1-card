/** Layer view: paths of the current layer with printed/pending state. */

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
        <div class="lv-legend" data-su1="lvlegend">${this._layerLegend()}</div>
        <div class="lv-objects" data-su1="lvobjects">${this._objectsHtml()}</div>
      </section>`;
  }

  /** Colour per logical filament: head from the mapping -> loaded spool, else the file colour. */
  _toolColor(tool) {
    const c = (this._lv && this._lv.data && this._lv.data.colors) || {};
    const head = Array.isArray(c.map_table) ? c.map_table[tool] : undefined;
    const slot = (this._slots() || [])[head !== undefined ? head : tool];
    if (slot && slot.loaded && slot.color) return slot.color;
    if (c.file && c.file[String(tool)]) return c.file[String(tool)];
    return LAYER_PALETTE[tool % LAYER_PALETTE.length];
  }

  _layerSvg() {
    const lv = this._lv;
    if (!lv || !lv.data) return `<div class="t-label lv-msg">${tr("Schichtansicht wird vorbereitet …")}</div>`;
    const v = lv.data;
    if (v.status === "error") return `<div class="t-label lv-msg">${esc(tr("Schichtansicht nicht verfügbar: {e}", { e: v.error || "" }))}</div>`;
    if (v.status !== "ready" || !v.bbox) return `<div class="t-label lv-msg">${tr("Schichtansicht wird vorbereitet …")}</div>`;
    const bed = this._lvMode() === "bed";
    const [x0, y0, x1, y1] = bed ? [0, 0, BED_W, BED_D] : v.bbox;
    const pad = bed ? 10 : Math.max(3, (x1 - x0 + y1 - y0) * 0.03);
    // bed view: extra room behind the plate for the parked heads
    const top = bed ? y1 + DOCK_DEPTH : y1;
    const vb = [x0 - pad, -(top + pad), x1 - x0 + 2 * pad, top - y0 + 2 * pad].map((n) => n.toFixed(2)).join(" ");
    const pos = lv.position;
    const ex = this._exclude();
    const excluded = new Set(ex.excluded);
    const lines = (v.segs || []).map(([tool, pts, off, obj]) => {
      const p = [];
      for (let i = 0; i < pts.length; i += 2) p.push(`${pts[i]},${-pts[i + 1]}`);
      const todo = pos !== null && pos !== undefined && off >= pos;
      const cls = [todo ? "todo" : "", obj && excluded.has(obj) ? "excl" : ""].filter(Boolean).join(" ");
      return `<polyline points="${p.join(" ")}" stroke="${esc(this._toolColor(tool))}" data-o="${off}"${cls ? ` class="${cls}"` : ""}/>`;
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
    const ground = bed ? this._bedSvg() : `<rect x="${(x0 - pad).toFixed(2)}" y="${(-(y1 + pad)).toFixed(2)}" width="${(x1 - x0 + 2 * pad).toFixed(2)}" height="${(y1 - y0 + 2 * pad).toFixed(2)}" class="lv-bed"/>`;
    return `<svg viewBox="${vb}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${tr("Schichtansicht")}">
        ${ground}
        <g class="lv-paths" stroke-width="${w.toFixed(2)}">${lines}</g>
        ${bed ? this._nozzleSvg(v, pos) : ""}
        ${outlines ? `<g class="lv-objs">${outlines}</g>` : ""}
        ${v.missing || !(v.segs || []).length ? `<text x="${((x0 + x1) / 2).toFixed(1)}" y="${(-(y0 + y1) / 2).toFixed(1)}" class="lv-empty">${tr("keine Bahnen")}</text>` : ""}
      </svg>`;
  }

  _layerLegend() {
    const v = this._lv && this._lv.data;
    if (!v || v.status !== "ready") return "";
    const used = [...new Set((v.segs || []).map((s) => s[0]))].sort((a, b) => a - b);
    const heads = this._d ? this._d.heads : [];
    const c = v.colors || {};
    return used.map((t) => {
      const head = Array.isArray(c.map_table) ? c.map_table[t] : t;
      const h = heads[head];
      return `<span><i style="background:${esc(this._toolColor(t))}"></i>${tr("Filament {n}", { n: t + 1 })}${h ? ` → ${esc(h.name)}` : ""}</span>`;
    }).join("") + (this._lv.position !== null && this._lv.position !== undefined
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
  _bedSvg() {
    const grid = [];
    for (let g = 10; g < BED_W; g += 10) {
      const major = g % 50 === 0 ? " major" : "";
      grid.push(`<line x1="${g}" y1="0" x2="${g}" y2="${-BED_D}" class="lv-grid${major}"/>`);
      grid.push(`<line x1="0" y1="${-g}" x2="${BED_W}" y2="${-g}" class="lv-grid${major}"/>`);
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
        <g>${grid.join("")}</g>
        <circle cx="4" cy="-4" r="1.6" class="lv-origin"/>
        <g class="lv-dock">${dock}</g>
      </g>`;
  }

  /** Nozzle marker: end of the last printed path before the file position. */
  _nozzleSvg(v, pos) {
    if (pos === null || pos === undefined || !this._d || !this._d.printing) return "";
    let best = null;
    for (const seg of v.segs || []) {
      if (seg[2] <= pos && (!best || seg[2] >= best[2])) best = seg;
    }
    if (!best || best[1].length < 2) return "";
    const n = best[1].length;
    const x = best[1][n - 2], y = best[1][n - 1];
    return `<g class="lv-nozzle" transform="translate(${x},${-y})">
        <circle r="7" class="ring"/><circle r="2.2" class="dot"/>
        <line x1="-11" y1="0" x2="-8" y2="0"/><line x1="8" y1="0" x2="11" y2="0"/>
        <line x1="0" y1="-11" x2="0" y2="-8"/><line x1="0" y1="8" x2="0" y2="11"/>
      </g>`;
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
    return `<div class="t-label">${tr("Objekte – antippen zum Ausschließen")}</div><div class="chip-row">${ex.objects.map((o) => {
      const off = excluded.has(o.name);
      const cur = !off && o.name === ex.current;
      const last = !off && left <= 1;
      return `<button type="button" class="chip obj-chip${off ? " off" : ""}${cur ? " cur" : ""}" data-obj="${esc(o.name)}"
        ${off || last ? "disabled" : ""} title="${esc(off ? tr("Ausgeschlossen") : last ? tr("Letztes Objekt") : tr("Ausschließen"))}">
        <ha-icon icon="${off ? "mdi:cancel" : cur ? "mdi:printer-3d-nozzle" : "mdi:cube-outline"}"></ha-icon>${esc(o.label || o.name)}</button>`;
    }).join("")}</div>`;
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

  _wireObjects(root) {
    if (!root || root._objWired) return;
    root._objWired = true;
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
    const want = d.layer || 1;
    const lv = this._lv || (this._lv = { layer: null, data: null, position: null });
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
    this._paintLayer(needLayer || exChanged);
  }

  _paintLayer(full) {
    const r = this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-lv]");
    if (!box) return;
    if (full || !box.querySelector("svg") || this._lvMode() === "bed") box.innerHTML = this._layerSvg();
    else {
      const pos = this._lv.position;
      box.querySelectorAll("polyline").forEach((pl) =>
        pl.classList.toggle("todo", pos !== null && pos !== undefined && Number(pl.dataset.o) >= pos));
    }
    const v = this._lv.data;
    const head = r.querySelector('[data-su1="lvhead"]');
    if (head) head.textContent = v && v.status === "ready" && !v.missing
      ? `${tr("Schicht {n} / {t}", { n: v.layer, t: (this._d && this._d.totalLayers) || v.total })}${v.z !== null && v.z !== undefined ? ` · Z ${fixed(v.z, 2)} mm` : ""}` : "";
    const leg = r.querySelector('[data-su1="lvlegend"]');
    if (leg) leg.innerHTML = this._layerLegend();
    const objs = r.querySelector('[data-su1="lvobjects"]');
    if (objs) objs.innerHTML = this._objectsHtml();
    this._wireObjects(box.closest(".lv-panel"));
  }

  /** Load average with context: "0,50 · 13 % von 4 Kernen". */
};
