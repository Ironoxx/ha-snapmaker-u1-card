"""Schlanker Moonraker-Client fuer den Snapmaker U1.

Lesen laeuft ueber HTTP. Der Druckstart mit Filamentzuordnung laeuft ueber
JSON-RPC auf dem WebSocket: Snapmakers Moonraker registriert
``server.files.start_local_print`` ausdruecklich ohne HTTP-Transport
(u1-moonraker/moonraker/components/snapmakercloud.py). Das ist derselbe Weg,
den Snapmaker Orca im LAN-Modus nimmt.
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
    """Moonraker hat mit einem Fehler geantwortet."""


class MoonrakerConnectionError(MoonrakerError):
    """Drucker nicht erreichbar."""


class MoonrakerClient:
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
        try:
            async with self._session.get(
                f"{self.base_url}{path}", params=params,
                headers=self._headers, timeout=HTTP_TIMEOUT,
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"HTTP {resp.status} fuer {path}: {body[:200]}")
                data = json.loads(body)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"{self.host} nicht erreichbar: {err}") from err
        except ValueError as err:
            raise MoonrakerError(f"Ungueltige Antwort von {path}") from err
        if isinstance(data, dict) and "error" in data:
            raise MoonrakerError(str(data["error"]))
        return data.get("result") if isinstance(data, dict) else data

    async def query_objects(
        self, *objects: str, fields: dict[str, tuple[str, ...]] | None = None
    ) -> dict[str, Any]:
        """Objekte abfragen; ``fields`` begrenzt die Felder je Objekt."""
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
        """Moonraker erreichbar und Klipper betriebsbereit."""
        result = await self._get_json("/server/info")
        return isinstance(result, dict) and result.get("klippy_state") == "ready"

    async def open_file(
        self, root: str, path: str, headers: dict[str, str] | None = None
    ) -> aiohttp.ClientResponse:
        """Datei als Antwortstrom oeffnen (fuer den Video-Proxy, Range wird durchgereicht).

        Der Aufrufer muss die Antwort schliessen.
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
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(relative)}"
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=HTTP_TIMEOUT
            ) as resp:
                if resp.status >= 400:
                    raise MoonrakerError(f"HTTP {resp.status} fuer {root}/{relative}")
                return await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def download_to(self, root: str, relative: str, target: Path, hass: Any) -> int:
        """Grosse Datei (Video, G-Code) streamend nach ``target`` laden.

        Schreibt erst in ``<target>.part`` und benennt am Ende um: ein
        abgebrochener Download hinterlaesst keine halbe Datei unter dem
        richtigen Namen.
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
                    raise MoonrakerError(f"HTTP {resp.status} fuer {root}/{relative}")
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
        """Lokale Datei nach ``root/path`` hochladen (Unterordner werden angelegt)."""
        folder, name = posixpath.split(path.lstrip("/"))
        form = aiohttp.FormData()
        form.add_field("root", root)
        if folder:
            form.add_field("path", folder)
        # aiohttp liest Dateiobjekte im Executor; Datei bleibt bis zum Ende offen.
        fh = await asyncio.get_running_loop().run_in_executor(None, source.open, "rb")
        try:
            form.add_field("file", fh, filename=name, content_type="application/octet-stream")
            async with self._session.post(
                f"{self.base_url}/server/files/upload", data=form, headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=120),
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Upload abgelehnt (HTTP {resp.status}): {body[:200]}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"Upload zu {self.host}: {err}") from err
        finally:
            await asyncio.get_running_loop().run_in_executor(None, fh.close)
        try:
            data = json.loads(body)
        except ValueError:
            return {}
        return data.get("result", data) if isinstance(data, dict) else {}

    async def move_file(self, source: str, dest: str, root: str = "gcodes") -> None:
        """Umbenennen/Verschieben; fehlende Zielordner werden angelegt."""
        folder = posixpath.dirname(dest.lstrip("/"))
        # Moonraker legt Zielordner beim Verschieben nicht an, und auch nur je eine Ebene
        parts = folder.split("/") if folder else []
        for depth in range(1, len(parts) + 1):
            try:
                async with self._session.post(
                    f"{self.base_url}/server/files/directory", json={"path": f"{root}/{'/'.join(parts[:depth])}"},
                    headers=self._headers, timeout=HTTP_TIMEOUT,
                ):
                    pass  # 400 = gibt es schon
            except (aiohttp.ClientError, TimeoutError) as err:
                raise MoonrakerConnectionError(str(err)) from err
        url = f"{self.base_url}/server/files/move"
        body = {"source": f"{root}/{source.lstrip('/')}", "dest": f"{root}/{dest.lstrip('/')}"}
        try:
            async with self._session.post(url, json=body, headers=self._headers, timeout=HTTP_TIMEOUT) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Verschieben abgelehnt (HTTP {resp.status}): {text[:200]}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def temperature_store(self) -> dict[str, Any]:
        """Temperaturverlauf, den Moonraker ohnehin vorhaelt (1/s, 20 min)."""
        result = await self._get_json("/server/temperature_store", {"include_monitors": "false"})
        return result if isinstance(result, dict) else {}

    async def delete_file(self, path: str, root: str = "gcodes") -> None:
        url = f"{self.base_url}/server/files/{quote(root)}/{quote(path.lstrip('/'))}"
        try:
            async with self._session.delete(url, headers=self._headers, timeout=HTTP_TIMEOUT) as resp:
                if resp.status >= 400 and resp.status != 404:
                    raise MoonrakerError(f"Loeschen abgelehnt (HTTP {resp.status})")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(str(err)) from err

    async def firmware_version(self) -> str | None:
        """Installierte Firmware: product_info (Snapmaker-Moonraker), sonst Klipper-Version."""
        try:
            result = await self._get_json("/machine/system_info")
            prod = ((result or {}).get("system_info") or {}).get("product_info") or {}
            ver = prod.get("firmware_version") or prod.get("software_version")
            # Nur echte Versionsnummern; sonst (z. B. "?") die Klipper-Version
            if isinstance(ver, str) and re.search(r"\d+\.\d+", ver) and ver != "0.0.0":
                return ver
        except MoonrakerError:
            pass
        info = await self._get_json("/printer/info")
        ver = (info or {}).get("software_version") if isinstance(info, dict) else None
        return ver if isinstance(ver, str) and ver else None

    async def cpu_count(self) -> int | None:
        """Anzahl CPU-Kerne (fuer die Einordnung der Systemlast)."""
        result = await self._get_json("/machine/system_info")
        info = ((result or {}).get("system_info") or {}).get("cpu_info") or {}
        count = info.get("cpu_count")
        return int(count) if isinstance(count, int) and count > 0 else None

    async def history(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Abgeschlossene Druckauftraege aus Moonrakers [history], neueste zuerst."""
        result = await self._get_json("/server/history/list", {"limit": limit, "order": "desc"})
        jobs = (result or {}).get("jobs") if isinstance(result, dict) else None
        return [j for j in jobs or [] if isinstance(j, dict)]

    async def history_totals(self) -> dict[str, Any]:
        result = await self._get_json("/server/history/totals")
        totals = (result or {}).get("job_totals") if isinstance(result, dict) else None
        return totals if isinstance(totals, dict) else {}

    async def print_action(self, action: str) -> None:
        """pause | resume | cancel ueber JSON-RPC (Moonraker: printer.print.<action>)."""
        await self.rpc(f"printer.print.{action}", response_timeout=30)

    def websocket(self) -> Any:
        """Dauerhafte WebSocket-Verbindung (Kontextmanager) fuer das Live-Abo."""
        return self._session.ws_connect(
            f"ws://{self.host}:{self.port}/websocket", headers=self._headers, heartbeat=30,
            timeout=aiohttp.ClientWSTimeout(ws_close=10),
        )

    # ── WebSocket JSON-RPC ──────────────────────────────────────────────────
    async def rpc(self, method: str, params: dict[str, Any] | None = None,
                  response_timeout: float = 60) -> Any:
        """Einzelner JSON-RPC-Aufruf, Verbindung danach wieder zu.

        Moonraker schickt auf derselben Verbindung laufend notify_*-Meldungen;
        es zaehlt nur die Antwort mit passender id.
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
                            raise MoonrakerError(text or "Unbekannter Fehler")
                        return data.get("result")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"WebSocket zu {self.host}: {err}") from err
        raise MoonrakerConnectionError("WebSocket ohne Antwort geschlossen")

    async def start_print(
        self,
        path: str,
        map_table: str | None = None,
        bed_leveling: bool | None = None,
        flow_calibration: bool | None = None,
        timelapse: bool | None = None,
        plate: int = 1,
    ) -> dict[str, Any]:
        """Druck starten wie Snapmaker Orca.

        Die options-Schluessel landen grossgeschrieben als Parameter von
        SDCARD_PRINT_FILE_WITH_PARAMETERS (klippy_apis.start_print_advanced)
        und werden von SET_PRINT_TASK_PARAMETERS ausgewertet.
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
    """Minimaler Spoolman-Client (API v1)."""

    def __init__(self, session: aiohttp.ClientSession, url: str) -> None:
        self._session = session
        url = url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        self.url = url.removesuffix("/api/v1")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with self._session.request(
                method, f"{self.url}/api/v1{path}", timeout=aiohttp.ClientTimeout(total=10), **kwargs
            ) as resp:
                body = await resp.text()
                if resp.status >= 400:
                    raise MoonrakerError(f"Spoolman HTTP {resp.status}: {body[:200]}")
                return json.loads(body) if body else None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MoonrakerConnectionError(f"Spoolman nicht erreichbar: {err}") from err
        except ValueError as err:
            raise MoonrakerError("Ungueltige Antwort von Spoolman") from err

    async def info(self) -> dict[str, Any]:
        return await self._request("GET", "/info") or {}

    async def spools(self) -> list[dict[str, Any]]:
        result = await self._request("GET", "/spool", params={"allow_archived": "false"})
        return result if isinstance(result, list) else []

    async def use_weight(self, spool_id: int, grams: float) -> dict[str, Any]:
        return await self._request("PUT", f"/spool/{int(spool_id)}/use", json={"use_weight": round(grams, 2)})
