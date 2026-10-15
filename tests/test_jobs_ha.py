"""Dienste und Sensoren fuer Warteschlange, Pause bei Schicht, Fehler, Statistik,
Wartung, Zeitraffer-Sicherung und Upload in einer echten HA-Testinstanz."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from tests.test_features import ORCA
from tests.test_init import API, DOMAIN, mock_client  # noqa: F401
from tests.test_power import (  # noqa: F401
    _refresh,
    _setup,
    _status,
    auto_enable,
    notifications,
)


@pytest.fixture
def transfer(tmp_path):
    """download_to/upload/delete_file/rpc als Attrappen mit kleinem Dateisystem."""
    uploaded: dict[str, str] = {}

    async def download_to(self, root, path, target, hass):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(ORCA if root == "gcodes" else f"VIDEO {path}")
        return target.stat().st_size

    async def upload(self, source, path, root="gcodes"):
        uploaded[path] = Path(source).read_text()
        return {"item": {"path": path}}

    with patch(f"{API}.download_to", download_to), patch(f"{API}.upload", upload), \
         patch(f"{API}.delete_file", AsyncMock()) as delete:
        yield {"uploaded": uploaded, "delete": delete}


async def test_start_with_pause_layers(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    entry = await _setup(hass)
    await hass.services.async_call(
        DOMAIN, "start_print", {"filename": "sub/new.gcode", "pause_layers": [3, 2], "mapping": {0: 1}},
        blocking=True,
    )
    copy = "sub/new.u1pause-2-3.gcode"
    assert list(transfer["uploaded"]) == [copy]
    assert transfer["uploaded"][copy].count("\nPAUSE\n") == 2
    sp = mock_client["start_print"]
    assert sp.call_args.args[0] == copy
    assert sp.call_args.kwargs["map_table"] is not None
    active = entry.runtime_data._print_state["active"]
    assert active["source"] == "sub/new.gcode" and active["pause_layers"] == [2, 3]

    # Kopie taucht nicht in der Dateiliste auf
    mock_client["files"]["gcodes"].append({"path": copy, "modified": 99, "size": 1})
    entry.runtime_data.request_files_refresh()
    _status(mock_client, "printing", copy)
    await _refresh(hass, entry)
    paths = [f["path"] for f in entry.runtime_data.data.files]
    assert copy not in paths and "sub/new.gcode" in paths

    # Druckende: Historie zeigt das Original, Kopie wird geloescht
    _status(mock_client, "complete", copy)
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    last = entry.runtime_data._print_state["last"]
    assert last["file"] == "sub/new.gcode" and last["pause_layers"] == [2, 3]
    assert last["name"] == "new"  # Name der Originaldatei, nicht der Kopie
    transfer["delete"].assert_awaited_with(copy)


async def test_pause_layer_out_of_range(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    await _setup(hass)
    with pytest.raises(HomeAssistantError, match="Schicht 9"):
        await hass.services.async_call(
            DOMAIN, "start_print", {"filename": "old.gcode", "pause_layers": [9]}, blocking=True
        )
    mock_client["start_print"].assert_not_called()
    assert transfer["uploaded"] == {}


async def test_queue_flow(hass: HomeAssistant, mock_client, transfer, notifications) -> None:
    entry = await _setup(hass, notify_targets=["notify.mobile_app_handy"])
    hass.config.language = "de"
    r1 = await hass.services.async_call(
        DOMAIN, "queue_add", {"filename": "old.gcode", "mapping": {0: 2}, "timelapse": True},
        blocking=True, return_response=True,
    )
    r2 = await hass.services.async_call(
        DOMAIN, "queue_add", {"filename": "sub/new.gcode"}, blocking=True, return_response=True,
    )
    await hass.async_block_till_done()
    queue = next(e for e in hass.states.async_all("sensor") if "jobs" in e.attributes)
    assert queue.state == "2"
    assert [j["file"] for j in queue.attributes["jobs"]] == ["old.gcode", "sub/new.gcode"]
    assert queue.attributes["jobs"][0]["mapping"] == {"0": 2}

    await hass.services.async_call(DOMAIN, "queue_move", {"job_id": r2["job"]["id"], "position": 0}, blocking=True)
    assert [j["file"] for j in entry.runtime_data.queue.jobs] == ["sub/new.gcode", "old.gcode"]
    await hass.services.async_call(DOMAIN, "queue_move", {"job_id": r2["job"]["id"], "position": 5}, blocking=True)

    # Drucker druckt: Start abgelehnt, Auftrag bleibt
    _status(mock_client, "printing", "x.gcode")
    await _refresh(hass, entry)
    with pytest.raises(HomeAssistantError, match="druckt bereits"):
        await hass.services.async_call(DOMAIN, "queue_start", {}, blocking=True)
    assert len(entry.runtime_data.queue.jobs) == 2

    # Druckende -> Hinweis auf den naechsten Auftrag
    _status(mock_client, "complete", "x.gcode")
    await _refresh(hass, entry)
    await hass.async_block_till_done()
    titles = [c.data["title"] for c in notifications]
    assert "Snapmaker U1: Nächster Auftrag wartet" in titles
    msg = next(c.data["message"] for c in notifications if "Nächster" in c.data["title"])
    assert msg.startswith("old") and "2 in der Warteschlange" in msg

    res = await hass.services.async_call(DOMAIN, "queue_start", {}, blocking=True, return_response=True)
    assert res["file"] == "old.gcode"
    kw = mock_client["start_print"].call_args.kwargs
    assert kw["timelapse"] is True and kw["map_table"]
    assert [j["file"] for j in entry.runtime_data.queue.jobs] == ["sub/new.gcode"]
    assert r1["job"]["id"] not in [j["id"] for j in entry.runtime_data.queue.jobs]  # gestartet = entfernt
    await hass.services.async_call(DOMAIN, "queue_remove", {"job_id": r2["job"]["id"]}, blocking=True)
    assert entry.runtime_data.queue.jobs == []
    with pytest.raises(HomeAssistantError, match="leer"):
        await hass.services.async_call(DOMAIN, "queue_start", {}, blocking=True)

    # Ueberlebt einen Neustart der Integration
    await hass.services.async_call(DOMAIN, "queue_add", {"filename": "old.gcode"}, blocking=True)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert [j["file"] for j in entry.runtime_data.queue.jobs] == ["old.gcode"]


async def test_errors_stats_maintenance(hass: HomeAssistant, mock_client, notifications) -> None:
    entry = await _setup(hass)
    st = _status(mock_client, "standby")
    st["exception_manager"] = {"exceptions": [
        {"id": 525, "index": 1, "code": 13, "level": 1, "message": "preload fail: no_filament"},
    ]}
    await _refresh(hass, entry)
    errors = [e for e in hass.states.async_all("sensor") if "errors" in e.attributes]
    assert errors and errors[0].state == "1"
    assert errors[0].attributes["errors"][0]["text"]["de"] == "Vorladen: kein Filament erkannt (Kopf 2)"

    stats = next(e for e in hass.states.async_all("sensor") if "months" in e.attributes)
    assert stats.state == "10.0"  # 36000 s aus history_totals
    assert stats.attributes["totals"]["prints"] == 1 and len(stats.attributes["months"]) == 12

    maint = next(e for e in hass.states.async_all("sensor") if "items" in e.attributes)
    keys = [i["key"] for i in maint.attributes["items"]]
    assert keys[:4] == ["plate", "nozzle", "rails", "belts"] and "tool_changer" in keys
    assert maint.state == "0"  # Baseline beim ersten Mal: nichts faellig
    # 40 Druckstunden spaeter: Druckplatte faellig
    with patch(f"{API}.history_totals", AsyncMock(return_value={"total_print_time": 50 * 3600.0})):
        entry.runtime_data._force_stats = True
        await _refresh(hass, entry)
    maint = hass.states.get(maint.entity_id)
    assert maint.state == "1"
    await hass.services.async_call(DOMAIN, "maintenance_done", {"item": "plate"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(maint.entity_id).state == "0"


async def test_timelapse_archive_and_cleanup(hass: HomeAssistant, mock_client, transfer, tmp_path, notifications) -> None:
    media = tmp_path / "media"
    hass.config.media_dirs = {"local": str(media)}
    cam = mock_client["files"]["camera"]
    cam[:] = []
    for i in range(4):
        stamp = f"2026100{i + 1}120000"
        cam += [
            {"path": f"Teil{i}_{stamp}.mp4", "modified": 100 + i, "size": len(f"VIDEO Teil{i}_{stamp}.mp4")},
            {"path": f"Teil{i}_{stamp}_cover.jpg", "modified": 100 + i, "size": 10},
        ]
    calls = []

    async def rpc(self, method, params=None, response_timeout=60):
        calls.append((method, dict(params or {})))
        # Nur die Form {"file_name": ...} loescht wirklich (wie unbekannte Firmware)
        if method == "camera.delete_timelapse_instance" and "file_name" in params:
            cam[:] = [f for f in cam if f["path"] != params["file_name"]]
            return {"state": "success"}
        return {"state": "failed", "message": "bad params"}

    with patch(f"{API}.rpc", rpc):
        entry = await _setup(hass, timelapse_archive=True, timelapse_keep=2)
        await hass.async_block_till_done()
        await hass.services.async_call(DOMAIN, "backup_timelapses", {}, blocking=True)
        await hass.async_block_till_done()
    folder = media / "snapmaker_u1"
    assert sorted(p.name for p in folder.glob("*.mp4")) == [f"Teil{i}_2026100{i + 1}120000.mp4" for i in range(4)]
    # Die beiden aeltesten sind auf dem Drucker weg, die neuesten zwei bleiben
    assert sorted(f["path"] for f in cam if f["path"].endswith(".mp4")) == [
        "Teil2_20261003120000.mp4", "Teil3_20261004120000.mp4"]
    styles = [p for m, p in calls if m == "camera.delete_timelapse_instance"]
    assert all("req_id" in p for p in styles)
    archive = entry.runtime_data._archive_data()
    assert archive["count"] == 4 and archive["cleanup"] == "ok"
    assert entry.runtime_data.archive.delete_style == "file_name"
    # Neustart merkt sich die Form: beim naechsten Mal direkt die richtige
    assert entry.runtime_data._stored()["archive"]["delete_style"] == "file_name"


async def test_archive_not_supported_keeps_everything(hass, mock_client, transfer, tmp_path, notifications) -> None:
    hass.config.media_dirs = {"local": str(tmp_path / "m")}
    cam = mock_client["files"]["camera"]

    async def rpc(self, method, params=None, response_timeout=60):
        from custom_components.snapmaker_u1_card.api import MoonrakerError
        raise MoonrakerError("Method not found")

    with patch(f"{API}.rpc", rpc):
        entry = await _setup(hass, timelapse_archive=True, timelapse_keep=0)
        await hass.services.async_call(DOMAIN, "backup_timelapses", {}, blocking=True)
    assert len(list((tmp_path / "m" / "snapmaker_u1").glob("*.mp4"))) == 1
    assert len(cam) == 3  # keep=0: nie loeschen
    assert entry.runtime_data._archive_data()["cleanup"] is None


async def test_upload_view(hass: HomeAssistant, mock_client, transfer, hass_client, notifications) -> None:
    entry = await _setup(hass)
    client = await hass_client()
    form = aiohttp.FormData()
    form.add_field("path", "../neu")
    form.add_field("file", b";LAYER_CHANGE\nG1\n", filename="Box.gcode")
    resp = await client.post(f"/api/{DOMAIN}/upload/{entry.entry_id}", data=form)
    assert resp.status == 200, await resp.text()
    assert (await resp.json())["file"] == "neu/Box.gcode"
    assert transfer["uploaded"]["neu/Box.gcode"] == ";LAYER_CHANGE\nG1\n"

    form = aiohttp.FormData()
    form.add_field("file", b"x", filename="evil.sh")
    resp = await client.post(f"/api/{DOMAIN}/upload/{entry.entry_id}", data=form)
    assert resp.status == 400
    resp = await client.post(f"/api/{DOMAIN}/upload/nope", data=aiohttp.FormData({"a": "b"}))
    assert resp.status == 404


async def test_upload_requires_auth(hass: HomeAssistant, mock_client, hass_client_no_auth, notifications) -> None:
    entry = await _setup(hass)
    client = await hass_client_no_auth()
    resp = await client.post(f"/api/{DOMAIN}/upload/{entry.entry_id}", data=b"x")
    assert resp.status == 401


async def test_layer_view(hass: HomeAssistant, mock_client, hass_client, notifications) -> None:
    from tests.test_features import LAYERED

    async def download_to(self, root, path, target, hass_):
        target.write_text(LAYERED)
        return len(LAYERED)

    with patch(f"{API}.download_to", download_to):
        entry = await _setup(hass)
        client = await hass_client()
        url = f"/api/{DOMAIN}/layers/{entry.entry_id}"
        assert (await (await client.get(f"{url}?layer=1")).json())["status"] == "none"
        st = _status(mock_client, "printing", "sub/new.gcode")
        await _refresh(hass, entry)
        await hass.async_block_till_done(wait_background_tasks=True)
        # Einmal je Druck automatisch (Zeitprofil fuer Restzeit)
        assert entry.runtime_data.layer_view["status"] == "ready"
        body = await (await client.get(f"{url}?layer=1")).json()
    assert body["status"] == "ready" and body["total"] == 3 and len(body["segs"]) == 3
    assert body["colors"]["map_table"][:4] == [0, 1, 2, 3]
    assert "file" in body["colors"]
    st["virtual_sdcard"] = {"file_position": 123}
    st["print_stats"]["info"] = {"current_layer": 2}
    pos = await (await client.get(f"{url}?position=1")).json()
    assert pos["position"] == 123 and pos["layer"] == 2
    # Live-Abo steht: Position ohne Abfrage beim Drucker
    coord = entry.runtime_data
    coord.live.connected = True
    coord.live.status = {"virtual_sdcard": {"file_position": 456}, "print_stats": {"info": {"current_layer": 3}},
                         "toolhead": {"extruder": "extruder2"}}
    pos = await (await client.get(f"{url}?position=1")).json()
    assert pos == {**pos, "position": 456, "layer": 3, "active_head": 2, "live": True}
    coord.live.connected = False
    assert (await (await client.get(f"{url}?layer=9")).json())["missing"] is True
    assert (await client.get(f"/api/{DOMAIN}/layers/nope")).status == 404


async def test_no_listing_while_printing(hass: HomeAssistant, mock_client, notifications) -> None:
    """Waehrend eines Drucks keine Zeitraffer-/Historienabfragen, Dateien nur selten."""
    import time as _time

    entry = await _setup(hass)
    coord = entry.runtime_data
    assert hass.states.async_all("sensor") and coord.data.cpu_count == 4
    roots = []
    orig = mock_client["files"]

    async def list_files(self, root="gcodes"):
        roots.append(root)
        return orig.get(root, [])

    with patch(f"{API}.list_files", list_files), \
         patch(f"{API}.history", AsyncMock(return_value=[])) as hist:
        _status(mock_client, "printing", "sub/new.gcode")
        # Intervalle laengst abgelaufen
        coord._files_at = coord._timelapses_at = coord._stats_at = _time.monotonic() - 3600
        coord._force_files = coord._force_timelapses = coord._force_stats = False
        await _refresh(hass, entry)
        assert roots == ["gcodes"], roots  # Dateien (10 min um), keine Zeitraffer
        hist.assert_not_called()
        roots.clear()
        await _refresh(hass, entry)
        assert roots == [], "Dateien erst nach 10 min wieder"
        # Druckende stoesst Zeitraffer und Statistik an
        _status(mock_client, "complete", "sub/new.gcode")
        await _refresh(hass, entry)
        assert "camera" in roots
        hist.assert_called()
