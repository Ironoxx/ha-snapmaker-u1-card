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
    };
    this._renderDialog();
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
      if (anyLoaded && !slot.loaded) issues[f.index] = { level: "error", text: tr("Slot ist leer") };
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
              <button type="button" class="icon ghost" data-dlg="delete" title="${tr("Datei löschen")}" ${g.busy ? "disabled" : ""}><ha-icon icon="mdi:delete-outline"></ha-icon></button>
            </div>
            ${costParts.length ? `<div class="t-label" data-cost>${tr("Geschätzt")}: ${costParts.map(esc).join(" · ")}</div>` : ""}
          </div>
        </header>
        ${off ? `<div class="dlg-note" data-tone="${p.autoOn ? "" : "error"}"><ha-icon icon="mdi:power-plug-off"></ha-icon>
          ${p.autoOn ? tr("Der Drucker ist aus. Er wird eingeschaltet und startet den Druck, sobald er bereit ist (ca. 1–2 min).")
            : tr("Der Drucker ist aus. Bitte erst einschalten.")}</div>` : ""}
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
    const del = el.querySelector('[data-dlg="delete"]');
    if (del) del.addEventListener("click", () => this._deleteFile());
    const qb = el.querySelector('[data-dlg="queue"]');
    if (qb) qb.addEventListener("click", () => this._submitPrint(true));
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
