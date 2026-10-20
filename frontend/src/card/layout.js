/** Card frame: header, power chip, alerts, tabs and section layout. */

import { CARD_VERSION, OFFLINE_SECTIONS, SECTIONS, TABLET_SIDE, TABS, TAB_STORE } from "../const.js";
import { esc, num } from "../format.js";
import { LANG, tr } from "../i18n.js";

/** Compares "1.2.10" and "1.3.0" numerically; -1, 0 or 1. */
export function cmpVersion(a, b) {
  const pa = String(a).split(/[.+-]/).map((x) => parseInt(x, 10) || 0);
  const pb = String(b).split(/[.+-]/).map((x) => parseInt(x, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d) return d > 0 ? 1 : -1;
  }
  return 0;
}

export const LayoutMixin = (Base) => class extends Base {
  _head() {
    const d = this._d;
    const tone = this._statusTone();
    const chipTone = { active: "active", warn: "warn", error: "error", ok: "ok" }[tone] || "";
    return `
      <header class="head">
        <div class="head-icon" data-tone="${tone === "error" ? "error" : ""}">
          <ha-icon icon="mdi:printer-3d-nozzle" style="--mdc-icon-size:26px"></ha-icon>
        </div>
        <div class="head-text">
          <div class="head-brand">${esc(this._cfg.printer_brand)}</div>
          <div class="t-title">${esc(this._cfg.printer_name)}</div>
        </div>
        <div class="chips">
          ${!d.online && d.power && d.power.available && !d.power.on ? "" : `<span class="chip ${d.printing ? "live" : ""}" data-tone="${chipTone}">
            <span class="dot"></span><span data-su1="status">${this._statusLabel()}</span>
          </span>`}
          ${d.power ? this._powerChip() : ""}
          ${this._cfg.network_tracker ? `<span class="chip" data-tone="${d.network === "home" ? "" : "error"}">
            <ha-icon icon="mdi:wifi" style="--mdc-icon-size:16px"></ha-icon>
            ${d.network === "home" ? tr("Verbunden") : tr("Getrennt")}
          </span>` : ""}
        </div>
      </header>`;
  }

  _powerChip() {
    const p = this._d.power;
    return `<button class="chip pwr" data-act="power" data-su1="pwr" ${this._powerAttrs(p)}>${this._powerLabel(p)}</button>`;
  }

  _powerAttrs(p) {
    const busy = p.shuttingDown || p.poweringOn;
    const tone = busy ? "warn" : p.on ? "ok" : "";
    const title = !p.available ? tr("Netzschalter nicht erreichbar")
      : busy ? tr("Bitte warten") : p.on ? tr("Herunterfahren und ausschalten") : tr("Einschalten");
    return `data-tone="${tone}" title="${title}" aria-label="${title}" ${busy || !p.available ? "disabled" : ""}`;
  }

  _powerLabel(p) {
    const text = p.shuttingDown ? tr("Fährt herunter …") : p.poweringOn ? tr("Startet …")
      : !p.available ? "—" : p.on ? (p.watts !== null ? num(p.watts, 0, "W") : tr("An")) : tr("Aus");
    const icon = p.shuttingDown || p.poweringOn ? "mdi:loading" : "mdi:power";
    return `<ha-icon icon="${icon}" class="${p.shuttingDown || p.poweringOn ? "spin" : ""}"
      style="--mdc-icon-size:16px"></ha-icon><span>${text}</span>`;
  }

  _body() {
    const d = this._d;
    if (!d.online) {
      const p = d.power;
      const off = p && p.available && !p.on;
      const msg = p && p.shuttingDown
        ? ["mdi:power-sleep", tr("Drucker fährt herunter"), tr("Der Strom wird abgeschaltet, sobald er heruntergefahren ist.")]
        : p && p.poweringOn
          ? ["mdi:power", tr("Drucker startet"), tr("Das dauert etwa 1–2 Minuten.")]
          : off
            ? ["mdi:power-plug-off", tr("Drucker ist aus"),
              p.autoOn ? tr("Zum Drucken einfach eine Datei wählen, er schaltet sich selbst ein.") : ""]
            : ["mdi:lan-disconnect", tr("Drucker nicht erreichbar"), tr("Die Moonraker-Integration meldet keinen Status.")];
      const btn = off ? `<button class="filled" data-act="power"><ha-icon icon="mdi:power"></ha-icon>${tr("Einschalten")}</button>` : "";
      const avail = OFFLINE_SECTIONS.filter((s) => this._cfg.show.includes(s)
        && (s !== "files" || (p && p.autoOn)));
      const extra = this._layout(avail);
      return `${this._head()}
        <div class="offline">
          <ha-icon icon="${msg[0]}" class="${p && (p.shuttingDown || p.poweringOn) ? "spin-slow" : ""}"></ha-icon>
          <div class="t-title">${msg[1]}</div>
          ${msg[2] ? `<div class="t-body">${msg[2]}</div>` : ""}
          ${btn}
        </div>
        ${extra}`;
    }
    return `
      ${this._head()}
      ${this._versionNotice()}
      ${this._alerts()}
      ${this._layout(this._cfg.show)}
      ${this._dangerZone()}`;
  }

  /**
   * Card and integration out of step: usually the browser or the Companion
   * app still runs the old card from its cache after an update, or Home
   * Assistant has not been restarted yet.
   */
  _versionNotice() {
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const v = st && st.attributes && st.attributes.version;
    if (!v || v === CARD_VERSION) return "";
    const newer = cmpVersion(v, CARD_VERSION) > 0;
    const text = newer
      ? tr("Die Integration ist auf {v}, im Browser läuft noch die Karte {c}. Seite neu laden; hilft das nicht, den Browser-Cache leeren (Companion App: Einstellungen → Companion App → Fehlerbehebung → Frontend-Cache zurücksetzen).", { v, c: CARD_VERSION })
      : tr("Die Karte ist auf {c}, die Integration noch auf {v}. Home Assistant neu starten, damit das Update vollständig aktiv wird.", { v, c: CARD_VERSION });
    return `<div class="alert" data-level="warn">
        <ha-icon icon="mdi:update"></ha-icon>
        <div><div class="alert-text">${newer ? tr("Veraltete Karte im Browser-Cache") : tr("Neustart von Home Assistant nötig")}</div>
        <div class="t-label">${esc(text)}</div></div>
        ${newer ? `<button class="tonal" data-reload>${tr("Neu laden")}</button>` : ""}
      </div>`;
  }

  /** Open firmware messages in plain language, visible on every tab. */
  _alerts() {
    const errs = this._d.errors || [];
    if (!errs.length) return "";
    const key = LANG === "de" ? "de" : "en";
    return `<div class="alerts">${errs.map((e) => `
        <div class="alert" data-level="${e.level >= 3 ? "error" : "warn"}" title="${esc(`${e.key} · ${e.message || ""}`)}">
          <ha-icon icon="${e.level >= 3 ? "mdi:alert-octagon" : "mdi:alert"}"></ha-icon>
          <div><div class="alert-text">${esc(this._errText(e))}</div>
          ${e.hint && e.hint[key] ? `<div class="t-label">${esc(e.hint[key])}</div>` : ""}</div>
        </div>`).join("")}</div>`;
  }

  _section(name) {
    switch (name) {
      case "stage": return this._sectionStage();
      case "job": return this._sectionJob();
      case "files": return this._sectionFiles();
      case "toolheads": return this._sectionHeads();
      case "climate": return this._sectionClimate();
      case "motion": return this._sectionMotion();
      case "system": return this._sectionSystem();
      case "stats": return this._sectionStats();
      case "history": return this._sectionHistory();
      case "timelapse": return this._sectionTimelapse();
      case "queue": return this._sectionQueue();
      case "charts": return this._sectionCharts();
      case "maintenance": return this._sectionMaintenance();
      case "layer": return this._sectionLayer();
      default: return "";
    }
  }

  /** Visible tabs for the given sections. */
  _tabs(sections) {
    return TABS.map((t) => ({ ...t, parts: t.sections.filter((s) => sections.includes(s)) }))
      .filter((t) => t.parts.length);
  }

  _activeTab(tabs) {
    return tabs.find((t) => t.id === this._tab) ? this._tab : tabs.length ? tabs[0].id : null;
  }

  /** Sections as tabs, stacked (layout: scroll) or camera beside the tabs (layout: tablet). */
  _layout(sections) {
    if (!sections.length) return "";
    if (this._cfg.layout === "scroll") {
      // Order as before: stage job files toolheads ...
      return `<div class="layout">${SECTIONS.filter((s) => sections.includes(s)).map((s) => this._section(s)).join("")}</div>`;
    }
    if (this._cfg.layout === "tablet") {
      // Tablet / wall monitor: camera and job stay visible on the left, the
      // remaining tabs on the right. Narrow screens stack both columns.
      const side = TABLET_SIDE.filter((s) => sections.includes(s));
      const rest = sections.filter((s) => !side.includes(s));
      if (side.length) {
        return `<div class="tablet">
          <div class="tablet-side">${side.map((s) => this._section(s)).join("")}</div>
          ${rest.length ? `<div class="tablet-main">${this._tabbed(rest)}</div>` : ""}
        </div>`;
      }
    }
    return this._tabbed(sections);
  }

  _tabbed(sections) {
    const tabs = this._tabs(sections);
    const cur = this._activeTab(tabs);
    const nav = tabs.length > 1 ? `<nav class="tabs" role="tablist">${tabs.map((t) => `
        <button type="button" role="tab" class="tab" data-tab="${t.id}" aria-selected="${t.id === cur}">
          <ha-icon icon="${t.icon}"></ha-icon><span>${tr(t.label)}</span>
        </button>`).join("")}</nav>` : "";
    const panes = tabs.map((t) => `<div class="layout" role="tabpanel" data-pane="${t.id}" ${t.id === cur ? "" : "hidden"}>
        ${t.parts.map((s) => this._section(s)).join("")}</div>`).join("");
    return nav + panes;
  }

  _selectTab(id) {
    this._tab = id;
    try { window.localStorage.setItem(TAB_STORE, id); } catch (e) { /* no storage */ }
    const r = this.shadowRoot.getElementById("u1card");
    if (!r) return;
    r.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === id)));
    r.querySelectorAll("[data-pane]").forEach((p) => { p.hidden = p.dataset.pane !== id; });
    this._tickCamera();
    this._tickTemps();  // right away instead of up to 10 s of "no data"
  }
};
