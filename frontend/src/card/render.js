/** Rendering: full rebuilds on structural changes, event wiring and in-place patching. */

import { BLANK, DOMAIN, MAINT_LABELS } from "../const.js";
import { clamp, esc, fixed, fmtClock, fmtEuro, fmtInt, fmtMin, num } from "../format.js";
import { LANG, tr } from "../i18n.js";
import { STYLES } from "../styles.js";

export const RenderMixin = (Base) => class extends Base {
  _render() {
    if (!this._d) return;
    const d = this._d;
    this._settlePending();
    this._applyPending();

    // Rebuild only when the structure changes. Numbers are patched; otherwise
    // the <img> would reload on every temperature change and the card would flicker.
    // Light, temperatures etc. are patched; a rebuild only happens on a
    // structural change. The light used to be part of the key: every click
    // rebuilt the card and left an orphaned MJPEG connection open.
    const key = [
      LANG,
      d.online ? d.state : "offline",
      d.heads.map((h) => `${h.name}|${h.material}|${h.colors.join("/")}|${h.vendor}|${h.official}|${h.active}|${h.heater}`).join(","),
      this._cfg.network_tracker ? d.network : "",
      !!d.filename,
      !!this._st(this._ents.thumbnail)?.attributes.entity_picture,
      this._cfg.show.join(","),
      `${this._cfg.layout}${this._cfg.camera_overlay}`,
      d.heads.findIndex((h) => h.active),
      (() => { const sm = this._spoolman(); return sm ? `sm${sm.online}${Object.values(sm.slots || {}).map((v) => v ? `${v.id}:${Math.round(v.remaining_weight || 0)}:${v.manual}` : "-").join(",")}r${Object.entries(sm.restore || {}).map(([k, v]) => `${k}:${v.id}`).join(",")}` : "nosm"; })(),
      d.tc ? `tc${d.tc.inProgress}${d.tc.heads.length}` : "notc",
      d.power ? `p${d.power.on}${d.power.available}${d.power.autoOn}${d.online ? "" : d.power.shuttingDown + "" + d.power.poweringOn}` : "nop",
      d.usage ? `u${d.usage.inProgress}${d.usage.hasEnergy}${d.usage.hasCost}` : "nou",
      d.history ? d.history.map((h) => `${h.ended}${h.total_cost}`).join(",") : "noh",
      d.timelapses ? d.timelapses.videos.map((v) => v.path).join(",") : "not",
      d.files ? d.files.map((f) => f.path + f.modified + (f.thumb || "")).join(",") : "none",
      d.queue ? d.queue.map((j) => j.id).join(",") : "noq",
      d.errors.map((e) => e.key).join(","),
      d.maint ? d.maint.map((m) => `${m.key}${m.due}${m.progress}${m.done_at || ""}`).join(",") : "nom",
      d.stats ? `${d.stats.hours}|${JSON.stringify(d.stats.totals)}|${this._metric || ""}` : "nos",
      d.timelapses && d.timelapses.archive ? `${d.timelapses.archive.count}${d.timelapses.archive.busy}${d.timelapses.archive.cleanup}${d.timelapses.archive.last_backup}` : "noa",
      this._up ? `up${!!this._up.error}${this._up.done}` : "",
      JSON.stringify(this._prefs()),
      this._st(this._ents.files)?.attributes.version || "",
      this._ents.ownCamera ? (this._st(this._ents.ownCamera)?.attributes.mode || "") : "",
      (() => { const l = this._st(this._ents.liveNotify); return l ? `${l.state}${l.attributes.sent_today}${(l.attributes.targets || []).length}` : ""; })(),
      d.mesh ? `m${d.mesh.profile}${d.mesh.range}${d.mesh.mean}${d.mesh.cols}x${d.mesh.rows}` : "nomesh",
      d.cover ? "cover" : "nocover",
      d.chamber ? `ch${d.chamber.filter !== null && d.chamber.filter !== undefined}` : "noch",
      `f${this._ents.flow && d.flow !== null}`,
      d.headStates.join(","),
      `${this._ents.camera}${this._hasCamera2()}`,
      this._pendingKey(),
    ].join("~");

    if (key === this._renderKey && this._root()) { this._patch(); this._accent(); return; }
    this._renderKey = key;

    const card = this._root(true);
    // Move the running camera image into the new build instead of
    // reconnecting: no black frame, no second connection.
    const old = card.querySelector("img[data-live]");
    card.innerHTML = this._body();
    const fresh = card.querySelector("img[data-live]");
    if (old && fresh && old.getAttribute("src")) {
      old.className = fresh.className;
      old.style.cssText = fresh.style.cssText;
      fresh.replaceWith(old);
    } else if (old) {
      if (this._streamImg === old) this._stopStream();
      else { old.onload = null; old.onerror = null; old.src = BLANK; }
    }
    this._wire();
    this._patch();
    this._accent();
  }

  /** Thin frame in the theme colour of the state (printing, paused, error, done); option state_accent. */
  _accent() {
    const card = this._root();
    if (!card || !this._d) return;
    const tone = this._cfg.state_accent === false ? "" : this._statusTone();
    if (["active", "warn", "error", "ok"].includes(tone)) card.dataset.accent = tone;
    else delete card.dataset.accent;
  }

  /** ha-card as a fixed container; the dialog sits next to it and survives rebuilds. */
  _root(create = false) {
    let card = this.shadowRoot.getElementById("u1card");
    if (!card && create) {
      this.shadowRoot.innerHTML =
        `<style>${STYLES}</style><ha-card id="u1card"></ha-card><div id="u1dlg"></div>`;
      card = this.shadowRoot.getElementById("u1card");
      this._dlgEl = null;
    }
    return card;
  }

  _wire() {
    const r = this.shadowRoot.getElementById("u1card");

    r.querySelectorAll("[data-act]").forEach((b) =>
      b.addEventListener("click", () => {
        const a = b.dataset.act;
        if (a === "pause") return this._pausePrint();
        if (a === "resume") return this._resumePrint();
        if (a === "home_all") return this._press("home_all_axes");
        if (a === "home_x") return this._press("home_x_axis");
        if (a === "home_y") return this._press("home_y_axis");
        if (a === "home_z") return this._press("home_z_axis");
        if (a === "light") return this._toggleLight();
        if (a === "refresh_files") return this._hass.callService(DOMAIN, "refresh", this._entryData());
        if (a === "upload") { const inp = r.querySelector("input[data-upload]"); if (inp) inp.click(); return; }
        if (a === "backup") return this._call("backup_timelapses", {});
        if (a === "backup_config") return this._call("backup_config", {});
        if (a === "selftest") return this._runSelfTest();
        if (a === "lock") return this._toggleLock();
        if (a === "power") return this._togglePower();
        if (a === "cancel") {
          this._confirmAction({
            icon: "mdi:stop-circle-outline", tone: "error", title: tr("Druck wirklich abbrechen?"),
            text: tr("Der laufende Druck lässt sich danach nicht fortsetzen."), ok: tr("Druck abbrechen"),
            cancel: tr("Weiterdrucken"),
          }).then((yes) => { if (yes) this._cancelPrint(); });
        }
      })
    );
    this._wireEstop(r);
    this._wireMachine(r);
    r.querySelectorAll("[data-camswitch]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._switchCamera(); }));
    this._wireObjects(r.querySelector(".lv-panel"));
    const rl = r.querySelector("[data-reload]");
    // Reload bypassing the cache for the card resource (the URL carries ?v=)
    if (rl) rl.addEventListener("click", () => window.location.reload());

    const inp = r.querySelector("input[data-upload]");
    if (inp) inp.addEventListener("change", () => { if (inp.files && inp.files[0]) this._upload(inp.files[0]); inp.value = ""; });
    r.querySelectorAll("[data-reprint]").forEach((b) =>
      b.addEventListener("click", () => this._reprint(Number(b.dataset.reprint))));
    r.querySelectorAll("[data-archive]").forEach((b) =>
      b.addEventListener("click", () => this._openArchive(Number(b.dataset.archive))));
    r.querySelectorAll("[data-q]").forEach((b) =>
      b.addEventListener("click", () => this._queueAction(b.dataset.q, b.dataset.job, Number(b.dataset.pos))));
    r.querySelectorAll("[data-metric]").forEach((b) =>
      b.addEventListener("click", () => { this._metric = b.dataset.metric; this._renderKey = null; this._render(); }));
    r.querySelectorAll("[data-maint]").forEach((b) =>
      b.addEventListener("click", () => {
        const label = tr(MAINT_LABELS[b.dataset.maint] || b.dataset.maint);
        if (confirm(tr("„{x}“ als erledigt markieren?", { x: label }))) this._call("maintenance_done", { item: b.dataset.maint });
      }));

    r.querySelectorAll("[data-tab]").forEach((b) =>
      b.addEventListener("click", () => this._selectTab(b.dataset.tab)));

    r.querySelectorAll("[data-headinfo]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._openHeadInfo(Number(b.dataset.headinfo)); }));
    // The spool and name open the same dialog (larger target than the button)
    r.querySelectorAll("[data-headopen]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._openHeadInfo(Number(b.dataset.headopen)); }));
    r.querySelectorAll("[data-prefset]").forEach((b) =>
      b.addEventListener("click", () => this._call("set_preference",
        { preference: b.dataset.prefset, value: b.getAttribute("aria-pressed") !== "true" })));
    const ln = r.querySelector("[data-livenotify]");
    if (ln) ln.addEventListener("click", () => this._hass.callService("switch", "toggle", { entity_id: this._ents.liveNotify }));
    r.querySelectorAll("[data-prefsen]").forEach((b) =>
      b.addEventListener("click", () => this._call("set_preference",
        { preference: "entangle_sensitivity", value: b.dataset.prefsen })));
    r.querySelectorAll("[data-spoolrestore]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._restoreSpool(Number(b.dataset.spoolrestore), Number(b.dataset.spool)); }));
    r.querySelectorAll("[data-spoolpick]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); this._openSpoolPicker(Number(b.dataset.spoolpick)); }));

    r.querySelectorAll("[data-toggle]").forEach((b) =>
      b.addEventListener("click", () => {
        this._toggleEntity(b.dataset.toggle, b);
      })
    );

    r.querySelectorAll("[data-set]").forEach((b) =>
      b.addEventListener("click", () => { this._touchLock(); this._setNumber(b.dataset.set, b.dataset.value); })
    );

    r.querySelectorAll("[data-print]").forEach((b) =>
      b.addEventListener("click", () => this._openPrint(b.dataset.print))
    );
    const fsearch = r.querySelector("[data-fsearch]");
    if (fsearch) {
      const fs = this._fstate || (this._fstate = { q: "", sort: "new", folder: "" });
      fsearch.addEventListener("input", () => { fs.q = fsearch.value; this._filterFiles(); });
      r.querySelector("[data-fsort]").addEventListener("change", (e) => { fs.sort = e.target.value; this._filterFiles(); });
      r.querySelectorAll("[data-ffolder]").forEach((b) => b.addEventListener("click", () => {
        fs.folder = b.dataset.ffolder;
        r.querySelectorAll("[data-ffolder]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        this._filterFiles();
      }));
      this._filterFiles();
    }
    r.querySelectorAll("[data-photo]").forEach((el) =>
      el.addEventListener("click", (e) => { e.stopPropagation(); this._showPhoto(el.dataset.photo); })
    );

    r.querySelectorAll("[data-video]").forEach((b) =>
      b.addEventListener("click", () => this._openVideo(Number(b.dataset.video)))
    );

    r.querySelectorAll("[data-more]").forEach((el) =>
      el.addEventListener("click", () => this._more(el.dataset.more))
    );

    // Sliders: update the label live, call the service only on release.
    // While the user is interacting, the value is not overwritten from outside.
    r.querySelectorAll("input[data-num]").forEach((el) => {
      const id = el.dataset.num;
      const dec = parseInt(el.dataset.dec, 10) || 0;
      const unit = el.dataset.unit || "";
      const label = r.querySelector(`[data-su1="n:${id}"]`);
      el.addEventListener("input", () => {
        this._touchLock();
        this._busy.set(id, Date.now());
        if (label) label.textContent = num(parseFloat(el.value), dec, unit);
      });
      el.addEventListener("change", () => {
        this._busy.set(id, Date.now());
        this._setNumber(id, el.value);
      });
    });

    this._applyLock();
    this._wireZoom(r);
    this._tickCamera();
  }

  _patch() {
    const r = this.shadowRoot.getElementById("u1card");
    if (!r || !this._d) return;
    const d = this._d;

    const set = (k, v) => {
      const el = r.querySelector(`[data-su1="${k}"]`);
      if (el && el.innerHTML !== String(v)) el.innerHTML = String(v);
    };
    const width = (k, v) => {
      const el = r.querySelector(`[data-su1="${k}"]`);
      if (el) el.style.width = `${v}%`;
    };

    set("status", this._statusLabel());
    set("camstate", this._statusLabel());
    const pwr = r.querySelector('[data-su1="pwr"]');
    if (pwr && d.power) {
      const html = this._powerLabel(d.power);
      if (pwr.dataset.html !== html) { pwr.innerHTML = html; pwr.dataset.html = html; }
      const tmp = document.createElement("div");
      tmp.innerHTML = `<b ${this._powerAttrs(d.power)}></b>`;
      const b = tmp.firstChild;
      pwr.dataset.tone = b.dataset.tone;
      pwr.title = b.title;
      pwr.disabled = b.hasAttribute("disabled");
    }
    if (d.usage) {
      set("uenergy", num(d.usage.energy, 2, "kWh"));
      set("ucost", fmtEuro(d.usage.cost));
    }
    r.querySelectorAll("[data-toggle]").forEach((b) =>
      b.classList.toggle("pending", this._isPending(`t:${b.dataset.toggle}`)));
    const lightBtn = r.querySelector('[data-su1="light"]');
    if (lightBtn) {
      lightBtn.classList.toggle("on", d.light);
      lightBtn.classList.toggle("outline", !d.light);
    }
    set("file", esc(d.filename || "—"));
    set("pct", fixed(d.progress, 1));
    width("bar", d.progress);

    set("layer", `${d.layer} / ${d.totalLayers}`);
    set("opct", d.progress.toFixed(0));
    set("olayer", `${d.layer} / ${d.totalLayers}`);
    set("oremain", fmtMin(d.remaining));
    set("oeta", fmtClock(d.eta));
    width("obar", d.progress);
    set("remain", fmtMin(d.remaining));
    set("eta", fmtClock(d.eta));
    set("elapsed", fmtMin(d.elapsed));
    set("fil", num(d.filamentUsed, 1, "m"));
    set("height", num(d.objectHeight, 1, "mm"));
    set("pspeed", num(d.printSpeed, 0, "mm/s"));
    set("sremain", fmtMin(d.slicerLeft));
    set("tjobs2", num(d.totalsJobs, 0));
    set("queued", num(d.jobsQueued, 0));

    set("bed", num(d.bed, 0, "°C"));
    set("cavity", num(d.cavity, 0, "°C"));
    set("bedpow", num(d.bedPower, 0, "%"));
    set("powfan", num(d.powerFan, 0, "%"));

    set("px", num(d.posX, 1));
    set("py", num(d.posY, 1));
    set("pz", num(d.posZ, 2));

    set("klipper", esc(d.klipper || "—"));
    if (this._ents.live) set("live", this._liveText());
    if (this._ents.firmware) set("fw", this._fwText());
    set("msg", esc(d.message || "—"));
    set("idle", esc(d.idleTimeout));
    set("queue", esc(d.queueState));
    set("mcuhost", `${num(d.mcuLoad, 2, "%")} / ${num(d.mcuAwake, 2, "%")}`);
    set("mem", num(d.memory, 1, "%"));
    set("sys", this._loadText());
    set("stepx", num(d.stepX, 1, "°C"));
    if (d.chamber) {
      set("chtemp", num(d.chamber.temperature, 1, "°C"));
      set("chtarget", d.chamber.target ? num(d.chamber.target, 0, "°C") : tr("aus"));
      set("chpower", num(d.chamber.power, 0, "%"));
      const fb = r.querySelector('[data-su1="chfilter"]');
      if (fb) { fb.classList.toggle("on", d.chamber.filter === true); fb.classList.toggle("outline", d.chamber.filter !== true); }
    }
    if (d.cover) {
      set("cvmode", esc(this._coverMode(d.cover.mode)));
      set("cvtarget", num(d.cover.desired_temp, 0, "°C"));
      set("cvrpm", num(d.cover.inner_rpm, 0));
      set("cvfilter", num(d.cover.filter_hours, 1, "h"));
    }
    set("stepy", num(d.stepY, 1, "°C"));

    set("tjobs", num(d.totalsJobs, 0));
    set("ttime", esc(d.totalsTime));
    set("tlong", esc(d.longest));
    set("tfil", num(d.totalsFilament, 1, "m"));
    if (d.tc) {
      set("tctotal", fmtInt(d.tc.total));
      set("tcprint", this._tcPrintText(d.tc));
      set("tcheads", this._tcHeadsText(d.tc));
      set("tcmaint", this._tcMaintText(d.tc));
    }

    d.heads.forEach((h) => {
      set(`htemp:${h.idx}`,
        `${num(h.temp, 0, "°C")}${h.target > 0 ? ` <span class="tgt">→ ${h.target.toFixed(0)} °C</span>` : ""}`);
      set(`hfan:${h.idx}`, tr("Lüfter {v}", { v: num(h.fan, 0, "%") }));
      set(`hpow:${h.idx}`, tr("Heiz. {v}", { v: num(h.power, 0, "%") }));
      set(`mcu:${h.idx}`, `${num(h.mcuLoad, 2, "%")} / ${num(h.mcuAwake, 2, "%")}`);
      width(`hbar:${h.idx}`,
        h.target > 0 && h.temp !== null ? clamp((h.temp / h.target) * 100, 0, 100) : 0);
      const pill = r.querySelector(`[data-su1="pill:${h.idx}"]`);
      if (pill) {
        pill.dataset.empty = h.loaded ? "0" : "1";
        const t = h.loaded ? tr("Geladen") : tr("Leer");
        if (pill.textContent.trim() !== t) pill.textContent = t;
      }
    });

    // Update sliders while nobody touches them (2 s grace after the
    // last interaction, otherwise the handle jumps back while dragging).
    const pairs = [
      [`number.${this._p("bed_target")}`, d.bedTarget, 0, "°C"],
      [`number.${this._p("fan_speed")}`, d.partFan, 0, "%"],
      [`number.${this._p("cavity_fan_speed")}`, d.cavityFanSet, 0, "%"],
      [`number.${this._p("speed_factor")}`, d.speedFactor, 0, "%"],
      ...(this._ents.flow ? [[this._ents.flow, d.flow, 0, "%"]] : []),
      ...(d.cover && this._ents.coverExhaust ? [[this._ents.coverExhaust, d.cover.exhaust, 0, "%"]] : []),
      ...(d.cover && this._ents.coverInner ? [[this._ents.coverInner, d.cover.inner, 0, "%"]] : []),
      ...(d.chamber && this._ents.chamberTarget ? [[this._ents.chamberTarget, d.chamber.target || 0, 0, "°C"]] : []),
      ...d.heads.map((h) => [h.targetEntity, h.target, 0, "°C"]),
    ];
    const now = Date.now();
    pairs.forEach(([id, value, dec, unit]) => {
      if (value === null) return;
      const last = this._busy.get(id) || 0;
      if (now - last < 2000) return;
      const el = r.querySelector(`input[data-num="${id}"]`);
      if (el && document.activeElement !== el && parseFloat(el.value) !== value) {
        el.value = value;
      }
      set(`n:${id}`, num(value, dec, unit));
    });
  }
};
