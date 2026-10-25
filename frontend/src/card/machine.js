/** Machine controls: bed mesh heatmap, top cover, G-code console and picking/parking heads. */

import { DOMAIN } from "../const.js";
import { esc, num } from "../format.js";
import { tr } from "../i18n.js";

// Console: entries kept in the card (per browser tab) and sent commands for the arrow keys
const CONSOLE_KEEP = 30;
const COVER_MODES = {
  idle: "Leerlauf", cool: "Kammer kühlen", preheat: "Kammer vorheizen", hot: "Heiße Kammer", unknown: "Unbekannt",
};

/** Signed millimetres with two decimals for the mesh cells ("+0.05", "−0.12"). */
export function meshLabel(v) {
  const r = Math.round(v * 100) / 100;
  if (r === 0) return "0.00";
  return `${r > 0 ? "+" : "−"}${Math.abs(r).toFixed(2)}`;
}

export const MachineMixin = (Base) => class extends Base {
  // ── Bed mesh ─────────────────────────────────────────────────────────────
  _sectionMesh() {
    const m = this._d.mesh;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:grid"></ha-icon>
          <span class="panel-title">${tr("Bettnivellierung")}</span>
          ${m && m.profile ? `<span class="t-label" style="margin-left:auto">${tr("Profil {p}", { p: esc(m.profile) })}</span>` : ""}
        </div>
        ${m ? `
          <div class="stats">
            ${this._stat(tr("Spanne (mm)"), num(m.range, 3), "", tr("Höchster minus tiefster Messpunkt"))}
            ${this._stat(tr("Tiefster (mm)"), num(m.min, 3))}
            ${this._stat(tr("Höchster (mm)"), num(m.max, 3))}
            ${this._stat(tr("Messpunkte"), `${m.cols} × ${m.rows}`)}
          </div>
          <div class="mesh">${this._meshSvg(m)}</div>`
        : `<div class="t-label">${tr("Kein Höhenprofil geladen. Es entsteht bei einem Druckstart mit Bettnivellierung.")}</div>`}
      </section>`;
  }

  /**
   * Heatmap of the probed points. Rows run along Y with the first row at the
   * front (Y min), so the front is drawn at the bottom like looking into the
   * printer. Colour: red above, blue below zero; strength relative to the
   * largest deviation (at least 0.05 mm, so a flat bed stays pale).
   */
  _meshSvg(m) {
    const rows = m.matrix || [];
    if (!rows.length) return "";
    const cols = m.cols || rows[0].length;
    const cell = 34, gap = 2, padL = 4, padB = 16;
    const W = padL + cols * (cell + gap), H = rows.length * (cell + gap) + padB;
    const lim = Math.max(0.05, Math.abs(m.min), Math.abs(m.max));
    const labels = cols <= 10;
    const cells = rows.map((row, ri) => row.map((v, ci) => {
      const x = padL + ci * (cell + gap);
      const y = (rows.length - 1 - ri) * (cell + gap);
      const a = Math.min(1, Math.abs(v) / lim);
      const color = v >= 0 ? "#e53935" : "#1e88e5";
      return `<g><title>${esc(`X${ci + 1} Y${ri + 1}: ${meshLabel(v)} mm`)}</title>
        <rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="4" class="mesh-cell"/>
        <rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="4" fill="${color}" fill-opacity="${(0.08 + a * 0.8).toFixed(2)}"/>
        ${labels ? `<text x="${x + cell / 2}" y="${y + cell / 2 + 4}" text-anchor="middle" class="mesh-val">${meshLabel(v)}</text>` : ""}
      </g>`;
    }).join("")).join("");
    return `<svg viewBox="0 0 ${W} ${H}" class="mesh-svg" role="img" aria-label="${tr("Höhenprofil des Druckbetts")}">
        ${cells}
        <text x="${W / 2}" y="${H - 3}" text-anchor="middle" class="tax">${tr("vorne")}</text>
      </svg>
      <div class="tlegend"><span><i style="background:#1e88e5"></i>${tr("tiefer")}</span><span><i style="background:#e53935"></i>${tr("höher")}</span></div>`;
  }

  // ── Top cover ────────────────────────────────────────────────────────────
  _coverPanel() {
    const c = this._d.cover;
    if (!c) return "";
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:air-filter"></ha-icon>
          <span class="panel-title">Top Cover</span>
          <span class="chip sm" data-su1="cvmode" title="${tr("Modus")}">${esc(this._coverMode(c.mode))}</span>
          ${this._lockBtn()}
        </div>
        <div class="stats">
          ${this._stat(tr("Kammer-Soll"), `<span data-su1="cvtarget">${num(c.desired_temp, 0, "°C")}</span>`)}
          ${this._stat(tr("Umluft (U/min)"), `<span data-su1="cvrpm">${num(c.inner_rpm, 0)}</span>`)}
          ${this._stat(tr("Filter-Laufzeit"), `<span data-su1="cvfilter">${num(c.filter_hours, 1, "h")}</span>`, "",
            tr("Betriebsstunden des Umluftlüfters (Filter)"))}
        </div>
        ${this._ents.coverExhaust ? this._slider({
          entity: this._ents.coverExhaust, label: tr("Abluftlüfter"), value: c.exhaust, unit: "%", presets: [0, 50, 100],
        }) : ""}
        ${this._ents.coverInner ? this._slider({
          entity: this._ents.coverInner, label: tr("Umluftlüfter"), value: c.inner, unit: "%", presets: [0, 50, 100],
        }) : ""}
        <div class="t-label">${tr("Während eines Drucks regelt die Firmware die Lüfter je nach Material selbst nach.")}</div>
      </section>`;
  }

  _coverMode(mode) { return tr(COVER_MODES[mode] || COVER_MODES.unknown); }

  // ── G-code console ───────────────────────────────────────────────────────
  _sectionConsole() {
    const d = this._d;
    return `
      <section class="panel">
        <div class="panel-head">
          <ha-icon icon="mdi:console-line"></ha-icon>
          <span class="panel-title">${tr("G-Code-Konsole")}</span>
          ${this._lockBtn()}
        </div>
        ${d.active ? `<div class="t-label">${tr("Während des Drucks nur Feineinstellungen: Temperaturen, Lüfter, Geschwindigkeit, Flussrate, Z-Versatz, Licht, Top Cover und Abfragen.")}</div>` : ""}
        <div class="con-log mono" data-conlog aria-live="polite">${this._consoleLog()}</div>
        <form class="con-form" data-conform data-lockable>
          <input name="script" data-conin autocomplete="off" autocapitalize="characters" spellcheck="false"
                 placeholder="${tr("z. B. M105")}" aria-label="G-Code" value="${esc(this._conDraft || "")}" />
          <button type="submit" class="tonal" aria-label="${tr("Senden")}"><ha-icon icon="mdi:send"></ha-icon></button>
        </form>
      </section>`;
  }

  _consoleLog() {
    const log = this._conLog || [];
    if (!log.length) return `<div class="t-label">${tr("Befehl eingeben, Antwort des Druckers erscheint hier.")}</div>`;
    return log.map((e) => `
      <div class="con-entry">
        <div class="con-cmd">› ${esc(e.script).replace(/\n/g, "<br>› ")}</div>
        ${e.pending ? `<div class="con-line t-label">${tr("Läuft …")}</div>` : ""}
        ${(e.lines || []).map((l) => `<div class="con-line">${esc(l)}</div>`).join("")}
        ${e.error ? `<div class="con-line con-err">${esc(e.error)}</div>` : ""}
        ${!e.pending && !e.error && !(e.lines || []).length ? `<div class="con-line t-label">ok</div>` : ""}
      </div>`).join("");
  }

  _showConsoleLog() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    const box = r && r.querySelector("[data-conlog]");
    if (!box) return;
    box.innerHTML = this._consoleLog();
    box.scrollTop = box.scrollHeight;
  }

  async _sendConsole(script) {
    const text = String(script || "").trim();
    if (!text) return;
    const hist = this._conHist || (this._conHist = []);
    if (hist[hist.length - 1] !== text) hist.push(text);
    if (hist.length > 50) hist.shift();
    this._conPos = hist.length;
    const entry = { script: text, pending: true, lines: [] };
    const log = this._conLog || (this._conLog = []);
    log.push(entry);
    if (log.length > CONSOLE_KEEP) log.shift();
    this._showConsoleLog();
    try {
      const res = await this._hass.callService(DOMAIN, "send_gcode", { script: text, ...this._entryData() },
        undefined, false, true);
      const out = (res && res.response) || {};
      entry.lines = out.responses || [];
      entry.error = out.ok === false ? out.error || tr("Fehler") : null;
    } catch (err) {
      entry.error = (err && (err.message || err.error)) || String(err);
    }
    entry.pending = false;
    this._showConsoleLog();
  }

  /** Console form, input history (arrow keys) and the draft surviving a rebuild. */
  _wireMachine(r) {
    const form = r.querySelector("[data-conform]");
    if (form) {
      const inp = form.querySelector("[data-conin]");
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        this._touchLock();
        const text = inp.value;
        inp.value = "";
        this._conDraft = "";
        this._sendConsole(text);
      });
      inp.addEventListener("input", () => { this._conDraft = inp.value; this._touchLock(); });
      inp.addEventListener("keydown", (e) => {
        const hist = this._conHist || [];
        if (!hist.length || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
        e.preventDefault();
        const pos = Math.max(0, Math.min(hist.length, (this._conPos ?? hist.length) + (e.key === "ArrowUp" ? -1 : 1)));
        this._conPos = pos;
        inp.value = hist[pos] || "";
        this._conDraft = inp.value;
      });
      const box = r.querySelector("[data-conlog]");
      if (box) box.scrollTop = box.scrollHeight;
    }
  }

  // ── Picking / parking heads (head dialog) ────────────────────────────────
  /** Block for the head dialog: state on the carriage and the pick/park button. */
  _headChangeBlock(idx, locked) {
    const states = this._d ? this._d.headStates : [];
    if (!states || !states.length) return "";
    const st = states[idx];
    const active = st === "active";
    const text = active ? tr("Auf dem Schlitten") : st === "parked" ? tr("Im Dock") : tr("Status unbekannt");
    return `<div class="t-label head-sub">${tr("Kopfwechsel")}</div>
      <div class="head-change">
        <span class="t-label"><ha-icon icon="${active ? "mdi:arrow-collapse-down" : "mdi:garage-variant"}"></ha-icon>${text}</span>
        <button type="button" class="tonal" data-headchange="${active ? "park" : "pick"}" ${locked ? "disabled" : ""}>
          <ha-icon icon="${active ? "mdi:arrow-collapse-up" : "mdi:arrow-collapse-down"}"></ha-icon>${active ? tr("Ablegen") : tr("Aufnehmen")}
        </button>
      </div>
      <div class="t-label">${tr("Fährt bei Bedarf vorher X/Y an.")}</div>`;
  }

  async _headChange(idx, action, btn) {
    const head = (this._d && this._d.heads[idx]) || { name: `E${idx}` };
    if (btn) { btn.disabled = true; btn.classList.add("busy"); }
    const ok = await this._call("tool_change", { head: idx + 1, action });
    if (btn) { btn.disabled = false; btn.classList.remove("busy"); }
    if (ok) this._toast(action === "park" ? tr("{head} abgelegt", { head: head.name }) : tr("{head} aufgenommen", { head: head.name }));
    return ok;
  }
};
