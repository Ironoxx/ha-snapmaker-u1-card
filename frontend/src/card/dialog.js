/** Print dialog: filament mapping like Snapmaker Orca, options, queue and photo viewer. */

import { onColor, suggestMapping } from "../color.js";
import { DOMAIN } from "../const.js";
import { esc, fixed, fmtEuro, fmtMin } from "../format.js";
import { tr } from "../i18n.js";

export const PrintDialogMixin = (Base) => class extends Base {
  _entryData() {
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const id = st && st.attributes && st.attributes.entry_id;
    return id ? { config_entry_id: id } : {};
  }

  _prefs() {
    const st = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    return (st && st.attributes && st.attributes.preferences) || {};
  }

  /** Result photo enlarged in a dialog; tap, Esc or the backdrop closes it. */
  _showPhoto(url) {
    let dlg = this.shadowRoot.querySelector("dialog.u1photo");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "u1photo";
      dlg.setAttribute("aria-label", tr("Ergebnisfoto"));
      dlg.addEventListener("click", () => dlg.close());
      this.shadowRoot.appendChild(dlg);
    }
    dlg.innerHTML = `<img src="${esc(url)}" alt="${tr("Ergebnisfoto")}" />
      <button class="icon photo-close" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>`;
    dlg.showModal();
  }

  async _renameFile() {
    const f = this._dlg && this._dlg.file;
    if (!f) return;
    const dest = prompt(tr("Neuer Name oder Pfad (Unterordner mit /):"), f.path);
    if (!dest || dest.trim() === f.path) return;
    if (await this._call("move_file", { source: f.path, dest: dest.trim() })) this._closeDialog();
  }

  /** Download the G-code through Home Assistant (signed URL, works remotely). */
  async _downloadFile() {
    const f = this._dlg && this._dlg.file;
    const entry = this._entryData().config_entry_id;
    if (!f || !entry) return;
    try {
      const path = `/api/${DOMAIN}/gcode/${entry}/${f.path.split("/").map(encodeURIComponent).join("/")}`;
      const url = await this._signed(path);
      const a = document.createElement("a");
      a.href = url;
      a.download = f.path.split("/").pop();
      a.rel = "noopener";
      this.shadowRoot.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      this._toast(tr("Download fehlgeschlagen"));
    }
  }

  async _deleteFile() {
    const f = this._dlg && this._dlg.file;
    if (!f || !confirm(tr("„{n}“ vom Drucker löschen?", { n: f.name || f.path }))) return;
    if (await this._call("delete_file", { path: f.path })) this._closeDialog();
  }

  _openPrint(path, preset = null) {
    const file = (this._d.files || []).find((f) => f.path === path) || (this._extraFiles || {})[path];
    if (!file) return;
    const used = (file.filaments || []).filter((f) => f.used);
    const slots = this._slots() || [];
    const prefs = { ...this._prefs(), ...((preset && preset.options) || {}) };
    const map = suggestMapping(used, slots);
    // Reprint: mapping of the old print, as far as the slots still match
    if (preset && preset.mapping) {
      Object.entries(preset.mapping).forEach(([k, v]) => {
        if (map[Number(k)] !== undefined && slots[Number(v)]) map[Number(k)] = Number(v);
      });
    }
    this._dlg = {
      file,
      used,
      map,
      pause: preset && Array.isArray(preset.pause_layers) ? preset.pause_layers.join(", ") : "",
      reprint: !!preset,
      prefs: {
        bed_leveling: !!prefs.bed_leveling,
        flow_calibration: !!prefs.flow_calibration,
        timelapse: !!prefs.timelapse,
      },
      confirmed: false,
      busy: false,
      error: null,
      slotsKey: JSON.stringify(slots),
      settings: undefined, // slicer settings: undefined = loading, null = none
    };
    this._renderDialog();
    this._loadSettings(this._dlg);
  }

  /** Slicer settings of the file (integration reads the G-code's config block once per version). */
  async _loadSettings(g) {
    const key = `${g.file.path}|${g.file.modified || ""}`;
    const cache = this._settingsCache || (this._settingsCache = new Map());
    if (cache.has(key) || !/\.gcode$/i.test(g.file.path)) {
      g.settings = cache.has(key) ? cache.get(key) : null;
      this._renderDialog();
      return;
    }
    let res = null;
    try {
      const r = await this._hass.callService(DOMAIN, "file_settings", { path: g.file.path, ...this._entryData() },
        undefined, false, true);
      res = (r && r.response && r.response.settings) || null;
      cache.set(key, res);
    } catch (e) { res = null; }
    if (this._dlg !== g) return;
    g.settings = res;
    this._renderDialog();
  }

  _settingsHtml(g) {
    const s = g.settings;
    if (s === undefined) return `<div class="t-label">${tr("Einstellungen werden gelesen …")}</div>`;
    if (!s) return `<div class="t-label">${tr("Die Datei enthält keine Slicer-Einstellungen.")}</div>`;
    const mm = (v) => (v == null ? null : `${fixed(v, 2)} mm`);
    const human = (v) => {
      const k = String(v || "").toLowerCase();
      const map = {
        "tree(auto)": tr("Baum (automatisch)"), "normal(auto)": tr("Normal (automatisch)"), "tree(manual)": tr("Baum (manuell)"),
        "normal(manual)": tr("Normal (manuell)"), auto_brim: tr("automatisch"), outer_only: tr("außen"), inner_only: tr("innen"),
        outer_and_inner: tr("außen und innen"), brim_ears: tr("Mausohren"), gyroid: "Gyroid", grid: tr("Gitter"),
        crosshatch: "Crosshatch", cubic: tr("Kubisch"), honeycomb: tr("Waben"), "3dhoneycomb": tr("3D-Waben"),
        adaptivecubic: tr("Adaptiv kubisch"), lightning: tr("Blitz"), line: tr("Linien"), rectilinear: tr("Geradlinig"),
        triangles: tr("Dreiecke"), aligned: tr("ausgerichtet"), nearest: tr("nächste"), back: tr("hinten"), random: tr("zufällig"),
        "top surfaces": tr("obere Flächen"), "topmost surface": tr("oberste Fläche"), "all solid layer": tr("alle festen Schichten"),
      };
      return map[k] || String(v || "").replace(/_/g, " ");
    };
    const rows = [];
    const row = (k, v) => { if (v != null && v !== "") rows.push(`<div class="set-row"><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`); };
    row(tr("Profil"), s.profile ? esc(s.profile) : null);
    row(tr("Schichthöhe"), s.layer_height != null
      ? esc(`${mm(s.layer_height)}${s.first_layer_height != null && s.first_layer_height !== s.layer_height ? ` · ${tr("erste {v}", { v: mm(s.first_layer_height) })}` : ""}`) : null);
    const shells = [s.walls != null ? tr("{n} Wände", { n: s.walls }) : null,
      s.top_layers != null ? tr("oben {n}", { n: s.top_layers }) : null,
      s.bottom_layers != null ? tr("unten {n}", { n: s.bottom_layers }) : null].filter(Boolean);
    row(tr("Wände"), shells.length ? esc(shells.join(" · ")) : null);
    row(tr("Infill"), s.infill != null ? esc(`${fixed(s.infill, 0)} %${s.infill_pattern ? ` · ${human(s.infill_pattern)}` : ""}`) : null);
    row(tr("Stützen"), s.support === null || s.support === undefined ? null
      : esc(s.support ? [tr("an"), s.support_type ? human(s.support_type) : "", s.support_build_plate_only ? tr("nur vom Bett") : ""].filter(Boolean).join(" · ") : tr("aus")));
    row(tr("Rand (Brim)"), s.brim ? esc([human(s.brim), s.brim_width ? mm(s.brim_width) : ""].filter(Boolean).join(" · ")) : null);
    row(tr("Reinigungsturm"), s.prime_tower === null || s.prime_tower === undefined ? null : esc(s.prime_tower ? tr("an") : tr("aus")));
    row(tr("Bügeln"), s.ironing ? esc(human(s.ironing)) : null);
    row(tr("Naht"), s.seam ? esc(human(s.seam)) : null);
    row(tr("Druckplatte"), s.plate ? esc(s.plate) : null);
    const speeds = [s.speed_outer_wall != null ? tr("Außenwand {v}", { v: `${fixed(s.speed_outer_wall, 0)} mm/s` }) : null,
      s.speed_infill != null ? tr("Infill {v}", { v: `${fixed(s.speed_infill, 0)} mm/s` }) : null].filter(Boolean);
    row(tr("Geschwindigkeit"), speeds.length ? esc(speeds.join(" · ")) : null);
    // Temperatures per used filament, in the order of the mapping list
    const temps = g.used.map((f, i) => {
      const n = (s.nozzle_temp || [])[i], b = (s.bed_temp || [])[i];
      const n1 = (s.nozzle_temp_first || [])[i], b1 = (s.bed_temp_first || [])[i];
      if (n == null && b == null) return "";
      const nz = n != null ? `${fixed(n, 0)}${n1 != null && n1 !== n ? ` (${fixed(n1, 0)})` : ""} °C` : "–";
      const bd = b != null ? `${fixed(b, 0)}${b1 != null && b1 !== b ? ` (${fixed(b1, 0)})` : ""} °C` : "–";
      return `<span class="set-temp"><span class="spool-dot" style="--fil:${esc(f.color || "var(--u1-outline)")}"></span>${esc(tr("Düse {n} · Bett {b}", { n: nz, b: bd }))}</span>`;
    }).filter(Boolean);
    if (temps.length) rows.push(`<div class="set-row"><span class="k">${esc(tr("Temperaturen"))}</span><span class="v set-temps">${temps.join("")}</span></div>`);
    if (!rows.length) return `<div class="t-label">${tr("Die Datei enthält keine Slicer-Einstellungen.")}</div>`;
    return `<div class="set-grid">${rows.join("")}</div>${temps.length ? `<div class="t-label">${tr("In Klammern: erste Schicht.")}</div>` : ""}`;
  }

  /** New slot data (e.g. spool changed) without losing the user's choices. */
  _refreshDialog() {
    const key = JSON.stringify(this._slots() || []);
    if (key !== this._dlg.slotsKey && !this._dlg.busy) {
      this._dlg.slotsKey = key;
      this._renderDialog();
    }
  }

  _closeDialog() {
    this._dlg = null;
    const el = this._dlgEl;
    if (el && el.open) el.close();
  }

  _dialogIssues() {
    const g = this._dlg;
    const slots = this._slots() || [];
    const anyLoaded = slots.some((s) => s.loaded);
    const issues = {};
    g.used.forEach((f) => {
      const slot = slots[g.map[f.index]];
      if (!slot) return;
      const nozzle = slot.nozzle && slot.nozzle.diameter;
      if (anyLoaded && !slot.loaded) issues[f.index] = { level: "error", text: tr("Slot ist leer") };
      // Sliced for another nozzle: extrusion widths and flow are wrong for this head
      else if (f.nozzle && nozzle && Math.abs(f.nozzle - nozzle) > 0.001)
        issues[f.index] = { level: "warn", text: tr("Düse passt nicht: Datei {a} mm, Kopf {b} mm", { a: f.nozzle, b: nozzle }) };
      else if (f.type && slot.type && f.type.toUpperCase() !== slot.type.toUpperCase())
        issues[f.index] = { level: "warn", text: tr("Material weicht ab: Datei {a}, Slot {b}", { a: f.type, b: slot.type }) };
    });
    // Spoolman: is the spool enough? Add up several filaments on one head.
    if (this._spoolman()) {
      const need = {};
      g.used.forEach((f) => { const k = g.map[f.index]; need[k] = (need[k] || 0) + (f.weight || 0); });
      g.used.forEach((f) => {
        if (issues[f.index]) return;
        const k = g.map[f.index];
        const sp = this._slotSpool(k);
        if (sp && sp.remaining_weight != null && need[k] > sp.remaining_weight)
          issues[f.index] = { level: "warn",
            text: tr("Spule #{id} hat noch {rest} g, gebraucht werden ca. {need} g", { id: sp.id, rest: Math.round(sp.remaining_weight), need: Math.round(need[k]) }) };
      });
    }
    return issues;
  }

  _renderDialog() {
    const g = this._dlg;
    if (!g) return;
    const host = this.shadowRoot.getElementById("u1dlg");
    if (!host) return;
    if (!this._dlgEl || !this._dlgEl.isConnected) {
      host.innerHTML = `<dialog class="u1dlg" aria-label="${tr("Druck starten")}"></dialog>`;
      this._dlgEl = host.querySelector("dialog");
      this._dlgEl.addEventListener("close", () => { this._dlg = null; });
      this._dlgEl.addEventListener("cancel", (e) => { if (this._dlg && this._dlg.busy) e.preventDefault(); });
    }
    const slots = this._slots() || [];
    const heads = this._d ? this._d.heads : [];
    const issues = this._dialogIssues();
    const p = this._d && this._d.power;
    const off = !!(p && p.available && !p.on && !(this._d && this._d.online));
    const pause = this._parsePause(g.pause, g.file.layers);
    const busyPrinter = !!(this._d && this._d.active);
    const blocked = Object.values(issues).some((i) => i.level === "error") || (off && !p.autoOn)
      || !!pause.error || busyPrinter;
    const qBlocked = Object.values(issues).some((i) => i.level === "error") || !!pause.error;
    const fst = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const stale = !!(fst && fst.attributes && fst.attributes.live === false);
    const f = g.file;

    const meta = [];
    if (f.time) meta.push(fmtMin(f.time / 60));
    if (f.weight) meta.push(`${Math.round(f.weight)} g`);
    if (f.layers) meta.push(tr("{n} Schichten", { n: f.layers }));
    // Cost before printing (integration: slicer weight x material price + time x average power x energy price)
    const cost = f.cost && f.cost.total != null ? f.cost : null;
    if (cost) meta.push(`≈ ${fmtEuro(cost.total)}`);
    const costParts = cost ? [
      cost.filament != null ? `${tr("Filament")} ${fmtEuro(cost.filament)}` : "",
      cost.energy != null ? `${tr("Strom")} ${fmtEuro(cost.energy)} (${fixed(cost.energy_kwh, 2)} kWh)` : "",
    ].filter(Boolean) : [];

    const rows = g.used.length ? g.used.map((fil) => {
      const issue = issues[fil.index];
      const buttons = slots.map((s) => {
        const on = g.map[fil.index] === s.index;
        const label = s.loaded ? [s.type, s.sub_type].filter(Boolean).join(" ") || "?" : tr("leer");
        return `<button type="button" class="slot-btn" data-map="${fil.index}" data-slot="${s.index}"
            aria-pressed="${on}" ${s.loaded ? "" : "data-empty=\"1\""}
            title="${esc((heads[s.index] || {}).name || tr("Slot {n}", { n: s.index + 1 }))} · ${esc(label)}">
            ${this._spoolSvg(s.loaded && s.color ? s.color : "var(--u1-outline)", false, s.loaded ? s.colors : null)}
            <span class="slot-no">${esc((heads[s.index] || {}).name || s.index + 1)}</span>
            <span class="slot-type">${esc(label)}</span>
            ${(() => { const sp = this._slotSpool(s.index); return sp && sp.remaining_weight != null ? `<span class="slot-rest">${Math.round(sp.remaining_weight)} g</span>` : ""; })()}
          </button>`;
      }).join("");
      return `
        <div class="map-row" data-issue="${issue ? issue.level : ""}">
          <div class="map-src">
            <span class="fil-badge" style="--fil:${esc(fil.color || "var(--u1-outline)")};--on-fil:${onColor(fil.color)}">${fil.index + 1}</span>
            <div class="map-src-text">
              <div class="map-type">${esc(fil.type || tr("Filament"))}</div>
              <div class="t-label">${[fil.weight ? `${fixed(fil.weight, 1)} g` : "", fil.name || ""].filter(Boolean).map(esc).join(" · ")}</div>
            </div>
          </div>
          <div class="map-slots">${buttons}</div>
          ${issue ? `<div class="map-issue"><ha-icon icon="${issue.level === "error" ? "mdi:alert-circle" : "mdi:alert"}"></ha-icon>${esc(issue.text)}</div>` : ""}
        </div>`;
    }).join("") : `<div class="t-label">${tr("Die Datei enthält keine Filamentangaben. Der Drucker nutzt seine Standardzuordnung (Filament 1 → Kopf 1 …).")}</div>`;

    const chk = (key, label) => `<label class="chk">
        <input type="checkbox" data-pref="${key}" ${g.prefs[key] ? "checked" : ""} ${g.busy ? "disabled" : ""} />
        <span>${label}</span></label>`;

    this._dlgEl.innerHTML = `
      <div class="dlg">
        <header class="dlg-head">
          <span class="dlg-thumb">${f.thumb ? `<img src="${esc(f.thumb)}" alt="" />` : `<ha-icon icon="mdi:file-document-outline"></ha-icon>`}</span>
          <div style="min-width:0">
            <div class="dlg-title">${esc(f.name)}</div>
            <div class="t-label">${meta.map(esc).join(" · ") || "&nbsp;"}</div>
            <div class="dlg-file-actions">
              <button type="button" class="icon ghost" data-dlg="rename" title="${tr("Umbenennen / verschieben")}" ${g.busy ? "disabled" : ""}><ha-icon icon="mdi:rename-outline"></ha-icon></button>
              <button type="button" class="icon ghost" data-dlg="download" title="${tr("G-Code herunterladen")}"><ha-icon icon="mdi:download"></ha-icon></button>
              <button type="button" class="icon ghost" data-dlg="delete" title="${tr("Datei löschen")}" ${g.busy ? "disabled" : ""}><ha-icon icon="mdi:delete-outline"></ha-icon></button>
            </div>
            ${costParts.length ? `<div class="t-label" data-cost>${tr("Geschätzt")}: ${costParts.map(esc).join(" · ")}</div>` : ""}
          </div>
        </header>
        ${off ? `<div class="dlg-note" data-tone="${p.autoOn ? "" : "error"}"><ha-icon icon="mdi:power-plug-off"></ha-icon>
          ${p.autoOn ? tr("Der Drucker ist aus. Er wird eingeschaltet und startet den Druck, sobald er bereit ist (ca. 1–2 min).")
            : tr("Der Drucker ist aus. Bitte erst einschalten.")}</div>` : ""}
        <details class="dlg-settings" data-settings ${g.settingsOpen ? "open" : ""}>
          <summary><ha-icon icon="mdi:tune-variant"></ha-icon>${tr("Slicer-Einstellungen")}${g.settings && g.settings.layer_height != null
            ? ` <span class="t-label">${esc([`${fixed(g.settings.layer_height, 2)} mm`, g.settings.infill != null ? `${fixed(g.settings.infill, 0)} %` : "",
              g.settings.support ? tr("Stützen") : ""].filter(Boolean).join(" · "))}</span>` : ""}</summary>
          ${this._settingsHtml(g)}
        </details>
        <div class="dlg-sec">${tr("Filamentzuordnung")}${stale ? ` <span class="t-label">${tr("(Stand vor dem Ausschalten)")}</span>` : ""}</div>
        <div class="map">${rows}</div>
        <div class="dlg-sec">${tr("Optionen")}</div>
        <div class="chks">
          ${chk("bed_leveling", tr("Bettnivellierung"))}
          ${chk("flow_calibration", tr("Flusskalibrierung"))}
          ${chk("timelapse", tr("Zeitraffer"))}
        </div>
        <label class="pause-in">
          <ha-icon icon="mdi:pause-circle-outline"></ha-icon>
          <span>${tr("Pause vor Schicht")}</span>
          <input type="text" inputmode="numeric" data-pause value="${esc(g.pause || "")}" placeholder="${tr("z. B. 12, 40")}"
            ${g.busy ? "disabled" : ""} />
        </label>
        ${pause.error ? `<div class="map-issue" style="color:var(--u1-error)"><ha-icon icon="mdi:alert-circle"></ha-icon>${esc(pause.error)}</div>`
          : pause.layers.length ? `<div class="t-label">${tr("Der Drucker hält vor Schicht {l} an (z. B. für Magnete). Fortsetzen am Display oder in der Karte.", { l: pause.layers.join(", ") })}</div>` : ""}
        ${busyPrinter ? `<div class="dlg-note"><ha-icon icon="mdi:tray-plus"></ha-icon>${tr("Der Drucker druckt gerade. Du kannst den Auftrag in die Warteschlange stellen.")}</div>` : ""}
        <label class="chk confirm">
          <input type="checkbox" data-confirm ${g.confirmed ? "checked" : ""} ${g.busy ? "disabled" : ""} />
          <span>${tr("Druckbett ist leer und der Drucker frei")}</span>
        </label>
        ${g.error ? `<div class="dlg-error"><ha-icon icon="mdi:alert-circle"></ha-icon>${esc(g.error)}</div>` : ""}
        <div class="dlg-actions">
          <button type="button" class="outline" data-dlg="cancel" ${g.busy ? "disabled" : ""}>${tr("Abbrechen")}</button>
          ${this._ents && this._ents.queue ? `<button type="button" class="tonal" data-dlg="queue" ${g.busy || qBlocked ? "disabled" : ""}>
            <ha-icon icon="mdi:tray-plus"></ha-icon>${tr("Warteschlange")}</button>` : ""}
          <button type="button" class="filled" data-dlg="print"
            ${!g.confirmed || g.busy || blocked ? "disabled" : ""}>
            <ha-icon icon="${g.busy ? "mdi:loading" : "mdi:printer-3d"}" class="${g.busy ? "spin" : ""}"></ha-icon>
            ${g.busy ? (off ? tr("Drucker startet …") : tr("Wird gestartet …")) : (off ? tr("Einschalten &amp; drucken") : tr("Drucken"))}</button>
        </div>
      </div>`;

    const el = this._dlgEl;
    el.querySelectorAll("[data-map]").forEach((b) => b.addEventListener("click", () => {
      if (g.busy) return;
      g.map[Number(b.dataset.map)] = Number(b.dataset.slot);
      this._renderDialog();
    }));
    el.querySelectorAll("[data-pref]").forEach((c) => c.addEventListener("change", () => {
      g.prefs[c.dataset.pref] = c.checked;
    }));
    const conf = el.querySelector("[data-confirm]");
    if (conf) conf.addEventListener("change", () => { g.confirmed = conf.checked; this._renderDialog(); });
    el.querySelector('[data-dlg="cancel"]').addEventListener("click", () => this._closeDialog());
    el.querySelector('[data-dlg="print"]').addEventListener("click", () => this._submitPrint());
    const ren = el.querySelector('[data-dlg="rename"]');
    if (ren) ren.addEventListener("click", () => this._renameFile());
    const dl = el.querySelector('[data-dlg="download"]');
    if (dl) dl.addEventListener("click", () => this._downloadFile());
    const del = el.querySelector('[data-dlg="delete"]');
    if (del) del.addEventListener("click", () => this._deleteFile());
    const qb = el.querySelector('[data-dlg="queue"]');
    if (qb) qb.addEventListener("click", () => this._submitPrint(true));
    const det = el.querySelector("[data-settings]");
    if (det) det.addEventListener("toggle", () => { g.settingsOpen = det.open; });
    const pin = el.querySelector("[data-pause]");
    if (pin) pin.addEventListener("change", () => { g.pause = pin.value; this._renderDialog(); });

    if (!el.open) {
      if (typeof el.showModal === "function") el.showModal();
      else el.setAttribute("open", "");
    }
  }

  /** "12, 40" -> [12, 40]; error text on invalid input. */
  _parsePause(text, layers) {
    const raw = String(text || "").split(/[\s,;]+/).filter(Boolean);
    const nums = raw.map((x) => Number(x));
    if (nums.some((n) => !Number.isInteger(n) || n < 1)) return { layers: [], error: tr("Schichten als ganze Zahlen ab 1 angeben, z. B. 12, 40.") };
    const max = Number(layers) || 0;
    const over = max ? nums.filter((n) => n > max) : [];
    if (over.length) return { layers: [], error: tr("Die Datei hat nur {n} Schichten.", { n: max }) };
    return { layers: [...new Set(nums)].sort((a, b) => a - b), error: null };
  }

  async _submitPrint(toQueue = false) {
    const g = this._dlg;
    if (!g || g.busy || (!g.confirmed && !toQueue)) return;
    g.busy = true;
    g.error = null;
    this._renderDialog();
    const mapping = {};
    g.used.forEach((f) => { mapping[String(f.index)] = g.map[f.index]; });
    const data = {
      filename: g.file.path,
      bed_leveling: g.prefs.bed_leveling,
      flow_calibration: g.prefs.flow_calibration,
      timelapse: g.prefs.timelapse,
      ...this._entryData(),
    };
    if (g.used.length) data.mapping = mapping;
    const pause = this._parsePause(g.pause, g.file.layers).layers;
    if (pause.length) data.pause_layers = pause;
    try {
      // notifyOnError=false: the error is shown in the dialog, no second toast.
      await this._hass.callService(DOMAIN, toQueue ? "queue_add" : "start_print", data, undefined, false);
      this._closeDialog();
      this._toast(toQueue ? tr("In die Warteschlange gestellt: {name}", { name: g.file.name })
        : tr("Druck gestartet: {name}", { name: g.file.name }));
    } catch (err) {
      if (this._dlg !== g) return;
      g.busy = false;
      g.error = (err && (err.message || err.error)) || String(err);
      this._renderDialog();
    }
  }
};
