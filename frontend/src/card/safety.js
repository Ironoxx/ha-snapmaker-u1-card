/** Emergency stop (option emergency_stop: show | hold | hide) and the card's own confirm dialog. */

import { esc } from "../format.js";
import { tr } from "../i18n.js";

const HOLD_MS = 1000;

export const SafetyMixin = (Base) => class extends Base {
  _estopMode() {
    const m = this._cfg.emergency_stop;
    if (m === false || m === "hide") return "hide";
    return m === "hold" ? "hold" : "show";
  }

  /** Bottom bar with the emergency stop; empty when hidden. */
  _dangerZone() {
    const mode = this._estopMode();
    if (mode === "hide") return "";
    const hold = mode === "hold";
    const hint = hold
      ? tr("Not-Halt 1 s gedrückt halten. Klipper stoppt sofort, danach ist ein Neustart der Firmware nötig.")
      : tr("Not-Halt stoppt Klipper sofort. Ein Neustart der Firmware ist danach nötig.");
    return `
      <div class="danger-zone">
        <ha-icon icon="mdi:alert-octagon-outline" style="color:var(--u1-error)"></ha-icon>
        <span class="t-label">${hint}</span>
        <button class="danger${hold ? " hold" : ""}" data-estop="${mode}">
          <span class="hold-fill"></span><span>${tr("Not-Halt")}</span>
        </button>
      </div>`;
  }

  _wireEstop(root) {
    const btn = root.querySelector("[data-estop]");
    if (!btn) return;
    if (btn.dataset.estop !== "hold") {
      btn.addEventListener("click", async () => {
        if (await this._confirmAction({
          icon: "mdi:alert-octagon", tone: "error", title: tr("Not-Halt auslösen?"),
          text: tr("Klipper stoppt sofort, Heizungen und Motoren gehen aus. Danach ist ein Neustart der Firmware nötig."),
          ok: tr("Not-Halt"),
        })) this._press("emergency_stop");
      });
      return;
    }
    // Hold: fires after HOLD_MS without a dialog (no extra step in an emergency),
    // releasing or leaving the button earlier aborts.
    let timer = null;
    const stop = () => {
      if (timer) { clearTimeout(timer); timer = null; }
      btn.classList.remove("holding");
    };
    btn.addEventListener("pointerdown", (e) => {
      if (e.button !== undefined && e.button !== 0) return;
      stop();
      btn.classList.add("holding");
      timer = setTimeout(() => { timer = null; btn.classList.remove("holding"); this._press("emergency_stop"); }, HOLD_MS);
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => btn.addEventListener(ev, stop));
    btn.addEventListener("contextmenu", (e) => e.preventDefault());
    // Keyboard: Enter/Space opens the dialog instead (no hold possible)
    btn.addEventListener("keydown", async (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      if (await this._confirmAction({
        icon: "mdi:alert-octagon", tone: "error", title: tr("Not-Halt auslösen?"),
        text: tr("Klipper stoppt sofort, Heizungen und Motoren gehen aus. Danach ist ein Neustart der Firmware nötig."),
        ok: tr("Not-Halt"),
      })) this._press("emergency_stop");
    });
  }

  /**
   * Confirm dialog in the card style instead of window.confirm (looks the same
   * in the Companion app, the critical button is clearly coloured).
   * Resolves true on OK, false on cancel, Esc or the backdrop.
   */
  _confirmAction({ icon = "mdi:help-circle-outline", tone = "", title, text = "", ok, cancel }) {
    let dlg = this.shadowRoot.querySelector("dialog.u1confirm");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.className = "u1confirm";
      this.shadowRoot.appendChild(dlg);
    }
    if (dlg._resolve) dlg._resolve(false);
    dlg.dataset.tone = tone;
    dlg.setAttribute("aria-label", title);
    dlg.innerHTML = `
      <div class="dlg">
        <div class="confirm-head"><ha-icon icon="${esc(icon)}"></ha-icon><div class="dlg-title">${esc(title)}</div></div>
        ${text ? `<div class="t-body">${esc(text)}</div>` : ""}
        <div class="dlg-actions">
          <button class="outline" data-cf="no">${esc(cancel || tr("Abbrechen"))}</button>
          <button class="${tone === "error" ? "danger strong" : "filled"}" data-cf="yes">${esc(ok || "OK")}</button>
        </div>
      </div>`;
    return new Promise((resolve) => {
      const finish = (v) => {
        if (dlg._resolve !== finish) return;
        dlg._resolve = null;
        if (dlg.open) dlg.close();
        resolve(v);
      };
      dlg._resolve = finish;
      dlg.querySelector('[data-cf="yes"]').addEventListener("click", () => finish(true));
      dlg.querySelector('[data-cf="no"]').addEventListener("click", () => finish(false));
      dlg.onclick = (e) => { if (e.target === dlg) finish(false); };
      dlg.onclose = () => finish(false);
      dlg.showModal();
      // Focus on cancel: Enter does not trigger the critical action by accident
      const no = dlg.querySelector('[data-cf="no"]');
      if (no && no.focus) no.focus();
    });
  }
};
