/**
 * Spoolman in the card (2.1): the stock of spools and a "new spool" form with
 * suggestions.
 *
 * Stock: every active spool with colour, vendor, material, location and the
 * remaining weight, filtered by material or text, totals on top. The data is
 * the spool list the integration already keeps (sensor filaments, attribute
 * spoolman.spools), so opening it costs no request.
 *
 * New spool: typing searches the own Spoolman filaments and Spoolman's
 * catalogue SpoolmanDB (websocket spoolman/suggest). A pick fills vendor,
 * material, name, colour and weights; saving runs the create_spool service
 * with the filament ID or the catalogue entry, so Spoolman gets the same
 * filament it would create itself.
 */

import { DOMAIN } from "../const.js";
import { clamp, esc, fmtEuro } from "../format.js";
import { tr } from "../i18n.js";

const SUGGEST_DELAY_MS = 250;

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

  _openSpoolStock(filter = this._stockFilter || { material: "", text: "" }) {
    const sm = this._spoolman();
    if (!sm) return;
    this._stockFilter = filter;
    this._stockSeen = JSON.stringify(sm.spools || []);
    const dlg = this._spoolDialog();
    const all = sm.spools || [];
    const heads = this._spoolHeads();
    const materials = [...new Set(all.map((s) => (s.material || "").toUpperCase()).filter(Boolean))].sort();
    const words = filter.text.toLowerCase().split(/\s+/).filter(Boolean);
    const list = all.filter((s) => (!filter.material || (s.material || "").toUpperCase() === filter.material)
      && words.every((w) => [s.name, s.vendor, s.material, s.location, `#${s.id}`].join(" ").toLowerCase().includes(w)))
      .sort((a, b) => (a.material || "").localeCompare(b.material || "") || (a.vendor || "").localeCompare(b.vendor || "")
        || (a.name || "").localeCompare(b.name || ""));
    const grams = list.reduce((n, s) => n + (s.remaining_weight || 0), 0);
    const value = list.reduce((n, s) => n + (s.price_kg && s.remaining_weight ? s.price_kg * s.remaining_weight / 1000 : 0), 0);
    const low = sm.low || 0;
    const row = (s) => {
      const rest = s.remaining_weight;
      const pct = rest != null && s.initial_weight ? clamp((rest / s.initial_weight) * 100, 0, 100) : null;
      const head = heads.get(s.id);
      const colors = (s.colors && s.colors.length > 1)
        ? `linear-gradient(135deg, ${s.colors.map(esc).join(", ")})` : esc(s.color || "var(--u1-outline)");
      return `<div class="stock-row" data-stock="${s.id}" data-low="${rest != null && rest < low ? 1 : 0}">
          <span class="spool-dot" style="--fil:${colors}"></span>
          <span class="spool-opt-text"><span>#${s.id} ${esc(s.name)}</span>
            <span class="t-label">${[s.vendor, s.material, s.location,
              head != null ? tr("steckt in {head}", { head: (this._d.heads[head] || {}).name || `E${head}` }) : ""]
              .filter(Boolean).map(esc).join(" · ")}</span>
            ${pct != null ? `<span class="spool-track"><i style="width:${pct}%"></i></span>` : ""}</span>
          <span class="spool-rest">${rest != null ? `${Math.round(rest)} g` : "–"}</span>
        </div>`;
    };
    dlg.innerHTML = `<div class="dlg">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${tr("Spoolman-Bestand")}</div>
          <div class="t-label" data-stocksum>${tr("{n} Spulen · {kg} kg", { n: list.length, kg: (grams / 1000).toFixed(1) })}${value > 0 ? ` · ${fmtEuro(value)}` : ""}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        ${sm.online ? "" : `<div class="dlg-note" data-tone="error"><ha-icon icon="mdi:database-off"></ha-icon>${tr("Spoolman nicht erreichbar")}${sm.error ? `: ${esc(sm.error)}` : ""}</div>`}
        <input class="stock-search" type="search" data-stocktext value="${esc(filter.text)}" placeholder="${tr("Suchen: Name, Hersteller, Ort, #ID")}" />
        <div class="chips stock-chips">
          <button type="button" class="chip sm" data-stockmat="" aria-pressed="${!filter.material}">${tr("Alle")}</button>
          ${materials.map((m) => `<button type="button" class="chip sm" data-stockmat="${esc(m)}" aria-pressed="${filter.material === m}">${esc(m)}</button>`).join("")}
        </div>
        <div class="spool-list">${list.map(row).join("") || `<div class="t-label">${all.length ? tr("Keine Spule passt zum Filter.") : tr("Keine aktiven Spulen in Spoolman.")}</div>`}</div>
        <div class="dlg-actions">
          <button type="button" class="filled" data-stocknew ${sm.online ? "" : "disabled"}><ha-icon icon="mdi:plus"></ha-icon>${tr("Neue Spule")}</button>
        </div>
      </div>`;
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    dlg.querySelectorAll("[data-stockmat]").forEach((b) => b.addEventListener("click", () =>
      this._openSpoolStock({ ...this._stockFilter, material: b.dataset.stockmat })));
    const txt = dlg.querySelector("[data-stocktext]");
    txt.addEventListener("input", () => {
      clearTimeout(this._stockTimer);
      this._stockTimer = setTimeout(() => {
        this._openSpoolStock({ ...this._stockFilter, text: txt.value });
        const again = this._spoolDialog().querySelector("[data-stocktext]");
        if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); }
      }, 200);
    });
    dlg.querySelector("[data-stocknew]").addEventListener("click", () => this._newSpoolForm(dlg, null));
    this._showDialog(dlg);
  }

  /** Stock open: show new or changed spools (not while typing in its search field). */
  _refreshStock() {
    const sm = this._spoolman();
    const dlg = this.shadowRoot && this.shadowRoot.querySelector("dialog.u1spool");
    if (!sm || !dlg || !dlg.open || !dlg.querySelector("[data-stocktext]")) return;
    if (JSON.stringify(sm.spools || []) === this._stockSeen) return;
    if (this.shadowRoot.activeElement === dlg.querySelector("[data-stocktext]")) return;
    this._openSpoolStock();
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
      (idx !== null ? this._openSpoolPicker(idx) : this._openSpoolStock()));

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
      };
      const nm = String(f.get("name") || "").trim();
      if (nm) data.name = nm;
      const loc = String(f.get("location") || "").trim();
      if (loc) data.location = loc;
      if (target) data.slot = target;
      if (picked && picked.source === "own") data.filament_id = picked.filament_id;
      else if (picked) data.external_id = picked.external_id;
      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      try {
        const res = await this._hass.callService(DOMAIN, "create_spool", data, undefined, false, true);
        const id = res && res.response && res.response.spool_id;
        const name = target ? ((heads[target - 1] || {}).name || `E${target - 1}`) : null;
        this._toast(name ? tr("Spule #{id} angelegt und {head} zugeordnet", { id: id ?? "?", head: name })
          : tr("Spule #{id} angelegt", { id: id ?? "?" }));
        if (head) dlg.close(); else this._openSpoolStock();
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
