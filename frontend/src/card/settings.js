/**
 * Settings of the integration right in the card (2.0, admins only).
 *
 * Fields, labels and validation come from the integration (websocket
 * snapmaker_u1_card/settings/get|set, built from the options flow), so the card
 * and *Configure* in Home Assistant always show the same. The card adds
 * context: current value of chosen entities, Spoolman prices next to the own
 * prices, a short summary per section.
 */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { LANG, tr } from "../i18n.js";

const SEC_ICONS = {
  power: "mdi:power-plug-outline", notify: "mdi:bell-outline", filament: "mdi:cash-multiple",
  spoolman: "mdi:database-outline", files: "mdi:folder-outline", timelapse: "mdi:timelapse",
  maintenance: "mdi:wrench-outline",
};

export const SettingsMixin = (Base) => class extends Base {
  _isAdmin() { return !!(this._hass && this._hass.user && this._hass.user.is_admin); }

  _settingsButtonHtml() {
    if (!this._isAdmin()) return "";
    return `<button class="tonal" data-act="settings"><ha-icon icon="mdi:cog-outline"></ha-icon>${tr("Einstellungen")}</button>`;
  }

  _settingsDialog() {
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1settings");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1settings" aria-label="${tr("Einstellungen")}"></dialog>`);
      dlg = host.querySelector("dialog.u1settings");
      dlg.addEventListener("click", (e) => { if (e.target === dlg) this._closeSettings(); });
      dlg.addEventListener("cancel", (e) => { if (this._set && this._set.dirty.size) { e.preventDefault(); this._closeSettings(); } });
    }
    return dlg;
  }

  _closeSettings() {
    const dlg = this._settingsDialog();
    if (this._set && this._set.dirty.size && !confirm(tr("Änderungen verwerfen?"))) return;
    this._set = null;
    dlg.close();
  }

  async _openSettings() {
    if (!this._isAdmin()) return;
    const dlg = this._settingsDialog();
    dlg.innerHTML = `<div class="dlg"><div class="t-label">${tr("Lade Einstellungen …")}</div></div>`;
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
    const entry = this._entryData().config_entry_id;
    try {
      const meta = await this._hass.callWS({ type: `${DOMAIN}/settings/get`, language: LANG,
        ...(entry ? { entry_id: entry } : {}) });
      this._set = { meta, entry, values: JSON.parse(JSON.stringify(meta.values || {})), dirty: new Set(), open: new Set() };
      this._renderSettings();
    } catch (err) {
      dlg.innerHTML = `<div class="dlg"><div class="dlg-error">${esc((err && err.message) || String(err))}</div>
        <div class="dlg-actions"><button class="outline" data-close>${tr("Schließen")}</button></div></div>`;
      dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    }
  }

  _val(sec, key) {
    const v = ((this._set.values || {})[sec] || {})[key];
    return v === undefined ? null : v;
  }

  /** Current value of the chosen entity, e.g. "85 W" or "an". */
  _entityNow(id) {
    const st = id && this._hass.states[id];
    if (!st) return id ? tr("Entität nicht gefunden") : "";
    const name = (st.attributes && st.attributes.friendly_name) || id;
    const unit = (st.attributes && st.attributes.unit_of_measurement) || "";
    const state = { on: tr("an"), off: tr("aus"), unavailable: tr("nicht verfügbar") }[st.state] || st.state;
    return `${name}: ${state}${unit ? ` ${unit}` : ""}`;
  }

  _entityChoices(f) {
    return Object.values(this._hass.states).filter((s) => {
      const dom = s.entity_id.split(".")[0];
      if (f.domains && f.domains.length && !f.domains.includes(dom)) return false;
      return !f.device_class || (s.attributes && s.attributes.device_class) === f.device_class;
    }).map((s) => s.entity_id).sort();
  }

  _sectionSummary(sec) {
    const v = (k) => this._val(sec, k);
    const m = this._set.meta;
    if (sec === "power") {
      const sw = v("power_switch");
      return sw ? [this._entityNow(sw).split(":")[0], v("auto_off") ? tr("Auto-Aus") : "", v("auto_on") ? tr("Auto-Ein") : ""]
        .filter(Boolean).join(" · ") : tr("kein Netzschalter");
    }
    if (sec === "notify") {
      const n = (v("notify_targets") || []).length;
      return n ? tr("{n} Ziel(e)", { n }) : tr("keine Benachrichtigungen");
    }
    if (sec === "filament") {
      const own = m.fields.filter((f) => f.section === sec && v(f.key) !== null).map((f) => `${f.label} ${num(v(f.key), 2)}`);
      const sm = Object.keys(m.spoolman_prices || {}).length;
      return [sm ? tr("Spoolman: {n} Materialien", { n: sm }) : "", own.join(", ")].filter(Boolean).join(" · ") || tr("keine Preise");
    }
    if (sec === "spoolman") return v("spoolman_url") || tr("aus");
    return "";
  }

  _fieldHtml(f) {
    const id = `${f.section}.${f.key}`;
    const val = this._val(f.section, f.key);
    const cur = val === null && f.default !== undefined ? f.default : val;
    const attr = `data-set="${esc(id)}"`;
    let control = "";
    let extra = "";
    if (f.type === "boolean") {
      return `<label class="cfg-row cfg-bool"><span class="cfg-text"><span>${esc(f.label)}</span>
          ${f.help ? `<small class="t-label">${esc(f.help)}</small>` : ""}</span>
        <input type="checkbox" role="switch" ${attr} ${cur ? "checked" : ""} /></label>`;
    }
    if (f.type === "entity") {
      const list = `dl-${f.key}`;
      control = `<input type="text" ${attr} value="${esc(cur || "")}" list="${list}" placeholder="${tr("keine")}" autocomplete="off" />
        <datalist id="${list}">${this._entityChoices(f).map((e) => `<option value="${esc(e)}">`).join("")}</datalist>`;
      extra = cur ? `<small class="cfg-now" data-now="${esc(id)}">${esc(this._entityNow(cur))}</small>` : `<small class="cfg-now" data-now="${esc(id)}"></small>`;
    } else if (f.type === "number") {
      const sm = f.section === "filament" ? (this._set.meta.spoolman_prices || {})[f.key.replace(/^price_/, "").toUpperCase()] : null;
      control = `<span class="cfg-num"><input type="number" ${attr} value="${cur === null || cur === undefined ? "" : esc(cur)}"
          ${f.min !== null && f.min !== undefined ? `min="${f.min}"` : ""} ${f.max !== null && f.max !== undefined ? `max="${f.max}"` : ""}
          step="${f.step || "any"}" placeholder="${sm !== null && sm !== undefined ? esc(num(sm, 2)) : f.required ? "" : tr("leer")}" />
        ${f.unit ? `<span class="t-label">${esc(f.unit)}</span>` : ""}</span>`;
      if (sm !== null && sm !== undefined) extra = `<small class="cfg-now">${esc(tr("Spoolman: {p} €/kg – hat Vorrang", { p: num(sm, 2) }))}</small>`;
    } else if (f.type === "select" && f.multiple) {
      const opts = [...new Set([...(f.options || []), ...((Array.isArray(cur) ? cur : []))])];
      const lab = (o) => (f.option_labels && f.option_labels[o]) || o;
      control = `<div class="cfg-multi" ${attr} data-multi>${opts.map((o) =>
        `<label class="cfg-chk"><input type="checkbox" value="${esc(o)}" ${(cur || []).includes(o) ? "checked" : ""} />${esc(lab(o))}</label>`).join("")
        || `<span class="t-label">${tr("keine verfügbar")}</span>`}</div>`;
    } else if (f.type === "select") {
      const lab = (o) => (f.option_labels && f.option_labels[o]) || o;
      control = `<select ${attr}>${f.required ? "" : `<option value="">—</option>`}${(f.options || []).map((o) =>
        `<option value="${esc(o)}" ${o === cur ? "selected" : ""}>${esc(lab(o))}</option>`).join("")}</select>`;
    } else {
      control = `<input type="text" ${attr} value="${esc(cur || "")}" />`;
    }
    return `<div class="cfg-row"><div class="cfg-text"><span>${esc(f.label)}</span>
        ${f.help ? `<small class="t-label">${esc(f.help)}</small>` : ""}</div>
      <div class="cfg-ctl">${control}${extra}</div></div>`;
  }

  /** Maintenance: one row per item with hours and months. */
  _maintHtml(fields) {
    const items = fields.filter((f) => f.key.startsWith("maint_") && !f.key.startsWith("maint_m_"));
    const rows = items.map((f) => {
      const k = f.key.slice("maint_".length);
      const m = fields.find((x) => x.key === `maint_m_${k}`);
      const inp = (fld) => {
        const v = this._val(fld.section, fld.key);
        const cur = v === null ? fld.default : v;
        return `<span class="cfg-num"><input type="number" data-set="${esc(`${fld.section}.${fld.key}`)}" value="${esc(cur ?? "")}"
          min="${fld.min ?? 0}" max="${fld.max ?? ""}" step="1" /><span class="t-label">${esc(fld.unit === "mo" ? tr("Mon.") : fld.unit || "")}</span></span>`;
      };
      return `<div class="cfg-maint"><span>${esc(f.label.replace(/\s*\([^)]*\)\s*$/, ""))}</span>${inp(f)}${m ? inp(m) : ""}</div>`;
    }).join("");
    return `<div class="cfg-maint cfg-maint-head t-label"><span></span><span>${tr("Stunden")}</span><span>${tr("Monate")}</span></div>${rows}
      <small class="t-label">${tr("0 = aus. Fällig ist, was zuerst erreicht wird.")}</small>`;
  }

  _renderSettings() {
    const dlg = this._settingsDialog();
    const s = this._set;
    if (!s) return;
    const order = Object.keys(s.meta.sections);
    const secs = order.map((sec) => {
      const info = s.meta.sections[sec];
      const fields = s.meta.fields.filter((f) => f.section === sec);
      const body = sec === "maintenance" ? this._maintHtml(fields) : fields.map((f) => this._fieldHtml(f)).join("");
      const sum = this._sectionSummary(sec);
      return `<details class="cfg-sec" data-sec="${esc(sec)}" ${s.open.has(sec) ? "open" : ""}>
          <summary><ha-icon icon="${SEC_ICONS[sec] || "mdi:cog-outline"}"></ha-icon>
            <span class="cfg-sum"><span>${esc(info.name)}</span>${sum ? `<small class="t-label">${esc(sum)}</small>` : ""}</span>
            ${s.dirty.has(sec) ? `<span class="cfg-dot" title="${tr("geändert")}"></span>` : ""}
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon></summary>
          <div class="cfg-body">${info.description ? `<div class="t-label">${esc(info.description)}</div>` : ""}${body}</div>
        </details>`;
    }).join("");
    dlg.innerHTML = `<div class="dlg cfg-dlg">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${tr("Einstellungen")}</div>
          <div class="t-label">${esc(s.meta.title || "")}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <div class="cfg-list">${secs}</div>
        <div class="cfg-foot">
          <div class="dlg-error" hidden></div>
          <div class="dlg-actions">
            <button type="button" class="outline" data-discard ${s.dirty.size ? "" : "disabled"}>${tr("Verwerfen")}</button>
            <button type="button" class="filled" data-save ${s.dirty.size ? "" : "disabled"}><ha-icon icon="mdi:content-save-outline"></ha-icon>${tr("Speichern")}</button>
          </div>
          <small class="t-label">${tr("Gilt für die Integration (alle Dashboards). Nach dem Speichern lädt sie kurz neu.")}</small>
        </div>
      </div>`;
    dlg.querySelector("[data-close]").addEventListener("click", () => this._closeSettings());
    dlg.querySelectorAll("details.cfg-sec").forEach((d) => d.addEventListener("toggle", () => {
      if (d.open) s.open.add(d.dataset.sec); else s.open.delete(d.dataset.sec);
    }));
    dlg.querySelectorAll("[data-set]").forEach((el) => {
      const [sec, key] = el.dataset.set.split(".");
      const f = s.meta.fields.find((x) => x.section === sec && x.key === key) || {};
      const read = () => {
        if (el.dataset.multi !== undefined) return [...el.querySelectorAll("input:checked")].map((i) => i.value);
        if (el.type === "checkbox") return el.checked;
        if (el.type === "number") return el.value === "" ? null : Number(el.value);
        return el.value.trim() === "" ? null : el.value.trim();
      };
      el.addEventListener("change", () => {
        s.values[sec] = { ...(s.values[sec] || {}), [key]: read() };
        const first = !s.dirty.has(sec);
        s.dirty.add(sec);
        if (f.type === "entity") {
          const now = dlg.querySelector(`[data-now="${CSS.escape(el.dataset.set)}"]`);
          if (now) now.textContent = this._entityNow(read());
        }
        dlg.querySelector("[data-save]").disabled = false;
        dlg.querySelector("[data-discard]").disabled = false;
        if (first) {
          const sum = dlg.querySelector(`details[data-sec="${sec}"] summary`);
          if (sum && !sum.querySelector(".cfg-dot")) sum.querySelector(".caret").insertAdjacentHTML("beforebegin", `<span class="cfg-dot" title="${tr("geändert")}"></span>`);
        }
      });
    });
    dlg.querySelector("[data-discard]").addEventListener("click", () => {
      s.values = JSON.parse(JSON.stringify(s.meta.values || {}));
      s.dirty.clear();
      this._renderSettings();
    });
    dlg.querySelector("[data-save]").addEventListener("click", () => this._saveSettings());
  }

  async _saveSettings() {
    const s = this._set;
    const dlg = this._settingsDialog();
    const btn = dlg.querySelector("[data-save]");
    const err = dlg.querySelector(".cfg-foot .dlg-error");
    btn.disabled = true;
    err.hidden = true;
    const values = {};
    s.dirty.forEach((sec) => { values[sec] = s.values[sec] || {}; });
    try {
      const res = await this._hass.callWS({ type: `${DOMAIN}/settings/set`, values, language: LANG,
        ...(s.entry ? { entry_id: s.entry } : {}) });
      this._set = null;
      dlg.close();
      this._toast(res && res.changed ? tr("Einstellungen gespeichert – die Integration lädt neu.") : tr("Keine Änderung."));
    } catch (e) {
      btn.disabled = false;
      err.hidden = false;
      err.textContent = (e && e.message) || String(e);
    }
  }
};
