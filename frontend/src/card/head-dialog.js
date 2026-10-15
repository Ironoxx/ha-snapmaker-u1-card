/** Head details: loaded filament, RFID tag data, Spoolman spool and editing the filament by hand. */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { LOCALE, tr } from "../i18n.js";

// Materials offered in the edit form; anything else the printer reports is added on top.
const MATERIALS = ["PLA", "PLA-CF", "PETG", "PETG-CF", "ABS", "ASA", "TPU", "PA", "PA-CF", "PC", "PVA", "HIPS"];

export const HeadDialogMixin = (Base) => class extends Base {
  /** RFID tag data as label/value rows; only fields the tag actually contains. */
  _rfidRows(r) {
    if (!r) return [];
    const range = (a, b) => (a && b ? `${a}–${b} °C` : a || b ? `${a || b} °C` : null);
    return [
      [tr("Hersteller"), r.manufacturer || r.vendor],
      [tr("Spulengewicht"), r.weight_g ? num(r.weight_g, 0, "g") : null],
      [tr("Länge"), r.length_m ? num(r.length_m, 0, "m") : null],
      [tr("Durchmesser"), r.diameter_mm ? num(r.diameter_mm, 2, "mm") : null],
      [tr("Düsentemperatur"), r.nozzle_temp ? range(r.nozzle_temp[0], r.nozzle_temp[1]) : null],
      [tr("Erste Schicht / weitere"), r.first_layer_temp || r.other_layer_temp
        ? `${r.first_layer_temp || "—"} / ${r.other_layer_temp || "—"} °C` : null],
      [tr("Bett"), r.bed_temp ? num(r.bed_temp, 0, "°C") : null],
      [tr("Trocknen"), r.drying_temp ? `${num(r.drying_temp, 0, "°C")}${r.drying_time_h ? ` · ${num(r.drying_time_h, 0, "h")}` : ""}` : null],
      [tr("Hergestellt"), r.manufactured ? new Date(`${r.manufactured}T12:00:00`).toLocaleDateString(LOCALE) : null],
      ["SKU", r.sku ? String(r.sku) : null],
    ].filter(([, v]) => v);
  }

  _openHeadInfo(idx) {
    const slot = (this._slots() || [])[idx];
    if (!slot) return;
    const head = (this._d && this._d.heads[idx]) || { name: `E${idx}` };
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1head");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1head" aria-label="${tr("Druckkopf")}"></dialog>`);
      dlg = host.querySelector("dialog.u1head");
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    const printing = !!(this._d && (this._d.printing || this._d.paused));
    const offline = !!(this._d && !this._d.online);
    const rfid = this._rfidRows(slot.rfid);
    const sm = this._spoolman();
    const spool = sm ? this._slotSpool(idx) : null;
    const types = [...new Set([...(slot.type ? [slot.type.toUpperCase()] : []), ...MATERIALS])];
    const color = /^#[0-9a-f]{6}$/i.test(slot.color || "") ? slot.color : "#ffffff";
    const locked = printing || offline;
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head">
          <span class="spool-dot big" style="--fil:${esc(slot.loaded ? slot.color || "var(--u1-outline)" : "transparent")}"></span>
          <div style="min-width:0">
            <div class="dlg-title">${esc(head.name)}${slot.official ? ` <span class="rfid">RFID</span>` : ""}</div>
            <div class="t-label">${esc(slot.loaded ? [slot.type, slot.sub_type, slot.vendor].filter(Boolean).join(" · ") || tr("unbekannt") : tr("Leer"))}</div>
          </div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        ${rfid.length ? `<div class="t-label head-sub">${tr("Daten der Spule (RFID)")}</div>
          <div class="rows head-rfid">${rfid.map(([k, v]) => `<div class="row"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`).join("")}</div>` : ""}
        ${sm ? `<div class="t-label head-sub">Spoolman</div>
          <button type="button" class="spool-line" data-headspool>
            <ha-icon icon="mdi:database-outline"></ha-icon>
            <span>${spool ? esc(`#${spool.id} ${spool.name}${spool.remaining_weight != null ? ` · ${Math.round(spool.remaining_weight)} g` : ""}`) : tr("Spule wählen")}</span>
          </button>` : ""}
        <div class="t-label head-sub">${tr("Filament von Hand setzen")}</div>
        ${locked ? `<div class="dlg-note"><ha-icon icon="mdi:information-outline"></ha-icon>${printing ? tr("Während eines Drucks nicht möglich.") : tr("Der Drucker ist ausgeschaltet.")}</div>` : ""}
        <form class="head-form" data-headform>
          <label>${tr("Material")}<select name="type" ${locked ? "disabled" : ""}>
            ${types.map((t) => `<option value="${esc(t)}" ${t === (slot.type || "").toUpperCase() ? "selected" : ""}>${esc(t)}</option>`).join("")}
          </select></label>
          <label>${tr("Unterart")}<input name="sub_type" value="${esc(slot.sub_type || "")}" placeholder="${tr("z. B. Silk, Matte, HF")}" ${locked ? "disabled" : ""} /></label>
          <label>${tr("Hersteller")}<input name="vendor" value="${esc(slot.vendor || "Generic")}" ${locked ? "disabled" : ""} /></label>
          <label>${tr("Farbe")}<input name="color" type="color" value="${esc(color)}" ${locked ? "disabled" : ""} /></label>
          ${slot.official ? `<label class="check"><input type="checkbox" name="force" ${locked ? "disabled" : ""} />${tr("RFID-Daten der Snapmaker-Spule überschreiben")}</label>` : ""}
          <div class="dlg-error" hidden></div>
          <div class="dlg-actions"><button type="submit" class="filled" ${locked ? "disabled" : ""}><ha-icon icon="mdi:content-save-outline"></ha-icon>${tr("Übernehmen")}</button></div>
        </form>
      </div>`;
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    const sp = dlg.querySelector("[data-headspool]");
    if (sp) sp.addEventListener("click", () => { dlg.close(); this._openSpoolPicker(idx); });
    const form = dlg.querySelector("[data-headform]");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = new FormData(form);
      const data = {
        slot: idx + 1, type: f.get("type"), sub_type: (f.get("sub_type") || "").trim(),
        vendor: (f.get("vendor") || "").trim() || "Generic", color: f.get("color"),
        ...(f.get("force") ? { force: true } : {}), ...this._entryData(),
      };
      const err = form.querySelector(".dlg-error");
      try {
        await this._hass.callService(DOMAIN, "set_filament", data, undefined, false);
        dlg.close();
        this._toast(tr("Filament für {head} gesetzt", { head: head.name }));
      } catch (ex) {
        err.hidden = false;
        err.textContent = (ex && ex.message) || String(ex);
      }
    });
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
  }
};
