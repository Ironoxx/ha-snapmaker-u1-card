"""Lean Moonraker client for the Snapmaker U1.

Reads go over HTTP. Starting a print with filament mapping goes over JSON-RPC
on the WebSocket: Snapmaker's Moonraker registers
``server.files.start_local_print`` explicitly without HTTP transport
(u1-moonraker/moonraker/components/snapmakercloud.py). This is the same path
Snapmaker Orca uses in LAN mode.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import posixpath
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=15)


class MoonrakerError(Exception):
    """Moonraker answered with an error."""


class MoonrakerConnectionError(MoonrakerError):
    """Printer not reachable."""


class MoonrakerClient:
    """HTTP and JSON-RPC access to one Moonraker instance."""
    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        api_key: str | None = None,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._headers = {"X-Api-Key": api_key} if api_key else {}
        self._ids = itertools.count(1)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ── HTTP ────────────────────────────────────────────────────────────────
    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET a Moonraker endpoint and return its ``result`` payload."""
        try:
            async with self._session.get(
                f"{self.base_url}{path}", params=params,
                headers=self._headers, timeout=HTTP_TIMEOUT,
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"HTTP {resp.status} for {path}: {body[:200]}")
                data = json.loads(body)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"{self.host} not reachable: {err}") from err
        except ValueError as err:
            raise MoonrakerError(f"Invalid response from {path}") from err
        if isinstance(data, dict) and "error" in data:
            raise MoonrakerError(str(data["error"]))
        return data.get("result") if isinstance(data, dict) else data

    async def query_objects(
        self, *objects: str, fields: dict[str, tuple[str, ...]] | None = None
    ) -> dict[str, Any]:
        """Query printer objects; ``fields`` limits the fields per object."""
        params = {name: "" for name in objects}
        for name, wanted in (fields or {}).items():
            params[name] = ",".join(wanted)
        result = await self._get_json("/printer/objects/query", params)
        return (result or {}).get("status", {})

    async def list_files(self, root: str = "gcodes") -> list[dict[str, Any]]:
        result = await self._get_json("/server/files/list", {"root": root})
        return result if isinstance(result, list) else []

    async def list_roots(self) -> list[str]:
        result = await self._get_json("/server/files/roots")
        return [r["name"] for r in result or [] if isinstance(r, dict) and r.get("name")]

    async def klippy_ready(self) -> bool:
        """Moonraker reachable and Klipper ready."""
        result = await self._get_json("/server/info")
        return isinstance(result, dict) and result.get("klippy_state") == "ready"

    async def open_file(
        self, root: str, path: str, headers: dict[str, str] | None = None
    ) -> aiohttp.ClientResponse:
        """Open a file as a response stream (video proxy; Range is passed through).

        The caller must close the response.
        """
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(path)}"
        try:
            return await self._session.get(
                url, headers={**self._headers, **(headers or {})},
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=60),
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def file_metadata(self, filename: str) -> dict[str, Any]:
        result = await self._get_json("/server/files/metadata", {"filename": filename})
        return result if isinstance(result, dict) else {}

    async def download(self, relative: str, root: str = "gcodes") -> bytes:
        """Download a small file completely into memory."""
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(relative)}"
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=HTTP_TIMEOUT
            ) as resp:
                if resp.status >= 400:
                    raise MoonrakerError(f"HTTP {resp.status} for {root}/{relative}")
                return await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def download_to(self, root: str, relative: str, target: Path, hass: Any) -> int:
        """Stream a large file (video, G-code) to ``target``.

        Writes to ``<target>.part`` first and renames at the end, so an
        aborted download never leaves a half file under the real name.
        """
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(relative)}"
        part = target.with_name(target.name + ".part")
        await hass.async_add_executor_job(lambda: target.parent.mkdir(parents=True, exist_ok=True))
        fh = await hass.async_add_executor_job(part.open, "wb")
        size = 0
        try:
            async with self._session.get(
                url, headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=60),
            ) as resp:
                if resp.status >= 400:
                    raise MoonrakerError(f"HTTP {resp.status} for {root}/{relative}")
                buf = bytearray()
                async for chunk in resp.content.iter_chunked(256 * 1024):
                    buf += chunk
                    if len(buf) >= 4 * 1024 * 1024:
                        await hass.async_add_executor_job(fh.write, bytes(buf))
                        size += len(buf)
                        buf.clear()
                if buf:
                    await hass.async_add_executor_job(fh.write, bytes(buf))
                    size += len(buf)
        except (aiohttp.ClientError, TimeoutError) as err:
            await hass.async_add_executor_job(fh.close)
            await hass.async_add_executor_job(lambda: part.unlink(missing_ok=True))
            raise MoonrakerConnectionError(str(err)) from err
        except BaseException:
            await hass.async_add_executor_job(fh.close)
            await hass.async_add_executor_job(lambda: part.unlink(missing_ok=True))
            raise
        await hass.async_add_executor_job(fh.close)
        await hass.async_add_executor_job(part.replace, target)
        return size

    async def upload(self, source: Path, path: str, root: str = "gcodes") -> dict[str, Any]:
        """Upload a local file to ``root/path`` (missing subfolders are created)."""
        folder, name = posixpath.split(path.lstrip("/"))
        form = aiohttp.FormData()
        form.add_field("root", root)
        if folder:
            form.add_field("path", folder)
        # aiohttp reads file objects in the executor; the file stays open until done.
        fh = await asyncio.get_running_loop().run_in_executor(None, source.open, "rb")
        try:
            form.add_field("file", fh, filename=name, content_type="application/octet-stream")
            async with self._session.post(
                f"{self.base_url}/server/files/upload", data=form, headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=120),
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Upload refused (HTTP {resp.status}): {body[:200]}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"Upload to {self.host}: {err}") from err
        finally:
            await asyncio.get_running_loop().run_in_executor(None, fh.close)
        try:
            data = json.loads(body)
        except ValueError:
            return {}
        return data.get("result", data) if isinstance(data, dict) else {}

    async def move_file(self, source: str, dest: str, root: str = "gcodes") -> None:
        """Rename/move a file; missing target folders are created."""
        folder = posixpath.dirname(dest.lstrip("/"))
        # Moonraker does not create target folders when moving, and only one level at a time
        parts = folder.split("/") if folder else []
        for depth in range(1, len(parts) + 1):
            try:
                async with self._session.post(
                    f"{self.base_url}/server/files/directory", json={"path": f"{root}/{'/'.join(parts[:depth])}"},
                    headers=self._headers, timeout=HTTP_TIMEOUT,
                ):
                    pass  # 400 = already exists
            except (aiohttp.ClientError, TimeoutError) as err:
                raise MoonrakerConnectionError(str(err)) from err
        url = f"{self.base_url}/server/files/move"
        body = {"source": f"{root}/{source.lstrip('/')}", "dest": f"{root}/{dest.lstrip('/')}"}
        try:
            async with self._session.post(url, json=body, headers=self._headers, timeout=HTTP_TIMEOUT) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Move refused (HTTP {resp.status}): {text[:200]}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def temperature_store(self) -> dict[str, Any]:
        """Temperature history Moonraker keeps anyway (1/s, 20 min)."""
        result = await self._get_json("/server/temperature_store", {"include_monitors": "false"})
        return result if isinstance(result, dict) else {}

    async def delete_file(self, path: str, root: str = "gcodes") -> None:
        """Delete a file below a Moonraker root; a missing file is not an error."""
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(path.lstrip('/'))}"
        try:
            async with self._session.delete(url, headers=self._headers, timeout=HTTP_TIMEOUT) as resp:
                if resp.status >= 400 and resp.status != 404:
                    raise MoonrakerError(f"Delete refused (HTTP {resp.status})")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def firmware_version(self) -> str | None:
        """Installed firmware: product_info (Snapmaker Moonraker), else the Klipper version."""
        try:
            result = await self._get_json("/machine/system_info")
            prod = ((result or {}).get("system_info") or {}).get("product_info") or {}
            ver = prod.get("firmware_version") or prod.get("software_version")
            # Real version numbers only; otherwise (e.g. "?") use the Klipper version
            if isinstance(ver, str) and re.search(r"\d+\.\d+", ver) and ver != "0.0.0":
                return ver
        except MoonrakerError:
            pass
        info = await self._get_json("/printer/info")
        ver = (info or {}).get("software_version") if isinstance(info, dict) else None
        return ver if isinstance(ver, str) and ver else None

    async def cpu_count(self) -> int | None:
        """Number of CPU cores (to put the system load into context)."""
        result = await self._get_json("/machine/system_info")
        info = ((result or {}).get("system_info") or {}).get("cpu_info") or {}
        count = info.get("cpu_count")
        return int(count) if isinstance(count, int) and count > 0 else None

    async def history(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Finished jobs from Moonraker's [history], newest first."""
        result = await self._get_json("/server/history/list", {"limit": limit, "order": "desc"})
        jobs = (result or {}).get("jobs") if isinstance(result, dict) else None
        return [j for j in jobs or [] if isinstance(j, dict)]

    async def history_totals(self) -> dict[str, Any]:
        result = await self._get_json("/server/history/totals")
        totals = (result or {}).get("job_totals") if isinstance(result, dict) else None
        return totals if isinstance(totals, dict) else {}

    async def print_action(self, action: str) -> None:
        """pause | resume | cancel via JSON-RPC (Moonraker: printer.print.<action>)."""
        await self.rpc(f"printer.print.{action}", response_timeout=30)

    async def gcode(self, script: str) -> None:
        """Run a G-code script (JSON-RPC printer.gcode.script); firmware errors raise."""
        await self.rpc("printer.gcode.script", {"script": script}, response_timeout=30)

    async def camera_wake(self) -> None:
        """Ask Snapmaker's camera service to (keep) stream(ing) in LAN mode.

        Same call the Snapmaker app makes (u1-moonraker repeater.py proxies
        camera.start_monitor to the closed camera service). Without it the
        stock firmware stops the camera after a while.
        """
        await self.rpc("camera.start_monitor", {"domain": "lan", "interval": 0, "req_id": next(self._ids)},
                       response_timeout=10)

    def websocket(self) -> Any:
        """Persistent WebSocket connection (context manager) for the live subscription."""
        return self._session.ws_connect(
            f"ws://{self.host}:{self.port}/websocket", headers=self._headers, heartbeat=30,
            timeout=aiohttp.ClientWSTimeout(ws_close=10),
        )

    # ── WebSocket JSON-RPC ──────────────────────────────────────────────────
    async def rpc(self, method: str, params: dict[str, Any] | None = None,
                  response_timeout: float = 60) -> Any:
        """Single JSON-RPC call; the connection is closed afterwards.

        Moonraker keeps sending notify_* messages on the same connection;
        only the response with the matching id counts.
        """
        req_id = next(self._ids)
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": req_id}
        url = f"ws://{self.host}:{self.port}/websocket"
        try:
            async with self._session.ws_connect(
                url, headers=self._headers, heartbeat=20,
                timeout=aiohttp.ClientWSTimeout(ws_close=10),
            ) as ws:
                await ws.send_json(payload)
                async with asyncio.timeout(response_timeout):
                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                            continue
                        data = json.loads(msg.data)
                        if data.get("id") != req_id:
                            continue
                        if "error" in data:
                            err = data["error"]
                            text = err.get("message") if isinstance(err, dict) else str(err)
                            raise MoonrakerError(text or "Unknown error")
                        return data.get("result")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"WebSocket to {self.host}: {err}") from err
        raise MoonrakerConnectionError("WebSocket closed without a response")

    async def start_print(
        self,
        path: str,
        map_table: str | None = None,
        bed_leveling: bool | None = None,
        flow_calibration: bool | None = None,
        timelapse: bool | None = None,
        plate: int = 1,
    ) -> dict[str, Any]:
        """Start a print the way Snapmaker Orca does.

        The option keys end up upper-cased as parameters of
        SDCARD_PRINT_FILE_WITH_PARAMETERS (klippy_apis.start_print_advanced)
        and are evaluated by SET_PRINT_TASK_PARAMETERS.
        """
        options: dict[str, Any] = {}
        if map_table:
            options["map_table"] = map_table
        if bed_leveling is not None:
            options["bed_level"] = int(bool(bed_leveling))
        if flow_calibration is not None:
            options["flow_calibrate"] = int(bool(flow_calibration))
        if timelapse is not None:
            options["time_lapse_camera"] = int(bool(timelapse))

        params: dict[str, Any] = {"path": path.lstrip("/"), "print_plate": plate}
        if options:
            params["options"] = options
        result = await self.rpc("server.files.start_local_print", params)
        if isinstance(result, dict) and result.get("state") not in (None, "success"):
            raise MoonrakerError(result.get("message") or str(result))
        return result if isinstance(result, dict) else {"state": "success"}


class SpoolmanClient:
    """Minimal Spoolman client (API v1)."""

    def __init__(self, session: aiohttp.ClientSession, url: str) -> None:
        self._session = session
        url = url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        self.url = url.removesuffix("/api/v1")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Call the Spoolman API and return the decoded JSON."""
        try:
            async with self._session.request(
                method, f"{self.url}/api/v1{path}", timeout=aiohttp.ClientTimeout(total=10), **kwargs
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Spoolman HTTP {resp.status}: {body[:200]}")
                return json.loads(body) if body else None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"Spoolman not reachable: {err}") from err
        except ValueError as err:
            raise MoonrakerError("Invalid response from Spoolman") from err

    async def info(self) -> dict[str, Any]:
        return await self._request("GET", "/info") or {}

    async def spools(self) -> list[dict[str, Any]]:
        result = await self._request("GET", "/spool", params={"allow_archived": "false"})
        return result if isinstance(result, list) else []

    async def use_weight(self, spool_id: int, grams: float) -> dict[str, Any]:
        return await self._request("PUT", f"/spool/{int(spool_id)}/use", json={"use_weight": round(grams, 2)})
