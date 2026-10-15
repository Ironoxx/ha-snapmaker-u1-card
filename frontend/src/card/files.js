/** Files tab: file grid, search/folders, queue and upload. */

import { DOMAIN } from "../const.js";
import { esc, fmtMin } from "../format.js";
import { tr } from "../i18n.js";

export const FilesMixin = (Base) => class extends Base {
  _sectionFiles() {
    const d = this._d;
    const head = (extra = "") => `
      <div class="panel-head">
        <ha-icon icon="mdi:file-document-multiple-outline"></ha-icon>
        <span class="panel-title">${tr("Dateien")}</span>${extra}
      </div>`;

    if (!d.files) {
      return `<section class="panel">${head()}
          <div class="t-label">${tr("Die Integration <b>Snapmaker U1 Card</b> ist nicht eingerichtet.")}
          ${tr("Einstellungen → Geräte &amp; Dienste → Integration hinzufügen → „Snapmaker U1 Card“.")}</div>
        </section>`;
    }

    const off = !d.online;
    const upload = `<button class="icon outline" data-act="upload" title="${tr("Datei hochladen")}"
        ${off ? "disabled" : ""}><ha-icon icon="mdi:upload"></ha-icon></button>
      <input type="file" accept=".gcode,.3mf" data-upload hidden />`;
    const refresh = `<button class="icon outline" data-act="refresh_files" title="${tr("Neu laden")}"
      style="margin-left:auto"><ha-icon icon="mdi:refresh"></ha-icon></button>`;
    const up = this._uploadLine();
    if (!d.files.length) {
      return `<section class="panel">${head(refresh + upload)}${up}
          <div class="t-label">${tr("Keine Druckdateien auf dem Drucker.")}</div></section>`;
    }

    const cards = d.files.map((f) => {
      const folder = f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) : "";
      const meta = [];
      if (f.time) meta.push(fmtMin(f.time / 60));
      if (f.weight) meta.push(`${Math.round(f.weight)} g`);
      else if (f.filament) meta.push(`${f.filament} m`);
      const thumb = f.thumb
        ? `<img src="${esc(f.thumb)}" alt="" loading="lazy" />`
        : `<ha-icon icon="mdi:file-document-outline"></ha-icon>`;
      const dots = (f.filaments || []).filter((x) => x.used).slice(0, 8)
        .map((x) => `<i style="background:${esc(x.color || "var(--u1-outline)")}" title="${esc(x.type || "")}"></i>`)
        .join("");
      return `
        <button class="file" data-print="${esc(f.path)}" title="${esc(f.path)}"
          data-fname="${esc((f.name + " " + f.path).toLowerCase())}" data-folder="${esc(folder)}"
          data-ftime="${Number(f.time) || 0}" data-fmod="${Number(f.modified) || 0}">
          <span class="file-thumb">${thumb}</span>
          <span class="file-name">${esc(f.name)}</span>
          ${dots ? `<span class="file-dots">${dots}</span>` : ""}
          <span class="file-meta">${meta.join(" · ") || "—"}</span>
        </button>`;
    }).join("");

    return `
      <section class="panel span2">
        ${head(`<span class="t-label" style="margin-left:auto">${tr("{n} neueste", { n: d.files.length })}</span>${refresh.replace('style="margin-left:auto"', "")}${upload}`)}
        ${up}
        ${d.active ? `<div class="t-label">${tr("Der Drucker druckt. Antippen, um einen Auftrag in die Warteschlange zu stellen.")}</div>` : ""}
        ${this._fileTools()}
        <div class="files">${cards}</div>
        <div class="files-more" data-fmore></div>
      </section>`;
  }

  /** Search, sort, folders. Filters the tiles in the DOM without a rebuild (focus stays). */
  _fileTools() {
    const all = this._allFiles();
    const folders = [...new Set(all.map((f) => (f.path.includes("/") ? f.path.split("/")[0] : "")).filter(Boolean))].sort();
    const fs = this._fstate || (this._fstate = { q: "", sort: "new", folder: "" });
    const chips = folders.length ? `<div class="fchips">
        <button class="chip sm" data-ffolder="" aria-pressed="${fs.folder === ""}">${tr("Alle")}</button>
        ${folders.map((f) => `<button class="chip sm" data-ffolder="${esc(f)}" aria-pressed="${fs.folder === f}"><ha-icon icon="mdi:folder-outline"></ha-icon>${esc(f)}</button>`).join("")}
      </div>` : "";
    return `<div class="ftools">
        <input type="search" data-fsearch placeholder="${tr("Suchen ({n} Dateien)", { n: all.length || (this._d.files || []).length })}" value="${esc(fs.q)}" />
        <select data-fsort aria-label="${tr("Sortierung")}">
          ${[["new", "Neueste"], ["name", "Name"], ["time", "Druckzeit"]].map(([v, l]) => `<option value="${v}" ${fs.sort === v ? "selected" : ""}>${tr(l)}</option>`).join("")}
        </select>
      </div>${chips}`;
  }

  _allFiles() {
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const a = st && st.attributes && st.attributes.all;
    return Array.isArray(a) ? a : [];
  }

  _filterFiles() {
    const r = this.shadowRoot && this.shadowRoot.getElementById("u1card");
    const grid = r && r.querySelector(".files");
    if (!grid) return;
    const fs = this._fstate || { q: "", sort: "new", folder: "" };
    const q = fs.q.trim().toLowerCase();
    const tiles = [...grid.querySelectorAll("button.file")];
    const inFolder = (folder) => !fs.folder || folder === fs.folder || folder.startsWith(fs.folder + "/");
    tiles.forEach((b) => { b.hidden = !(inFolder(b.dataset.folder || "") && (!q || b.dataset.fname.includes(q))); });
    const key = { new: (b) => -Number(b.dataset.fmod), name: (b) => b.dataset.fname, time: (b) => Number(b.dataset.ftime) }[fs.sort];
    tiles.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0)).forEach((b) => grid.appendChild(b));
    // Matches among older files (without preview), loaded on click
    const more = r.querySelector("[data-fmore]");
    if (!more) return;
    const shown = new Set(tiles.map((b) => b.dataset.print));
    const hits = q || fs.folder ? this._allFiles().filter((f) => !shown.has(f.path)
      && inFolder(f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) : "")
      && (!q || f.path.toLowerCase().includes(q))).slice(0, 20) : [];
    more.innerHTML = hits.length ? `<div class="t-label">${tr("Ältere Dateien")}</div>` + hits.map((f) =>
      `<button class="ghost" data-fopen="${esc(f.path)}"><ha-icon icon="mdi:file-document-outline"></ha-icon>${esc(f.path)}</button>`).join("") : "";
    more.querySelectorAll("[data-fopen]").forEach((b) => b.addEventListener("click", () => this._openOlder(b.dataset.fopen)));
  }

  async _openOlder(path) {
    try {
      const res = await this._hass.callService(DOMAIN, "file_details", { path, ...this._entryData() }, undefined, false, true);
      const file = res && res.response && res.response.file;
      if (!file) return;
      (this._extraFiles || (this._extraFiles = {}))[path] = file;
      this._openPrint(path);
    } catch (err) {
      alert((err && (err.message || err.error)) || String(err));
    }
  }

  _sectionQueue() {
    const jobs = this._d.queue;
    if (!jobs || !jobs.length) return "";
    const d = this._d;
    const slots = this._slots() || [];
    const canStart = !d.active && (d.online || !!(d.power && d.power.autoOn));
    const items = jobs.map((j, i) => {
      const dots = Object.values(j.mapping || {}).map((sl) => {
        const slot = slots[Number(sl)];
        return `<i style="background:${esc(slot && slot.loaded && slot.color ? slot.color : "var(--u1-outline)")}"></i>`;
      }).join("");
      const opts = [
        j.timelapse ? `<ha-icon icon="mdi:filmstrip" title="${tr("Zeitraffer")}"></ha-icon>` : "",
        j.bed_leveling ? `<ha-icon icon="mdi:grid" title="${tr("Bettnivellierung")}"></ha-icon>` : "",
        Array.isArray(j.pause_layers) && j.pause_layers.length ? `<span>${tr("Pause vor {l}", { l: j.pause_layers.join(", ") })}</span>` : "",
      ].join("");
      return `
        <div class="q-item" data-first="${i === 0 ? 1 : 0}">
          <span class="q-pos">${i + 1}</span>
          <span class="hist-thumb">${j.thumb ? `<img src="${esc(j.thumb)}" alt="" loading="lazy" />` : `<ha-icon icon="mdi:file-document-outline"></ha-icon>`}</span>
          <div class="hist-main">
            <div class="hist-name" title="${esc(j.file)}">${esc(j.name || j.file)}</div>
            <div class="q-meta">${dots ? `<span class="file-dots">${dots}</span>` : ""}${opts}</div>
          </div>
          <div class="q-btns">
            ${i === 0 ? `<button class="filled" data-q="start" data-job="${esc(j.id)}" ${canStart ? "" : "disabled"}>
              <ha-icon icon="mdi:play"></ha-icon>${tr("Starten")}</button>` : `
              <button class="icon ghost" data-q="move" data-job="${esc(j.id)}" data-pos="${i - 1}" title="${tr("Nach oben")}"><ha-icon icon="mdi:arrow-up"></ha-icon></button>`}
            <button class="icon ghost" data-q="remove" data-job="${esc(j.id)}" title="${tr("Entfernen")}"><ha-icon icon="mdi:close"></ha-icon></button>
          </div>
        </div>`;
    }).join("");
    return `
      <section class="panel span2 span3">
        <div class="panel-head">
          <ha-icon icon="mdi:tray-full"></ha-icon>
          <span class="panel-title">${tr("Warteschlange")}</span>
          <span class="t-label" style="margin-left:auto">${tr("{n} Aufträge", { n: jobs.length })}</span>
        </div>
        ${d.active ? `<div class="t-label">${tr("Startet nicht von selbst: nach dem Druck das Bett räumen und hier starten.")}</div>` : ""}
        <div class="q-list">${items}</div>
      </section>`;
  }

  async _queueAction(action, jobId, pos) {
    if (action === "remove") return this._call("queue_remove", { job_id: jobId });
    if (action === "move") return this._call("queue_move", { job_id: jobId, position: pos });
    if (action === "start") {
      const job = (this._d.queue || []).find((j) => j.id === jobId);
      const name = (job && (job.name || job.file)) || "";
      if (!confirm(tr("{name} starten? Druckbett ist leer und der Drucker frei?", { name }))) return;
      if (await this._call("queue_start", { job_id: jobId })) this._toast(tr("Druck gestartet: {name}", { name }));
    }
  }

  // ── Upload ──────────────────────────────────────────────────────────────
  _uploadLine() {
    const u = this._up;
    if (!u) return "";
    if (u.error) {
      return `<div class="dlg-error"><ha-icon icon="mdi:alert-circle"></ha-icon>${esc(u.name)}: ${esc(u.error)}</div>`;
    }
    return `<div class="upl">
        <ha-icon icon="${u.done ? "mdi:check-circle" : "mdi:upload"}"></ha-icon>
        <span class="upl-name">${esc(u.name)}</span>
        <div class="track"><i data-su1="uplbar" style="width:${u.pct}%"></i></div>
        <span class="mono" data-su1="uplpct">${u.done ? tr("fertig") : `${u.pct} %`}</span>
      </div>`;
  }

  _upload(file) {
    const entry = this._entryData().config_entry_id;
    if (!entry || !this._hass) return;
    if (!/\.(gcode|3mf)$/i.test(file.name)) { alert(tr("Nur .gcode- und .3mf-Dateien.")); return; }
    this._up = { name: file.name, pct: 0, done: false, error: null };
    this._renderKey = null; this._render();
    const rerender = () => { this._renderKey = null; this._render(); };
    const send = (token) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `/api/${DOMAIN}/upload/${entry}`);
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable || !this._up) return;
        this._up.pct = Math.min(99, Math.round((e.loaded / e.total) * 100));
        const root = this.shadowRoot.getElementById("u1card");
        const bar = root && root.querySelector('[data-su1="uplbar"]');
        const pct = root && root.querySelector('[data-su1="uplpct"]');
        if (bar) bar.style.width = `${this._up.pct}%`;
        if (pct) pct.textContent = `${this._up.pct} %`;
      };
      xhr.onload = () => {
        let body = {};
        try { body = JSON.parse(xhr.responseText || "{}"); } catch (e) { /* no JSON */ }
        if (xhr.status >= 200 && xhr.status < 300) {
          this._up = { name: file.name, pct: 100, done: true, error: null };
          this._afterUpload = { path: body.file, until: Date.now() + 30000 };
          this._toast(tr("Hochgeladen: {name}", { name: file.name }));
          setTimeout(() => { if (this._up && this._up.done) { this._up = null; rerender(); } }, 4000);
        } else {
          this._up = { name: file.name, pct: 0, done: false, error: body.message || `HTTP ${xhr.status}` };
        }
        rerender();
        this._checkAfterUpload();
      };
      xhr.onerror = () => {
        this._up = { name: file.name, pct: 0, done: false, error: tr("Verbindung abgebrochen") };
        rerender();
      };
      const form = new FormData();
      form.append("file", file, file.name);
      xhr.send(form);
    };
    const auth = this._hass.auth;
    const go = () => send(auth && auth.data ? auth.data.access_token : "");
    if (auth && auth.expired && typeof auth.refreshAccessToken === "function") auth.refreshAccessToken().then(go, go);
    else go();
  }

  /** After the upload, open the print dialog as soon as the file is listed. */
  _checkAfterUpload() {
    const a = this._afterUpload;
    if (!a || this._dlg) return;
    if (Date.now() > a.until) { this._afterUpload = null; return; }
    if ((this._d.files || []).some((f) => f.path === a.path)) {
      this._afterUpload = null;
      this._openPrint(a.path);
    }
  }
};
