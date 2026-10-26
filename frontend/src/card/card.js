/**
 * The full card. Behaviour is split into mixins (one file per topic); this
 * class owns the lifecycle: config, hass updates, entity resolution and timers.
 *
 * Data sources, all through the Home Assistant connection (local, VPN and
 * Nabu Casa behave the same):
 *   - Moonraker integration: temperatures, state, controls, camera
 *   - snapmaker_u1_card:     loaded filaments, print files, print start
 *
 * Minimal config:
 *   type: custom:snapmaker-u1-card
 *
 * Everything is detected automatically. Options only to override:
 *   prefix            Moonraker entity prefix                (auto)
 *   camera            camera entity                          (auto)
 *   thumbnail         slicer preview                         (camera.<prefix>_thumbnail)
 *   filaments_sensor  filament sensor of the integration     (auto)
 *   files_sensor      file sensor of the integration         (auto)
 *   network_tracker   device_tracker for a WiFi chip         (off)
 *   printer_image     static image instead of the camera
 *   camera_fit        contain | cover | fill                 (contain)
 *   camera_height     height of the image area in px         (auto: image aspect ratio)
 *   camera_max_height upper limit for the automatic height   (520)
 *   camera_mode       auto | stream | still                  (auto: the camera entity decides)
 *   refresh           still image rate in seconds            (2)
 *   stream_check      stream check interval in seconds       (10)
 *   stale_after       "image outdated" after x seconds       (90)
 *   printer_name / printer_brand
 *   layout            tabs | scroll | tablet                 (tabs)
 *   emergency_stop    show | hold | hide                     (show)
 *   layer_view        part | bed: layer view zoomed or whole plate (part)
 *   bed_image         own background image for the bed view (/local/...)
 *   bed_image_area    printer mm the image covers: x0, y0, x1, y1 (0, 0, 270, 270)
 *   bed_image_opacity 0.1-1 (1); bed_grid: grid over the image (false)
 *   camera_wake       wake the camera when the image stops   (true)
 *   camera_direct     auto | off: stream straight from the printer (auto)
 *   camera_direct_url own URL for the direct stream          (http://<printer>/webcam/?action=stream)
 *   camera_overlay    progress on the camera image           (true)
 *   state_accent      frame in the state colour              (true)
 *   hide / show       sections: stage layer job queue files toolheads climate
 *                     mesh motion console system maintenance charts stats history timelapse
 *   controls_lock     off | 30 | 60 | 120 | 300 | manual     (60)
 *   nozzle_presets    [0, 210, 240, 260]
 *   bed_presets       [0, 55, 65, 85]
 *   files_limit       number of files shown                  (12)
 *   toolheads         per head: name (and material/color as a fallback
 *                     when the integration is missing)
 */

import { DOMAIN, SECTIONS, TAB_STORE } from "../const.js";
import { configForm } from "../editor.js";
import { toneThumb } from "../format.js";
import { setLang } from "../i18n.js";

import { StateMixin } from "./state.js";
import { ControlsMixin } from "./controls.js";
import { OverviewMixin } from "./overview.js";
import { FilesMixin } from "./files.js";
import { ControlTabMixin } from "./control-tab.js";
import { SystemMixin } from "./system.js";
import { HistoryMixin } from "./history.js";
import { TimelapseMixin } from "./timelapse.js";
import { LayerViewMixin } from "./layer.js";
import { LayoutMixin } from "./layout.js";
import { RenderMixin } from "./render.js";
import { ZoomMixin } from "./zoom.js";
import { PrintDialogMixin } from "./dialog.js";
import { CameraMixin } from "./camera.js";
import { HeadDialogMixin } from "./head-dialog.js";
import { SafetyMixin } from "./safety.js";
import { MachineMixin } from "./machine.js";

// Each mixin adds the methods of one topic. Method names are unique across
// mixins (checked in tests), so the order only affects the prototype chain.
const MIXINS = [
  StateMixin, ControlsMixin, OverviewMixin, FilesMixin, ControlTabMixin, SystemMixin, HistoryMixin,
  TimelapseMixin, LayerViewMixin, LayoutMixin, RenderMixin, ZoomMixin, PrintDialogMixin, CameraMixin,
  HeadDialogMixin, SafetyMixin, MachineMixin,
];
const U1Base = MIXINS.reduce((Base, mixin) => mixin(Base), HTMLElement);

export class SnapmakerU1Card extends U1Base {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    // load does not bubble; capturing catches every image in the shadow DOM
    this.shadowRoot.addEventListener("load", (e) => toneThumb(e.target), true);
    this._cfg = {};
    this._d = null;
    this._renderKey = null;
    this._camTimer = null;
    this._canvas = null;
    this._lastHash = null;
    this._lastChange = Date.now();
    this._loading = false;
    this._busy = new Map(); // sliders the user is currently touching
    this._streamImg = null;   // <img> that currently holds a stream
    this._streamFailUntil = 0; // until then fall back to still images
    this._lastCheck = 0;
    this._lastStill = 0;
    this._failCount = 0;
    this._streamProven = false;
    this._streamStart = 0;
    this._preHash = null;
    this._loadStart = 0;
    this._ents = null;        // resolved entity IDs
    this._entsSource = null;  // hass.entities the IDs were resolved from
    this._dlg = null;         // open print dialog
    this._onVis = () => {
      if (document.hidden) this._stopStream();
      else this._tickCamera();
    };
    this._preview = false;   // edit mode or preview in the editor
    this._onScreen = true;   // via IntersectionObserver
    this._tab = null;        // active tab
    try { this._tab = window.localStorage.getItem(TAB_STORE); } catch (e) { /* no storage */ }
  }

  // HA sets preview (new) or editMode (old) in edit mode. There HA
  // rebuilds the card on every change; a live stream per build occupies
  // connections the editor itself needs for loading.
  set preview(v) { this._setPreview(v); }
  get preview() { return this._preview; }
  set editMode(v) { this._setPreview(v); }
  get editMode() { return this._preview; }
  _setPreview(v) {
    const on = !!v;
    if (on === this._preview) return;
    this._preview = on;
    if (on) this._stopStream();
  }

  static getConfigForm() {
    return configForm(false);
  }

  static getStubConfig() {
    return { type: "custom:snapmaker-u1-card" };
  }

  setConfig(config) {
    this._cfg = {
      camera_mode: "auto",
      refresh: 2,
      stream_check: 10,
      stale_after: 90,
      camera_fit: "contain",
      camera_max_height: 520,
      printer_brand: "snapmaker",
      printer_name: "U1",
      compact: false,
      layout: "tabs",
      camera_overlay: true,
      state_accent: true,
      emergency_stop: "show",
      camera_wake: true,
      camera_direct: "auto",
      show: SECTIONS,
      nozzle_presets: [0, 210, 240, 260],
      bed_presets: [0, 55, 65, 85],
      files_limit: 12,
      toolheads: [],
      ...config,
    };
    if (typeof this._cfg.show === "string") this._cfg.show = this._cfg.show.split(/[\s,]+/);
    const hide = Array.isArray(this._cfg.hide) ? this._cfg.hide : [];
    this._cfg.show = (this._cfg.show || SECTIONS).filter((s) => SECTIONS.includes(s) && !hide.includes(s));
    if (this._cfg.hide_overlay) this._cfg.camera_overlay = false;
    this._renderKey = null;
    this._lastHash = null;
    this._lastChange = Date.now();
    this._streamFailUntil = 0;
    this._failCount = 0;
    this._directFailUntil = 0;
    this._lastStill = 0;
    this._ents = null;
    this._dlg = null;
    this._dlgEl = null;
    this._stopStream();
    if (this.shadowRoot) this.shadowRoot.innerHTML = "";
  }

  getCardSize() { return 20; }
  getGridOptions() {
    return { columns: "full", rows: "auto", min_columns: 6 };
  }

  set hass(hass) {
    this._hass = hass;
    setLang(hass);
    this._resolve();
    this._collect();
    this._render();
    if (this._dlg) this._refreshDialog();
    else if (this._afterUpload) this._checkAfterUpload();
    this._tickLayer(true);
  }

  // ── Find entities automatically ───────────────────────────────────────────
  // hass.entities is the frontend's entity registry incl. platform and
  // translation_key, so the card needs no prefixes in YAML.
  _resolve() {
    const reg = this._hass.entities;
    if (this._ents && this._entsSource === reg) return;
    this._entsSource = reg;
    const list = reg ? Object.values(reg) : [];
    const c = this._cfg;

    let prefix = c.prefix;
    if (!prefix) {
      const hit = list.find((e) => e.platform === "moonraker" && /^sensor\..+_printer_state$/.test(e.entity_id));
      prefix = hit ? hit.entity_id.slice("sensor.".length, -"_printer_state".length) : "snapmaker_u1";
    }

    const own = list.filter((e) => e.platform === DOMAIN);
    const ownKey = (k) => (own.find((e) => e.translation_key === k) || {}).entity_id || null;

    // Camera: option, else the integration's own camera (detects stream / still
    // images / stock firmware itself), else the Moonraker integration's camera.
    const ownCam = ownKey("camera");
    let camera = c.camera || ownCam;
    if (!camera) {
      const cams = list.filter((e) => e.platform === "moonraker" && e.entity_id.startsWith("camera.")
        && !/thumbnail/.test(e.entity_id));
      const mine = cams.find((e) => e.entity_id.startsWith(`camera.${prefix}`)) || cams[0];
      camera = mine ? mine.entity_id : `camera.${prefix}_kamera`;
    }

    // Second camera (paxx12 USB): the card can switch to it (camera button on the image)
    const cam2 = ownKey("camera2");
    const alt = !!(this._camAlt && cam2 && !c.camera);
    this._ents = {
      prefix,
      camera: alt ? cam2 : camera,
      ownCamera: alt ? cam2 : camera === ownCam ? ownCam : null,
      camera2: cam2,
      camAlt: alt,
      thumbnail: c.thumbnail || `camera.${prefix}_thumbnail`,
      filaments: c.filaments_sensor || ownKey("filaments"),
      files: c.files_sensor || ownKey("files"),
      toolChanges: ownKey("tool_changes"),
      toolChangesPrint: ownKey("tool_changes_print"),
      power: ownKey("power"),
      energyPrint: ownKey("print_energy"),
      costPrint: ownKey("print_cost"),
      history: ownKey("history"),
      timelapses: ownKey("timelapses"),
      queue: ownKey("queue"),
      statistics: ownKey("statistics"),
      maintenance: ownKey("maintenance"),
      errors: ownKey("errors"),
      live: ownKey("live"),
      remaining: ownKey("remaining"),
      finish: ownKey("finish"),
      firmware: ownKey("firmware"),
      liveNotify: ownKey("live_notify"),
      flow: ownKey("flow_factor"),
      bedMesh: ownKey("bed_mesh"),
      topCover: ownKey("top_cover"),
      coverExhaust: ownKey("top_cover_exhaust"),
      coverInner: ownKey("top_cover_inner"),
      chamber: ownKey("chamber_heater"),
      chamberTarget: ownKey("chamber_target"),
      chamberFilter: ownKey("chamber_filter"),
    };
  }

  connectedCallback() {
    document.addEventListener("visibilitychange", this._onVis);
    // Stream only while the card is visible (other view, scrolled away,
    // collapsed section => connection released).
    if (!this._io && "IntersectionObserver" in window) {
      this._io = new IntersectionObserver((entries) => {
        const vis = entries.some((e) => e.isIntersecting);
        if (vis === this._onScreen) return;
        this._onScreen = vis;
        if (!vis) this._stopStream();
        else this._tickCamera();
      });
    }
    if (this._io) this._io.observe(this);
    if (this._camTimer) return;
    // Fixed one-second tick; _tickStill paces the still image rate
    // itself. This way the stream check works independently of refresh.
    this._camTimer = setInterval(() => {
      this._tickCamera();
      this._lvTick = (this._lvTick || 0) + 1;
      if (this._unlockUntil && Date.now() > this._unlockUntil) { this._unlockUntil = 0; this._applyLock(); }
      if (this._lvTick % 5 === 0) this._tickLayer();
      if (this._lvTick % 10 === 1) this._tickTemps();
    }, 1000);
    this._tickCamera();
  }

  disconnectedCallback() {
    document.removeEventListener("visibilitychange", this._onVis);
    if (this._io) this._io.disconnect();
    if (this._camTimer) clearInterval(this._camTimer);
    this._camTimer = null;
    this._stopStream();
  }
}
