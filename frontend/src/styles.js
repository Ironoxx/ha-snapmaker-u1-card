/** Card styles: everything through theme tokens, each with a fallback. */

export const STYLES = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :host {
    display: block;
    container-type: inline-size;
    container-name: u1;

    --u1-gap: 12px;
    --u1-pad: 16px;

    --u1-surface: var(--ha-card-background, var(--card-background-color, #1a1b21));
    --u1-panel: var(--md-sys-color-surface-container, var(--secondary-background-color, #1e1f25));
    --u1-panel-high: var(--md-sys-color-surface-container-high, var(--u1-panel));
    --u1-panel-highest: var(--md-sys-color-surface-container-highest, var(--u1-panel-high));
    --u1-on: var(--md-sys-color-on-surface, var(--primary-text-color, #e3e1e9));
    --u1-on-variant: var(--md-sys-color-on-surface-variant, var(--secondary-text-color, #c6c6d0));
    --u1-outline: var(--md-sys-color-outline-variant, var(--divider-color, #45464f));
    --u1-primary: var(--md-sys-color-primary, var(--primary-color, #b5c4ff));
    --u1-on-primary: var(--md-sys-color-on-primary, #1c2d61);
    --u1-primary-container: var(--md-sys-color-primary-container, #344479);
    --u1-on-primary-container: var(--md-sys-color-on-primary-container, #dce1ff);
    --u1-error: var(--md-sys-color-error, var(--error-color, #ffb4ab));
    --u1-error-container: var(--md-sys-color-error-container, #93000a);
    --u1-on-error-container: var(--md-sys-color-on-error-container, #ffdad6);
    --u1-warn: var(--warning-color, #ffa600);
    --u1-ok: var(--success-color, #43a047);

    --u1-r-xl: var(--md-sys-shape-corner-extra-large, 28px);
    --u1-r-l: var(--md-sys-shape-corner-large, 16px);
    --u1-r-m: var(--md-sys-shape-corner-medium, 12px);
    --u1-r-s: var(--md-sys-shape-corner-small, 8px);
    --u1-r-full: var(--md-sys-shape-corner-full, 9999px);

    --u1-elev1: var(--md-sys-elevation-level1, 0 1px 3px rgba(0,0,0,.2));
    --u1-elev2: var(--md-sys-elevation-level2, 0 3px 6px rgba(0,0,0,.24));

    --u1-motion: var(--md-sys-motion-standard-effects-default, 200ms cubic-bezier(0.34,0.80,0.34,1));
    --u1-motion-slow: var(--md-sys-motion-standard-spatial-default, 500ms cubic-bezier(0.27,1.06,0.18,1));

    --u1-font: var(--font-family, var(--primary-font-family, system-ui, sans-serif));
    --u1-mono: ui-monospace, "SF Mono", "JetBrains Mono", "Roboto Mono", monospace;

    font-family: var(--u1-font);
    color: var(--u1-on);
  }

  ha-card {
    padding: var(--u1-pad);
    display: flex;
    flex-direction: column;
    gap: var(--u1-gap);
    overflow: hidden;
  }

  /* ── Typography (Material type scale) ────────────────────────────────── */
  .t-title {
    font-size: var(--md-sys-typescale-title-large-size, 22px);
    font-weight: var(--md-sys-typescale-title-large-weight, 400);
    line-height: var(--md-sys-typescale-title-large-line-height, 28px);
  }
  .t-label {
    font-size: var(--md-sys-typescale-label-medium-size, 12px);
    font-weight: var(--md-sys-typescale-label-medium-weight, 500);
    letter-spacing: var(--md-sys-typescale-label-medium-tracking, .5px);
    line-height: var(--md-sys-typescale-label-medium-line-height, 16px);
    color: var(--u1-on-variant);
  }
  .t-body {
    font-size: var(--md-sys-typescale-body-medium-size, 14px);
    line-height: var(--md-sys-typescale-body-medium-line-height, 20px);
  }
  .mono { font-family: var(--u1-mono); font-variant-numeric: tabular-nums; }

  /* ── Header ──────────────────────────────────────────────────────────── */
  .head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .head-icon {
    width: 48px; height: 48px; flex-shrink: 0;
    border-radius: var(--u1-r-l);
    background: var(--u1-primary-container);
    color: var(--u1-on-primary-container);
    display: flex; align-items: center; justify-content: center;
    transition: background var(--u1-motion);
  }
  .head-icon[data-tone="error"] { background: var(--u1-error-container); color: var(--u1-on-error-container); }
  .head-text { flex: 1; min-width: 120px; }
  .head-brand {
    font-size: var(--md-sys-typescale-label-small-size, 11px);
    letter-spacing: .18em; text-transform: uppercase;
    color: var(--u1-on-variant);
  }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; }
  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    height: 32px; padding: 0 12px;
    border-radius: var(--u1-r-s);
    border: 1px solid var(--u1-outline);
    background: transparent;
    color: var(--u1-on-variant);
    font-size: var(--md-sys-typescale-label-large-size, 14px);
    font-weight: var(--md-sys-typescale-label-large-weight, 500);
    white-space: nowrap;
    transition: background var(--u1-motion), color var(--u1-motion), border-color var(--u1-motion);
  }
  .chip[data-tone="active"]   { background: var(--u1-primary-container); color: var(--u1-on-primary-container); border-color: transparent; }
  .chip[data-tone="warn"]     { background: color-mix(in srgb, var(--u1-warn) 22%, transparent); color: var(--u1-warn); border-color: transparent; }
  .chip[data-tone="error"]    { background: var(--u1-error-container); color: var(--u1-on-error-container); border-color: transparent; }
  .chip[data-tone="ok"]       { background: color-mix(in srgb, var(--u1-ok) 20%, transparent); color: var(--u1-ok); border-color: transparent; }
  .chip .dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
  .chip.live .dot { animation: pulse 2s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .3 } }

  /* ── Grid ────────────────────────────────────────────────────────────── */
  .layout { display: grid; gap: var(--u1-gap); grid-template-columns: 1fr; }
  @container u1 (min-width: 660px) {
    .layout { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .span2 { grid-column: span 2; }
  }
  @container u1 (min-width: 1040px) {
    .layout { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .span3 { grid-column: span 3; }
    :host { --u1-pad: 20px; --u1-gap: 16px; }
  }

  /* layout: tablet – camera/job column beside the tabs. Both columns are
     containers named u1 themselves, so the grid rules above follow the
     column width instead of the card width. */
  .tablet { display: grid; gap: var(--u1-gap); grid-template-columns: minmax(0, 1fr); align-items: start; }
  .tablet-side, .tablet-main {
    container-type: inline-size; container-name: u1;
    display: flex; flex-direction: column; gap: var(--u1-gap); min-width: 0;
  }
  .tablet-side > .panel { width: 100%; }
  .tablet-main > .tabs { margin: 0; padding: 0; }
  @container u1 (min-width: 900px) {
    .tablet { grid-template-columns: minmax(0, 11fr) minmax(0, 9fr); }
  }
  @container u1 (min-width: 1500px) {
    .tablet { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  }

  /* Emergency stop: hold mode fills the button while pressed */
  button.danger { position: relative; overflow: hidden; }
  button.danger > span { position: relative; }
  button.danger .hold-fill {
    position: absolute; inset: 0; transform-origin: left; transform: scaleX(0);
    background: color-mix(in srgb, var(--u1-error) 55%, transparent);
  }
  button.danger.holding .hold-fill { transform: scaleX(1); transition: transform 1s linear; }
  button.danger.hold { touch-action: none; user-select: none; -webkit-user-select: none; }
  button.danger.strong { background: var(--u1-error); color: var(--md-sys-color-on-error, #690005); }

  /* Confirm dialog */
  dialog.u1confirm {
    border: none; padding: 0; margin: auto; width: min(420px, calc(100vw - 32px));
    border-radius: var(--u1-r-xl); background: var(--u1-panel-high); color: var(--u1-on);
    box-shadow: var(--md-sys-elevation-level3, 0 8px 24px rgba(0,0,0,.4));
  }
  dialog.u1confirm::backdrop { background: rgba(0,0,0,.5); }
  dialog.u1confirm .confirm-head { display: flex; gap: 12px; align-items: center; }
  dialog.u1confirm .confirm-head ha-icon { --mdc-icon-size: 28px; color: var(--u1-primary); flex-shrink: 0; }
  dialog.u1confirm[data-tone="error"] .confirm-head ha-icon { color: var(--u1-error); }
  dialog.u1confirm .t-body { color: var(--u1-on-variant); }
  dialog.u1confirm .dlg-actions { flex-wrap: wrap; }
  dialog.u1confirm .dlg-actions button { min-width: 0; flex: 1 1 140px; }

  .panel {
    background: var(--u1-panel);
    border-radius: var(--u1-r-l);
    padding: 14px;
    display: flex; flex-direction: column; gap: 12px;
    min-width: 0;
  }
  .panel-head { display: flex; align-items: center; gap: 8px; }
  .panel-head ha-icon { --mdc-icon-size: 18px; color: var(--u1-on-variant); }
  .panel-title {
    font-size: var(--md-sys-typescale-title-small-size, 14px);
    font-weight: var(--md-sys-typescale-title-small-weight, 500);
    letter-spacing: var(--md-sys-typescale-title-small-tracking, .1px);
  }

  /* ── Image area ──────────────────────────────────────────────────────── */
  .stage { padding: 0; overflow: hidden; gap: 0; }
  .frame {
    position: relative; width: 100%;
    background: var(--md-sys-color-surface-container-lowest, #0d0e13);
    overflow: hidden;
  }
  .frame img {
    position: absolute; inset: 0; width: 100%; height: 100%;
    display: block; background: inherit;
  }
  .frame .veil {
    position: absolute; inset: 0; pointer-events: none;
    transition: backdrop-filter var(--u1-motion), background var(--u1-motion);
  }
  .frame[data-dim="1"] .veil { background: rgba(0,0,0,.45); }
  .badge-stale {
    position: absolute; top: 10px; right: 10px; z-index: 3; display: none;
    align-items: center; gap: 6px; height: 28px; padding: 0 10px;
    border-radius: var(--u1-r-s);
    background: color-mix(in srgb, var(--u1-warn) 90%, black);
    color: #000;
    font-size: var(--md-sys-typescale-label-small-size, 11px); font-weight: 700;
  }
  .frame[data-stale="1"] .badge-stale { display: inline-flex; }
  /* Zoom: the page scrolls vertically, two fingers go to the card */
  .stage .frame { touch-action: pan-y; }
  .stage .frame.zoomed { touch-action: none; cursor: grab; user-select: none; }
  .stage .frame.zoomed:active { cursor: grabbing; }
  .stage .frame img { -webkit-user-drag: none; user-select: none; }
  .frame img { will-change: transform; }
  .zoom-ctl { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); z-index: 3;
    display: flex; flex-direction: column; gap: 6px; opacity: .55; transition: opacity var(--u1-motion); }
  .frame:hover .zoom-ctl, .frame.zoomed .zoom-ctl { opacity: 1; }
  button.zoom-btn { width: 36px; height: 36px; padding: 0; border-radius: 50%; background: rgba(0,0,0,.55); color: #fff; box-shadow: none; }
  button.zoom-btn ha-icon { --mdc-icon-size: 20px; }
  button.zoom-btn[hidden] { display: none; }
  .zoom-badge { position: absolute; left: 50%; top: 10px; transform: translateX(-50%); z-index: 3; padding: 2px 8px; border-radius: var(--u1-r-s);
    background: rgba(0,0,0,.55); color: #fff; font-size: 12px; font-family: var(--u1-mono); }
  .zoom-badge[hidden] { display: none; }
  .frame:fullscreen { height: 100% !important; min-height: 0 !important; background: #000; }
  .frame:fullscreen img { object-fit: contain !important; }
  .thumb {
    position: absolute; left: 10px; bottom: 10px; z-index: 3;
    background: color-mix(in srgb, var(--u1-panel) 85%, transparent);
    border: 1px solid var(--u1-outline);
    border-radius: var(--u1-r-m);
    padding: 6px; display: flex; flex-direction: column; gap: 4px;
    align-items: center; max-width: 130px;
    backdrop-filter: blur(8px);
  }
  .thumb img { position: static; width: 72px; height: 72px; object-fit: contain; background: transparent; }
  .thumb span {
    font-size: 10px; color: var(--u1-on-variant); max-width: 118px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .overlay {
    position: absolute; inset: 0; z-index: 2;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
    text-align: center; padding: 16px;
  }
  .overlay-ring {
    width: 64px; height: 64px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: var(--u1-primary-container); color: var(--u1-on-primary-container);
    box-shadow: var(--u1-elev2);
  }
  .overlay-ring[data-tone="warn"]  { background: color-mix(in srgb, var(--u1-warn) 30%, var(--u1-panel)); color: var(--u1-warn); }
  .overlay-ring[data-tone="error"] { background: var(--u1-error-container); color: var(--u1-on-error-container); }
  .overlay-ring ha-icon { --mdc-icon-size: 32px; }
  .overlay-title {
    font-size: var(--md-sys-typescale-title-medium-size, 16px);
    font-weight: var(--md-sys-typescale-title-medium-weight, 500);
  }
  .overlay-sub { font-size: 12px; color: var(--u1-on-variant); max-width: 30ch; }

  .stage-actions {
    display: flex; gap: 8px; padding: 12px; flex-wrap: wrap;
    border-top: 1px solid var(--u1-outline);
  }

  /* ── Controls ────────────────────────────────────────────────────────── */
  button {
    font-family: inherit; cursor: pointer; border: none;
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    height: 40px; padding: 0 20px;
    border-radius: var(--u1-r-full);
    background: var(--u1-panel-highest); color: var(--u1-on);
    font-size: var(--md-sys-typescale-label-large-size, 14px);
    font-weight: var(--md-sys-typescale-label-large-weight, 500);
    letter-spacing: var(--md-sys-typescale-label-large-tracking, .1px);
    transition: background var(--u1-motion), color var(--u1-motion), box-shadow var(--u1-motion);
  }
  button ha-icon { --mdc-icon-size: 18px; }
  button:hover { background: color-mix(in srgb, var(--u1-on) 10%, var(--u1-panel-highest)); }
  button:active { box-shadow: none; transform: scale(.98); }
  button:focus-visible { outline: 3px solid var(--u1-primary); outline-offset: 2px; }
  button[disabled] { opacity: .38; pointer-events: none; }
  button.filled { background: var(--u1-primary); color: var(--u1-on-primary); box-shadow: var(--u1-elev1); }
  button.filled:hover { background: color-mix(in srgb, var(--u1-on-primary) 8%, var(--u1-primary)); }
  button.tonal { background: var(--u1-primary-container); color: var(--u1-on-primary-container); }
  button.danger { background: var(--u1-error-container); color: var(--u1-on-error-container); }
  button.outline { background: transparent; border: 1px solid var(--u1-outline); color: var(--u1-on); }
  button.on { background: color-mix(in srgb, var(--u1-warn) 26%, transparent); color: var(--u1-warn); }
  button.grow { flex: 1 1 130px; }
  button.icon { width: 40px; padding: 0; }

  /* ── Value grid ──────────────────────────────────────────────────────── */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(92px, 1fr)); gap: 10px; }
  .stat {
    background: var(--u1-panel-high); border-radius: var(--u1-r-m);
    padding: 10px; min-width: 0;
    display: flex; flex-direction: column; justify-content: space-between;
  }
  .stat .k {
    font-size: var(--md-sys-typescale-label-small-size, 11px);
    letter-spacing: .04em; text-transform: uppercase; color: var(--u1-on-variant);
    line-height: 1.25; hyphens: auto; overflow-wrap: anywhere;
  }
  .stat .v {
    font-family: var(--u1-mono); font-variant-numeric: tabular-nums;
    font-size: 18px; margin-top: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .stat .v.sm { font-size: 14px; }

  /* ── Progress ────────────────────────────────────────────────────────── */
  .job-file {
    font-family: var(--u1-mono); font-size: 13px; color: var(--u1-on-variant);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .job-pct-row { display: flex; align-items: baseline; gap: 10px; }
  .job-pct {
    font-family: var(--u1-mono); font-variant-numeric: tabular-nums;
    font-size: var(--md-sys-typescale-display-small-size, 36px);
    line-height: 1;
  }
  .track {
    height: var(--ha-progress-bar-track-height, 8px);
    border-radius: var(--ha-progress-bar-border-radius, 8px);
    background: var(--ha-progress-bar-track-color, var(--u1-panel-highest));
    overflow: hidden;
  }
  .track > i {
    display: block; height: 100%; width: 0%;
    border-radius: inherit;
    background: var(--ha-progress-bar-indicator-color, var(--u1-primary));
    transition: width var(--u1-motion-slow);
  }
  .track[data-tone="warn"]  > i { background: var(--u1-warn); }
  .track[data-tone="error"] > i { background: var(--u1-error); }

  /* ── Print heads ─────────────────────────────────────────────────────── */
  .heads { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  .head-card {
    background: var(--u1-panel-high); border-radius: var(--u1-r-m);
    padding: 10px; display: flex; flex-direction: column; gap: 8px;
    border: 2px solid transparent;
    transition: border-color var(--u1-motion), background var(--u1-motion);
    min-width: 0;
  }
  .head-card[data-active="1"] { border-color: var(--u1-primary); background: var(--u1-panel-highest); }
  .head-card-top { display: flex; align-items: center; gap: 8px; }
  .spool { width: 34px; height: 34px; flex-shrink: 0; }
  .head-name { font-weight: 600; font-size: 14px; }
  .head-mat { font-size: 11px; color: var(--u1-on-variant); }
  .head-temp { font-family: var(--u1-mono); font-size: 17px; font-variant-numeric: tabular-nums; }
  .head-temp .tgt { font-size: 12px; color: var(--u1-on-variant); }
  .mini { display: flex; justify-content: space-between; font-size: 11px; color: var(--u1-on-variant); }
  .pill {
    align-self: flex-start; font-size: 10px; font-weight: 700; letter-spacing: .06em;
    padding: 2px 8px; border-radius: var(--u1-r-full);
    background: color-mix(in srgb, var(--u1-ok) 20%, transparent); color: var(--u1-ok);
  }
  .pill[data-empty="1"] { background: color-mix(in srgb, var(--u1-error) 18%, transparent); color: var(--u1-error); }

  /* ── Sliders ─────────────────────────────────────────────────────────── */
  .ctl { display: flex; flex-direction: column; gap: 6px; }
  .ctl-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .ctl-val { font-family: var(--u1-mono); font-size: 14px; font-variant-numeric: tabular-nums; }
  input[type="range"] {
    -webkit-appearance: none; appearance: none; width: 100%;
    height: var(--ha-slider-track-size, 8px);
    border-radius: var(--u1-r-full);
    background: var(--ha-slider-track-color, var(--u1-panel-highest));
    outline: none; margin: 6px 0;
  }
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--u1-primary); border: none; cursor: pointer;
    box-shadow: var(--u1-elev1);
    transition: transform var(--u1-motion);
  }
  input[type="range"]::-webkit-slider-thumb:active { transform: scale(1.25); }
  input[type="range"]::-moz-range-thumb {
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--u1-primary); border: none; cursor: pointer;
  }
  input[type="range"]:focus-visible { outline: 3px solid var(--u1-primary); outline-offset: 4px; }
  .presets { display: flex; gap: 6px; flex-wrap: wrap; }
  .ctl.locked input[type="range"] { pointer-events: none; opacity: .45; }
  .ctl.locked .presets { opacity: .6; }
  button.lock-btn { cursor: pointer; box-shadow: none; gap: 4px; }
  button.lock-btn ha-icon { --mdc-icon-size: 14px; }
  button.lock-btn[aria-pressed="true"] { background: color-mix(in srgb, var(--u1-warn) 22%, transparent); color: var(--u1-warn); border-color: transparent; }
  .preset {
    height: 28px; padding: 0 12px; font-size: 12px;
    border-radius: var(--u1-r-s);
    background: transparent; border: 1px solid var(--u1-outline); color: var(--u1-on-variant);
  }
  .preset:hover { background: var(--u1-panel-highest); color: var(--u1-on); }

  /* ── List ────────────────────────────────────────────────────────────── */
  .rows { display: flex; flex-direction: column; }
  .row {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 9px 0; border-bottom: 1px solid var(--u1-outline);
    font-size: var(--md-sys-typescale-body-medium-size, 14px);
  }
  .row:last-child { border-bottom: none; }
  .row .k { color: var(--u1-on-variant); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .row .v { font-family: var(--u1-mono); font-variant-numeric: tabular-nums; text-align: right; }

  details { border-radius: var(--u1-r-m); }
  details > summary {
    list-style: none; cursor: pointer; display: flex; align-items: center; gap: 8px;
    padding: 4px 0; color: var(--u1-on-variant);
    font-size: var(--md-sys-typescale-title-small-size, 14px);
    font-weight: var(--md-sys-typescale-title-small-weight, 500);
  }
  details > summary::-webkit-details-marker { display: none; }
  details > summary ha-icon { --mdc-icon-size: 18px; transition: transform var(--u1-motion); }
  details[open] > summary ha-icon.caret { transform: rotate(180deg); }
  details > .body { padding-top: 10px; }

  .switches { display: flex; gap: 6px; flex-wrap: wrap; }

  /* ── Files ───────────────────────────────────────────────────────────── */
  .files { display: grid; grid-template-columns: repeat(auto-fill, minmax(116px, 1fr)); gap: 10px; }
  button.file {
    height: auto; padding: 8px; flex-direction: column; gap: 6px;
    border-radius: var(--u1-r-m);
    background: var(--u1-panel-high); color: var(--u1-on);
    text-align: center; min-width: 0;
  }
  button.file:hover { background: var(--u1-panel-highest); }
  .file-thumb {
    width: 100%; aspect-ratio: 1 / 1;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--u1-r-s);
    background: var(--md-sys-color-surface-container-lowest, rgba(0,0,0,.25));
    overflow: hidden;
  }
  .file-thumb img { width: 100%; height: 100%; object-fit: contain; }
  .tsvg { width: 100%; height: auto; display: block; }
  .tsvg .tgrid { stroke: var(--u1-outline); stroke-width: .5; opacity: .5; }
  .tsvg .tax { font-size: 8px; fill: var(--u1-on-variant); font-family: var(--u1-mono); }
  .tlegend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; color: var(--u1-on-variant); margin-top: 4px; }
  .tlegend i { display: inline-block; width: 10px; height: 3px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
  .ftools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .ftools input[type=search], .ftools select {
    flex: 1 1 140px; min-width: 0; height: 36px; padding: 0 10px; border-radius: var(--u1-r-s);
    border: 1px solid var(--u1-outline); background: var(--u1-panel-high); color: var(--u1-on); font: inherit;
  }
  .ftools select { flex: 0 0 auto; }
  .fchips { display: flex; gap: 6px; flex-wrap: wrap; }
  .fchips button[aria-pressed="true"] { background: var(--u1-primary); color: var(--u1-on-primary, #fff); }
  .files-more { display: flex; flex-direction: column; gap: 4px; }
  .files-more button { justify-content: flex-start; text-align: left; }
  dialog.u1photo { padding: 0; border: 0; background: transparent; max-width: 96vw; max-height: 92vh; overflow: visible; }
  dialog.u1photo::backdrop { background: rgba(0,0,0,.8); }
  dialog.u1photo img { display: block; max-width: 96vw; max-height: 92vh; border-radius: var(--u1-r-m); object-fit: contain; cursor: zoom-out; }
  dialog.u1photo .photo-close { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,.55); color: #fff; }
  .hist-photo { width: 44px; height: 44px; border-radius: var(--u1-r-s); object-fit: cover; cursor: zoom-in; flex-shrink: 0; }
  .runout { font-size: 11px; color: var(--u1-warn); }
  .selftest-wrap { display: flex; flex-direction: column; gap: 8px; padding-top: 10px; align-items: flex-start; }
  .selftest { display: flex; flex-direction: column; gap: 4px; }
  .selftest .st { display: flex; gap: 8px; align-items: baseline; font-size: 13px; }
  .selftest .st b { width: 16px; flex-shrink: 0; text-align: center; }
  .mat-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .mat-table td, .mat-table th { padding: 4px 6px; text-align: right; border-bottom: 1px solid color-mix(in srgb, var(--u1-outline) 40%, transparent); }
  .mat-table td:first-child, .mat-table th:first-child { text-align: left; }
  .mat-table th { font-weight: 500; color: var(--u1-on-variant); font-size: 11px; }
  .colors { display: flex; flex-wrap: wrap; gap: 6px; }
  .colors span { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--u1-on-variant); }
  .colors i { width: 14px; height: 14px; border-radius: 50%; border: 1px solid var(--u1-outline); display: inline-block; }
  /* Dark thumbnail (black part) -> light background, very light -> dark background */
  .file-thumb, .dlg-thumb, .hist-thumb, .thumb { transition: background var(--u1-motion); }
  [data-tone-bg="dark"] { background: #d4d6dc !important; }
  [data-tone-bg="light"] { background: #24262c !important; }
  /* File name in the camera thumbnail: text colour matching the recoloured background */
  .thumb[data-tone-bg="dark"] span { color: #2b2d33; }
  .thumb[data-tone-bg="light"] span { color: #d4d6dc; }
  .file-thumb ha-icon { --mdc-icon-size: 32px; color: var(--u1-on-variant); }
  .file-name {
    font-size: 12px; font-weight: 500; line-height: 1.3;
    max-width: 100%; overflow: hidden; text-overflow: ellipsis;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    white-space: normal; word-break: break-word;
  }
  .file-meta { font-size: 11px; color: var(--u1-on-variant); font-family: var(--u1-mono); }

  .file-dots { display: flex; gap: 3px; justify-content: center; flex-wrap: wrap; }
  .file-dots i { width: 10px; height: 10px; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(0,0,0,.25); }
  .head-vendor { font-size: 11px; color: var(--u1-on-variant); opacity: .8; }
  .spool-line {
    all: unset; box-sizing: border-box; cursor: pointer; display: flex; flex-direction: column; gap: 4px;
    width: 100%; padding: 6px 8px; border-radius: 10px; background: var(--u1-panel-highest);
    font-size: 11px; color: var(--u1-on-variant);
  }
  .spool-line:hover { outline: 1px solid var(--u1-outline); }
  .spool-line:focus-visible { outline: 2px solid var(--u1-primary); }
  .spool-line[data-none] { flex-direction: row; align-items: center; gap: 6px; }
  .spool-line ha-icon { --mdc-icon-size: 16px; }
  .spool-top { display: flex; gap: 6px; align-items: baseline; min-width: 0; }
  .spool-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--u1-on); }
  .spool-rest { font-family: var(--u1-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .spool-track { height: 4px; border-radius: 2px; background: color-mix(in srgb, var(--u1-outline) 40%, transparent); overflow: hidden; }
  .spool-track i { display: block; height: 100%; background: var(--u1-primary); border-radius: 2px; }
  .spool-line[data-low="1"] .spool-track i { background: var(--u1-warn); }
  .spool-line[data-low="1"] .spool-rest { color: var(--u1-warn); }
  .slot-rest { font-size: 10px; opacity: .75; font-variant-numeric: tabular-nums; }
  .dlg-error[hidden] { display: none; }
  .spool-list { display: flex; flex-direction: column; gap: 6px; max-height: 55vh; overflow: auto; }
  .spool-opt {
    all: unset; box-sizing: border-box; cursor: pointer; display: flex; align-items: center; gap: 10px;
    padding: 10px 12px; border-radius: 12px; border: 1px solid color-mix(in srgb, var(--u1-outline) 50%, transparent);
  }
  .spool-opt[aria-pressed="true"] { border-color: var(--u1-primary); background: color-mix(in srgb, var(--u1-primary) 14%, transparent); }
  .spool-opt:hover { border-color: var(--u1-outline); }
  .spool-opt:focus-visible { outline: 2px solid var(--u1-primary); }
  .spool-opt ha-icon { --mdc-icon-size: 20px; color: var(--u1-on-variant); }
  .spool-opt-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .spool-opt-text > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .spool-dot { width: 18px; height: 18px; border-radius: 50%; background: var(--fil); flex-shrink: 0;
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--u1-on) 25%, transparent); }
  .rfid {
    font-size: 9px; font-weight: 700; letter-spacing: .08em; vertical-align: middle;
    padding: 1px 5px; border-radius: var(--u1-r-full);
    background: var(--u1-primary-container); color: var(--u1-on-primary-container);
  }

  /* ── Print dialog ────────────────────────────────────────────────────── */
  dialog.u1dlg {
    border: none; padding: 0; margin: auto;
    width: min(640px, calc(100vw - 24px)); max-height: calc(100vh - 32px);
    border-radius: var(--u1-r-xl);
    background: var(--u1-panel-high); color: var(--u1-on);
    box-shadow: var(--md-sys-elevation-level3, 0 8px 24px rgba(0,0,0,.4));
  }
  dialog.u1dlg::backdrop { background: rgba(0,0,0,.5); }
  .dlg { padding: 22px; display: flex; flex-direction: column; gap: 12px; }
  .dlg-head { display: flex; gap: 14px; align-items: center; }
  .dlg-thumb {
    width: 72px; height: 72px; flex-shrink: 0; border-radius: var(--u1-r-m); overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    background: var(--md-sys-color-surface-container-lowest, rgba(0,0,0,.25));
  }
  .dlg-thumb img { width: 100%; height: 100%; object-fit: contain; }
  .dlg-file-actions { display: flex; gap: 2px; margin: 2px 0 0 -8px; }
  .dlg-thumb ha-icon { --mdc-icon-size: 32px; color: var(--u1-on-variant); }
  .dlg-title {
    font-size: var(--md-sys-typescale-headline-small-size, 22px); line-height: 1.25;
    overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
    -webkit-line-clamp: 2; -webkit-box-orient: vertical; word-break: break-word;
  }
  .dlg-sec {
    margin-top: 6px; font-size: 11px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: var(--u1-on-variant);
  }
  .map { display: flex; flex-direction: column; gap: 8px; }
  .map-row {
    display: grid; grid-template-columns: minmax(120px, 1fr) auto; gap: 8px 12px; align-items: center;
    padding: 10px 12px; border-radius: var(--u1-r-l); background: var(--u1-panel);
  }
  .map-row[data-issue="error"] { box-shadow: inset 0 0 0 1px var(--u1-error); }
  .map-row[data-issue="warn"] { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--u1-warn) 70%, transparent); }
  .map-src { display: flex; gap: 10px; align-items: center; min-width: 0; }
  .map-src-text { min-width: 0; }
  .map-type { font-weight: 600; }
  .map-src .t-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .fil-badge {
    width: 30px; height: 30px; flex-shrink: 0; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; background: var(--fil);
    color: var(--on-fil, #fff);
    box-shadow: inset 0 0 0 1px rgba(0,0,0,.3);
  }
  .map-slots { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
  button.slot-btn {
    height: auto; width: 64px; padding: 6px 4px; flex-direction: column; gap: 2px;
    border-radius: var(--u1-r-m); background: var(--u1-panel-high);
    box-shadow: inset 0 0 0 1px var(--u1-outline);
  }
  button.slot-btn .spool { width: 26px; height: 26px; }
  button.slot-btn[aria-pressed="true"] {
    background: var(--u1-primary-container); color: var(--u1-on-primary-container);
    box-shadow: inset 0 0 0 2px var(--u1-primary);
  }
  button.slot-btn[data-empty="1"] { opacity: .55; }
  .slot-no { font-size: 12px; font-weight: 700; }
  .slot-type { font-size: 10px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .map-issue {
    grid-column: 1 / -1; display: flex; gap: 6px; align-items: center;
    font-size: 12px; color: var(--u1-warn);
  }
  .map-row[data-issue="error"] .map-issue { color: var(--u1-error); }
  .map-issue ha-icon { --mdc-icon-size: 16px; }
  .chks { display: flex; gap: 6px 18px; flex-wrap: wrap; }
  label.chk { display: inline-flex; gap: 8px; align-items: center; cursor: pointer; font-size: 14px; }
  label.chk input { width: 18px; height: 18px; accent-color: var(--u1-primary); }
  label.chk.confirm {
    margin-top: 6px; padding: 10px 12px; border-radius: var(--u1-r-m);
    background: color-mix(in srgb, var(--u1-warn) 12%, transparent);
  }
  .dlg-error {
    display: flex; gap: 8px; align-items: flex-start; padding: 10px 12px;
    border-radius: var(--u1-r-m); background: var(--u1-error-container); color: var(--u1-on-error-container);
    font-size: 13px; line-height: 1.4;
  }
  .dlg-error ha-icon { --mdc-icon-size: 18px; flex-shrink: 0; }
  /* State accent: thin frame in the theme colour of the state (option state_accent) */
  ha-card[data-accent] { transition: box-shadow var(--u1-motion); }
  ha-card[data-accent="active"] { box-shadow: 0 0 0 2px color-mix(in srgb, var(--u1-primary) 70%, transparent), 0 0 22px -4px color-mix(in srgb, var(--u1-primary) 45%, transparent); }
  ha-card[data-accent="warn"]   { box-shadow: 0 0 0 2px color-mix(in srgb, var(--u1-warn) 75%, transparent), 0 0 22px -4px color-mix(in srgb, var(--u1-warn) 45%, transparent); }
  ha-card[data-accent="error"]  { box-shadow: 0 0 0 2px color-mix(in srgb, var(--u1-error) 80%, transparent), 0 0 22px -4px color-mix(in srgb, var(--u1-error) 50%, transparent); }
  ha-card[data-accent="ok"]     { box-shadow: 0 0 0 2px color-mix(in srgb, var(--u1-ok) 70%, transparent); }

  /* Head details */
  .head-card-top[data-headopen] { cursor: pointer; border-radius: var(--u1-r-m); }
  .head-card-top[data-headopen]:hover .head-name { color: var(--u1-primary); }
  .head-tags { display: flex; align-items: center; justify-content: space-between; gap: 6px; flex-wrap: wrap; }
  .head-tags .pill { margin: 0; align-self: center; }
  button.head-info {
    height: 28px; padding: 0 10px 0 8px; gap: 4px; font-size: 12px;
    background: var(--u1-primary-container); color: var(--u1-on-primary-container); box-shadow: none; }
  button.head-info:hover { background: color-mix(in srgb, var(--u1-on-primary-container) 12%, var(--u1-primary-container)); }
  button.head-info ha-icon { --mdc-icon-size: 16px; }
  .spool-dot.big { width: 32px; height: 32px; box-shadow: inset 0 0 0 1px rgba(127,127,127,.5); }
  .head-sub { margin: 12px 0 4px; }
  .head-rfid .row { padding: 4px 0; }
  .head-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  .head-form label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--u1-on-variant); }
  .head-form label.check { flex-direction: row; align-items: center; grid-column: 1 / -1; color: var(--u1-on); font-size: 13px; }
  .head-form select, .head-form input:not([type="checkbox"]) {
    font: inherit; font-size: 14px; color: var(--u1-on); background: var(--u1-panel-high);
    border: 1px solid var(--u1-outline); border-radius: var(--u1-r-s); padding: 8px; min-height: 38px; box-sizing: border-box; }
  .head-form input[type="color"] { padding: 2px; cursor: pointer; }
  .head-form .dlg-error, .head-form .dlg-actions { grid-column: 1 / -1; }
  .chip-row { display: inline-flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
  .rows .chip[data-prefset], .rows .chip[data-prefsen] { height: 28px; padding: 0 12px; font-size: 12px; cursor: pointer; box-shadow: none; }
  .rows .chip[aria-pressed="true"], .rows .chip.sel { background: var(--u1-primary-container); color: var(--u1-on-primary-container); border-color: transparent; }
  .dlg-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
  .dlg-actions button { min-width: 120px; }
  ha-icon.spin { animation: u1spin 1s linear infinite; }
  ha-icon.spin-slow { animation: pulse 2s ease-in-out infinite; }

  /* ── Power switch ────────────────────────────────────────────────────── */
  button.chip.pwr { cursor: pointer; box-shadow: none; padding: 0 12px; min-width: 0; height: 32px; }
  button.chip.pwr[disabled] { opacity: 1; }
  button.chip.pwr span { font-family: var(--u1-mono); font-variant-numeric: tabular-nums; }
  .chip.sm { height: 24px; padding: 0 8px; font-size: 12px; }
  .offline button { margin-top: 6px; }
  .dlg-note {
    display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px;
    border-radius: var(--u1-r-m); font-size: 13px;
    background: var(--u1-primary-container); color: var(--u1-on-primary-container);
  }
  .dlg-note[data-tone="error"] { background: var(--u1-error-container); color: var(--u1-on-error-container); }
  .dlg-note ha-icon { --mdc-icon-size: 18px; flex-shrink: 0; }

  /* ── History ─────────────────────────────────────────────────────────── */
  .hist-list { display: flex; flex-direction: column; }
  .hist {
    display: flex; align-items: center; gap: 12px; padding: 8px 0;
    border-bottom: 1px solid color-mix(in srgb, var(--u1-outline) 50%, transparent);
  }
  .hist:last-child { border-bottom: none; }
  .hist-thumb {
    width: 44px; height: 44px; flex-shrink: 0; border-radius: var(--u1-r-s);
    background: var(--u1-panel-highest); display: flex; align-items: center; justify-content: center; overflow: hidden;
  }
  .hist-thumb img { width: 100%; height: 100%; object-fit: contain; }
  .hist-thumb ha-icon { --mdc-icon-size: 22px; color: var(--u1-on-variant); }
  .hist-main { flex: 1; min-width: 0; }
  .hist-name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hist-main .t-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hist-side { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
  .last-print { display: flex; gap: 12px; align-items: center; }
  .last-thumb { width: 64px; height: 64px; }
  .hist-cost { font-family: var(--u1-mono); font-variant-numeric: tabular-nums; font-size: 13px; }

  /* ── Timelapses ──────────────────────────────────────────────────────── */
  .tl-thumb { position: relative; aspect-ratio: 16 / 9; height: auto; }
  .tl-thumb img { object-fit: cover; }
  .tl-play {
    position: absolute; inset: 0; margin: auto; --mdc-icon-size: 36px !important;
    color: #fff !important; filter: drop-shadow(0 1px 3px rgba(0,0,0,.6)); width: 36px; height: 36px;
  }
  dialog.u1video { max-width: min(960px, calc(100vw - 32px)); width: 100%; }
  .dlg.vid { gap: 10px; }
  .vid-box {
    background: #000; border-radius: var(--u1-r-m); overflow: hidden; min-height: 200px;
    display: flex; align-items: center; justify-content: center; color: #fff;
  }
  .vid-box video { width: 100%; max-height: 70vh; display: block; }
  a.btn {
    display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 16px;
    border-radius: var(--u1-r-full, 20px); border: 1px solid var(--u1-outline); color: var(--u1-on);
    text-decoration: none; font-weight: 500; font-size: 14px;
  }
  a.btn ha-icon { --mdc-icon-size: 18px; }
  @keyframes u1spin { to { transform: rotate(360deg); } }
  @container u1 (max-width: 520px) {
    .map-row { grid-template-columns: 1fr; }
    .map-slots { justify-content: flex-start; }
  }

  /* ── Messages ────────────────────────────────────────────────────────── */
  .alerts { display: flex; flex-direction: column; gap: 6px; }
  .alert {
    display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: var(--u1-r-m);
    background: color-mix(in srgb, var(--u1-warn) 16%, transparent); color: var(--u1-on);
  }
  .alert[data-level="error"] { background: var(--u1-error-container); color: var(--u1-on-error-container); }
  .alert ha-icon { --mdc-icon-size: 20px; flex-shrink: 0; color: var(--u1-warn); }
  .alert > div { flex: 1; min-width: 0; }
  .alert > button { flex-shrink: 0; align-self: center; }
  .alert[data-level="error"] ha-icon { color: inherit; }
  .alert-text { font-weight: 500; }

  /* ── Queue, upload, reprint ──────────────────────────────────────────── */
  button.ghost { background: transparent; box-shadow: none; }
  button.ghost:hover { background: color-mix(in srgb, var(--u1-on) 8%, transparent); }
  .q-list { display: flex; flex-direction: column; gap: 6px; }
  .q-item {
    display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: var(--u1-r-m);
    background: var(--u1-panel-high);
  }
  .q-item[data-first="1"] { box-shadow: inset 0 0 0 1px var(--u1-primary); }
  .q-pos { width: 22px; text-align: center; font-family: var(--u1-mono); color: var(--u1-on-variant); flex-shrink: 0; }
  .q-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--u1-on-variant); margin-top: 2px; flex-wrap: wrap; }
  .q-meta ha-icon { --mdc-icon-size: 15px; }
  .q-meta .file-dots { margin: 0; }
  .q-btns { display: flex; gap: 4px; align-items: center; flex-shrink: 0; }
  .q-btns button.filled { height: 36px; padding: 0 14px; }
  .upl { display: flex; align-items: center; gap: 10px; font-size: 13px; }
  .upl ha-icon { --mdc-icon-size: 18px; color: var(--u1-primary); flex-shrink: 0; }
  .upl-name { max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .upl .track { flex: 1; }
  .hist-top { display: inline-flex; align-items: center; gap: 2px; }
  .hist-top button.icon { width: 32px; height: 32px; }
  label.pause-in { display: flex; align-items: center; gap: 8px; font-size: 14px; flex-wrap: wrap; }
  label.pause-in ha-icon { --mdc-icon-size: 18px; color: var(--u1-on-variant); }
  label.pause-in input {
    flex: 1; min-width: 120px; height: 36px; padding: 0 10px; border-radius: var(--u1-r-s);
    border: 1px solid var(--u1-outline); background: var(--u1-panel-high); color: var(--u1-on); font: inherit;
  }
  label.pause-in input:focus { outline: 2px solid var(--u1-primary); outline-offset: -1px; }

  /* ── Chart ───────────────────────────────────────────────────────────── */
  .chart-chips { margin-left: auto; display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; }
  .chart-chips .chip { height: 28px; padding: 0 10px; font-size: 12px; cursor: pointer; box-shadow: none; }
  .chart-chips .chip.sel { background: var(--u1-primary-container); color: var(--u1-on-primary-container); border-color: transparent; }
  .chart { display: flex; align-items: stretch; gap: 4px; height: 150px; padding-top: 6px; }
  .bar { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 4px; min-width: 0; }
  .bar-col { width: 100%; max-width: 34px; display: flex; flex-direction: column; justify-content: flex-end; min-height: 2px;
    border-radius: 4px 4px 0 0; overflow: hidden; background: var(--u1-panel-highest); }
  .bar-col i { display: block; width: 100%; }
  i.bar-ok { background: var(--u1-primary); }
  i.bar-fail { background: color-mix(in srgb, var(--u1-error) 70%, var(--u1-panel)); }
  .bar-x { font-size: 10px; color: var(--u1-on-variant); white-space: nowrap; overflow: hidden; max-width: 100%; }
  .legend { display: flex; align-items: center; gap: 6px; }
  .legend i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-left: 8px; }
  .legend i:first-child { margin-left: 0; }
  .top-file { margin-right: 10px; }

  /* ── Maintenance, archive ────────────────────────────────────────────── */
  .m-list { display: flex; flex-direction: column; gap: 10px; }
  .m-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .m-name { flex: 1; min-width: 0; font-size: 14px; }
  .m-top button.icon { width: 32px; height: 32px; }
  .m-item[data-due="1"] .m-name { color: var(--u1-error); font-weight: 500; }
  .arch-head { display: flex; align-items: center; gap: 8px; margin-top: 14px; }
  .arch-head ha-icon { --mdc-icon-size: 18px; color: var(--u1-on-variant); }

  /* ── Layer view ──────────────────────────────────────────────────────── */
  .lv { position: relative; aspect-ratio: 1 / 1; max-height: 360px; width: 100%; border-radius: var(--u1-r-m);
    /* Mid grey: black and white filaments stay visible in light and dark themes */
    background: color-mix(in srgb, #7a7d86 70%, var(--u1-panel)); overflow: hidden; display: flex; align-items: center; justify-content: center; }
  .lv svg { width: 100%; height: 100%; display: block; }
  .lv-bed { fill: none; stroke: rgba(255,255,255,.18); stroke-width: .3; stroke-dasharray: 2 2; }
  .lv-paths polyline { fill: none; stroke-linecap: round; stroke-linejoin: round; transition: opacity .4s; }
  .lv-paths polyline.todo { opacity: .28; }
  .lv-empty { fill: var(--u1-on-variant); font-size: 6px; text-anchor: middle; }
  .lv-msg { padding: 16px; text-align: center; }
  .lv-legend { display: flex; gap: 6px 14px; flex-wrap: wrap; font-size: 12px; color: var(--u1-on-variant); }
  .lv-legend span { display: inline-flex; align-items: center; gap: 6px; }
  .lv-legend i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; box-shadow: inset 0 0 0 1px rgba(127,127,127,.5); }
  .lv-legend i.lv-done { background: var(--u1-on); border-radius: 2px; }
  .lv-legend i.lv-todo { background: var(--u1-on); opacity: .2; border-radius: 2px; margin-left: 6px; }
  .lv-hint { margin-left: auto; }
  .lv-paths polyline.excl { opacity: .08; }
  .lv-objs polygon { fill: transparent; stroke: var(--u1-on-variant); stroke-width: 1px; stroke-dasharray: 4 3; opacity: .6; }
  .lv-objs polygon.pick { cursor: pointer; pointer-events: all; }
  .lv-objs polygon.pick:hover { fill: color-mix(in srgb, var(--u1-error) 12%, transparent); stroke: var(--u1-error); opacity: 1; }
  .lv-objs polygon.cur { stroke: var(--u1-primary); stroke-dasharray: none; opacity: 1; }
  .lv-objs polygon.excl { fill: color-mix(in srgb, var(--u1-error) 14%, transparent); stroke: var(--u1-error); opacity: .8; }
  .lv-objects { display: flex; flex-direction: column; gap: 6px; }
  .lv-objects:empty { display: none; }
  .lv-objects .chip-row { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-start; }
  .obj-chip { cursor: pointer; }
  .obj-chip ha-icon { --mdc-icon-size: 16px; }
  .obj-chip.cur { border-color: var(--u1-primary); color: var(--u1-primary); }
  .obj-chip.off { text-decoration: line-through; opacity: .6; }

  /* ── Mini card ────────────────────────────────────────────────────────── */
  .mini-wrap { display: flex; flex-direction: column; gap: 12px; cursor: pointer; }
  .mini-top { display: flex; align-items: center; gap: 12px; }
  .mini-top .head-icon { width: 40px; height: 40px; }
  .mini-top .head-icon ha-icon { --mdc-icon-size: 22px; }
  .mini-top .head-text { min-width: 0; }
  .mini-status { margin-top: 2px; }
  .mini-file { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mini-prog { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
  .mini-prog .track { flex: 1; }
  .mini-prog .mono { font-weight: 600; min-width: 3.5em; text-align: right; }
  .mini-meta { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 6px; }
  .mini-meta > span { display: inline-flex; align-items: center; gap: 4px; }
  .mini-meta ha-icon { --mdc-icon-size: 14px; }
  .mini-fil { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
  .mini-slot { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 0; text-align: center; }
  .mini-slot .spool { width: 34px; height: 34px; }
  .mini-slot[data-empty="1"] { opacity: .5; }
  .mini-mat { font-size: 11px; color: var(--u1-on-variant); max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mini-g { font-size: 11px; }
  .mini-err { display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--u1-error); }
  .mini-err ha-icon, .mini-q ha-icon { --mdc-icon-size: 16px; flex-shrink: 0; }
  .mini-q { display: flex; gap: 6px; align-items: center; }
  .mini-g[data-low="1"] { color: var(--u1-warn); }

  /* ── Tabs ──────────────────────────────────────────────────────────── */
  .tabs {
    display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none;
    border-bottom: 1px solid var(--u1-outline); margin: 0 calc(-1 * var(--u1-pad)); padding: 0 var(--u1-pad);
  }
  .tabs::-webkit-scrollbar { display: none; }
  .tab {
    all: unset; cursor: pointer; flex-shrink: 0;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 10px 12px; min-height: 24px;
    color: var(--u1-on-variant);
    font-size: var(--md-sys-typescale-title-small-size, 14px); font-weight: 500;
    border-bottom: 3px solid transparent; border-radius: 4px 4px 0 0;
    transition: color var(--u1-motion), border-color var(--u1-motion), background var(--u1-motion);
  }
  .tab ha-icon { --mdc-icon-size: 18px; }
  .tab:hover { background: color-mix(in srgb, var(--u1-on) 6%, transparent); }
  .tab:focus-visible { outline: 2px solid var(--u1-primary); outline-offset: -2px; }
  .tab[aria-selected="true"] { color: var(--u1-primary); border-bottom-color: var(--u1-primary); }
  @container u1 (max-width: 520px) { .tab span { display: none; } .tab { padding: 10px 14px; } .tab[aria-selected="true"] span { display: inline; } }
  .layout[hidden] { display: none; }

  /* ── Overlay on the camera image ─────────────────────────────────────── */
  .hud {
    position: absolute; left: 0; right: 0; bottom: 0; z-index: 2;
    padding: 28px 12px 0;
    background: linear-gradient(to top, rgba(0,0,0,.72), rgba(0,0,0,.35) 65%, transparent);
    color: #fff; pointer-events: none;
  }
  .hud-row { display: flex; align-items: center; gap: 6px 14px; flex-wrap: wrap; padding-bottom: 8px; font-size: 13px; }
  .hud-pct { display: inline-flex; align-items: baseline; gap: 2px; margin-right: 2px; }
  .hud-pct b { font-size: 22px; font-weight: 600; }
  .hud-pct small { font-size: 13px; opacity: .8; }
  .hud-item { display: inline-flex; align-items: center; gap: 4px; font-variant-numeric: tabular-nums; }
  .hud-item ha-icon { --mdc-icon-size: 16px; opacity: .8; }
  .hud-head { display: inline-flex; align-items: center; gap: 6px; margin-left: auto; opacity: .95; }
  .hud-head i { width: 12px; height: 12px; border-radius: 50%; border: 1px solid rgba(255,255,255,.6); }
  .hud-track { height: 4px; margin: 0 -12px; background: rgba(255,255,255,.2); }
  .hud-track i { display: block; height: 100%; background: var(--u1-primary); transition: width var(--u1-motion); }
  .thumb.top { top: 52px; bottom: auto; }
  /* State in the top-left corner of the camera (replaces the idle overlay) */
  .cam-state {
    position: absolute; left: 10px; top: 10px; z-index: 3; max-width: calc(100% - 80px);
    display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px 6px 10px;
    border-radius: var(--u1-r-full); background: rgba(0,0,0,.55); color: #fff;
    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
    font-size: 13px; line-height: 1.2; pointer-events: none; }
  .cam-state .dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; background: #9e9e9e; }
  .cam-state[data-tone="active"] .dot { background: var(--u1-primary); box-shadow: 0 0 0 0 var(--u1-primary); animation: u1pulse 1.8s ease-out infinite; }
  .cam-state[data-tone="ok"] .dot { background: var(--u1-ok); }
  .cam-state[data-tone="warn"] .dot { background: var(--u1-warn); }
  .cam-state[data-tone="error"] .dot { background: var(--u1-error); }
  .cam-state-text { display: flex; flex-direction: column; min-width: 0; }
  .cam-state-text b { font-weight: 600; }
  .cam-state-text small { font-size: 11px; opacity: .8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  @keyframes u1pulse { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--u1-primary) 70%, transparent); }
    100% { box-shadow: 0 0 0 8px transparent; } }
  @media (prefers-reduced-motion: reduce) { .cam-state .dot { animation: none !important; } }

  .danger-zone {
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    padding: 12px 14px; border-radius: var(--u1-r-l);
    border: 1px solid color-mix(in srgb, var(--u1-error) 40%, transparent);
    background: color-mix(in srgb, var(--u1-error) 8%, transparent);
  }
  .danger-zone .t-label { flex: 1; min-width: 140px; color: var(--u1-error); }

  .offline {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    padding: 48px 16px; color: var(--u1-on-variant); text-align: center;
  }
  .offline ha-icon { --mdc-icon-size: 48px; }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { transition: none !important; animation: none !important; }
  }
`;
