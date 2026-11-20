/** Timelapse tab: videos on the printer and in the media archive. */

import { archiveName, esc, fmtDate } from "../format.js";
import { tr } from "../i18n.js";

export const TimelapseMixin = (Base) => class extends Base {
  _sectionTimelapse() {
    const tl = this._d.timelapses;
    if (!tl) return "";
    const a = tl.archive;
    const limit = this._cfg.timelapse_limit || 8;
    let body;
    let count;
    if (a) {
      // 2.4.0b4: one list. Backed-up videos (play always, also with the printer off) plus
      // the ones only on the printer, marked and playable only while it is on.
      const items = this._timelapseItems(tl, a).slice(0, limit);
      count = items.length;
      body = `${this._archiveStatus(a)}
        ${items.length ? `<div class="files">${items.map((it) => this._tlTile(it, tl.playable)).join("")}</div>`
          : `<div class="t-label">${tr("Keine Zeitraffer auf dem Drucker. Aufnahme im Druckdialog unter „Zeitraffer“ einschalten.")}</div>`}`;
    } else {
      count = tl.videos.length;
      body = tl.videos.length ? `<div class="files">${tl.videos.slice(0, limit).map((v, i) => this._tlTile({
        kind: "p", index: i, name: v.name, poster: v.poster_url || v.thumb_url,
        ts: v.recorded ? Date.parse(v.recorded) / 1000 : v.modified, size: v.size, title: v.path,
      }, true)).join("")}</div>`
        : `<div class="t-label">${tr("Keine Zeitraffer auf dem Drucker. Aufnahme im Druckdialog unter „Zeitraffer“ einschalten.")}</div>`;
    }
    return `
      <section class="panel span2">
        <details ${this._cfg.compact ? "" : "open"}>
          <summary>
            <ha-icon icon="mdi:filmstrip-box-multiple"></ha-icon>
            <span>${tr("Zeitraffer")}</span>
            ${count ? `<span class="t-label" style="margin-left:auto">${count}</span>` : ""}
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon>
          </summary>
          <div class="body">${body}</div>
        </details>
      </section>`;
  }

  /**
   * 2.4.0b4: backed-up videos and the ones only on the printer as one list, newest first.
   * A video in both places counts once, as the backup (same file name, see archive.py).
   */
  _timelapseItems(tl, a) {
    const backed = new Set((a.videos || []).map((v) => v.file));
    const items = (a.videos || []).map((v, i) => ({
      kind: "a", index: i, name: archiveName(v.file), poster: v.poster_url, ts: v.modified, size: v.size, title: v.file,
    }));
    tl.videos.forEach((v, i) => {
      const file = (v.path || "").split("/").pop();
      if (backed.has(file)) return;
      items.push({ kind: "p", index: i, name: v.name, poster: v.poster_url || v.thumb_url, title: v.path,
        ts: v.recorded ? Date.parse(v.recorded) / 1000 : v.modified, size: v.size, onlyPrinter: true });
    });
    return items.sort((x, y) => (y.ts || 0) - (x.ts || 0));
  }

  _tlTile(it, playable) {
    const off = it.kind === "p" && !playable;
    return `
        <button class="file tl" data-tlvid="${it.kind}:${it.index}" title="${esc(it.title || it.name)}" ${off ? 'aria-disabled="true" data-off="1"' : ""}>
          <span class="file-thumb tl-thumb">
            ${it.poster ? `<img src="${esc(it.poster)}" alt="" loading="lazy" />` : ""}
            <ha-icon icon="${off ? "mdi:power-plug-off" : "mdi:play-circle"}" class="tl-play"></ha-icon>
          </span>
          <span class="file-name">${esc(it.name)}</span>
          <span class="file-meta">${esc(fmtDate(it.ts ? new Date(it.ts * 1000).toISOString() : null))}${it.size ? ` · ${(it.size / 1048576).toFixed(0)} MB` : ""}</span>
          ${it.onlyPrinter ? `<span class="chip sm tl-where" title="${tr("Noch nicht in Home Assistant gesichert")}"><ha-icon icon="mdi:printer-3d"></ha-icon>${off ? tr("nur auf dem Drucker · Drucker aus") : tr("nur auf dem Drucker")}</span>` : ""}
        </button>`;
  }

  /** Tap on a timelapse tile of the merged list (2.4.0b4). */
  _tlOpen(ref) {
    const [kind, idx] = String(ref).split(":");
    if (kind === "a") return this._openArchive(Number(idx));
    return this._openVideo(Number(idx));
  }

  /** Backup status line with "back up now" (the videos themselves are in the merged list). */
  _archiveStatus(a) {
    const status = [
      a.busy ? tr("Sicherung läuft …") : a.last_backup ? tr("Zuletzt gesichert: {d}", { d: fmtDate(new Date(a.last_backup * 1000).toISOString()) }) : tr("Noch nichts gesichert."),
      a.keep > 0 ? (a.cleanup === "not_supported" ? tr("Löschen auf dem Drucker wird von der Firmware nicht unterstützt.")
        : tr("Auf dem Drucker bleiben die {n} neuesten.", { n: a.keep })) : null,
    ].filter(Boolean).join(" · ");
    return `
      <div class="arch-head">
        <ha-icon icon="mdi:folder-play-outline"></ha-icon>
        <span class="t-label">${tr("Gesichert in Medien")} (${a.count}) · ${esc(status)}</span>
        <button class="icon outline" data-act="backup" title="${tr("Jetzt sichern")}" ${a.busy ? "disabled" : ""}
          style="margin-left:auto"><ha-icon icon="${a.busy ? "mdi:loading" : "mdi:content-save-move-outline"}" class="${a.busy ? "spin" : ""}"></ha-icon></button>
      </div>
      ${(a.errors || []).length ? `<div class="t-label" style="color:var(--u1-error)">${a.errors.map(esc).join("<br>")}</div>` : ""}`;
  }

  /** Play a backed-up video via HA's media source (signed URL). */
  async _openArchive(index) {
    const a = this._d.timelapses && this._d.timelapses.archive;
    const v = a && a.videos[index];
    if (!v) return;
    this._showVideo(archiveName(v.file), fmtDate(new Date(v.modified * 1000).toISOString()), v.file,
      async () => {
        const res = await this._hass.callWS({ type: "media_source/resolve_media", media_content_id: v.media_id, expires: 3600 });
        return { url: res.url, poster: v.poster_url || "" };
      });
  }

  // Signed URL for the video proxy: <video>/<img> cannot send an
  // Authorization header. Signatures are valid for 1 h and are cached.
  async _signed(path) {
    this._sigs = this._sigs || new Map();
    const hit = this._sigs.get(path);
    if (hit && hit.until > Date.now()) return hit.url;
    const res = await this._hass.callWS({ type: "auth/sign_path", path, expires: 3600 });
    // HA returns the path decoded ('%23' becomes '#'). So only take the
    // signature and append it to the path we encoded ourselves.
    const q = res.path.indexOf("?");
    const url = q >= 0 ? path + res.path.slice(q) : res.path;
    this._sigs.set(path, { url, until: Date.now() + 50 * 60 * 1000 });
    return url;
  }

  _videoPath(v, file) {
    const tl = this._d.timelapses;
    return `${tl.url}/${encodeURIComponent(v.root)}/${file.split("/").map(encodeURIComponent).join("/")}`;
  }

  async _openVideo(index) {
    const tl = this._d.timelapses;
    const v = tl && tl.videos[index];
    if (!v) return;
    if (!tl.playable) {
      // The proxy would only hang while the printer is off.
      alert(tr("Der Drucker ist aus oder nicht erreichbar. Zeitraffer lassen sich erst nach dem Einschalten abspielen."));
      return;
    }
    this._showVideo(v.name, fmtDate(v.recorded), v.path.split("/").pop(), async () => ({
      url: await this._signed(this._videoPath(v, v.path)), poster: v.poster_url || v.thumb_url || "",
    }));
  }

  async _showVideo(title, sub, fileName, source) {
    const host = this.shadowRoot.getElementById("u1dlg");
    let dlg = host.querySelector("dialog.u1video");
    if (!dlg) {
      host.insertAdjacentHTML("beforeend", `<dialog class="u1dlg u1video" aria-label="${tr("Zeitraffer")}"></dialog>`);
      dlg = host.querySelector("dialog.u1video");
      // Stop the video when closing and release the connection
      dlg.addEventListener("close", () => { const vid = dlg.querySelector("video"); if (vid) { vid.pause(); vid.removeAttribute("src"); vid.load(); } dlg.innerHTML = ""; });
      dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    }
    dlg.innerHTML = `<div class="dlg vid">
        <header class="dlg-head"><div style="min-width:0">
          <div class="dlg-title">${esc(title)}</div>
          <div class="t-label">${esc(sub)}</div></div>
          <button type="button" class="icon outline" data-close style="margin-left:auto" aria-label="${tr("Schließen")}"><ha-icon icon="mdi:close"></ha-icon></button>
        </header>
        <div class="vid-box"><ha-icon icon="mdi:loading" class="spin"></ha-icon></div>
        <div class="dlg-actions"><a class="btn outline" data-dl download="${esc(fileName)}"><ha-icon icon="mdi:download"></ha-icon>${tr("Herunterladen")}</a></div>
      </div>`;
    dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
    if (!dlg.open) { if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", ""); }
    try {
      const { url, poster } = await source();
      const box = dlg.querySelector(".vid-box");
      if (!box) return;
      box.innerHTML = `<video controls autoplay playsinline preload="metadata" ${poster ? `poster="${esc(poster)}"` : ""} src="${esc(url)}"></video>`;
      dlg.querySelector("[data-dl]").setAttribute("href", url);
    } catch (err) {
      const box = dlg.querySelector(".vid-box");
      if (box) box.innerHTML = `<div class="dlg-error"><ha-icon icon="mdi:alert-circle"></ha-icon>${esc((err && err.message) || tr("Video nicht abrufbar"))}</div>`;
    }
  }
};
