/** Overview tab: camera stage, job progress, last print and the print heads. */

import { colorDistance } from "../color.js";
import { DOMAIN, RESULT } from "../const.js";
import { clamp, esc, fixed, fmtClock, fmtDate, fmtEuro, fmtInt, fmtMin, num } from "../format.js";
import { tr } from "../i18n.js";

export const OverviewMixin = (Base) => class extends Base {
  _sectionStage() {
    const d = this._d;
    const fit = ["cover", "contain", "fill"].includes(this._cfg.camera_fit)
      ? this._cfg.camera_fit : "contain";
    const h = parseInt(this._cfg.camera_height, 10) || 0;
    const still = this._cfg.printer_image;
    // Without a fixed height: aspect ratio of the camera image (16:9 until it has loaded)
    const frameStyle = h ? `min-height:${h}px;height:${h}px`
      : `aspect-ratio:${this._camAspect || "16 / 9"};max-height:${parseInt(this._cfg.camera_max_height, 10) || 520}px`;

    // Own camera found nothing: no black area, a short hint instead
    const own = !still && this._ents.ownCamera && this._st(this._ents.ownCamera);
    if (own && own.attributes.mode === "none") return this._noCamera();

    const img = still
      ? `<img src="${esc(still)}" style="object-fit:${fit}" alt="Snapmaker U1" />`
      : `<img data-live style="object-fit:${fit}" alt="${tr("Druckraum")}" />`;

    const thumbEnt = this._st(this._ents.thumbnail);
    const hud = this._cfg.camera_overlay !== false && d.active && !d.paused && d.state !== "error"
      ? this._hud() : "";
    const thumb = thumbEnt && thumbEnt.attributes.entity_picture && d.filename
      ? `<div class="thumb${hud ? " top" : ""}"><img src="${thumbEnt.attributes.entity_picture}" alt="${tr("Vorschau")}" /><span>${esc(d.filename)}</span></div>`
      : "";

    let overlay = "";
    let dim = "0";
    if (d.paused) {
      dim = "1";
      overlay = `<div class="overlay">
        <div class="overlay-ring" data-tone="warn"><ha-icon icon="mdi:pause"></ha-icon></div>
        <div class="overlay-title">${tr("Pausiert")}</div>
        <div class="overlay-sub">${tr("Temperaturen werden gehalten")}</div>
      </div>`;
    } else if (d.state === "error") {
      dim = "1";
      overlay = `<div class="overlay">
        <div class="overlay-ring" data-tone="error"><ha-icon icon="mdi:alert-circle-outline"></ha-icon></div>
        <div class="overlay-title">${tr("Druck gestoppt")}</div>
        <div class="overlay-sub">${esc((d.errors[0] && this._errText(d.errors[0])) || d.message || tr("Der Drucker meldet einen Fehler"))}</div>
      </div>`;
    }
    // State in the corner instead of a full overlay: the camera stays visible while idle.
    const tone = this._statusTone();
    const sub = !d.active && (d.display || d.message) ? `<small>${esc(d.display || d.message)}</small>` : "";
    const pill = `<div class="cam-state" data-tone="${tone}" role="status">
        <span class="dot"></span><span class="cam-state-text"><b data-su1="camstate">${this._statusLabel()}</b>${sub}</span>
      </div>`;

    const actions = [this._stageActions()];

    return `
      <section class="panel stage span2">
        <div class="frame" data-dim="${dim}" style="${frameStyle}">
          ${img}
          <div class="veil"></div>
          <span class="badge-stale"><ha-icon icon="mdi:camera-off" style="--mdc-icon-size:14px"></ha-icon>${tr("Bild veraltet")}</span>
          <div class="zoom-ctl">
            <button type="button" class="zoom-btn" data-zoom="in" title="${tr("Vergrößern")}" aria-label="${tr("Vergrößern")}"><ha-icon icon="mdi:magnify-plus-outline"></ha-icon></button>
            <button type="button" class="zoom-btn" data-zoom="out" title="${tr("Verkleinern")}" aria-label="${tr("Verkleinern")}" hidden><ha-icon icon="mdi:magnify-minus-outline"></ha-icon></button>
            ${document.fullscreenEnabled || document.webkitFullscreenEnabled ? `<button type="button" class="zoom-btn" data-zoom="full" title="${tr("Vollbild")}" aria-label="${tr("Vollbild")}"><ha-icon icon="mdi:fullscreen"></ha-icon></button>` : ""}
            ${this._hasCamera2() ? `<button type="button" class="zoom-btn" data-camswitch title="${tr("Kamera wechseln")}" aria-label="${tr("Kamera wechseln")}" aria-pressed="${!!this._ents.camAlt}"><ha-icon icon="mdi:camera-switch-outline"></ha-icon></button>` : ""}
          </div>
          <span class="zoom-badge" hidden></span>
          ${pill}
          ${thumb}
          ${overlay}
          ${hud}
        </div>
        <div class="stage-actions">${actions.join("")}</div>
      </section>`;
  }

  _noCamera() {
    const actions = [this._stageActions()];
    return `
      <section class="panel stage span2 no-cam">
        <div class="no-cam-msg"><ha-icon icon="mdi:camera-off"></ha-icon>
          <span>${tr("Keine Kamera erkannt. Der Selbsttest im System-Reiter zeigt, was die Integration gefunden hat.")}</span></div>
        <div class="stage-actions">${actions.join("")}</div>
      </section>`;
  }

  /** Progress directly on the camera image (running print). */
  _hud() {
    const d = this._d;
    const h = d.heads.find((x) => x.active);
    const head = h ? `<span class="hud-head" title="${tr("Aktiver Kopf")}">
        <i style="background:${esc(h.color)}"></i>${esc(h.name)} · ${esc(h.material)}</span>` : "";
    return `<div class="hud">
        <div class="hud-row">
          <span class="hud-pct"><b class="mono" data-su1="opct">${d.progress.toFixed(0)}</b><small>%</small></span>
          <span class="hud-item"><ha-icon icon="mdi:layers-triple-outline"></ha-icon><span data-su1="olayer">${d.layer} / ${d.totalLayers}</span></span>
          <span class="hud-item"><ha-icon icon="mdi:timer-sand"></ha-icon><span data-su1="oremain">${fmtMin(d.remaining)}</span></span>
          <span class="hud-item"><ha-icon icon="mdi:flag-checkered"></ha-icon><span data-su1="oeta">${fmtClock(d.eta)}</span></span>
          ${head}
        </div>
        <div class="hud-track"><i data-su1="obar" style="width:${d.progress}%"></i></div>
      </div>`;
  }

  _sectionJob() {
    const d = this._d;
    const pct = d.progress;
    const tone = d.state === "error" ? "error" : d.paused ? "warn" : "";

    const w = (k, v) => `<span data-su1="${k}">${v}</span>`;
    if (!d.active) return this._sectionLastPrint();
    const grid = d.active ? [
      this._stat(tr("Schicht"), w("layer", `${d.layer} / ${d.totalLayers}`)),
      this._stat(tr("Restzeit"), w("remain", fmtMin(d.remaining)), "sm"),
      this._stat(tr("Fertig um"), w("eta", fmtClock(d.eta)), "sm"),
      this._stat(tr("Bisher"), w("elapsed", fmtMin(d.elapsed)), "sm"),
      this._stat(tr("Filament"), w("fil", num(d.filamentUsed, 1, "m"))),
      this._stat(tr("Höhe"), w("height", num(d.objectHeight, 1, "mm"))),
      this._stat(tr("Geschw."), w("pspeed", num(d.printSpeed, 0, "mm/s")), "sm"),
      this._stat(tr("Slicer-Rest"), w("sremain", fmtMin(d.slicerLeft)), "sm"),
    ] : [
      this._stat(tr("Drucke gesamt"), w("tjobs2", num(d.totalsJobs, 0))),
      this._stat(tr("Warteschlange"), w("queued", num(d.jobsQueued, 0))),
      this._stat(tr("Zuletzt"), w("elapsed", fmtMin(d.elapsed)), "sm"),
      this._stat(tr("Filament"), w("fil", num(d.filamentUsed, 1, "m"))),
    ];

    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:progress-clock"></ha-icon>
          <span class="panel-title">${d.active ? tr("Laufender Druck") : tr("Letzter Druck")}</span>
        </div>
        <div class="job-file" data-su1="file">${esc(d.filename || "—")}</div>
        <div class="job-pct-row">
          <span class="job-pct" data-su1="pct">${fixed(pct, 1)}</span>
          <span class="t-label">${tr("Prozent")}</span>
        </div>
        <div class="track" data-tone="${tone}"><i data-su1="bar" style="width:${pct}%"></i></div>
        <div class="stats">${grid.join("")}</div>
      </section>`;
  }

  /** Without a running print: last print from the history instead of empty zeros. */
  _sectionLastPrint() {
    const d = this._d;
    const h = (d.history || [])[0];
    const q = (d.queue || []).length;
    if (!h) {
      return `
      <section class="panel">
        <div class="panel-head"><ha-icon icon="mdi:progress-clock"></ha-icon>
          <span class="panel-title">${tr("Letzter Druck")}</span></div>
        <div class="t-label">${tr("Noch keine Drucke erfasst. Die Historie füllt sich ab dem nächsten Druck.")}</div>
        <div class="stats">
          ${this._stat(tr("Drucke gesamt"), num(d.totalsJobs || (d.stats && d.stats.totals.prints) || 0, 0))}
          ${this._stat(tr("Warteschlange"), fmtInt(q))}
        </div>
      </section>`;
    }
    const [rawLabel, tone] = RESULT[h.result] || [h.result || "—", ""];
    const tiles = [
      [tr("Dauer"), h.duration ? fmtMin(h.duration / 60) : "—"],
      [tr("Filament"), h.filament_g !== undefined && h.filament_g !== null ? `${Math.round(h.filament_g)} g` : "—"],
      h.energy !== undefined && h.energy !== null ? [tr("Strom"), num(h.energy, 2, "kWh")] : null,
      h.total_cost !== undefined && h.total_cost !== null ? [tr("Kosten"), fmtEuro(h.total_cost)] : null,
      [tr("Drucke gesamt"), num(d.totalsJobs || (d.stats && d.stats.totals.prints) || 0, 0)],
      [tr("Warteschlange"), fmtInt(q)],
    ].filter(Boolean).map(([k, v]) => this._stat(k, v, "sm")).join("");
    const thumb = h.thumb ? `<img src="${esc(h.thumb)}" alt="" loading="lazy" />` : `<ha-icon icon="mdi:printer-3d"></ha-icon>`;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:progress-clock"></ha-icon>
          <span class="panel-title">${tr("Letzter Druck")}</span>
          <span class="chip sm" data-tone="${tone}" style="margin-left:auto">${esc(tr(rawLabel))}</span>
        </div>
        <div class="last-print">
          <span class="hist-thumb last-thumb">${thumb}</span>
          <div style="min-width:0">
            <div class="hist-name">${esc(h.name || h.file || "—")}</div>
            <div class="t-label">${esc(fmtDate(h.ended))}${h.error ? ` · ${esc(h.error)}` : ""}</div>
          </div>
        </div>
        <div class="stats">${tiles}</div>
      </section>`;
  }

  _sectionHeads() {
    const d = this._d;
    const cards = d.heads.map((h) => {
      const heaterBtn = h.heater !== null
        ? `<button class="preset" data-lockable data-toggle="switch.${this._p(`output_pin_e${h.idx}_heat_sw`)}">
             ${h.heater === "on" ? tr("Heizung an") : tr("Heizung aus")}
           </button>`
        : "";
      return `
        <div class="head-card" data-active="${h.active ? 1 : 0}" data-head="${h.idx}">
          <div class="head-card-top" data-headopen="${h.idx}" title="${tr("Details und Filament bearbeiten")}">
            ${this._spoolSvg(h.color, h.active, h.colors)}
            <div style="min-width:0">
              <div class="head-name">${esc(h.name)}${h.official ? ` <span class="rfid" title="${tr("Snapmaker-Spule, per RFID erkannt")}">RFID</span>` : ""}</div>
              <div class="head-mat">${esc(h.material)}</div>
              ${h.vendor ? `<div class="head-vendor">${esc(h.vendor)}</div>` : ""}
            </div>
          </div>
          ${this._spoolLine(h)}
          <div class="head-tags">
            <span class="pill" data-empty="${h.loaded ? 0 : 1}" data-su1="pill:${h.idx}">
              ${h.loaded ? tr("Geladen") : tr("Leer")}
            </span>
            <button type="button" class="head-info" data-headinfo="${h.idx}" title="${tr("Details und Filament bearbeiten")}" aria-label="${tr("Details und Filament bearbeiten")}">
              <ha-icon icon="mdi:pencil-outline"></ha-icon><span>${tr("Filament")}</span>
            </button>
          </div>
          <div class="head-temp" data-su1="htemp:${h.idx}">
            ${num(h.temp, 0, "°C")}${h.target > 0 ? ` <span class="tgt">→ ${h.target.toFixed(0)} °C</span>` : ""}
          </div>
          <div class="track"><i data-su1="hbar:${h.idx}"
            style="width:${h.target > 0 && h.temp !== null ? clamp((h.temp / h.target) * 100, 0, 100) : 0}%"></i></div>
          <div class="mini">
            <span data-su1="hfan:${h.idx}">${tr("Lüfter {v}", { v: num(h.fan, 0, "%") })}</span>
            <span data-su1="hpow:${h.idx}">${tr("Heiz. {v}", { v: num(h.power, 0, "%") })}</span>
          </div>
          ${this._slider({
            entity: h.targetEntity, label: tr("Soll"), value: h.target,
            unit: "°C", presets: this._cfg.nozzle_presets,
          })}
          ${heaterBtn}
        </div>`;
    }).join("");

    return `
      <section class="panel span2 span3">
        <div class="panel-head">
          <ha-icon icon="mdi:printer-3d-nozzle"></ha-icon>
          <span class="panel-title">${tr("Druckköpfe")}</span>
          ${this._lockBtn()}
        </div>
        <div class="heads">${cards}</div>
      </section>`;
  }

  /** The head's spool from Spoolman (only with Spoolman configured). */
  _spoolLine(h) {
    const sm = this._spoolman();
    if (!sm) return "";
    const sp = this._slotSpool(h.idx);
    if (!h.loaded && !sp) return "";
    const back = !sp && sm.online && sm.restore && sm.restore[String(h.idx)];
    if (back) {
      // Unloading made the printer forget the spool: offer the one this head had
      const busy = this._isPending(`r:${h.idx}`);
      return `<div class="spool-restore">
          <button type="button" class="spool-line" data-spoolrestore="${h.idx}" data-spool="${back.id}" ${busy ? 'disabled aria-busy="true"' : ""}
            title="${esc(tr("Diese Spule steckte vor dem Entladen in diesem Kopf"))}">
            ${busy ? this._spin() : `<span class="spool-dot" style="--fil:${esc(back.color || "var(--u1-outline)")}"></span>`}
            <span>${esc(tr("Wieder #{id} {name}?", { id: back.id, name: [back.vendor, back.name].filter(Boolean).join(" ") }))}</span>
          </button>
          <button type="button" class="icon outline sm" data-spoolpick="${h.idx}" aria-label="${tr("Andere Spule wählen")}" title="${tr("Andere Spule wählen")}">
            <ha-icon icon="mdi:database-search-outline"></ha-icon></button>
        </div>`;
    }
    if (!sp) {
      return `<button type="button" class="spool-line" data-spoolpick="${h.idx}" data-none="1">
          <ha-icon icon="mdi:database-search-outline"></ha-icon><span>${sm.online ? tr("Spule wählen") : tr("Spoolman nicht erreichbar")}</span>
        </button>`;
    }
    const rest = sp.remaining_weight;
    const pct = rest != null && sp.initial_weight ? clamp((rest / sp.initial_weight) * 100, 0, 100) : null;
    const low = rest != null && rest < (sm.low || 0);
    return `<button type="button" class="spool-line" data-spoolpick="${h.idx}" data-low="${low ? 1 : 0}"
        title="${sp.manual ? tr("Spoolman-Spule #{id} (manuell gewählt) – zum Ändern tippen", { id: sp.id }) : tr("Spoolman-Spule #{id} (automatisch) – zum Ändern tippen", { id: sp.id })}">
        <span class="spool-top"><span class="spool-name">#${sp.id} ${esc(sp.name)}</span>
          <span class="spool-rest">${rest != null ? `${Math.round(rest)} g` : "–"}</span></span>
        ${pct != null ? `<span class="spool-track"><i style="width:${pct}%"></i></span>` : ""}
        ${this._runoutText(h.idx)}
      </button>`;
  }

  /** Spool runs out during the print (integration: time profile x Spoolman remainder). */
  _runoutText(idx) {
    const fst = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const r = fst && fst.attributes && fst.attributes.runout && fst.attributes.runout[String(idx)];
    if (!r) return "";
    const heads = this._d ? this._d.heads : [];
    const take = r.takeover !== null && r.takeover !== undefined
      ? ` · ${tr("{h} übernimmt", { h: (heads[r.takeover] || {}).name || tr("Kopf {n}", { n: r.takeover + 1 }) })}` : "";
    return `<span class="runout" data-runout="${idx}">${tr("leer in ~{m} min", { m: r.minutes })}${esc(take)}</span>`;
  }

  _openSpoolPicker(idx) {
    const sm = this._spoolman();
    if (!sm) return;
    const slot = (this._slots() || [])[idx] || {};
    const cur = this._slotSpool(idx);
    const head = (this._d && this._d.heads[idx]) || { name: `E${idx}` };
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1spool");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1spool" aria-label="${tr("Spule wählen")}"></dialog>`);
      dlg = host.querySelector("dialog.u1spool");
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    const type = (slot.type || "").toUpperCase();
    const list = (sm.spools || []).slice().sort((a, b) =>
      ((a.material || "").toUpperCase() === type ? 0 : 1) - ((b.material || "").toUpperCase() === type ? 0 : 1)
      || colorDistance(slot.color, a.color) - colorDistance(slot.color, b.color)
      || (a.name || "").localeCompare(b.name || ""));
    const used = Object.entries(sm.slots || {}).filter(([k, v]) => v && Number(k) !== idx).map(([k, v]) => [v.id, Number(k)]);
    const usedBy = new Map(used);
    const item = (sp) => {
      const other = usedBy.get(sp.id);
      return `<button type="button" class="spool-opt" data-pick="${sp.id}" aria-pressed="${cur && cur.id === sp.id}">
          <span class="spool-dot" style="--fil:${esc(sp.color || "var(--u1-outline)")}"></span>
          <span class="spool-opt-text"><span>#${sp.id} ${esc(sp.name)}</span>
            <span class="t-label">${[sp.vendor, sp.material, sp.location, other != null ? tr("steckt in {head}", { head: (this._d.heads[other] || {}).name || `E${other}` }) : ""].filter(Boolean).map(esc).join(" · ")}</span></span>
          <span class="spool-rest">${sp.remaining_weight != null ? `${Math.round(sp.remaining_weight)} g` : ""}</span>
        </button>`;
    };
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${esc(tr("Spule für {head}", { head: head.name }))}</div>
          <div class="t-label">${esc([slot.type, slot.sub_type, slot.vendor].filter(Boolean).join(" ") || tr("kein Filament erkannt"))}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        ${sm.spoollink ? `<div class="t-label">${tr("SpoolLink im Drucker: die Wahl geht an den Drucker (SET_SPOOL_ID), er übernimmt das Filament der Spule.")}</div>`
          : slot.official ? "" : `<div class="t-label">${tr("Material, Hersteller und Farbe der gewählten Spule werden in den Kopf übernommen.")}</div>`}
        ${sm.online ? "" : `<div class="dlg-note" data-tone="error"><ha-icon icon="mdi:database-off"></ha-icon>${tr("Spoolman nicht erreichbar")}${sm.error ? `: ${esc(sm.error)}` : ""}</div>`}
        <div class="spool-list">
          ${sm.spoollink ? "" : `<button type="button" class="spool-opt" data-pick="auto" aria-pressed="${!!(cur && !cur.manual)}">
            <ha-icon icon="mdi:auto-fix"></ha-icon><span class="spool-opt-text"><span>${tr("Automatisch")}</span>
            <span class="t-label">${tr("nach Material, Farbe und Hersteller")}</span></span></button>`}
          <button type="button" class="spool-opt" data-pick="0" aria-pressed="${!cur}">
            <ha-icon icon="mdi:close-circle-outline"></ha-icon><span class="spool-opt-text"><span>${tr("Keine Spule")}</span>
            <span class="t-label">${tr("nichts abbuchen")}</span></span></button>
          ${list.map(item).join("") || `<div class="t-label">${tr("Keine aktiven Spulen in Spoolman.")}</div>`}
        </div>
        <div class="dlg-error" hidden></div>
      </div>`;
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    dlg.querySelectorAll("[data-pick]").forEach((b) => b.addEventListener("click", async () => {
      const v = b.dataset.pick;
      const data = { slot: idx + 1, ...this._entryData() };
      if (v !== "auto") data.spool_id = Number(v);
      try {
        await this._hass.callService(DOMAIN, "set_spool", data, undefined, false);
        dlg.close();
      } catch (err) {
        const e = dlg.querySelector(".dlg-error");
        e.hidden = false;
        e.textContent = (err && err.message) || String(err);
      }
    }));
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
  }
};
