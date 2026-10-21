# Contributing

Thanks for helping! Bug reports, test results from real printers and pull
requests are all welcome. Please open an [issue](https://github.com/Ironoxx/ha-snapmaker-u1-card/issues)
first for larger changes so we can agree on the approach.

## Reporting bugs

Please attach:

- the diagnostics file (*Settings → Devices & services → Snapmaker U1 Card → ⋮ → Download diagnostics*),
- the firmware version of the printer,
- for print problems, the G-code file.

## Development setup

Requirements: Python 3.13 and Node.js 22.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
npm ci
```

Repository layout and design are described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Checks

All of these run in CI and must pass:

```bash
ruff check custom_components   # Python lint
pytest -q                      # Python tests (real HA test instance)
npm run lint                   # ESLint for frontend/src
npm run build                  # bundle the card (commit the result)
npm test                       # card tests in jsdom against the bundle
```

## Working on the card

- Edit the sources in `frontend/src`, never the bundle
  `custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js`.
- Run `npm run build` and commit the rebuilt bundle; CI fails if it is outdated.
- New UI text: write it in German in the source and add the English
  translation to `EN` in `frontend/src/i18n.js`. The tests check for German
  leftovers in the English UI.
- Method names must be unique across the mixins in `frontend/src/card`
  (checked by `tests/js/structure.test.cjs`).

## Working on the integration

- Blocking I/O only in the executor (`hass.async_add_executor_job`).
- Pure logic goes into the HA-free modules (`parsing.py`, `layers.py`,
  `stats.py`, ...) so it can be tested in isolation.
- Messages shown to users go through `i18n.tr(hass, de, en)`.
- New options: config flow sections are `vol.Required` without a default,
  otherwise the frontend reports "Not all required fields are filled in".
- Translations: change `strings.json` and keep `translations/en.json` (identical)
  and `translations/de.json` in sync; a test checks the keys.

## Releasing

1. Bump the version in `manifest.json`, `const.py` (`VERSION`) and
   `frontend/src/const.js` (`CARD_VERSION`); a test checks they match.
2. Add a `## <version>` section at the top of `CHANGELOG.md` (what users get,
   English first, short German summary below). It becomes the release text that
   HACS shows in the update dialog; the release fails without it.
3. `npm run build`, run all checks, push to `main`.
4. The release workflow creates the tag, the GitHub release and the HACS zip.
   **From 2.0 on, new features go out as a beta first:** version `2.0.0b1`,
   `2.0.0b2` ... (changelog section `## 2.0.0b1`) become GitHub pre-releases that
   HACS only offers with "show beta versions" enabled. After testing on a real
   printer, the same state is released as `2.0.0`. Until then (1.x) releases
   go to everyone directly; pre-release versions are possible any time.
   Later edits to `CHANGELOG.md` update the text of existing releases
   (`release-notes.yml`).

## Code style

- Comments and docstrings in English; explain *why*, not *what*.
- Python: type hints, `from __future__ import annotations`, ruff clean.
- JavaScript: ES2020, no framework, no runtime dependencies.
