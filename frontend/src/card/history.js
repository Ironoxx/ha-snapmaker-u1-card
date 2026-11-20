/** History tab: 12-month charts, material table, print history and statistics. */

import { METRICS, RESULT } from "../const.js";
import { esc, fmtDate, fmtInt, fmtMin, fmtMoney, num } from "../format.js";
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
        h.switches > 1 ? tr("{n} Wechsel", { n: fmtInt(h.switches) }) : null,
        Array.isArray(h.pause_layers) && h.pause_layers.length ? tr("Pause vor {l}", { l: h.pause_layers.join(", ") }) : null,
        h.error || null,
        // Spoolman per spool: remaining before -> after, else the booked amount (⏳ = not booked yet)
        Array.isArray(h.spools) && h.spools.length
          ? h.spools.map((sp) => {
            const g = (v) => `${Math.round(v)} g`;
            const pending = sp.booked === false ? " ⏳" : "";
            if (typeof sp.before === "number" && typeof sp.after === "number")
              return `#${sp.spool_id} ${g(sp.before)} → ${g(sp.after)}${pending}`;
            return `#${sp.spool_id} −${String(sp.grams).replace(".", ",")} g${pending}`;
          }).join(", ")
          : null,
      ].filter(Boolean);
      const thumb = h.thumb ? `<img src="${esc(h.thumb)}" alt="" loading="lazy" />`
        : `<ha-icon icon="mdi:printer-3d"></ha-icon>`;
      return `
        <div class="hist" data-hist="${idx}" role="button" tabindex="0" title="${tr("Details anzeigen")}">
          <span class="hist-thumb">${thumb}</span>
          ${h.photo ? `<span class="hist-photo-wrap"><img class="hist-photo" src="${esc(h.photo)}" alt="${tr("Ergebnisfoto")}" loading="lazy" />
            <ha-icon class="hist-zoom" icon="mdi:magnify-plus-outline" aria-hidden="true"></ha-icon></span>` : ""}
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
              ? `<span class="hist-cost" title="${esc(tr("Strom {e} · Filament {f}", { e: fmtMoney(h.energy_cost), f: fmtMoney(h.filament_cost) }))}">${fmtMoney(h.total_cost)}</span>` : ""}
          </div>
          <ha-icon class="row-go" icon="mdi:chevron-right" aria-hidden="true"></ha-icon>
        </div>`;
    }).join("") : `<div class="t-label">${tr("Noch keine Drucke erfasst. Die Historie füllt sich ab dem nächsten Druck.")}</div>`;
    const sum = list.reduce((acc, h) => {
      if (h.total_cost !== undefined && h.total_cost !== null) acc.cost += h.total_cost;
      if (h.energy) acc.energy += h.energy;
      return acc;
    }, { cost: 0, energy: 0 });
    const summary = list.length
      ? `<span class="t-label" style="margin-left:auto">${tr("{n} Drucke", { n: list.length })}${sum.energy ? ` · ${num(sum.energy, 1, "kWh")}` : ""}${sum.cost ? ` · ${fmtMoney(sum.cost)}` : ""}</span>` : "";
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

  /**
   * 2.4.0b4: one print of the history as a pop-up, like the timelapse player:
   * result photo (or the file's preview, switchable when both exist), the facts,
   * the spools with their grams, and reprint / timelapse / photo download.
   * Everything comes from the history sensor the card has anyway; the image
   * loads only now.
   */
  _historyDetail(idx) {
    const h = (this._d.history || [])[idx];
    if (!h) return;
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1hist");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1hist" aria-label="${tr("Druckdetails")}"></dialog>`);
      dlg = host.querySelector("dialog.u1hist");
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
      dlg.addEventListener("close", () => { dlg.innerHTML = ""; });
    }
    const [rawLabel, tone] = RESULT[h.result] || [h.result || "—", ""];
    const files = new Set((this._d.files || []).map((f) => f.path));
    const canReprint = files.has(h.source || h.file);
    const video = this._historyVideo(h);
    const images = [h.photo ? { src: h.photo, label: tr("Ergebnisfoto") } : null,
      h.thumb ? { src: h.thumb, label: tr("Vorschau") } : null].filter(Boolean);
    const spoolRows = Array.isArray(h.spools) ? h.spools.map((sp) => {
      const g = (v) => `${Math.round(v)} g`;
      const head = (this._d.heads[sp.slot] || {}).name || `E${sp.slot}`;
      const rest = typeof sp.before === "number" && typeof sp.after === "number" ? ` (${g(sp.before)} → ${g(sp.after)})` : "";
      return [`${tr("Spule")} #${sp.spool_id}`, `${head} · −${String(sp.grams).replace(".", ",")} g${rest}${sp.booked === false ? " ⏳" : ""}`];
    }) : [];
    const opts = h.options || {};
    const optList = [opts.timelapse ? tr("Zeitraffer") : null, opts.bed_leveling ? tr("Bettnivellierung") : null,
      opts.flow_calibration ? tr("Flusskalibrierung") : null,
      Array.isArray(h.pause_layers) && h.pause_layers.length ? tr("Pause vor {l}", { l: h.pause_layers.join(", ") }) : null]
      .filter(Boolean);
    const rows = [
      [tr("Ergebnis"), tr(rawLabel)],
      h.error ? [tr("Meldung"), h.error] : null,
      [tr("Ende"), fmtDate(h.ended)],
      h.duration ? [tr("Dauer"), fmtMin(h.duration / 60)] : null,
      h.filament_g != null ? [tr("Filament"), `${Math.round(h.filament_g)} g`] : null,
      ...spoolRows,
      h.energy != null ? [tr("Strom"), num(h.energy, 2, "kWh")] : null,
      h.total_cost != null ? [tr("Kosten"), `${fmtMoney(h.total_cost)}${h.filament_cost != null || h.energy_cost != null
        ? ` (${tr("Strom {e} · Filament {f}", { e: fmtMoney(h.energy_cost), f: fmtMoney(h.filament_cost) })})` : ""}`] : null,
      h.switches > 1 ? [tr("Werkzeugwechsel"), fmtInt(h.switches)] : null,
      optList.length ? [tr("Optionen"), optList.join(" · ")] : null,
    ].filter(Boolean);
    dlg.innerHTML = `<div class="dlg vid">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${esc(h.name || h.file || tr("Druck"))}</div>
          <div class="t-label"><span class="chip sm" data-tone="${tone}">${esc(tr(rawLabel))}</span> ${esc(fmtDate(h.ended))}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        ${images.length ? `<div class="hist-big"><img data-histimg style="cursor:zoom-in" src="${esc(images[0].src)}" alt="${esc(images[0].label)}" /></div>
          ${images.length > 1 ? `<div class="chips">${images.map((im, i) => `<button type="button" class="chip sm" data-histpic="${i}" aria-pressed="${i === 0}">${esc(im.label)}</button>`).join("")}</div>` : ""}` : ""}
        <div class="rows">${rows.map(([k, v]) => `<div class="row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`).join("")}</div>
        <div class="dlg-actions">
          ${h.photo ? `<a class="btn outline" href="${esc(h.photo)}" download><ha-icon icon="mdi:download"></ha-icon>${tr("Foto")}</a>` : ""}
          ${video ? `<button type="button" class="outline" data-histvideo><ha-icon icon="mdi:filmstrip"></ha-icon>${tr("Zeitraffer")}</button>` : ""}
          ${canReprint ? `<button type="button" class="filled" data-histreprint><ha-icon icon="mdi:restart"></ha-icon>${tr("Nochmal drucken")}</button>` : ""}
        </div>
      </div>`;
    const q = (sel) => dlg.querySelector(sel);
    q("[data-close]").addEventListener("click", () => dlg.close());
    // the big picture opens full size (same viewer as before 2.4.0b4)
    if (q("[data-histimg]")) q("[data-histimg]").addEventListener("click", () => this._showPhoto(q("[data-histimg]").getAttribute("src")));
    dlg.querySelectorAll("[data-histpic]").forEach((b) => b.addEventListener("click", () => {
      const im = images[Number(b.dataset.histpic)];
      q("[data-histimg]").src = im.src;
      dlg.querySelectorAll("[data-histpic]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }));
    if (q("[data-histvideo]")) q("[data-histvideo]").addEventListener("click", () => { dlg.close(); this._tlOpen(video); });
    if (q("[data-histreprint]")) q("[data-histreprint]").addEventListener("click", () => { dlg.close(); this._reprint(idx); });
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
  }

  /** Timelapse of a print: same file name stem, recorded within a few hours of its end (backup first). */
  _historyVideo(h) {
    const tl = this._d.timelapses;
    if (!tl || !h.ended) return null;
    // file names on the printer use "_" where the print name has spaces
    const norm = (x) => String(x || "").toLowerCase().replace(/[\s_]+/g, " ").trim();
    const stem = norm(h.name || (h.file || "").split("/").pop().replace(/\.gcode$/i, ""));
    if (!stem) return null;
    const end = Date.parse(h.ended) / 1000;
    const near = (ts) => ts && Math.abs(ts - end) < 4 * 3600;
    const archive = (tl.archive && tl.archive.videos) || [];
    const ai = archive.findIndex((v) => norm(v.file).startsWith(stem) && near(v.modified));
    if (ai >= 0) return `a:${ai}`;
    const pi = (tl.videos || []).findIndex((v) => norm(v.name || (v.path || "").split("/").pop()).startsWith(stem)
      && near(v.recorded ? Date.parse(v.recorded) / 1000 : v.modified));
    return pi >= 0 ? `p:${pi}` : null;
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
      return b.cost === null ? "—" : fmtMoney(b.cost);
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
      : `${String(t.success_rate).replace(".", LANG === "en" ? "." : ",")} %`;
    const tiles = [
      [tr("Drucke"), fmtInt(t.prints)],
      [tr("Erfolgsquote"), rate],
      [tr("Druckstunden"), num(t.hours_total ?? t.hours, 0, "h")],
      [tr("Filament"), num(t.filament_kg, 2, "kg")],
      t.energy !== null && t.energy !== undefined
        ? [tr("Strom"), num(t.energy, 1, "kWh"), tr("Gemessen bei Drucken seit Installation der Integration.")] : null,
      t.cost !== null && t.cost !== undefined
        ? [tr("Kosten"), (t.cost_estimated ? "≈ " : "") + fmtMoney(t.cost),
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
        <td>${m.cost !== null && m.cost !== undefined ? fmtMoney(m.cost) : "—"}</td>
        <td>${m.success_rate !== null && m.success_rate !== undefined ? num(m.success_rate, 0, "%") : "—"}</td></tr>`).join("");
    const colors = ((st && st.colors) || []).map((c) =>
      `<span title="${esc(c.type)}"><i style="background:${esc(c.color)}"></i>${esc(c.type)} ${num(c.grams, 0, "g")}</span>`).join("");
    return `<div class="panel-sub"><div class="t-label" style="margin:8px 0 4px">${tr("Nach Material")}</div>
      <table class="mat-table"><thead><tr><th>${tr("Material")}</th><th>${tr("Drucke")}</th><th>${tr("Verbrauch")}</th><th>${tr("Kosten")}</th><th>${tr("Erfolg")}</th></tr></thead>
      <tbody>${rows}</tbody></table>
      ${colors ? `<div class="t-label" style="margin:10px 0 4px">${tr("Meistgenutzte Farben")}</div><div class="colors">${colors}</div>` : ""}</div>`;
  }
};
