/** Timelapse tab: videos on the printer and in the media archive. */

import { archiveName, esc, fmtDate } from "../format.js";
import { tr } from "../i18n.js";

export const TimelapseMixin = (Base) => class extends Base {
  _sectionTimelapse() {
    const tl = this._d.timelapses;
    if (!tl) return "";
    const tiles = tl.videos.length ? tl.videos.slice(0, this._cfg.timelapse_limit || 8).map((v, i) => `
        <button class="file tl" data-video="${i}" title="${esc(v.path)}">
          <span class="file-thumb tl-thumb">
            ${v.poster_url || v.thumb_url ? `<img src="${esc(v.poster_url || v.thumb_url)}" alt="" loading="lazy" />` : ""}
            <ha-icon icon="mdi:play-circle" class="tl-play"></ha-icon>
          </span>
          <span class="file-name">${esc(v.name)}</span>
          <span class="file-meta">${esc(fmtDate(v.recorded || (v.modified ? new Date(v.modified * 1000).toISOString() : null)))}${v.size ? ` · ${(v.size / 1048576).toFixed(0)} MB` : ""}</span>
        </button>`).join("")
      : `<div class="t-label">${tr("Keine Zeitraffer auf dem Drucker. Aufnahme im Druckdialog unter „Zeitraffer“ einschalten.")}</div>`;
    return `
      <section class="panel span2">
        <details ${this._cfg.compact ? "" : "open"}>
          <summary>
            <ha-icon icon="mdi:filmstrip-box-multiple"></ha-icon>
            <span>${tr("Zeitraffer")}</span>
            ${tl.videos.length ? `<span class="t-label" style="margin-left:auto">${tl.videos.length}</span>` : ""}
            <ha-icon class="caret" icon="mdi:chevron-down"></ha-icon>
          </summary>
          <div class="body"><div class="files">${tiles}</div>${this._archiveBlock(tl.archive)}</div>
        </details>
      </section>`;
  }

  _archiveBlock(a) {
    if (!a) return "";
    const status = [
      a.busy ? tr("Sicherung läuft …") : a.last_backup ? tr("Zuletzt gesichert: {d}", { d: fmtDate(new Date(a.last_backup * 1000).toISOString()) }) : tr("Noch nichts gesichert."),
      a.keep > 0 ? (a.cleanup === "not_supported" ? tr("Löschen auf dem Drucker wird von der Firmware nicht unterstützt.")
        : tr("Auf dem Drucker bleiben die {n} neuesten.", { n: a.keep })) : null,
    ].filter(Boolean).join(" · ");
    const tiles = (a.videos || []).slice(0, this._cfg.timelapse_limit || 8).map((v, i) => `
        <button class="file tl" data-archive="${i}" title="${esc(v.file)}">
          <span class="file-thumb tl-thumb">
            ${v.poster_url ? `<img src="${esc(v.poster_url)}" alt="" loading="lazy" />` : ""}
            <ha-icon icon="mdi:play-circle" class="tl-play"></ha-icon>
          </span>
          <span class="file-name">${esc(archiveName(v.file))}</span>
          <span class="file-meta">${esc(fmtDate(new Date(v.modified * 1000).toISOString()))} · ${(v.size / 1048576).toFixed(0)} MB</span>
        </button>`).join("");
    return `
      <div class="arch-head">
        <ha-icon icon="mdi:folder-play-outline"></ha-icon>
        <span class="panel-title">${tr("Gesichert in Medien")} (${a.count})</span>
        <button class="icon outline" data-act="backup" title="${tr("Jetzt sichern")}" ${a.busy ? "disabled" : ""}
          style="margin-left:auto"><ha-icon icon="${a.busy ? "mdi:loading" : "mdi:content-save-move-outline"}" class="${a.busy ? "spin" : ""}"></ha-icon></button>
      </div>
      <div class="t-label">${esc(status)}</div>
      ${(a.errors || []).length ? `<div class="t-label" style="color:var(--u1-error)">${a.errors.map(esc).join("<br>")}</div>` : ""}
      ${tiles ? `<div class="files">${tiles}</div>` : ""}`;
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
