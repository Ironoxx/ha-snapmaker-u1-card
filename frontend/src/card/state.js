/** Reading Home Assistant state: entities, integration sensors and the data model used for rendering. */

import { SUFFIX } from "../const.js";
import { LANG, tr } from "../i18n.js";

export const StateMixin = (Base) => class extends Base {
  _st(id) { return this._hass && this._hass.states[id]; }

  _s(id, fb = null) {
    const e = this._st(id);
    if (!e || ["unknown", "unavailable", ""].includes(e.state)) return fb;
    return e.state;
  }

  /** Duration entity in minutes, converted from its unit_of_measurement (fallback: ``unit``). */
  _minutes(id, unit, fb = null) {
    const v = this._n(id, null);
    if (v === null) return fb;
    const st = this._st(id);
    const u = String((st && st.attributes && st.attributes.unit_of_measurement) || unit).toLowerCase();
    const f = { d: 1440, h: 60, min: 1, s: 1 / 60, ms: 1 / 60000 }[u];
    return v * (f === undefined ? ({ h: 60, min: 1, s: 1 / 60 }[unit] || 1) : f);
  }

  _n(id, fb = null) {
    const v = this._s(id, null);
    if (v === null) return fb;
    const f = parseFloat(v);
    return Number.isNaN(f) ? fb : f;
  }

  _p(n) { return `${this._ents ? this._ents.prefix : "snapmaker_u1"}_${n}`; }

  /** Spoolman data from the integration; null if not configured. */
  _spoolman() {
    const st = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const sm = st && st.attributes && st.attributes.spoolman;
    return sm && typeof sm === "object" ? sm : null;
  }

  _slotSpool(idx) {
    const sm = this._spoolman();
    return sm && sm.slots ? sm.slots[String(idx)] || null : null;
  }

  /** Four slots from the integration, otherwise null. */
  _slots() {
    const st = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const s = st && st.attributes && st.attributes.slots;
    return Array.isArray(s) && s.length ? s : null;
  }

  /** Loaded bed mesh from the integration's sensor; null without one. */
  _meshData() {
    const st = this._ents && this._ents.bedMesh && this._st(this._ents.bedMesh);
    const a = st && st.attributes;
    if (!a || !Array.isArray(a.matrix) || !a.matrix.length || ["unknown", "unavailable"].includes(st.state)) return null;
    return { ...a, range: parseFloat(st.state) };
  }

  /** Top cover state; null if none is plugged in (entity missing or unavailable). */
  _coverData() {
    const st = this._ents && this._ents.topCover && this._st(this._ents.topCover);
    if (!st || ["unknown", "unavailable"].includes(st.state)) return null;
    return { mode: st.state, ...st.attributes };
  }

  /** Chamber heater (Panda Breath / DragonBreath); null without one. */
  _chamberData() {
    const st = this._ents && this._ents.chamber && this._st(this._ents.chamber);
    if (!st || st.state === "unavailable") return null;
    const temp = parseFloat(st.state);
    return { ...st.attributes, temperature: Number.isNaN(temp) ? null : temp };
  }

  _collect() {
    if (!this._hass) return;
    const P = (n) => this._p(n);
    const klipper = this._s(`sensor.${P("printer_state")}`, null);

    const slots = this._slots();
    const heads = SUFFIX.map((sfx, i) => {
      const meta = (this._cfg.toolheads && this._cfg.toolheads[i]) || {};
      const slot = slots ? slots[i] : null;
      // Live data from the printer takes precedence; YAML only as a fallback.
      const material = slot
        ? (slot.loaded ? [slot.type, slot.sub_type].filter(Boolean).join(" ") || tr("Unbekannt") : tr("Leer"))
        : meta.material || "—";
      const color = slot
        ? (slot.loaded && slot.color ? slot.color : "var(--u1-outline)")
        : meta.color || "var(--u1-outline)";
      return {
        idx: i,
        sfx,
        name: meta.name || tr("Kopf {n}", { n: i + 1 }),
        material,
        color,
        colors: slot && slot.loaded && slot.colors && slot.colors.length ? slot.colors : [color],
        vendor: slot && slot.loaded ? slot.vendor : null,
        official: !!(slot && slot.official && slot.loaded),
        live: !!slot,
        temp: this._n(`sensor.${P(`extruder${sfx}_temperature`)}`),
        target: this._n(`number.${P(`extruder${sfx}_target`)}`, 0),
        power: this._n(`sensor.${P(`extruder${sfx}_power`)}`, 0),
        fan: this._n(`sensor.${P(`e${i}_nozzle_fan`)}`, 0),
        loaded: slot ? !!slot.loaded : this._s(`binary_sensor.${P(`e${i}_filament`)}`) === "on",
        heater: this._s(`switch.${P(`output_pin_e${i}_heat_sw`)}`),
        mcuLoad: this._n(`sensor.${P(`mcu_e${i}_load`)}`),
        mcuAwake: this._n(`sensor.${P(`mcu_e${i}_awake`)}`),
        targetEntity: `number.${P(`extruder${sfx}_target`)}`,
      };
    });

    // Active head: from the firmware (toolhead.extruder) via the integration,
    // fresher from the layer view (every 5 s). Only without both the old
    // heuristic via the highest target temperature, which is often wrong in
    // multi-colour prints because waiting heads are kept warm.
    const fst = this._ents && this._ents.filaments && this._st(this._ents.filaments);
    const fw = fst && fst.attributes && Number.isInteger(fst.attributes.active_head) ? fst.attributes.active_head : null;
    const live = this._liveHead && Date.now() - this._liveHead.at < 15000 ? this._liveHead.idx : null;
    let active = live !== null ? live : fw !== null ? fw : -1;
    if (active < 0) {
      let best = 0;
      heads.forEach((h, i) => { if (h.target > best) { best = h.target; active = i; } });
    }
    heads.forEach((h, i) => { h.active = i === active; });
    const hot = active >= 0 ? heads[active] : heads[0];

    // The integration's live state (WebSocket) is seconds ahead of the
    // Moonraker integration, which only shows a pause at its next poll.
    const liveState = fst && fst.attributes && fst.attributes.live ? fst.attributes.print_state : null;
    const state = liveState || this._s(`sensor.${P("current_print_state")}`, "standby");

    this._d = {
      online: klipper !== null,
      klipper,
      state,
      printing: state === "printing",
      paused: state === "paused",
      active: state === "printing" || state === "paused",
      idleTimeout: this._s(`sensor.${P("idle_timeout_state")}`, "—"),
      queueState: this._s(`sensor.${P("queue_state")}`, "—"),
      jobsQueued: (this._attr("queue", "jobs") || []).length,
      message:
        this._s(`sensor.${P("current_print_message")}`) ||
        this._s(`sensor.${P("printer_message")}`, ""),
      display: this._s(`sensor.${P("current_display_message")}`, ""),
      filename: (this._s(`sensor.${P("filename")}`, "") || "").replace(/\.(gcode|3mf)$/i, ""),
      progress: this._n(`sensor.${P("progress")}`, 0),
      // Durations in minutes (fmtMin). The unit comes from the entity: users can
      // change the display unit, and the own sensor (min) differs from Moonraker's (h).
      elapsed: this._minutes(`sensor.${P("print_duration")}`, "min", 0),
      // Remaining/finish time: own sensors (file time profile), else the Moonraker integration
      remaining: (() => { const v = this._ents.remaining && this._minutes(this._ents.remaining, "min");
        return v !== null && v !== undefined ? v : this._minutes(`sensor.${P("print_time_left")}`, "h", 0); })(),
      projected: this._minutes(`sensor.${P("print_projected_total_duration")}`, "h", 0),
      slicerLeft: this._minutes(`sensor.${P("slicer_print_time_left_estimate")}`, "h", 0),
      slicerTotal: this._minutes(`sensor.${P("slicer_print_duration_estimate")}`, "h", 0),
      eta: (this._ents.finish && this._s(this._ents.finish)) || this._s(`sensor.${P("print_eta")}`),
      filamentUsed: this._n(`sensor.${P("filament_used")}`, 0),
      layer: this._n(`sensor.${P("current_layer")}`, 0),
      totalLayers: this._n(`sensor.${P("total_layer")}`, 0),
      objectHeight: this._n(`sensor.${P("object_height")}`),
      printSpeed: this._n(`sensor.${P("print_speed")}`, 0),
      // Machine controls of the integration (flow, bed mesh, top cover, head park states)
      flow: this._ents.flow ? this._n(this._ents.flow) : null,
      mesh: this._meshData(),
      cover: this._coverData(),
      chamber: this._chamberData(),
      headStates: (fst && fst.attributes && Array.isArray(fst.attributes.head_states)) ? fst.attributes.head_states : [],

      hot,
      heads,

      bed: this._n(`sensor.${P("bed_temperature")}`, 0),
      bedTarget: this._n(`number.${P("bed_target")}`, 0),
      bedPower: this._n(`sensor.${P("bed_power")}`, 0),
      cavity: this._n(`sensor.${P("cavity_temp")}`),
      cavityFan: this._n(`sensor.${P("cavity_fan")}`, 0),
      powerFan: this._n(`sensor.${P("power_fan")}`, 0),

      posX: this._n(`sensor.${P("toolhead_position_x")}`),
      posY: this._n(`sensor.${P("toolhead_position_y")}`),
      posZ: this._n(`sensor.${P("toolhead_position_z")}`),
      stepX: this._n(`sensor.${P("stepper_x_temp")}`),
      stepY: this._n(`sensor.${P("stepper_y_temp")}`),

      speedFactor: this._n(`number.${P("speed_factor")}`, 100),
      partFan: this._n(`number.${P("fan_speed")}`, 0),
      cavityFanSet: this._n(`number.${P("cavity_fan_speed")}`, 0),

      mcuLoad: this._n(`sensor.${P("mcu_load")}`),
      mcuAwake: this._n(`sensor.${P("mcu_awake")}`),
      memory: this._n(`sensor.${P("memory_used")}`),
      sysLoad: this._n(`sensor.${P("system_load")}`),

      totalsJobs: this._n(`sensor.${P("totals_jobs")}`, 0),
      totalsTime: this._s(`sensor.${P("totals_print_time")}`, "—"),
      longest: this._s(`sensor.${P("longest_print")}`, "—"),
      totalsFilament: this._n(`sensor.${P("totals_filament_used")}`, 0),

      light: this._s(`light.${this._p("led_cavity_led")}`) === "on",
      lightReal: this._s(`light.${this._p("led_cavity_led")}`) === "on",
      lightBri: (this._st(`light.${this._p("led_cavity_led")}`) || {}).attributes?.brightness ?? 0,
      network: this._cfg.network_tracker ? this._s(this._cfg.network_tracker) : null,
      files: this._files(),
      tc: this._toolChanges(),
      power: this._power(),
      usage: this._usage(),
      history: this._historyList(),
      timelapses: this._timelapseList(),
      queue: this._attr("queue", "jobs"),
      stats: this._statsData(),
      maint: this._attr("maintenance", "items"),
      backup: (() => { const st = this._ents && this._ents.maintenance && this._st(this._ents.maintenance);
        return (st && st.attributes && st.attributes.config_backup) || null; })(),
      errors: this._attr("errors", "errors") || [],
    };
  }

  /** List attribute of one of our sensors; null if the sensor does not exist. */
  _attr(key, name) {
    const st = this._ents && this._ents[key] && this._st(this._ents[key]);
    const v = st && st.attributes && st.attributes[name];
    return Array.isArray(v) ? v : null;
  }

  _statsData() {
    const st = this._ents && this._ents.statistics && this._st(this._ents.statistics);
    const a = st && st.attributes;
    if (!a || !Array.isArray(a.months) || !a.months.length) return null;
    return { months: a.months, totals: a.totals || {}, top: a.top_files || [], hours: parseFloat(st.state),
      materials: a.materials || [], colors: a.colors || [] };
  }

  _errText(e) {
    const key = LANG === "de" ? "de" : "en";
    let t = (e.text && e.text[key]) || e.message || "";
    if (!e.known && e.message) t = `${t}: ${e.message}`;
    return t;
  }

  /** The integration's power switch (options) incl. power draw. */
  _power() {
    const id = this._ents && this._ents.power;
    const st = id && this._st(id);
    if (!st) return null;
    const a = st.attributes || {};
    return {
      entity: id,
      on: st.state === "on",
      available: st.state !== "unavailable" && st.state !== "unknown",
      shuttingDown: !!a.shutting_down,
      poweringOn: !!a.powering_on,
      autoOn: !!a.auto_on,
      autoOffPending: !!a.auto_off_pending,
      watts: a.power_sensor ? this._n(a.power_sensor) : null,
      hasEnergy: !!a.energy_sensor,
    };
  }

  /** Consumption and cost of the running or last print. */
  _usage() {
    const e = this._ents || {};
    const en = e.energyPrint && this._st(e.energyPrint);
    const co = e.costPrint && this._st(e.costPrint);
    if (!en && !co) return null;
    const val = (st) => (st && !Number.isNaN(parseFloat(st.state)) ? parseFloat(st.state) : null);
    const a = ((en || co).attributes) || {};
    return {
      energy: val(en),
      cost: val(co),
      inProgress: !!a.in_progress,
      result: a.result || null,
      hasEnergy: !!en,
      hasCost: !!co,
      currency: (co && co.attributes.unit_of_measurement) || "€",
    };
  }

  _historyList() {
    const st = this._ents && this._ents.history && this._st(this._ents.history);
    const list = st && st.attributes && st.attributes.prints;
    return Array.isArray(list) ? list : null;
  }

  _timelapseList() {
    const st = this._ents && this._ents.timelapses && this._st(this._ents.timelapses);
    const a = st && st.attributes;
    if (!a || !Array.isArray(a.videos)) return null;
    return { videos: a.videos, url: a.url, playable: a.playable !== false, archive: a.archive || null };
  }

  /** Tool changes from the integration's sensors; null without firmware counters. */
  _toolChanges() {
    const e = this._ents || {};
    const tot = e.toolChanges && this._st(e.toolChanges);
    if (!tot || !/^\d+$/.test(tot.state)) return null;
    const pr = e.toolChangesPrint && this._st(e.toolChangesPrint);
    const pa = (pr && pr.attributes) || {};
    const heads = Array.isArray(tot.attributes.heads) ? tot.attributes.heads : [];
    const threshold = tot.attributes.maintenance_threshold || null;
    const since = heads.length ? Math.max(...heads.map((h) => h.since_maintenance || 0)) : null;
    return {
      total: Number(tot.state),
      heads,
      threshold,
      since,
      print: pr && /^\d+$/.test(pr.state) ? Number(pr.state) : null,
      inProgress: !!pa.in_progress,
      file: pa.file || null,
      result: pa.result || null,
    };
  }

  /** The file list comes from a sensor attribute, not from a fetch,
   *  so this part also stays on the HA connection. */
  _files() {
    const st = this._ents && this._ents.files && this._st(this._ents.files);
    const raw = st && st.attributes && st.attributes.files;
    if (!Array.isArray(raw)) return null;
    return raw
      .filter((f) => f && f.path)
      .slice(0, this._cfg.files_limit || 12);
  }
};
