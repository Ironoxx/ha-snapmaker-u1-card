/** Control tab: bed/chamber (with the top cover), temperature chart and motion (speed, flow). */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { tr } from "../i18n.js";

const TEMP_HIDDEN = "snapmaker-u1-card.temp-hidden";
const KNOWN_SERIES = ["extruder", "extruder1", "extruder2", "extruder3", "heater_bed", "cavity", "stepper_x", "stepper_y", "cpu"];
const EXTRA_COLORS = ["#fdd835", "#d81b60", "#5e35b1", "#00897b", "#c0ca33"];

export const ControlTabMixin = (Base) => class extends Base {
  _sectionClimate() {
    const d = this._d;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          <span class="panel-title">${tr("Bett &amp; Innenraum")}</span>
          ${this._lockBtn()}
        </div>
        <div class="stats">
          ${this._stat(tr("Druckbett"), `<span data-su1="bed">${num(d.bed, 0, "°C")}</span>`)}
          ${this._stat(tr("Innenraum"), `<span data-su1="cavity">${num(d.cavity, 0, "°C")}</span>`)}
          ${this._stat(tr("Bett-Heizung"), `<span data-su1="bedpow">${num(d.bedPower, 0, "%")}</span>`)}
          ${this._stat(tr("Netzteil-Lüfter"), `<span data-su1="powfan">${num(d.powerFan, 0, "%")}</span>`)}
        </div>
        ${this._slider({
          entity: `number.${this._p("bed_target")}`, label: tr("Bett-Solltemperatur"),
          value: d.bedTarget, unit: "°C", presets: this._cfg.bed_presets,
        })}
        ${this._slider({
          entity: `number.${this._p("fan_speed")}`, label: tr("Bauteillüfter"),
          value: d.partFan, unit: "%", presets: [0, 50, 100],
        })}
        ${this._slider({
          entity: `number.${this._p("cavity_fan_speed")}`, label: tr("Innenraumlüfter"),
          value: d.cavityFanSet, unit: "%", presets: [0, 50, 100],
        })}
      </section>
      ${this._coverPanel()}
      ${this._chamberPanel()}
      <section class="panel tpanel">
        <div class="panel-head">
          <ha-icon icon="mdi:chart-line"></ha-icon>
          <span class="panel-title">${tr("Temperaturverlauf")}</span>
          <span class="t-label" style="margin-left:auto">${tr("letzte 20 min")}</span>
        </div>
        <div class="tchart" data-tchart>${this._tempSvg()}</div>
      </section>`;
  }

  /** History from Moonraker's temperature_store (via the integration), every 10 s, only when visible. */
  async _tickTemps() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-tchart]");
    if (!box || document.hidden || !this._onScreen) return;
    const pane = box.closest("[data-pane]");
    if (pane && pane.hidden) return;
    const entry = this._entryData().config_entry_id;
    if (!entry || this._tBusy) return;
    this._tBusy = true;
    try {
      this._temps = await this._fetchJson(`/api/${DOMAIN}/temps/${entry}`);
      box.innerHTML = this._tempSvg();
    } catch (e) { /* next attempt */ } finally { this._tBusy = false; }
  }

  /** Lines hidden by a tap on the legend (per browser). */
  _tempHidden() {
    if (!this._tHidden) {
      try { this._tHidden = new Set(JSON.parse(window.localStorage.getItem(TEMP_HIDDEN) || "[]")); } catch (e) { this._tHidden = new Set(); }
    }
    return this._tHidden;
  }

  _toggleTempSeries(key) {
    const h = this._tempHidden();
    if (h.has(key)) h.delete(key); else h.add(key);
    try { window.localStorage.setItem(TEMP_HIDDEN, JSON.stringify([...h])); } catch (e) { /* no storage */ }
    const box = this.shadowRoot && this.shadowRoot.querySelector("[data-tchart]");
    if (box) box.innerHTML = this._tempSvg();
  }

  _tempSvg() {
    const t = this._temps;
    if (!t) return `<div class="t-label">${tr("Lädt …")}</div>`;
    if (t.offline) return `<div class="t-label">${tr("Drucker nicht erreichbar.")}</div>`;
    const series = t.series || null;
    if (!series || !Object.keys(series).length) return `<div class="t-label">${tr("Noch keine Daten.")}</div>`;
    const heads = this._d ? this._d.heads : [];
    const hidden = this._tempHidden();
    const isNum = (v) => typeof v === "number" && Number.isFinite(v);
    // heads and bed (actual + target), then chamber and stepper drivers (actual only)
    const defs = [
      ...["extruder", "extruder1", "extruder2", "extruder3"].map((k, i) => ({
        key: k, color: ["#e53935", "#1e88e5", "#43a047", "#fb8c00"][i],
        label: (heads[i] && heads[i].name) || tr("Kopf {n}", { n: i + 1 }), heater: true })),
      { key: "heater_bed", color: "#8e24aa", label: tr("Bett"), heater: true, always: true },
      { key: "cavity", color: "#00acc1", label: tr("Innenraum") },
      { key: "stepper_x", color: "#8d6e63", label: tr("Stepper X") },
      { key: "stepper_y", color: "#9e9e9e", label: tr("Stepper Y") },
      { key: "cpu", color: "#78909c", label: tr("CPU") },
      // further sensors of the printer config (mods): own colours, name from Klipper
      ...Object.keys(series).filter((k) => !KNOWN_SERIES.includes(k)).map((k, i) => ({
        key: k, color: EXTRA_COLORS[i % EXTRA_COLORS.length], label: k.replace(/_/g, " ") })),
    ].filter((s) => {
      const d = series[s.key];
      if (!d || !(d.temperatures || []).some(isNum)) return false;
      // cold, unused heads stay out of the chart and the legend
      return !s.heater || s.always || d.temperatures.some((v) => v > 45) || (d.targets || []).some((v) => v > 0);
    });
    if (!defs.length) return `<div class="t-label">${tr("Noch keine Daten.")}</div>`;
    const shown = defs.filter((s) => !hidden.has(s.key));
    const W = 300, H = 120, PAD = 22;
    let max = 60, n = 0;
    defs.forEach((s) => { n = Math.max(n, series[s.key].temperatures.length); });
    shown.forEach((s) => { [...series[s.key].temperatures, ...(series[s.key].targets || [])].forEach((v) => { if (isNum(v) && v > max) max = v; }); });
    max = Math.ceil((max + 10) / 50) * 50;
    if (n < 2) return `<div class="t-label">${tr("Noch keine Daten.")}</div>`;
    const x = (i) => PAD + (i / (n - 1)) * (W - PAD - 4);
    const y = (v) => H - 14 - (v / max) * (H - 22);
    // gaps (stepper off) split the line
    const line = (vals, color, dash, width) => {
      const off = n - vals.length;
      const runs = [];
      let cur = [];
      vals.forEach((v, i) => {
        if (isNum(v)) cur.push(`${x(i + off).toFixed(1)},${y(v).toFixed(1)}`);
        else if (cur.length) { runs.push(cur); cur = []; }
      });
      if (cur.length) runs.push(cur);
      return runs.filter((r) => r.length > 1).map((r) => `<polyline points="${r.join(" ")}" fill="none" stroke="${color}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ""} stroke-linejoin="round"/>`).join("");
    };
    const grid = [0, max / 2, max].map((v) => `<line x1="${PAD}" x2="${W - 4}" y1="${y(v)}" y2="${y(v)}" class="tgrid"/><text x="${PAD - 3}" y="${y(v) + 3}" class="tax" text-anchor="end">${Math.round(v)}</text>`).join("");
    const mins = Math.round((n * (t.step || 5)) / 60);
    const xlab = `<text x="${PAD}" y="${H - 2}" class="tax">−${mins} min</text><text x="${W - 4}" y="${H - 2}" class="tax" text-anchor="end">${tr("jetzt")}</text>`;
    const paths = shown.map((s) => {
      const d = series[s.key];
      return (s.heater ? line(d.targets || [], s.color, "3 3", 0.8) : "") + line(d.temperatures, s.color, "", s.heater ? 1.6 : 1.2);
    }).join("");
    const legend = defs.map((s) => {
      const vals = series[s.key].temperatures.filter(isNum);
      const off = hidden.has(s.key);
      return `<button type="button" class="tleg" data-tser="${s.key}" aria-pressed="${!off}" title="${esc(off ? tr("Einblenden") : tr("Ausblenden"))}"><i style="background:${s.color}"></i>${esc(s.label)} ${num(vals[vals.length - 1], 0, "°C")}</button>`;
    }).join("");
    return `<svg viewBox="0 0 ${W} ${H}" class="tsvg" role="img" aria-label="${tr("Temperaturverlauf")}">${grid}${paths}${xlab}</svg>
      <div class="tlegend">${legend}</div>`;
  }

  async _fetchJson(url) {
    const h = this._hass;
    const res = typeof h.fetchWithAuth === "function"
      ? await h.fetchWithAuth(url)
      : await fetch(url, { headers: { Authorization: `Bearer ${h.auth && h.auth.data ? h.auth.data.access_token : ""}` } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  _sectionMotion() {
    const d = this._d;
    const homing = d.active
      ? `<div class="t-label">${tr("Referenzfahrt ist während des Drucks gesperrt.")}</div>`
      : `<div class="switches" data-lockable>
           <button class="tonal" data-act="home_all"><ha-icon icon="mdi:home"></ha-icon>${tr("Alle Achsen")}</button>
           <button class="outline" data-act="home_x">X</button>
           <button class="outline" data-act="home_y">Y</button>
           <button class="outline" data-act="home_z">Z</button>
         </div>`;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:axis-arrow"></ha-icon>
          <span class="panel-title">${tr("Bewegung")}</span>
          ${this._lockBtn()}
        </div>
        <div class="stats">
          ${this._stat(tr("Position X"), `<span data-su1="px">${num(d.posX, 1)}</span>`)}
          ${this._stat(tr("Position Y"), `<span data-su1="py">${num(d.posY, 1)}</span>`)}
          ${this._stat(tr("Position Z"), `<span data-su1="pz">${num(d.posZ, 2)}</span>`)}
        </div>
        ${this._slider({
          entity: `number.${this._p("speed_factor")}`, label: tr("Geschwindigkeit"),
          value: d.speedFactor, unit: "%", presets: [50, 100, 150],
        })}
        ${this._ents.flow && d.flow !== null ? this._slider({
          entity: this._ents.flow, label: tr("Flussrate"), value: d.flow, unit: "%", presets: [95, 100, 105],
        }) : ""}
        ${homing}
      </section>`;
  }
};
