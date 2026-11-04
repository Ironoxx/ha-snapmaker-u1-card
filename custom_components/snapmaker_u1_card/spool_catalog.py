"""Suggestions for a new spool: own Spoolman filaments and the SpoolmanDB catalogue.

Spoolman ships the community database SpoolmanDB (``/api/v1/external/filament``,
several thousand filaments of known vendors with colour, weight, empty spool
weight and temperatures). The card searches it together with the filaments
already in Spoolman, so a new spool is usually one pick away. The catalogue
changes rarely and is a few MB, so it is fetched once a day and searched here,
not in the browser.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .api import MoonrakerError, SpoolmanClient
from .parsing import DENSITY, normalize_color

_LOGGER = logging.getLogger(__name__)

EXTERNAL_TTL = 24 * 3600
LIMIT = 40


def _num(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def compact_own(f: dict[str, Any]) -> dict[str, Any]:
    """A filament already in Spoolman."""
    color = normalize_color(f.get("color_hex"))
    multi = [c for c in (normalize_color(x) for x in str(f.get("multi_color_hexes") or "").split(",")) if c]
    return {
        "key": f"f:{f.get('id')}", "source": "own", "filament_id": f.get("id"),
        "vendor": (f.get("vendor") or {}).get("name") or "", "name": f.get("name") or "",
        "material": str(f.get("material") or "").upper(), "color": color or (multi[0] if multi else None),
        "colors": multi or ([color] if color else []),
        "weight": _num(f.get("weight")), "spool_weight": _num(f.get("spool_weight")),
        "price": _num(f.get("price")),
        "extruder_temp": f.get("settings_extruder_temp"), "bed_temp": f.get("settings_bed_temp"),
        "external_id": f.get("external_id"),
    }


def compact_external(f: dict[str, Any]) -> dict[str, Any]:
    """A filament from SpoolmanDB."""
    color = normalize_color(f.get("color_hex"))
    multi = [c for c in (normalize_color(x) for x in (f.get("color_hexes") or [])) if c]
    return {
        "key": f"x:{f.get('id')}", "source": "db", "external_id": f.get("id"),
        "vendor": f.get("manufacturer") or "", "name": f.get("name") or "",
        "material": str(f.get("material") or "").upper(), "color": color or (multi[0] if multi else None),
        "colors": multi or ([color] if color else []),
        "weight": _num(f.get("weight")), "spool_weight": _num(f.get("spool_weight")),
        "density": _num(f.get("density")), "diameter": _num(f.get("diameter")),
        "extruder_temp": f.get("extruder_temp"), "bed_temp": f.get("bed_temp"),
    }


def search(items: list[dict[str, Any]], query: str = "", vendor: str = "", material: str = "",
           limit: int = LIMIT) -> list[dict[str, Any]]:
    """Items whose vendor, name and material contain every word of the query.

    Own filaments come first, then exact vendor and material matches, then by name.
    """
    words = [w for w in query.casefold().split() if w]
    ven, mat = vendor.strip().casefold(), material.strip().casefold()
    hits = []
    for it in items:
        if ven and ven not in it["vendor"].casefold():
            continue
        text = f"{it['vendor']} {it['name']} {it['material']}".casefold()
        if not all(w in text for w in words):
            continue
        score = (0 if it["source"] == "own" else 1,
                 0 if ven and it["vendor"].casefold() == ven else 1,
                 0 if mat and it["material"].casefold() == mat else 1,
                 it["vendor"].casefold(), it["name"].casefold())
        hits.append((score, it))
    hits.sort(key=lambda h: h[0])
    return [it for _, it in hits[:limit]]


def external_body(ext: dict[str, Any], vendor_id: int) -> dict[str, Any]:
    """Spoolman filament body for a SpoolmanDB entry."""
    mat = ext["material"] or "PLA"
    body: dict[str, Any] = {
        "name": ext["name"] or mat, "vendor_id": vendor_id, "material": mat,
        "density": ext.get("density") or DENSITY.get(mat, DENSITY.get(mat.split("-")[0], 1.24)),
        "diameter": ext.get("diameter") or 1.75,
        "external_id": ext["external_id"],
    }
    if ext.get("weight"):
        body["weight"] = ext["weight"]
    if ext.get("spool_weight"):
        body["spool_weight"] = ext["spool_weight"]
    if len(ext.get("colors") or []) > 1:
        body["multi_color_hexes"] = ",".join(c.lstrip("#").lower() for c in ext["colors"])
    elif ext.get("color"):
        body["color_hex"] = ext["color"].lstrip("#").lower()
    if isinstance(ext.get("extruder_temp"), int):
        body["settings_extruder_temp"] = ext["extruder_temp"]
    if isinstance(ext.get("bed_temp"), int):
        body["settings_bed_temp"] = ext["bed_temp"]
    return body


class SpoolCatalog:
    """Own filaments (fresh per request) plus the cached SpoolmanDB catalogue."""

    def __init__(self) -> None:
        self._external: list[dict[str, Any]] = []
        self._fetched = 0.0

    async def external(self, client: SpoolmanClient) -> list[dict[str, Any]]:
        if time.time() - self._fetched > EXTERNAL_TTL or not self._external:
            try:
                raw = await client.external_filaments()
                # the U1 takes 1.75 mm only
                self._external = [compact_external(f) for f in raw
                                  if isinstance(f, dict) and (f.get("diameter") in (None, 1.75))]
                self._fetched = time.time()
            except MoonrakerError as err:
                # older Spoolman without SpoolmanDB, or no internet on the Spoolman host
                _LOGGER.debug("Spoolman catalogue not available: %s", err)
                self._fetched = time.time() - EXTERNAL_TTL + 600  # try again in 10 min
        return self._external

    def find_external(self, external_id: str) -> dict[str, Any] | None:
        return next((f for f in self._external if f["external_id"] == external_id), None)

    async def items(self, client: SpoolmanClient) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        own = [compact_own(f) for f in await client.filaments() if isinstance(f, dict)]
        known = {f["external_id"] for f in own if f["external_id"]}
        # a SpoolmanDB entry already imported shows up once, as the own filament
        ext = [f for f in await self.external(client) if f["external_id"] not in known]
        return own, ext

    async def overview(self, client: SpoolmanClient) -> dict[str, Any]:
        """Vendor and material names for the form's suggestions."""
        own, ext = await self.items(client)
        own_vendors = [str(v.get("name") or "") for v in await client.vendors()]
        vendors = sorted({v for v in own_vendors if v}, key=str.casefold)
        vendors += sorted({f["vendor"] for f in ext if f["vendor"]} - set(vendors), key=str.casefold)
        materials = sorted({f["material"] for f in own + ext if f["material"]})
        return {"vendors": vendors, "own_vendors": len([v for v in own_vendors if v]),
                "materials": materials, "catalog": len(ext)}

    async def suggest(self, client: SpoolmanClient, query: str, vendor: str, material: str) -> list[dict[str, Any]]:
        own, ext = await self.items(client)
        return search(own + ext, query, vendor, material)
