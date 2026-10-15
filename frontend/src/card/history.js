/** History tab: 12-month charts, material table, print history and statistics. */

import { METRICS, RESULT } from "../const.js";
import { esc, fmtDate, fmtEuro, fmtInt, fmtMin, num } from "../format.js";
import { LANG, LOCALE, tr } from "../i18n.js";

export const HistoryMixin = (Base) => class extends Base {
  _sectionHistory() {
    const list = this._d.history;
    if (!list) return "";
    const files = new Set((this._d.files || []).map((f) => f.path));
    const rows = list.length ? list.map((h, idx) => {
      const [rawLabel, tone] = RESULT[h.result] || [h.result || "—", ""];
      const label = tr(rawLabel);
      const facts = [
        h.duration ? fmtMin(h.duration / 60) : null,
        h.filament_g !== undefined && h.filament_g !== null ? `${Math.round(h.filament_g)} g` : null,
        h.energy !== undefined && h.energy !== null ? num(h.energy, 2, "kWh") : null,
        h.switches ? tr("{n} Wechsel", { n: fmtInt(h.switches) }) : null,
        Array.isArray(h.pause_layers) && h.pause_layers.length ? tr("Pause vor {l}", { l: h.pause_layers.join(", ") }) : null,
        h.error || null,
        // Spoolman: booked amounts per spool (⏳ = not booked yet)
        Array.isArray(h.spools) && h.spools.length
          ? h.spools.map((sp) => `#${sp.spool_id} −${String(sp.grams).replace(".", ",")} g${sp.booked === false ? " ⏳" : ""}`).join(", ")
          : null,
      ].filter(Boolean);
      const thumb = h.thumb ? `<img src="${esc(h.thumb)}" alt="" loading="lazy" />`
        : `<ha-icon icon="mdi:printer-3d"></ha-icon>`;
      return `
        <div class="hist">
          <span class="hist-thumb">${thumb}</span>
          ${h.photo ? `<img class="hist-photo" src="${esc(h.photo)}" alt="${tr("Ergebnisfoto")}" title="${tr("Ergebnisfoto")}" data-photo="${esc(h.photo)}" loading="lazy" />` : ""}
          <div class="hist-main">
            <div class="hist-name" title="${esc(h.file || "")}">${esc(h.name || h.file || tr("Druck"))}</div>
            <div class="t-label">${esc(fmtDate(h.ended))} · ${facts.map(esc).join(" · ") || "—"}</div>
          </div>
          <div class="hist-side">
            <span class="hist-top">
              ${files.has(h.source || h.file) ? `<button class="icon ghost" data-reprint="${idx}" title="${tr("Nochmal drucken")}" aria-label="${tr("Nochmal drucken")}"><ha-icon icon="mdi:restart"></ha-icon></button>` : ""}
              <span class="chip sm" data-tone="${tone}">${esc(label)}</span>
            </span>
            ${h.total_cost !== undefined && h.total_cost !== null
              ? `<span class="hist-cost" title="${esc(tr("Strom {e} · Filament {f}", { e: fmtEuro(h.energy_cost), f: fmtEuro(h.filament_cost) }))}">${fmtEuro(h.total_cost)}</span>` : ""}
          </div>
        </div>`;
    }).join("") : `<div class="t-label">${tr("Noch keine Drucke erfasst. Die Historie füllt sich ab dem nächsten Druck.")}</div>`;
    const sum = list.reduce((acc, h) => {
      if (h.total_cost !== undefined && h.total_cost !== null) acc.cost += h.total_cost;
      if (h.energy) acc.energy += h.energy;
      return acc;
    }, { cost: 0, energy: 0 });
    const summary = list.length
      ? `<span class="t-label" style="margin-left:auto">${tr("{n} Drucke", { n: list.length })}${sum.energy ? ` · ${num(sum.energy, 1, "kWh")}` : ""}${sum.cost ? ` · ${fmtEuro(sum.cost)}` : ""}</span>` : "";
    return `
      <section class="panel span2">
        <details ${this._cfg.compact ? "" : "open"}>
          <summary>
            <ha-icon icon="mdi:history"></ha-icon>
            <span>${tr("Druckhistorie")}</span>${summary}
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon>
          </summary>
          <div class="body hist-list">${rows}</div>
        </details>
      </section>`;
  }

  _sectionCharts() {
    const st = this._d.stats;
    if (!st) return "";
    const metric = this._metric || "prints";
    const monthName = (m) => {
      const [y, mo] = m.split("-").map(Number);
      return new Date(y, mo - 1, 1).toLocaleDateString(LOCALE, { month: "short" });
    };
    const val = (b) => (metric === "prints" ? b.prints + b.failed : Number(b[metric]) || 0);
    const max = Math.max(1e-9, ...st.months.map(val));
    const fmt = (b) => {
      if (metric === "prints") return `${b.prints} ${tr("fertig")}, ${b.failed} ${tr("abgebrochen")}`;
      if (metric === "hours") return num(b.hours, 1, "h");
      if (metric === "filament_g") return b.filament_g >= 1000 ? num(b.filament_g / 1000, 2, "kg") : num(b.filament_g, 0, "g");
      return b.cost === null ? "—" : fmtEuro(b.cost);
    };
    const bars = st.months.map((b) => {
      const total = val(b);
      const h = (total / max) * 100;
      const okPart = metric === "prints" && total ? (b.prints / total) * 100 : 100;
      return `<div class="bar" title="${esc(`${monthName(b.month)} ${b.month.slice(0, 4)}: ${fmt(b)}`)}">
          <div class="bar-col" style="height:${h.toFixed(1)}%">
            ${metric === "prints" && b.failed ? `<i class="bar-fail" style="height:${(100 - okPart).toFixed(1)}%"></i>` : ""}
            <i class="bar-ok" style="height:${okPart.toFixed(1)}%"></i>
          </div>
          <span class="bar-x">${esc(monthName(b.month))}</span>
        </div>`;
    }).join("");
    const t = st.totals;
    const cost = st.months.some((b) => b.cost !== null);
    const chips = METRICS.filter(([k]) => k !== "cost" || cost).map(([k, label]) =>
      `<button class="chip ${k === metric ? "sel" : ""}" data-metric="${k}">${tr(label)}</button>`).join("");
    const rate = t.success_rate === null || t.success_rate === undefined ? "—"
      : `${String(t.success_rate).replace(".", LANG === "de" ? "," : ".")} %`;
    const tiles = [
      [tr("Drucke"), fmtInt(t.prints)],
      [tr("Erfolgsquote"), rate],
      [tr("Druckstunden"), num(t.hours_total ?? t.hours, 0, "h")],
      [tr("Filament"), num(t.filament_kg, 2, "kg")],
      t.energy !== null && t.energy !== undefined
        ? [tr("Strom"), num(t.energy, 1, "kWh"), tr("Gemessen bei Drucken seit Installation der Integration.")] : null,
      t.cost !== null && t.cost !== undefined
        ? [tr("Kosten"), (t.cost_estimated ? "≈ " : "") + fmtEuro(t.cost),
          t.cost_estimated ? tr("Ältere Drucke mit Filamentpreis geschätzt, ohne Strom.") : ""] : null,
    ].filter(Boolean).map(([k, v, hint]) => this._stat(k, v, "sm", hint)).join("");
    const top = (st.top || []).slice(0, 3).map((f) =>
      `<span class="top-file">${esc(String(f.file).split("/").pop().replace(/\.(gcode|3mf)$/i, ""))} <b>×${f.count}</b></span>`).join("");
    return `
      <section class="panel span2 span3">
        <div class="panel-head">
          <ha-icon icon="mdi:chart-bar"></ha-icon>
          <span class="panel-title">${tr("Letzte 12 Monate")}</span>
          <span class="chart-chips">${chips}</span>
        </div>
        <div class="chart" role="img" aria-label="${tr("Diagramm")}">${bars}</div>
        ${metric === "prints" ? `<div class="legend t-label"><i class="bar-ok"></i>${tr("fertig")}<i class="bar-fail"></i>${tr("abgebrochen")}</div>` : ""}
        <div class="stats">${tiles}</div>
        ${top ? `<div class="t-label">${tr("Am häufigsten")}: ${top}</div>` : ""}
        ${this._materialsHtml(st)}
      </section>`;
  }

  /** Consumption per material and colour from Moonraker's print history. */
  _materialsHtml(st) {
    const mats = (st && st.materials) || [];
    if (!mats.length) return "";
    const rows = mats.map((m) => `<tr><td>${esc(m.type)}</td><td>${m.prints}</td>
        <td>${m.grams >= 1000 ? num(m.grams / 1000, 2, "kg") : num(m.grams, 0, "g")}</td>
        <td>${m.cost !== null && m.cost !== undefined ? fmtEuro(m.cost) : "—"}</td>
        <td>${m.success_rate !== null && m.success_rate !== undefined ? num(m.success_rate, 0, "%") : "—"}</td></tr>`).join("");
    const colors = ((st && st.colors) || []).map((c) =>
      `<span title="${esc(c.type)}"><i style="background:${esc(c.color)}"></i>${esc(c.type)} ${num(c.grams, 0, "g")}</span>`).join("");
    return `<div class="panel-sub"><div class="t-label" style="margin:8px 0 4px">${tr("Nach Material")}</div>
      <table class="mat-table"><thead><tr><th>${tr("Material")}</th><th>${tr("Drucke")}</th><th>${tr("Verbrauch")}</th><th>${tr("Kosten")}</th><th>${tr("Erfolg")}</th></tr></thead>
      <tbody>${rows}</tbody></table>
      ${colors ? `<div class="t-label" style="margin:10px 0 4px">${tr("Meistgenutzte Farben")}</div><div class="colors">${colors}</div>` : ""}</div>`;
  }
};
