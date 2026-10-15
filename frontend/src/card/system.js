/** System tab: diagnostics, self test, maintenance and config backup. */

import { DOMAIN, MAINT_LABELS } from "../const.js";
import { esc, fmtDate, fmtEuro, fmtInt, num } from "../format.js";
import { LANG, tr } from "../i18n.js";

export const SystemMixin = (Base) => class extends Base {
  _sectionSystem() {
    const d = this._d;
    // Same formulas as Mainsail/Fluidd (Moonraker integration): small values are normal.
    const mcuTip = tr("Last: längste Aufgabe des Controllers (Mittel + 3 σ) im Verhältnis zu 2,5 ms. Ab etwa 100 % meldet Klipper 'Timer too close'. Wach: Anteil der Zeit, in der der Controller rechnet statt zu schlafen. Einstellige Werte sind normal.");
    const heads = d.heads.map((h) =>
      this._row(`MCU ${h.name}`,
        `<span data-su1="mcu:${h.idx}">${num(h.mcuLoad, 2, "%")} / ${num(h.mcuAwake, 2, "%")}</span>`, null, mcuTip)
    ).join("");
    return `
      <section class="panel">
        <details ${this._cfg.compact ? "" : "open"}>
          <summary>
            <ha-icon icon="mdi:chip"></ha-icon>
            <span style="flex:1">${tr("System &amp; Diagnose")}</span>
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon>
          </summary>
          <div class="body rows">
            ${this._ents.firmware ? this._row(tr("Firmware"), `<span data-su1="fw">${this._fwText()}</span>`, this._ents.firmware) : ""}
            ${this._ents.live ? this._row(tr("Live-Verbindung"), `<span data-su1="live">${this._liveText()}</span>`, this._ents.live) : ""}
            ${this._row("Klipper", `<span data-su1="klipper">${esc(d.klipper || "—")}</span>`, `sensor.${this._p("printer_state")}`)}
            ${this._row(tr("Meldung"), `<span data-su1="msg" style="font-family:var(--u1-font)">${esc(d.message || "—")}</span>`)}
            ${this._row(tr("Idle-Status"), `<span data-su1="idle">${esc(d.idleTimeout)}</span>`)}
            ${this._row(tr("MCU Host (Last / Wach)"), `<span data-su1="mcuhost">${num(d.mcuLoad, 2, "%")} / ${num(d.mcuAwake, 2, "%")}</span>`, null, mcuTip)}
            ${heads}
            ${this._row(tr("Arbeitsspeicher"), `<span data-su1="mem">${num(d.memory, 1, "%")}</span>`, null, tr("Belegter Arbeitsspeicher des Druckerrechners (ohne Puffer und Cache)."))}
            <div class="row" title="${tr("Load Average über 1 Minute: im Mittel laufende oder wartende Prozesse. Liegt der Wert unter der Zahl der Kerne, ist der Drucker nicht ausgelastet.")}">
              <span class="k">${tr("Systemlast (Ø 1 min)")}</span><span class="v" data-su1="sys">${this._loadText()}</span></div>
            ${d.stepX !== null ? this._row(tr("Stepper X"), `<span data-su1="stepx">${num(d.stepX, 1, "°C")}</span>`) : ""}
            ${d.stepY !== null ? this._row(tr("Stepper Y"), `<span data-su1="stepy">${num(d.stepY, 1, "°C")}</span>`) : ""}
            <div class="selftest-wrap">
              <button class="tonal" data-act="selftest"><ha-icon icon="mdi:stethoscope"></ha-icon>${tr("Selbsttest")}</button>
              <div class="selftest" data-selftest>${this._selfTestHtml()}</div>
            </div>
            <div class="t-label" style="padding-top:6px">${tr("MCU-Last und -Wachzeit sind wie in Mainsail berechnet; einstellige Werte sind normal, kritisch wird die Last erst gegen 100 %.")}</div>
          </div>
        </details>
      </section>`;
  }

  _fwText() {
    const st = this._st(this._ents && this._ents.firmware);
    if (!st || st.state === "unavailable" || st.state === "unknown") return "—";
    const a = st.attributes || {};
    if (st.state === "on" && a.latest_version) {
      return `${esc(a.installed_version || "?")} <span style="color:var(--u1-warn)">→ ${esc(a.latest_version)} ${tr("verfügbar")}</span>`;
    }
    return `${esc(a.installed_version || "?")} · ${tr("aktuell")}`;
  }

  _selfTestHtml() {
    const t = this._selftest;
    if (!t) return "";
    if (t.busy) return `<div class="t-label">${tr("Prüfe …")}</div>`;
    if (t.error) return `<div class="t-label" style="color:var(--u1-error)">${esc(t.error)}</div>`;
    const icon = (ok) => (ok === true ? `<b style="color:var(--u1-ok)">✓</b>` : ok === false ? `<b style="color:var(--u1-error)">✗</b>` : `<b style="color:var(--u1-warn)">!</b>`);
    return (t.checks || []).map((c) => `<div class="st">${icon(c.ok)}<span>${esc(c.detail)}</span></div>`).join("");
  }

  async _runSelfTest() {
    const box = () => this.shadowRoot.querySelector("[data-selftest]");
    this._selftest = { busy: true };
    if (box()) box().innerHTML = this._selfTestHtml();
    try {
      const res = await this._hass.callService(DOMAIN, "self_test", { ...this._entryData(), language: LANG }, undefined, false, true);
      this._selftest = (res && res.response) || { error: tr("Keine Antwort") };
    } catch (err) {
      this._selftest = { error: (err && (err.message || err.error)) || String(err) };
    }
    if (box()) box().innerHTML = this._selfTestHtml();
  }

  /** Live subscription to Moonraker: connected since ... or disconnected (polling every x s). */
  _liveText() {
    const st = this._st(this._ents && this._ents.live);
    if (!st || st.state === "unavailable" || st.state === "unknown") return "—";
    const a = st.attributes || {};
    if (st.state === "on") {
      return `<span style="color:var(--u1-ok)">●</span> ${tr("verbunden")}${a.connected_since ? ` · ${tr("seit")} ${esc(fmtDate(a.connected_since))}` : ""}`;
    }
    const sec = a.poll_interval_s ? Math.round(a.poll_interval_s) : 10;
    return `<span style="color:var(--u1-warn)">●</span> ${tr("getrennt · Abfrage alle {n} s", { n: sec })}`;
  }

  _sectionStats() {
    const d = this._d;
    return `
      <section class="panel">
        <details ${this._cfg.compact ? "" : "open"}>
          <summary>
            <ha-icon icon="mdi:chart-box"></ha-icon>
            <span style="flex:1">${tr("Statistik")}</span>
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon>
          </summary>
          <div class="body rows">
            ${this._row(tr("Drucke gesamt"), `<span data-su1="tjobs">${num(d.totalsJobs, 0)}</span>`)}
            ${this._row(tr("Druckzeit gesamt"), `<span data-su1="ttime">${esc(d.totalsTime)}</span>`)}
            ${this._row(tr("Längster Druck"), `<span data-su1="tlong">${esc(d.longest)}</span>`)}
            ${this._row(tr("Filament gesamt"), `<span data-su1="tfil">${num(d.totalsFilament, 1, "m")}</span>`)}
            ${d.usage ? this._usageRows() : ""}
            ${d.tc ? this._toolChangeRows() : ""}
          </div>
        </details>
      </section>`;
  }

  _usageRows() {
    const u = this._d.usage;
    const e = this._ents;
    return [
      u.hasEnergy ? this._row(u.inProgress ? tr("Strom aktueller Druck") : tr("Strom letzter Druck"), `<span data-su1="uenergy">${num(u.energy, 2, "kWh")}</span>`, e.energyPrint) : "",
      u.hasCost ? this._row(u.inProgress ? tr("Kosten aktueller Druck") : tr("Kosten letzter Druck"), `<span data-su1="ucost">${fmtEuro(u.cost)}</span>`, e.costPrint) : "",
    ].join("");
  }

  _sectionMaintenance() {
    const items = this._d.maint;
    if (!items || !items.length) return "";
    const rows = items.map((m) => {
      const pct = Math.min(100, m.progress || 0);
      const tone = m.due ? "error" : pct >= 80 ? "warn" : "";
      const used = m.firmware ? `${fmtInt(m.used)} / ${fmtInt(m.interval)} ${tr("Wechsel")}`
        : m.used_h === null || m.used_h === undefined ? "—" : `${num(m.used_h, 0)} / ${m.interval_h} h`;
      const left = m.firmware ? "" : m.due ? tr("fällig") : m.remaining_h !== null && m.remaining_h !== undefined
        ? tr("noch {h} h", { h: Math.round(m.remaining_h) }) : "";
      return `
        <div class="m-item" data-due="${m.due ? 1 : 0}">
          <div class="m-top">
            <span class="m-name">${esc(tr(MAINT_LABELS[m.key] || m.key))}</span>
            <span class="t-label">${esc(used)}${left ? ` · ${esc(left)}` : ""}</span>
            ${m.firmware ? "" : `<button class="icon ghost" data-maint="${esc(m.key)}" title="${tr("Erledigt")}"><ha-icon icon="mdi:check"></ha-icon></button>`}
          </div>
          <div class="track" data-tone="${tone}"><i style="width:${pct}%"></i></div>
        </div>`;
    }).join("");
    const due = items.filter((m) => m.due).length;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:wrench-clock"></ha-icon>
          <span class="panel-title">${tr("Wartung")}</span>
          ${due ? `<span class="chip sm" data-tone="error" style="margin-left:auto">${tr("{n} fällig", { n: due })}</span>` : ""}
        </div>
        <div class="m-list">${rows}</div>
        <div class="t-label">${tr("Gezählt in Druckstunden. Intervalle in den Optionen der Integration.")}</div>
        ${this._backupLine()}
      </section>`;
  }

  /** Config backup: last snapshot and a "back up now" button. */
  _backupLine() {
    const b = this._d.backup;
    if (!b || !b.enabled) return "";
    const when = b.saved_at ? fmtDate(b.saved_at) : tr("noch keine");
    const info = [when, b.files ? tr(b.files === 1 ? "{n} Datei" : "{n} Dateien", { n: b.files }) : "", b.status === "error" ? tr("Fehler") : ""]
      .filter(Boolean).join(" · ");
    return `
        <div class="m-item" data-backup>
          <div class="m-top">
            <span class="m-name">${tr("Drucker-Konfiguration gesichert")}</span>
            <span class="t-label" title="${esc(b.folder || "")}">${esc(info)}</span>
            <button class="icon ghost" data-act="backup_config" title="${tr("Jetzt sichern")}"><ha-icon icon="mdi:content-save-cog-outline"></ha-icon></button>
          </div>
        </div>`;
  }

  _togglePower() {
    const p = this._d && this._d.power;
    if (!p || !p.available || p.shuttingDown || p.poweringOn) return;
    if (p.on) {
      if (this._d.active) {
        alert(tr("Der Drucker druckt gerade. Druck erst beenden oder abbrechen."));
        return;
      }
      if (!confirm(tr("Drucker herunterfahren und ausschalten?"))) return;
      this._hass.callService(DOMAIN, "power_off", this._entryData(), undefined, false).catch((err) => {
        const msg = (err && err.message) || String(err);
        // Crashed printer: does not answer but still counts as printing.
        if (!this._d.online && /druckt gerade/.test(msg)
          && confirm(`${msg}\n\n${tr("Der Drucker antwortet nicht. Trotzdem ausschalten?")}`)) {
          this._hass.callService(DOMAIN, "power_off", { ...this._entryData(), force: true });
        } else {
          alert(msg);
        }
      });
    } else {
      this._hass.callService(DOMAIN, "power_on", this._entryData());
    }
  }

  _toolChangeRows() {
    const tc = this._d.tc;
    const e = this._ents;
    return [
      this._row(tr("Werkzeugwechsel gesamt"), `<span data-su1="tctotal">${fmtInt(tc.total)}</span>`, e.toolChanges),
      this._row(tc.inProgress ? tr("Wechsel aktueller Druck") : tr("Wechsel letzter Druck"),
        `<span data-su1="tcprint">${this._tcPrintText(tc)}</span>`, e.toolChangesPrint),
      tc.heads.length ? this._row(tr("Wechsel je Kopf"), `<span data-su1="tcheads">${this._tcHeadsText(tc)}</span>`, e.toolChanges) : "",
      tc.threshold && tc.since !== null
        ? this._row(tr("Seit Wartung (max.)"), `<span data-su1="tcmaint">${this._tcMaintText(tc)}</span>`, e.toolChanges) : "",
    ].join("");
  }

  _tcPrintText(tc) {
    if (tc.print === null) return "—";
    const res = { complete: tr("fertig"), cancelled: tr("abgebrochen"), error: tr("Fehler") }[tc.result];
    return `${fmtInt(tc.print)}${!tc.inProgress && res ? ` <span class="tgt">(${res})</span>` : ""}`;
  }

  _tcHeadsText(tc) {
    // The row already says "per head": show custom names, else just the number like on the printer
    const own = (this._cfg.toolheads || []).map((t) => t && t.name);
    return tc.heads.map((h) => `${esc(own[h.index] || String(h.index + 1))}: ${fmtInt(h.switches)}`).join(" · ");
  }

  _tcMaintText(tc) {
    const warn = tc.since >= tc.threshold * 0.9;
    const txt = `${fmtInt(tc.since)} / ${fmtInt(tc.threshold)}`;
    return warn ? `<span style="color:var(--u1-warn, #f9a825)">${txt}</span>` : txt;
  }
};
