/**
 * Spoolman in the card (2.1): the stock of spools and a "new spool" form with
 * suggestions.
 *
 * Tab "Spoolman": every active spool with colour, vendor, material, location
 * and the remaining weight, filtered by material or text, totals on top. The
 * data is the spool list the integration already keeps (sensor filaments,
 * attribute spoolman.spools), so it costs no request. Picking a spool for a
 * head stays in the print heads panel.
 *
 * New spool: typing searches the own Spoolman filaments and Spoolman's
 * catalogue SpoolmanDB (websocket spoolman/suggest). A pick fills vendor,
 * material, name, colour and weights; saving runs the create_spool service
 * with the filament ID or the catalogue entry, so Spoolman gets the same
 * filament it would create itself.
 *
 * 2.4: tapping a spool opens its details with "edit" (2.4.0b3, spool and
 * filament, incl. the user's own Spoolman fields), "label", "archive" and (admins)
 * "delete"; empty spools offer archiving right in the list; the chip
 * "Archived" loads the archived spools on demand (websocket
 * spoolman/archived, nothing extra in the regular poll) so they can be
 * restored. The form takes the other Spoolman fields worth keeping
 * (temperatures, density, diameter, article and lot number, comment) in a
 * collapsed "more details" part. Labels: QR code (link to the spool in
 * Spoolman, own encoder in qr.js) with the main data, previewed in the dialog,
 * printed from a hidden iframe or saved as an HTML file.
 */

import { DOMAIN } from "../const.js";
import { clamp, esc, fmtMoney } from "../format.js";
import { tr } from "../i18n.js";
import { qrSvg } from "../qr.js";

const SUGGEST_DELAY_MS = 250;

/** First temperature of an RFID tag value (list or number) for a form field, "" if none. */
const rfidTemp = (v) => {
  const t = Array.isArray(v) ? v[0] : v;
  return Number.isFinite(Number(t)) && Number(t) > 0 ? Math.round(Number(t)) : "";
};

/**
 * 2.4.0b3: the user's own Spoolman fields (Settings → Extra fields in Spoolman) as form
 * inputs. ``f`` = {key, name, type, unit, default, choices, multi} from the integration
 * (spoolman/fields); ``prefix`` keeps spool and filament fields apart in one form.
 */
const extraName = (prefix, f, part = "") => `${prefix}x_${f.key}${part}`;
export const extraInput = (f, value, prefix) => {
  const v = value === undefined ? f.default : value;
  const label = `${esc(f.name)}${f.unit ? ` (${esc(f.unit)})` : ""}`;
  const num = (name, val, step) => `<input name="${name}" type="number" step="${step}" value="${val === null || val === undefined ? "" : esc(val)}" />`;
  switch (f.type) {
    case "boolean":
      return `<label class="check"><input type="checkbox" name="${extraName(prefix, f)}" ${v === true ? "checked" : ""} />${label}</label>`;
    case "integer": case "float":
      return `<label>${label}${num(extraName(prefix, f), v, f.type === "integer" ? "1" : "any")}</label>`;
    case "integer_range": case "float_range": {
      const [a, b] = Array.isArray(v) ? v : [null, null];
      const step = f.type === "integer_range" ? "1" : "any";
      return `<label>${label}<span class="range-in">${num(extraName(prefix, f, "__0"), a, step)}–${num(extraName(prefix, f, "__1"), b, step)}</span></label>`;
    }
    case "datetime":
      return `<label>${label}<input name="${extraName(prefix, f)}" type="datetime-local" value="${v ? esc(String(v).slice(0, 16)) : ""}" /></label>`;
    case "choice": {
      const sel = new Set(Array.isArray(v) ? v : v ? [v] : []);
      return `<label>${label}<select name="${extraName(prefix, f)}" ${f.multi ? "multiple" : ""}>
          ${f.multi ? "" : `<option value=""></option>`}
          ${(f.choices || []).map((c) => `<option value="${esc(c)}" ${sel.has(c) ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>`;
    }
    default:
      return `<label>${label}<input name="${extraName(prefix, f)}" value="${v === null || v === undefined ? "" : esc(v)}" /></label>`;
  }
};

/** Value of one own field from the form; null = empty (the integration then drops it). */
export const extraValue = (form, f, prefix) => {
  const el = (part = "") => form.querySelector(`[name="${extraName(prefix, f, part)}"]`);
  const n = (x) => (x && String(x.value).trim() !== "" ? Number(x.value) : null);
  switch (f.type) {
    case "boolean": return el().checked;
    case "integer": case "float": return n(el());
    case "integer_range": case "float_range": {
      const a = n(el("__0")), b = n(el("__1"));
      return a === null && b === null ? null : [a, b];
    }
    case "datetime": return el().value ? new Date(el().value).toISOString() : null;
    case "choice":
      if (f.multi) { const vals = [...el().selectedOptions].map((o) => o.value); return vals.length ? vals : null; }
      return el().value || null;
    default: return String(el().value || "").trim() || null;
  }
};

export const SpoolStockMixin = (Base) => class extends Base {
  /** The dialog element shared by picker, stock and form. */
  _spoolDialog() {
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1spool");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1spool" aria-label="${tr("Spoolman")}"></dialog>`);
      dlg = host.querySelector("dialog.u1spool");
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    return dlg;
  }

  _showDialog(dlg) {
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
  }

  /** Spool in a head: head index by spool ID. */
  _spoolHeads() {
    const sm = this._spoolman();
    const out = new Map();
    Object.entries((sm && sm.slots) || {}).forEach(([k, v]) => { if (v) out.set(v.id, Number(k)); });
    return out;
  }

  /** One spool row of the stock list (active or archived). */
  _stockRow(s, heads, low, archived = false) {
    const rest = s.remaining_weight;
    const pct = rest != null && s.initial_weight ? clamp((rest / s.initial_weight) * 100, 0, 100) : null;
    const head = heads.get(s.id);
    const colors = (s.colors && s.colors.length > 1)
      ? `linear-gradient(135deg, ${s.colors.map(esc).join(", ")})` : esc(s.color || "var(--u1-outline)");
    const text = [s.name, s.vendor, s.material, s.location, `#${s.id}`].join(" ").toLowerCase();
    // empty and in no head: offer to put it away right here (2.4)
    const empty = !archived && rest != null && rest <= 0 && head == null;
    return `<div class="stock-row" data-stock="${s.id}" ${archived ? "data-archived" : ""} role="button" tabindex="0"
        data-low="${rest != null && rest < low ? 1 : 0}"
        data-mat="${esc((s.material || "").toUpperCase())}" data-text="${esc(text)}"
        data-rest="${rest || 0}" data-value="${s.price_kg && rest ? (s.price_kg * rest / 1000).toFixed(2) : 0}">
        <span class="spool-dot" style="--fil:${colors}"></span>
        <span class="spool-opt-text"><span>#${s.id} ${esc(s.name)}</span>
          <span class="t-label">${[s.vendor, s.material, s.location,
            head != null ? tr("steckt in {head}", { head: (this._d.heads[head] || {}).name || `E${head}` }) : "",
            archived ? tr("archiviert") : ""]
            .filter(Boolean).map(esc).join(" · ")}</span>
          ${pct != null ? `<span class="spool-track"><i style="width:${pct}%"></i></span>` : ""}</span>
        ${empty ? `<button type="button" class="chip sm" data-emptyarch="${s.id}" title="${tr("Leere Spule archivieren")}">
          <ha-icon icon="mdi:archive-arrow-down-outline"></ha-icon><span>${tr("leer · archivieren")}</span></button>` : ""}
        <span class="spool-rest">${rest != null ? `${Math.round(rest)} g` : "–"}</span>
      </div>`;
  }

  /** Tab "Spoolman": every active spool; filter and search work in place (no rebuild, focus stays). */
  _sectionSpools() {
    const sm = this._spoolman();
    if (!sm) return "";
    const sorted = (list) => list.slice().sort((a, b) => (a.material || "").localeCompare(b.material || "")
      || (a.vendor || "").localeCompare(b.vendor || "") || (a.name || "").localeCompare(b.name || ""));
    const all = sorted(sm.spools || []);
    const heads = this._spoolHeads();
    const materials = [...new Set(all.map((s) => (s.material || "").toUpperCase()).filter(Boolean))].sort();
    const f = this._stockFilter || (this._stockFilter = { material: "", text: "", archived: false });
    const low = sm.low || 0;
    const arch = f.archived ? this._archSpools : null; // loaded on demand, kept across rebuilds
    return `
      <section class="panel span2 span3 stock" data-spools>
        <div class="panel-head">
          <ha-icon icon="mdi:package-variant-closed"></ha-icon>
          <span class="panel-title">${tr("Spoolman-Bestand")}</span>
          <button type="button" class="chip sm" data-stocklabels style="margin-left:auto" title="${tr("Etiketten für die angezeigten Spulen drucken")}">
            <ha-icon icon="mdi:qrcode"></ha-icon><span>${tr("Etiketten")}</span></button>
          <button type="button" class="chip sm" data-stocknew ${sm.online ? "" : "disabled"}>
            <ha-icon icon="mdi:plus"></ha-icon><span>${tr("Neue Spule")}</span></button>
        </div>
        ${sm.online ? "" : `<div class="dlg-note" data-tone="error"><ha-icon icon="mdi:database-off"></ha-icon>${tr("Spoolman nicht erreichbar")}${sm.error ? `: ${esc(sm.error)}` : ""}</div>`}
        <div class="t-label" data-stocksum></div>
        <input class="stock-search" type="search" data-stocktext value="${esc(f.text)}" placeholder="${tr("Suchen: Name, Hersteller, Ort, #ID")}" />
        <div class="chips stock-chips">
          <button type="button" class="chip sm" data-stockmat="" aria-pressed="${!f.material}">${tr("Alle")}</button>
          ${materials.map((m) => `<button type="button" class="chip sm" data-stockmat="${esc(m)}" aria-pressed="${f.material === m}">${esc(m)}</button>`).join("")}
          <button type="button" class="chip sm" data-stockarch aria-pressed="${!!f.archived}" ${sm.online ? "" : "disabled"}>
            <ha-icon icon="mdi:archive-outline"></ha-icon><span>${tr("Archiviert")}</span></button>
        </div>
        <div class="stock-list" data-activelist ${f.archived ? "hidden" : ""}>${all.map((s) => this._stockRow(s, heads, low)).join("")}</div>
        <div class="stock-list" data-archlist ${f.archived ? "" : "hidden"}>${arch ? sorted(arch).map((s) => this._stockRow(s, heads, low, true)).join("") : ""}</div>
        <div class="t-label" data-stockempty hidden>${f.archived ? tr("Keine archivierten Spulen.")
          : all.length ? tr("Keine Spule passt zum Filter.") : tr("Keine aktiven Spulen in Spoolman.")}</div>
      </section>`;
  }

  _wireSpools(r) {
    const sec = r.querySelector("[data-spools]");
    if (!sec) return;
    sec.querySelectorAll("[data-stockmat]").forEach((b) => b.addEventListener("click", () => {
      this._stockFilter.material = b.dataset.stockmat;
      this._filterSpools(sec);
    }));
    const txt = sec.querySelector("[data-stocktext]");
    txt.addEventListener("input", () => { this._stockFilter.text = txt.value; this._filterSpools(sec); });
    sec.querySelector("[data-stocknew]").addEventListener("click", () => {
      const dlg = this._spoolDialog();
      this._newSpoolForm(dlg, null);
      this._showDialog(dlg);
    });
    sec.querySelector("[data-stockarch]").addEventListener("click", () => this._toggleArchived(sec));
    sec.querySelector("[data-stocklabels]").addEventListener("click", () => {
      const list = sec.querySelector(this._stockFilter.archived ? "[data-archlist]" : "[data-activelist]");
      const ids = [...list.querySelectorAll("[data-stock]")].filter((el) => !el.hidden).map((el) => Number(el.dataset.stock));
      this._printLabels(ids.map((id) => this._stockSpool(id)).filter(Boolean));
    });
    this._wireStockRows(sec);
    this._filterSpools(sec);
  }

  /** Row tap = details; the inline "empty" chip archives straight away. */
  _wireStockRows(sec) {
    sec.querySelectorAll("[data-stock]:not([data-wired])").forEach((el) => {
      el.dataset.wired = "1";
      const open = () => this._spoolDetail(Number(el.dataset.stock), el.hasAttribute("data-archived"));
      el.addEventListener("click", (e) => { if (!e.target.closest("[data-emptyarch]")) open(); });
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
    sec.querySelectorAll("[data-emptyarch]:not([data-wired])").forEach((b) => {
      b.dataset.wired = "1";
      b.addEventListener("click", (e) => { e.stopPropagation(); this._spoolArchive(Number(b.dataset.emptyarch), true); });
    });
  }

  /** Chip "Archived": fetch the archived spools once per switch-on (not polled), then filter in place. */
  async _toggleArchived(sec) {
    const f = this._stockFilter;
    f.archived = !f.archived;
    sec.querySelector("[data-activelist]").hidden = f.archived;
    const box = sec.querySelector("[data-archlist]");
    box.hidden = !f.archived;
    if (f.archived) {
      box.innerHTML = `<div class="t-label">${tr("Lade archivierte Spulen …")}</div>`;
      const res = await this._spoolCatalogWS("archived", {});
      this._archSpools = (res && res.spools) || [];
      if (!res) this._toast(tr("Archivierte Spulen konnten nicht geladen werden."));
      const sm = this._spoolman() || {};
      box.innerHTML = this._archSpools.map((s) => this._stockRow(s, this._spoolHeads(), sm.low || 0, true)).join("");
      this._wireStockRows(sec);
    }
    this._filterSpools(sec);
  }

  _filterSpools(sec) {
    const f = this._stockFilter;
    const words = f.text.toLowerCase().split(/\s+/).filter(Boolean);
    let n = 0, grams = 0, value = 0;
    // only the list on show counts (active or archived)
    const list = sec.querySelector(f.archived ? "[data-archlist]" : "[data-activelist]");
    list.querySelectorAll("[data-stock]").forEach((el) => {
      const show = (!f.material || el.dataset.mat === f.material) && words.every((w) => el.dataset.text.includes(w));
      el.hidden = !show;
      if (show) { n++; grams += Number(el.dataset.rest); value += Number(el.dataset.value); }
    });
    sec.querySelectorAll("[data-stockmat]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.stockmat === f.material)));
    sec.querySelector("[data-stockarch]").setAttribute("aria-pressed", String(!!f.archived));
    sec.querySelector("[data-stocksum]").textContent =
      tr("{n} Spulen · {kg} kg", { n, kg: (grams / 1000).toFixed(1) }) + (value > 0 ? ` · ${fmtMoney(value)}` : "");
    const empty = sec.querySelector("[data-stockempty]");
    empty.hidden = n > 0;
    empty.textContent = f.archived ? tr("Keine archivierten Spulen.")
      : ((this._spoolman() || {}).spools || []).length ? tr("Keine Spule passt zum Filter.") : tr("Keine aktiven Spulen in Spoolman.");
  }

  /** Spool by ID from the active list or the archived ones loaded last. */
  _stockSpool(id) {
    const sm = this._spoolman() || {};
    return (sm.spools || []).find((s) => s.id === id) || (this._archSpools || []).find((s) => s.id === id) || null;
  }

  /** Details of one spool with its actions (label, archive/restore, delete for admins). */
  _spoolDetail(id, archived) {
    const s = this._stockSpool(id);
    if (!s) return;
    const dlg = this._spoolDialog();
    const head = this._spoolHeads().get(id);
    const headName = head != null ? ((this._d.heads[head] || {}).name || `E${head}`) : null;
    const admin = !!(this._hass && this._hass.user && this._hass.user.is_admin);
    const rows = [
      [tr("Hersteller"), s.vendor], [tr("Material"), s.material],
      [tr("Rest"), s.remaining_weight != null ? `${Math.round(s.remaining_weight)} g${s.initial_weight ? ` / ${Math.round(s.initial_weight)} g` : ""}` : null],
      [tr("Leerspule (g)"), s.spool_weight != null ? `${Math.round(s.spool_weight)} g` : null],
      [tr("Düse"), s.extruder_temp ? `${s.extruder_temp} °C` : null], [tr("Bett"), s.bed_temp ? `${s.bed_temp} °C` : null],
      [tr("Ort"), s.location], [tr("Charge"), s.lot_nr],
      [tr("Preis"), s.price_kg ? `${fmtMoney(s.price_kg)}/kg` : null],
      [tr("Zuletzt benutzt"), s.last_used ? new Date(s.last_used).toLocaleDateString() : null],
      [tr("Kopf"), headName],
    ].filter(([, v]) => v != null && v !== "");
    const colors = (s.colors && s.colors.length > 1)
      ? `linear-gradient(135deg, ${s.colors.map(esc).join(", ")})` : esc(s.color || "var(--u1-outline)");
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><span class="spool-dot" style="--fil:${colors}"></span><div style="min-width:0">
          <div class="dlg-title">#${s.id} ${esc(s.name)}</div>
          <div class="t-label">${archived ? tr("archiviert") : tr("in Spoolman")}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <div class="rows">${rows.map(([k, v]) => `<div class="row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`).join("")}</div>
        ${headName ? `<div class="dlg-note"><ha-icon icon="mdi:information-outline"></ha-icon>${tr("Steckt in {head} – zum Archivieren oder Löschen erst die Zuordnung im Druckkopf lösen.", { head: headName })}</div>` : ""}
        <div class="dlg-error" hidden></div>
        <div class="dlg-actions" data-spoolacts>
          <button type="button" class="outline" data-edit><ha-icon icon="mdi:pencil-outline"></ha-icon>${tr("Bearbeiten")}</button>
          <button type="button" class="outline" data-label><ha-icon icon="mdi:qrcode"></ha-icon>${tr("Etikett")}</button>
          ${archived
            ? `<button type="button" class="outline" data-restore><ha-icon icon="mdi:archive-arrow-up-outline"></ha-icon>${tr("Wiederherstellen")}</button>`
            : `<button type="button" class="outline" data-archive ${headName ? "disabled" : ""}><ha-icon icon="mdi:archive-arrow-down-outline"></ha-icon>${tr("Archivieren")}</button>`}
          ${admin ? `<button type="button" class="outline danger" data-delete ${headName ? "disabled" : ""}><ha-icon icon="mdi:delete-outline"></ha-icon>${tr("Löschen")}</button>` : ""}
        </div>
      </div>`;
    const q = (sel) => dlg.querySelector(sel);
    q("[data-close]").addEventListener("click", () => dlg.close());
    q("[data-label]").addEventListener("click", () => this._printLabels([s]));
    q("[data-edit]").addEventListener("click", () => this._editSpoolForm(id, archived));
    if (q("[data-archive]")) q("[data-archive]").addEventListener("click", () => this._spoolArchive(id, true, dlg));
    if (q("[data-restore]")) q("[data-restore]").addEventListener("click", () => this._spoolArchive(id, false, dlg));
    if (q("[data-delete]")) q("[data-delete]").addEventListener("click", () => {
      // second step in the same dialog: deleting cannot be undone
      q("[data-spoolacts]").innerHTML = `<div class="dlg-note" data-tone="error" style="flex-basis:100%"><ha-icon icon="mdi:alert-outline"></ha-icon>
          ${tr("Spule #{id} endgültig löschen? Spoolman löscht auch ihren Verbrauch. Archivieren lässt sich dagegen rückgängig machen.", { id })}</div>
        <button type="button" class="outline" data-cancel>${tr("Abbrechen")}</button>
        <button type="button" class="danger strong" data-confirm><ha-icon icon="mdi:delete-forever-outline"></ha-icon>${tr("Endgültig löschen")}</button>`;
      q("[data-cancel]").addEventListener("click", () => this._spoolDetail(id, archived));
      q("[data-confirm]").addEventListener("click", () => this._spoolDelete(id, dlg));
    });
    this._showDialog(dlg);
  }

  /** Own Spoolman fields {spool, filament}; asked once per page, empty lists if Spoolman has none. */
  async _smFieldsLoad() {
    if (!this._smFields) this._smFields = this._spoolCatalogWS("fields", {}).then((r) => r || { spool: [], filament: [] });
    const r = await this._smFields;
    return { spool: r.spool || [], filament: r.filament || [] };
  }

  /**
   * 2.4.0b3: edit a spool (and its filament). Loads the spool once when it opens
   * (websocket spoolman/spool); saving sends only what changed to update_spool.
   * Filament values change every spool of that filament – the form says how many.
   */
  async _editSpoolForm(id, archived = false) {
    const dlg = this._spoolDialog();
    dlg.innerHTML = `<div class="dlg"><div class="t-label">${tr("Lade Spule …")}</div></div>`;
    this._showDialog(dlg);
    const res = await this._spoolCatalogWS("spool", { spool_id: id });
    if (!res || !res.spool) {
      dlg.innerHTML = `<div class="dlg"><div class="dlg-error">${tr("Spule konnte nicht geladen werden.")}</div>
        <div class="dlg-actions"><button type="button" class="outline" data-close>${tr("Schließen")}</button></div></div>`;
      dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
      return;
    }
    const sp = res.spool, fil = sp.filament || {};
    const fl = { spool: (res.fields && res.fields.spool) || [], filament: (res.fields && res.fields.filament) || [] };
    const val = (v) => (v === null || v === undefined ? "" : esc(v));
    const numIn = (name, v, min, max, step) => `<input name="${name}" type="number" min="${min}" max="${max}" step="${step}" value="${val(v)}" />`;
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${tr("Spule #{id} bearbeiten", { id })}</div>
          <div class="t-label">${esc([fil.vendor, fil.name].filter(Boolean).join(" · "))}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <form class="head-form" data-editform autocomplete="off">
          <div class="wide dlg-sec">${tr("Spule")}</div>
          <label>${tr("Restgewicht (g)")}${numIn("remaining", sp.remaining_weight, 0, 10000, "any")}</label>
          <label>${tr("Nettogewicht (g)")}${numIn("initial_weight", sp.initial_weight, 0, 10000, "1")}</label>
          <label>${tr("Leerspule (g)")}${numIn("spool_weight", sp.spool_weight, 0, 2000, "1")}</label>
          <label>${tr("Preis")}${numIn("price", sp.price, 0, 10000, "0.01")}</label>
          <label>${tr("Ort")}<input name="location" maxlength="64" value="${val(sp.location)}" /></label>
          <label>${tr("Charge")}<input name="lot_nr" maxlength="64" value="${val(sp.lot_nr)}" /></label>
          <label class="wide">${tr("Kommentar")}<textarea name="comment" maxlength="1024" rows="2">${val(sp.comment)}</textarea></label>
          ${fl.spool.map((x) => extraInput(x, sp.extra[x.key] ?? null, "s")).join("")}
          <details class="wide more-fields" data-filpart>
            <summary>${tr("Filament")}</summary>
            <div class="t-label">${res.filament_spools > 1 ? tr("Gilt für alle {n} Spulen dieses Filaments.", { n: res.filament_spools }) : tr("Gilt für das Filament dieser Spule.")}</div>
            <div class="head-form">
              <label>${tr("Name")}<input name="f_name" maxlength="64" value="${val(fil.name)}" /></label>
              <label>${tr("Hersteller")}<input name="f_vendor" maxlength="64" value="${val(fil.vendor)}" /></label>
              <label>${tr("Material")}<input name="f_material" maxlength="32" value="${val(fil.material)}" /></label>
              ${fil.multi ? "" : `<label>${tr("Farbe")}<input name="f_color" type="color" value="${val(fil.color || "#ffffff")}" /></label>`}
              <label>${tr("Dichte (g/cm³)")}${numIn("f_density", fil.density, 0.5, 3, "0.01")}</label>
              <label>${tr("Durchmesser (mm)")}${numIn("f_diameter", fil.diameter, 1, 3, "0.01")}</label>
              <label>${tr("Düsentemperatur (°C)")}${numIn("f_extruder_temp", fil.extruder_temp, 150, 350, "1")}</label>
              <label>${tr("Betttemperatur (°C)")}${numIn("f_bed_temp", fil.bed_temp, 0, 150, "1")}</label>
              <label>${tr("Artikelnummer")}<input name="f_article_number" maxlength="64" value="${val(fil.article_number)}" /></label>
              ${fl.filament.map((x) => extraInput(x, fil.extra[x.key] ?? null, "f")).join("")}
            </div>
          </details>
          <div class="dlg-error" hidden></div>
          <div class="dlg-actions">
            <button type="button" class="outline" data-back>${tr("Zurück")}</button>
            <button type="submit" class="filled"><ha-icon icon="mdi:content-save-outline"></ha-icon>${tr("Speichern")}</button>
          </div>
        </form>
      </div>`;
    const form = dlg.querySelector("[data-editform]");
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    dlg.querySelector("[data-back]").addEventListener("click", () => this._spoolDetail(id, archived));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const g = (n) => form.querySelector(`[name="${n}"]`);
      const txt = (n) => String(g(n) ? g(n).value : "").trim();
      const num = (n) => (txt(n) === "" ? null : Number(txt(n)));
      const same = (a, b) => (a === null || a === undefined || a === "" ? null : a) === (b === null || b === undefined || b === "" ? null : b);
      const data = { spool_id: id, ...this._entryData() };
      // spool: only what changed (empty clears)
      [["remaining", sp.remaining_weight], ["initial_weight", sp.initial_weight], ["spool_weight", sp.spool_weight], ["price", sp.price]]
        .forEach(([k, old]) => { if (!same(num(k), old === null || old === undefined ? null : Number(old))) data[k] = num(k); });
      [["location", sp.location], ["lot_nr", sp.lot_nr], ["comment", sp.comment]]
        .forEach(([k, old]) => { if (!same(txt(k), old)) data[k] = txt(k) || null; });
      const changedExtra = (list, prefix, current) => {
        const out = {};
        list.forEach((x) => {
          const v = extraValue(form, x, prefix);
          // an unset yes/no field reads as "no" in the form: not a change
          const cur = current[x.key] ?? (x.type === "boolean" ? false : null);
          if (JSON.stringify(v) !== JSON.stringify(cur)) out[x.key] = v;
        });
        return out;
      };
      const sx = changedExtra(fl.spool, "s", sp.extra);
      if (Object.keys(sx).length) data.extra = sx;
      // filament
      [["name", fil.name], ["vendor", fil.vendor], ["material", fil.material]]
        .forEach(([k, old]) => { if (txt(`f_${k}`) && !same(txt(`f_${k}`), old)) data[`filament_${k}`] = txt(`f_${k}`); });
      if (!same(txt("f_article_number"), fil.article_number)) data.filament_article_number = txt("f_article_number") || null;
      if (g("f_color") && !same(g("f_color").value.toLowerCase(), (fil.color || "").toLowerCase())) data.filament_color = g("f_color").value;
      [["density", fil.density], ["diameter", fil.diameter]]
        .forEach(([k, old]) => { const v = num(`f_${k}`); if (v !== null && !same(v, old)) data[`filament_${k}`] = v; });
      [["extruder_temp", fil.extruder_temp], ["bed_temp", fil.bed_temp]]
        .forEach(([k, old]) => { const v = num(`f_${k}`); if (!same(v, old)) data[`filament_${k}`] = v; });
      const fx = changedExtra(fl.filament, "f", fil.extra);
      if (Object.keys(fx).length) data.filament_extra = fx;
      if (Object.keys(data).filter((k) => k !== "spool_id" && k !== "config_entry_id").length === 0) {
        this._spoolDetail(id, archived);
        return;
      }
      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      try {
        await this._hass.callService(DOMAIN, "update_spool", data, undefined, false, true);
        this._toast(tr("Spule #{id} gespeichert", { id }));
        dlg.close();
      } catch (err) {
        btn.disabled = false;
        const el = form.querySelector(".dlg-error");
        el.hidden = false;
        el.textContent = (err && err.message) || String(err);
      }
    });
  }

  /** Service spool_archive; restoring also drops the spool from the cached archived list. */
  async _spoolArchive(id, archived, dlg = null) {
    try {
      await this._hass.callService(DOMAIN, "spool_archive", { spool_id: id, archived, ...this._entryData() });
      if (!archived && this._archSpools) this._archSpools = this._archSpools.filter((s) => s.id !== id);
      if (archived && this._archSpools) this._archSpools = null; // reloaded next time the chip is switched on
      this._toast(archived ? tr("Spule #{id} archiviert", { id }) : tr("Spule #{id} wiederhergestellt", { id }));
      if (dlg) dlg.close();
      this._refreshArchList();
    } catch (err) {
      this._spoolError(dlg, err);
    }
  }

  /** Service spool_delete (admins only, the integration checks again). */
  async _spoolDelete(id, dlg) {
    try {
      await this._hass.callService(DOMAIN, "spool_delete", { spool_id: id, ...this._entryData() });
      if (this._archSpools) this._archSpools = this._archSpools.filter((s) => s.id !== id);
      this._toast(tr("Spule #{id} gelöscht", { id }));
      dlg.close();
      this._refreshArchList();
    } catch (err) {
      this._spoolError(dlg, err);
    }
  }

  /** The archived list is not part of the render signature: redraw it in place after a change. */
  _refreshArchList() {
    const sec = this.shadowRoot && this.shadowRoot.querySelector("[data-spools]");
    if (!sec || !this._stockFilter || !this._stockFilter.archived) return;
    const box = sec.querySelector("[data-archlist]");
    box.querySelectorAll("[data-stock]").forEach((el) => {
      if (!(this._archSpools || []).some((s) => s.id === Number(el.dataset.stock))) el.remove();
    });
    if (this._archSpools === null) box.innerHTML = "";
    this._filterSpools(sec);
  }

  _spoolError(dlg, err) {
    const msg = (err && err.message) || String(err);
    const el = dlg && dlg.querySelector(".dlg-error");
    if (el) { el.hidden = false; el.textContent = msg; } else this._toast(msg);
  }

  /**
   * Labels for the given spools: QR code to the spool in Spoolman plus name,
   * vendor, material, colour, temperatures and ID, 62 mm wide (fits label
   * printers and A4 sheets alike).
   *
   * 2.4.0b2 fix: shown as a preview in the card's own dialog and printed from a
   * hidden iframe – no new window. The Home Assistant app hands window.open()
   * to the phone's browser, which then showed whatever page it had open last
   * instead of the labels. "Save file" is the way out where printing from the
   * app is not available (Android WebView ignores print()).
   */
  _printLabels(spools) {
    if (!spools.length) { this._toast(tr("Keine Spule zum Drucken.")); return; }
    const sm = this._spoolman() || {};
    const base = String(sm.url || "").replace(/\/+$/, "");
    const label = (s) => {
      const link = base ? `${base}/spool/show/${s.id}` : `web+spoolman:s-${s.id}`;
      const temps = [s.extruder_temp ? `${tr("Düse")} ${s.extruder_temp} °C` : "", s.bed_temp ? `${tr("Bett")} ${s.bed_temp} °C` : ""].filter(Boolean).join(" · ");
      const colors = (s.colors && s.colors.length > 1) ? `linear-gradient(135deg, ${s.colors.map(esc).join(", ")})` : esc(s.color || "#ccc");
      return `<div class="lbl"><div class="qr">${qrSvg(link, { quiet: 2 })}</div><div class="txt">
          <div class="id">#${s.id}</div><div class="nm">${esc(s.name)}</div>
          <div>${[s.vendor, s.material].filter(Boolean).map(esc).join(" · ")}</div>
          ${temps ? `<div>${esc(temps)}</div>` : ""}
          <div class="sw" style="background:${colors}"></div></div></div>`;
    };
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>${esc(tr("Spulen-Etiketten"))}</title><style>
      body { font: 11px/1.25 system-ui, sans-serif; margin: 8mm; color: #000; background: #fff; }
      .sheet { display: flex; flex-wrap: wrap; gap: 4mm; }
      .lbl { width: 62mm; height: 29mm; box-sizing: border-box; border: 0.2mm dashed #999; padding: 2mm;
        display: flex; gap: 2mm; align-items: center; break-inside: avoid; page-break-inside: avoid; }
      .qr { width: 25mm; height: 25mm; flex: none; } .qr svg { width: 100%; height: 100%; }
      .txt { min-width: 0; } .id { font-weight: 700; font-size: 13px; }
      .nm { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .sw { width: 14mm; height: 3mm; border: 0.2mm solid #000; margin-top: 1mm; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      @media print { body { margin: 0; } .lbl { border-color: transparent; } }
      </style></head><body><div class="sheet">${spools.map(label).join("")}</div></body></html>`;
    this._labelDialog(spools, html);
  }

  /** Label preview in the spool dialog with "Print" (hidden iframe) and "Save file". */
  _labelDialog(spools, html) {
    const dlg = this._spoolDialog();
    const single = spools.length === 1 ? spools[0] : null;
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><ha-icon icon="mdi:qrcode"></ha-icon><div style="min-width:0">
          <div class="dlg-title">${esc(single ? tr("Etikett") : tr("Spulen-Etiketten"))}</div>
          <div class="t-label">${esc(single ? `#${single.id} ${single.name}` : tr("{n} Spulen", { n: spools.length }))}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <iframe class="label-preview" data-labelframe title="${esc(tr("Spulen-Etiketten"))}"></iframe>
        <div class="t-label">${tr("Druckt die Etiketten über den Druckdialog des Browsers. In der Home-Assistant-App ggf. als Datei speichern und von dort drucken.")}</div>
        <div class="dlg-actions">
          ${single ? `<button type="button" class="outline" data-back>${tr("Zurück")}</button>` : ""}
          <button type="button" class="outline" data-labelsave><ha-icon icon="mdi:download"></ha-icon>${tr("Als Datei speichern")}</button>
          <button type="button" class="filled" data-labelprint><ha-icon icon="mdi:printer"></ha-icon>${tr("Drucken")}</button>
        </div>
      </div>`;
    const frame = dlg.querySelector("[data-labelframe]");
    frame.srcdoc = html; // same origin, our own escaped markup – no scripts inside
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    if (single) dlg.querySelector("[data-back]").addEventListener("click", () => this._spoolDetail(single.id, !!single.archived));
    dlg.querySelector("[data-labelprint]").addEventListener("click", () => {
      try {
        frame.contentWindow.focus();
        frame.contentWindow.print();
      } catch (e) {
        this._toast(tr("Drucken geht hier nicht – bitte als Datei speichern."));
      }
    });
    dlg.querySelector("[data-labelsave]").addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([html], { type: "text/html" }));
      a.download = single ? `spool-${single.id}-label.html` : "spool-labels.html";
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 10000);
    });
    this._showDialog(dlg);
  }

  /** Form: create a spool in Spoolman. idx = head to assign to (prefilled from it), null = from the stock. */
  _newSpoolForm(dlg, idx) {
    const slot = idx !== null ? (this._slots() || [])[idx] || {} : {};
    const head = idx !== null ? (this._d && this._d.heads[idx]) || { name: `E${idx}` } : null;
    const rfid = slot.rfid || {};
    const color = /^#[0-9a-f]{6}$/i.test(slot.color || "") ? slot.color : "#ffffff";
    const vendor = idx === null ? "" : slot.vendor && slot.vendor !== "Generic" ? slot.vendor : (rfid.manufacturer || rfid.vendor || "");
    const material = idx === null ? "" : (slot.type || "PLA").toUpperCase();
    const name = idx === null ? "" : [material, slot.sub_type].filter(Boolean).join(" ");
    const heads = (this._d && this._d.heads) || [];
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${esc(head ? tr("Neue Spule für {head}", { head: head.name }) : tr("Neue Spule"))}</div>
          <div class="t-label">${tr("Tippen zeigt Filamente aus deinem Spoolman und dem Spoolman-Katalog.")}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <form class="head-form" data-newspoolform autocomplete="off">
          <label class="wide">${tr("Filament suchen")}<input name="q" type="search" placeholder="${tr("z. B. Polymaker PLA Pro schwarz")}" /></label>
          <div class="suggest wide" data-suggest hidden></div>
          <div class="picked wide" data-picked hidden></div>
          <label>${tr("Hersteller")}<input name="vendor" value="${esc(vendor)}" list="u1-vendors" required maxlength="64" placeholder="Generic" /></label>
          <label>${tr("Material")}<input name="material" value="${esc(material)}" list="u1-materials" required maxlength="32" /></label>
          <label>${tr("Name")}<input name="name" value="${esc(name)}" maxlength="64" placeholder="${tr("z. B. PLA Matte Schwarz")}" /></label>
          <label>${tr("Farbe")}<input name="color" type="color" value="${esc(color)}" /></label>
          <label>${tr("Nettogewicht (g)")}<input name="weight" type="number" min="1" max="10000" step="1" value="${Math.round(rfid.weight_g || 1000)}" required /></label>
          <label>${tr("Leerspule (g)")}<input name="spool_weight" type="number" min="0" max="2000" step="1" placeholder="${tr("optional")}" /></label>
          <label>${tr("Preis")}<input name="price" type="number" min="0" max="10000" step="0.01" placeholder="${tr("optional")}" /></label>
          <label>${tr("Ort")}<input name="location" maxlength="64" placeholder="${tr("optional")}" /></label>
          <details class="wide more-fields">
            <summary>${tr("Weitere Angaben")}</summary>
            <div class="t-label">${tr("Temperaturen, Dichte, Durchmesser und Artikelnummer gehören zum Filament und gelten nur, wenn es neu angelegt wird.")}</div>
            <div class="head-form">
              <label>${tr("Düsentemperatur (°C)")}<input name="extruder_temp" type="number" min="150" max="350" step="1" value="${rfidTemp(rfid.nozzle_temp)}" placeholder="${tr("optional")}" /></label>
              <label>${tr("Betttemperatur (°C)")}<input name="bed_temp" type="number" min="0" max="150" step="1" value="${rfidTemp(rfid.bed_temp)}" placeholder="${tr("optional")}" /></label>
              <label>${tr("Dichte (g/cm³)")}<input name="density" type="number" min="0.5" max="3" step="0.01" placeholder="${tr("nach Material")}" /></label>
              <label>${tr("Durchmesser (mm)")}<input name="diameter" type="number" min="1" max="3" step="0.01" placeholder="1.75" /></label>
              <label>${tr("Restgewicht (g)")}<input name="remaining" type="number" min="0" max="10000" step="1" placeholder="${tr("voll")}" /></label>
              <label>${tr("Artikelnummer")}<input name="article_number" maxlength="64" placeholder="${tr("optional")}" /></label>
              <label>${tr("Charge")}<input name="lot_nr" maxlength="64" placeholder="${tr("optional")}" /></label>
              <label class="wide">${tr("Kommentar")}<textarea name="comment" maxlength="1024" rows="2" placeholder="${tr("optional")}"></textarea></label>
              <div class="wide head-form" data-extrabox></div>
            </div>
          </details>
          ${head ? "" : `<label>${tr("Zuordnen")}<select name="slot"><option value="">${tr("keinem Kopf")}</option>
            ${heads.map((h) => `<option value="${h.idx + 1}">${esc(h.name)}</option>`).join("")}</select></label>`}
          <datalist id="u1-vendors"></datalist><datalist id="u1-materials"></datalist>
          <div class="dlg-error" hidden></div>
          <div class="dlg-actions">
            <button type="button" class="outline" data-back>${tr("Zurück")}</button>
            <button type="submit" class="filled"><ha-icon icon="mdi:content-save-outline"></ha-icon>${head ? tr("Anlegen und zuordnen") : tr("Anlegen")}</button>
          </div>
        </form>
      </div>`;
    const form = dlg.querySelector("[data-newspoolform]");
    const field = (n) => form.querySelector(`[name="${n}"]`);
    let picked = null;
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    dlg.querySelector("[data-back]").addEventListener("click", () =>
      (idx !== null ? this._openSpoolPicker(idx) : dlg.close()));

    // 2.4.0b3: own Spoolman fields, fetched once per page when a form opens
    let fields = { spool: [], filament: [] };
    this._smFieldsLoad().then((fl) => {
      fields = fl;
      const box = form.querySelector("[data-extrabox]");
      if (!box) return;
      box.innerHTML = [
        fl.spool.length ? `<div class="wide t-label">${tr("Eigene Felder der Spule")}</div>${fl.spool.map((x) => extraInput(x, undefined, "s")).join("")}` : "",
        fl.filament.length ? `<div class="wide t-label">${tr("Eigene Felder des Filaments (nur bei neuem Filament)")}</div>${fl.filament.map((x) => extraInput(x, undefined, "f")).join("")}` : "",
      ].join("");
    });

    // vendor and material names for the browser's suggestion lists
    this._spoolCatalogWS("catalog", {}).then((cat) => {
      if (!cat) return;
      const opts = (list) => list.map((v) => `<option value="${esc(v)}"></option>`).join("");
      form.querySelector("#u1-vendors").innerHTML = opts(cat.vendors || []);
      form.querySelector("#u1-materials").innerHTML = opts(cat.materials || []);
    });

    const box = form.querySelector("[data-suggest]");
    const showPicked = () => {
      const el = form.querySelector("[data-picked]");
      el.hidden = !picked;
      if (!picked) { el.innerHTML = ""; return; }
      el.innerHTML = `<ha-icon icon="${picked.source === "own" ? "mdi:database-check-outline" : "mdi:book-open-variant"}"></ha-icon>
        <span>${esc(picked.source === "own" ? tr("Filament aus deinem Spoolman") : tr("aus dem Spoolman-Katalog, wird übernommen"))}</span>
        <button type="button" class="chip sm" data-unpick>${tr("Lösen")}</button>`;
      el.querySelector("[data-unpick]").addEventListener("click", () => { picked = null; showPicked(); });
    };
    const pick = (it) => {
      picked = it;
      field("vendor").value = it.vendor || "";
      field("material").value = it.material || "";
      field("name").value = it.name || "";
      if (it.color) field("color").value = it.color;
      if (it.weight) field("weight").value = Math.round(it.weight);
      field("spool_weight").value = it.spool_weight ? Math.round(it.spool_weight) : "";
      if (it.price) field("price").value = it.price;
      // 2.4: the filament's own values, for the "more details" part
      [["extruder_temp", it.extruder_temp], ["bed_temp", it.bed_temp], ["density", it.density],
        ["diameter", it.diameter], ["article_number", it.article_number]]
        .forEach(([k, v]) => { field(k).value = v != null && v !== "" ? v : ""; });
      box.hidden = true;
      showPicked();
    };
    const suggest = async () => {
      const q = field("q").value.trim();
      if (q.length < 2) { box.hidden = true; return; }
      const seq = (this._suggestSeq = (this._suggestSeq || 0) + 1);
      const res = await this._spoolCatalogWS("suggest", { query: q });
      if (seq !== this._suggestSeq || !res) return;
      const items = res.items || [];
      box.hidden = false;
      box.innerHTML = items.length ? items.map((it, i) => `<button type="button" class="spool-opt" data-sug="${i}">
          <span class="spool-dot" style="--fil:${esc(it.colors && it.colors.length > 1 ? `linear-gradient(135deg, ${it.colors.join(", ")})` : it.color || "var(--u1-outline)")}"></span>
          <span class="spool-opt-text"><span>${esc(it.name || it.material)}</span>
            <span class="t-label">${[it.vendor, it.material, it.weight ? `${Math.round(it.weight)} g` : "",
              it.source === "own" ? tr("in Spoolman") : tr("Katalog")].filter(Boolean).map(esc).join(" · ")}</span></span>
        </button>`).join("") : `<div class="t-label">${tr("Nichts gefunden – Felder unten einfach ausfüllen.")}</div>`;
      box.querySelectorAll("[data-sug]").forEach((b) => b.addEventListener("click", () => pick(items[Number(b.dataset.sug)])));
    };
    field("q").addEventListener("input", () => {
      clearTimeout(this._suggestTimer);
      this._suggestTimer = setTimeout(suggest, SUGGEST_DELAY_MS);
    });
    // changing what defines the filament means it is no longer the picked one
    ["vendor", "material", "name", "color"].forEach((n) => field(n).addEventListener("input", () => {
      if (picked) { picked = null; showPicked(); }
    }));

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = new FormData(form);
      const opt = (k) => (String(f.get(k) || "").trim() === "" ? {} : { [k]: Number(f.get(k)) });
      const target = head ? idx + 1 : (f.get("slot") ? Number(f.get("slot")) : null);
      const data = {
        vendor: String(f.get("vendor") || "").trim() || "Generic",
        material: String(f.get("material") || "").trim(), color: f.get("color"),
        weight: Number(f.get("weight")), ...opt("spool_weight"), ...opt("price"), ...this._entryData(),
        ...opt("extruder_temp"), ...opt("bed_temp"), ...opt("density"), ...opt("diameter"), ...opt("remaining"),
      };
      ["article_number", "lot_nr", "comment"].forEach((k) => {
        const v = String(f.get(k) || "").trim();
        if (v) data[k] = v;
      });
      const nm = String(f.get("name") || "").trim();
      if (nm) data.name = nm;
      const loc = String(f.get("location") || "").trim();
      if (loc) data.location = loc;
      if (target) data.slot = target;
      if (picked && picked.source === "own") data.filament_id = picked.filament_id;
      else if (picked) data.external_id = picked.external_id;
      const ex = (list, prefix) => Object.fromEntries(list.map((x) => [x.key, extraValue(form, x, prefix)])
        .filter(([, v]) => v !== null && v !== false));
      const sx = ex(fields.spool, "s"), fx = ex(fields.filament, "f");
      if (Object.keys(sx).length) data.extra = sx;
      if (Object.keys(fx).length) data.filament_extra = fx;
      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      try {
        const res = await this._hass.callService(DOMAIN, "create_spool", data, undefined, false, true);
        const id = res && res.response && res.response.spool_id;
        const name = target ? ((heads[target - 1] || {}).name || `E${target - 1}`) : null;
        this._toast(name ? tr("Spule #{id} angelegt und {head} zugeordnet", { id: id ?? "?", head: name })
          : tr("Spule #{id} angelegt", { id: id ?? "?" }));
        dlg.close();
      } catch (err) {
        btn.disabled = false;
        const el = form.querySelector(".dlg-error");
        el.hidden = false;
        el.textContent = (err && err.message) || String(err);
      }
    });
  }

  /** Websocket spoolman/catalog | spoolman/suggest; null on error (the form still works without). */
  async _spoolCatalogWS(kind, params) {
    const entry = this._entryData().config_entry_id;
    try {
      return await this._hass.callWS({ type: `${DOMAIN}/spoolman/${kind}`, ...params, ...(entry ? { entry_id: entry } : {}) });
    } catch (e) {
      return null;
    }
  }
};
