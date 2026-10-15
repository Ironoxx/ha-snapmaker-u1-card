"""MoonrakerClient against a simulated U1 Moonraker."""

import ast
import json

import aiohttp
import pytest
from aiohttp import web

from conftest import api, parsing

# socket_enabled: the HA test plugin otherwise blocks sockets even on localhost.

PTC = {"filament_type": ["PLA", "NONE", "NONE", "NONE"], "filament_exist": [True, False, False, False]}


@pytest.fixture
async def moonraker(socket_enabled, aiohttp_server):
    seen = {"rpc": []}

    async def query(request):
        assert "print_task_config" in request.query
        return web.json_response({"result": {"eventtime": 1, "status": {"print_task_config": PTC}}})

    async def files(request):
        assert request.query["root"] == "gcodes"
        return web.json_response({"result": [{"path": "sub/a.gcode", "modified": 2, "size": 1}]})

    async def metadata(request):
        return web.json_response({"result": {"filament_type": "PLA", "thumbnails": []}})

    async def gcodes(request):
        seen["download"] = request.match_info["path"]
        return web.Response(body=b"PNG")

    async def websocket(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        async for msg in ws:
            req = json.loads(msg.data)
            seen["rpc"].append(req)
            # Moonraker sends unsolicited status messages in between
            await ws.send_json({"jsonrpc": "2.0", "method": "notify_status_update", "params": [{}]})
            if req["params"]["path"] == "busy.gcode":
                await ws.send_json({"jsonrpc": "2.0", "id": req["id"],
                                    "result": {"state": "error", "message": "Printer is busy, cannot start print"}})
            elif req["params"]["path"] == "rpcerr.gcode":
                await ws.send_json({"jsonrpc": "2.0", "id": req["id"],
                                    "error": {"code": 400, "message": "kaputt"}})
            else:
                await ws.send_json({"jsonrpc": "2.0", "id": req["id"],
                                    "result": {"state": "success", "message": "Print started"}})
        return ws

    app = web.Application()
    app.router.add_get("/printer/objects/query", query)
    app.router.add_get("/server/files/list", files)
    app.router.add_get("/server/files/metadata", metadata)
    app.router.add_get("/server/files/gcodes/{path:.*}", gcodes)
    app.router.add_get("/websocket", websocket)
    server = await aiohttp_server(app)
    return server, seen


@pytest.fixture
async def client(moonraker):
    server, seen = moonraker
    async with aiohttp.ClientSession() as session:
        yield api.MoonrakerClient(session, server.host, server.port), seen


async def test_reads(client):
    c, seen = client
    status = await c.query_objects("print_task_config")
    assert status["print_task_config"]["filament_type"][0] == "PLA"
    assert (await c.list_files())[0]["path"] == "sub/a.gcode"
    assert (await c.file_metadata("sub/a.gcode"))["filament_type"] == "PLA"
    assert await c.download("sub/.thumbs/a b.png") == b"PNG"
    assert seen["download"] == "sub/.thumbs/a b.png"


async def test_start_print_like_orca(client):
    c, seen = client
    table = parsing.map_table_option({0: 2, 1: 0})
    result = await c.start_print("/sub/a.gcode", map_table=table, bed_leveling=True,
                                 flow_calibration=False, timelapse=True)
    assert result["state"] == "success"
    req = seen["rpc"][-1]
    assert req["method"] == "server.files.start_local_print"
    assert req["params"]["path"] == "sub/a.gcode"
    opts = req["params"]["options"]
    assert opts == {"map_table": "[[0, 2], [1, 0]]", "bed_level": 1, "flow_calibrate": 0, "time_lapse_camera": 1}
    # This is how u1-moonraker builds the G-code (klippy_apis.start_print_advanced)
    script = "SDCARD_PRINT_FILE_WITH_PARAMETERS" + "".join(f' {k.upper()}="{v}"' for k, v in opts.items())
    assert 'MAP_TABLE="[[0, 2], [1, 0]]"' in script
    assert ast.literal_eval(opts["map_table"]) == [[0, 2], [1, 0]]


async def test_start_print_without_options(client):
    c, seen = client
    await c.start_print("a.gcode")
    assert "options" not in seen["rpc"][-1]["params"]


async def test_start_print_refused(client):
    c, _ = client
    with pytest.raises(api.MoonrakerError, match="busy"):
        await c.start_print("busy.gcode")
    with pytest.raises(api.MoonrakerError, match="kaputt"):
        await c.start_print("rpcerr.gcode")


async def test_unreachable(socket_enabled):
    async with aiohttp.ClientSession() as session:
        c = api.MoonrakerClient(session, "127.0.0.1", 1)
        with pytest.raises(api.MoonrakerConnectionError):
            await c.query_objects("print_task_config")
        with pytest.raises(api.MoonrakerConnectionError):
            await c.start_print("a.gcode")
