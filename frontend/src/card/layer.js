/** Layer view: paths of the current layer with printed/pending state. */

import { DOMAIN, LAYER_PALETTE } from "../const.js";
import { esc, fixed } from "../format.js";
import { tr } from "../i18n.js";

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
        </div>
        <div class="lv" data-lv>${this._layerSvg()}</div>
        <div class="lv-legend" data-su1="lvlegend">${this._layerLegend()}</div>
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
    const [x0, y0, x1, y1] = v.bbox;
    const pad = Math.max(3, (x1 - x0 + y1 - y0) * 0.03);
    const vb = [x0 - pad, -(y1 + pad), x1 - x0 + 2 * pad, y1 - y0 + 2 * pad].map((n) => n.toFixed(2)).join(" ");
    const pos = lv.position;
    const lines = (v.segs || []).map(([tool, pts, off]) => {
      const p = [];
      for (let i = 0; i < pts.length; i += 2) p.push(`${pts[i]},${-pts[i + 1]}`);
      const todo = pos !== null && pos !== undefined && off >= pos;
      return `<polyline points="${p.join(" ")}" stroke="${esc(this._toolColor(tool))}" data-o="${off}"${todo ? ' class="todo"' : ""}/>`;
    }).join("");
    // Stroke width like a real extrusion (0.45 mm), a little bolder for very large parts
    const w = Math.max(0.45, Math.min(0.9, (x1 - x0) / 250));
    return `<svg viewBox="${vb}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${tr("Schichtansicht")}">
        <rect x="${(x0 - pad).toFixed(2)}" y="${(-(y1 + pad)).toFixed(2)}" width="${(x1 - x0 + 2 * pad).toFixed(2)}" height="${(y1 - y0 + 2 * pad).toFixed(2)}" class="lv-bed"/>
        <g class="lv-paths" stroke-width="${w.toFixed(2)}">${lines}</g>
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
    this._paintLayer(needLayer);
  }

  _paintLayer(full) {
    const r = this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-lv]");
    if (!box) return;
    if (full || !box.querySelector("svg")) box.innerHTML = this._layerSvg();
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
  }

  /** Load average with context: "0,50 · 13 % von 4 Kernen". */
};
