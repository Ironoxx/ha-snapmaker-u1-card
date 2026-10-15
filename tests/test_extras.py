"""Cost before printing, config backup, voice control and diagnostics."""

from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent

from custom_components.snapmaker_u1_card import voice
from custom_components.snapmaker_u1_card.diagnostics import async_get_config_entry_diagnostics
from custom_components.snapmaker_u1_card.parsing import average_kw, estimate_cost
from tests.test_init import API, DOMAIN, mock_client  # noqa: F401
from tests.test_power import _refresh, _setup, _status, auto_enable, notifications  # noqa: F401


# ── Cost ────────────────────────────────────────────────────────────────────
def test_average_kw_and_estimate() -> None:
    hist = [{"energy": 0.2, "duration": 3600}, {"energy": 0.3, "duration": 3600},
            {"energy": 5.0, "duration": 60}, {"duration": 7200}]
    assert average_kw(hist) == 0.25
    assert average_kw([]) is None
    f = {"time": 7200, "filaments": [{"type": "PLA", "weight": 100, "used": True},
                                     {"type": "PETG", "weight": 50, "used": True},
                                     {"type": "TPU", "weight": 0, "used": False}]}
    c = estimate_cost(f, {"PLA": 20.0, "PETG": 30.0}, 0.30, 0.25)
    assert c == {"filament": 3.5, "energy_kwh": 0.5, "energy": 0.15, "total": 3.65}
    # Price for one material missing: energy only
    assert estimate_cost(f, {"PLA": 20.0}, 0.30, 0.25) == {"energy_kwh": 0.5, "energy": 0.15, "total": 0.15}
    assert estimate_cost({"time": 10}, {}, None, None) is None


async def test_files_sensor_has_cost(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    coord = entry.runtime_data
    coord._print_state["history"] = [{"energy": 0.5, "duration": 3600}]
    await _refresh(hass, entry)
    st = next(s for s in hass.states.async_all("sensor") if "files" in s.attributes and "cost_basis" in s.attributes)
    assert st.attributes["cost_basis"] == {"kwh_price": 0.3, "avg_kw": 0.5}
    f = next(x for x in st.attributes["files"] if x["path"] == "old.gcode")
    # META: 4 g PETG + 6 g PLA, 600 s -> 0.10 + 0.12 = 0.22 EUR filament; 0.083 kWh x 0.30
    assert f["cost"] == {"filament": 0.22, "energy_kwh": 0.083, "energy": 0.02, "total": 0.24}


# ── Config backup ──────────────────────────────────────────────────────────
async def test_config_backup(hass: HomeAssistant, mock_client, notifications) -> None:
    mock_client["files"]["config"] = [
        {"path": "printer.cfg", "size": 10}, {"path": "macros/start.cfg", "size": 5},
        {"path": "klippy.log", "size": 10}, {"path": "huge.cfg", "size": 5 * 1024**2},
        {"path": "../evil.cfg", "size": 1},
    ]
    content = {"printer.cfg": b"[printer]\n", "macros/start.cfg": b"G28\n"}

    async def download(self, rel, root="gcodes"):
        return content[rel] if root == "config" else b"\x89PNG"

    with patch(f"{API}.download", download):
        entry = await _setup(hass)
        await hass.async_block_till_done(wait_background_tasks=True)
        coord = entry.runtime_data
        folder = coord.backup_folder
        snaps = sorted(p for p in folder.iterdir())
        assert len(snaps) == 1, "taeglich beim ersten Abgleich"
        assert (snaps[0] / "printer.cfg").read_bytes() == b"[printer]\n"
        assert (snaps[0] / "macros/start.cfg").exists()
        assert not (snaps[0] / "klippy.log").exists() and not (snaps[0] / "huge.cfg").exists()
        assert not (folder.parent / "evil.cfg").exists()
        # Unchanged -> no new snapshot; the service returns a result
        res = await hass.services.async_call(DOMAIN, "backup_config", {}, blocking=True, return_response=True)
        assert res["status"] == "unchanged" and len(res["snapshots"]) == 1
        # Changed -> new snapshot
        content["printer.cfg"] = b"[printer]\nmax_velocity: 500\n"
        with patch("custom_components.snapmaker_u1_card.backup.dt_util.now") as now:
            now.return_value.strftime.return_value = "2099-01-01_000000"
            res = await hass.services.async_call(DOMAIN, "backup_config", {}, blocking=True, return_response=True)
        assert res["status"] == "saved" and res["snapshot"] == "2099-01-01_000000"
        assert res["skipped"] == ["huge.cfg", "klippy.log"]
    await _refresh(hass, entry)
    st = next(s for s in hass.states.async_all("sensor") if "config_backup" in s.attributes)
    assert st.attributes["config_backup"]["snapshot"] == "2099-01-01_000000"
    assert st.attributes["config_backup"]["status"] == "saved"


async def test_backup_keeps_ten(hass: HomeAssistant, tmp_path) -> None:
    from custom_components.snapmaker_u1_card.backup import _write_snapshot

    for i in range(12):
        _write_snapshot(tmp_path, f"2026-01-{i + 1:02d}_000000", {"a.cfg": b"x"}, 10)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert len(names) == 10 and names[0] == "2026-01-03_000000"


async def test_backup_disabled(hass: HomeAssistant, mock_client, notifications) -> None:
    with patch(f"{API}.list_files", AsyncMock(return_value=[])) as lf:
        entry = await _setup(hass, config_backup=False)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert "config" not in [c.args[0] if c.args else "gcodes" for c in lf.call_args_list]
    assert entry.runtime_data.data.backup is None


# ── Voice control ───────────────────────────────────────────────────────────
def test_sentences_parse() -> None:
    import io

    from hassil import Intents, recognize

    for lang, sample, expect in (
        ("de", "Wie weit ist der Drucker", voice.INTENT_STATUS),
        ("de", "wie lange braucht der 3D-Drucker noch", voice.INTENT_STATUS),
        # HA removes filler words such as "noch" before matching
        ("de", "wie lange braucht der Drucker", voice.INTENT_STATUS),
        ("de", "Pausiere den Drucker", voice.INTENT_PAUSE),
        ("de", "Drucker fortsetzen", voice.INTENT_RESUME),
        ("en", "how far is the printer", voice.INTENT_STATUS),
        ("en", "pause the printer", voice.INTENT_PAUSE),
        ("en", "resume the print", voice.INTENT_RESUME),
    ):
        intents = Intents.from_yaml(io.StringIO(voice.SENTENCES[lang]))
        result = recognize(sample, intents)
        assert result is not None and result.intent.name == expect, (lang, sample)


def test_sentence_files_respect_user(tmp_path) -> None:
    assert voice._write_sentences(str(tmp_path)) is True
    de = tmp_path / "custom_sentences/de/snapmaker_u1_card.yaml"
    assert de.read_text().startswith(voice.MARKER)
    assert voice._write_sentences(str(tmp_path)) is False, "unveraendert"
    de.write_text("language: de\n# eigene Saetze\n")
    assert voice._write_sentences(str(tmp_path)) is False
    assert "eigene" in de.read_text(), "ohne Kopfzeile nicht ueberschrieben"


async def _ask(hass, name, lang="de"):
    resp = await intent.async_handle(hass, "test", name, {}, language=lang)
    return resp.speech["plain"]["speech"]


async def test_intents(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    hass.config.language = "de"
    assert "bereit" in await _ask(hass, voice.INTENT_STATUS)
    assert "kein Druck" in await _ask(hass, voice.INTENT_PAUSE)
    st = _status(mock_client, "printing", "sub/new.gcode", print_duration=1800,
                 info={"current_layer": 12, "total_layer": 40})
    st["virtual_sdcard"] = {"progress": 0.5}
    await _refresh(hass, entry)
    text = await _ask(hass, voice.INTENT_STATUS)
    assert "50 Prozent" in text and "Schicht 12 von 40" in text and "30 Minuten" in text, text
    assert "50 percent" in await _ask(hass, voice.INTENT_STATUS, "en")
    with patch(f"{API}.print_action", AsyncMock()) as act:
        assert "pausiert" in await _ask(hass, voice.INTENT_PAUSE)
        act.assert_awaited_with("pause")
        assert "läuft bereits" in await _ask(hass, voice.INTENT_RESUME)


# ── Diagnostics ─────────────────────────────────────────────────────────────
async def test_diagnostics_redacts(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"]["host"] == "**REDACTED**"
    assert diag["entry"]["options"]["notify_targets"] == "**REDACTED**"
    assert diag["live"]["connected"] is False and diag["online"] is True
    assert "printer" in diag and diag["version"]
