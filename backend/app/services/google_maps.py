import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DM_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

TILE_LABELS = {
    0: "Brent → Work",
    1: "Brent ← Work",
    2: "Danielle → Work",
    3: "Danielle ← Work",
}

# In-memory cache of last good tile data, keyed by tile index.
# Survives across glance refreshes; lost on process restart.
_tiles: dict[int, dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_tile(label: str, element: dict | None) -> dict[str, Any] | None:
    if not element or element.get("status") != "OK":
        return None
    duration = element.get("duration_in_traffic") or element.get("duration")
    distance = element.get("distance")
    if not duration or not distance:
        return None
    return {
        "label": label,
        "duration_min": round(duration["value"] / 60),
        "distance_km": round(distance["value"] / 1000, 2),
        "updated_at": _now_iso(),
    }


def _addresses_configured() -> bool:
    return bool(
        settings.google_maps_api_key
        and settings.home_address
        and settings.brent_work_address
        and settings.danielle_work_address
    )


async def _call_dm(origins: list[str], destinations: list[str]) -> dict | None:
    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "departure_time": "now",
        "key": settings.google_maps_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DM_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Distance Matrix request failed")
        return None
    if data.get("status") != "OK":
        logger.warning("Distance Matrix non-OK status: %s", data.get("status"))
        return None
    return data


async def refresh_outbound() -> None:
    """Refresh tiles 0 (Brent→Work) and 2 (Danielle→Work) — single batched call."""
    if not _addresses_configured():
        return
    data = await _call_dm(
        origins=[settings.home_address],
        destinations=[settings.brent_work_address, settings.danielle_work_address],
    )
    if not data:
        return
    elements = data.get("rows", [{}])[0].get("elements", [])
    if len(elements) >= 2:
        if t0 := _build_tile(TILE_LABELS[0], elements[0]):
            _tiles[0] = t0
        if t2 := _build_tile(TILE_LABELS[2], elements[1]):
            _tiles[2] = t2


async def refresh_inbound() -> None:
    """Refresh tiles 1 (Brent←Work) and 3 (Danielle←Work) — single batched call."""
    if not _addresses_configured():
        return
    data = await _call_dm(
        origins=[settings.brent_work_address, settings.danielle_work_address],
        destinations=[settings.home_address],
    )
    if not data:
        return
    rows = data.get("rows", [])
    if len(rows) >= 2:
        b_el = rows[0].get("elements", [None])[0]
        d_el = rows[1].get("elements", [None])[0]
        if t1 := _build_tile(TILE_LABELS[1], b_el):
            _tiles[1] = t1
        if t3 := _build_tile(TILE_LABELS[3], d_el):
            _tiles[3] = t3


async def refresh_all() -> None:
    """Refresh all 4 tiles. Used for cold-start and manual button press."""
    await asyncio.gather(refresh_outbound(), refresh_inbound())


def _is_morning_rush(now_et: datetime) -> bool:
    if now_et.weekday() >= 5:
        return False
    hm = (now_et.hour, now_et.minute)
    return (6, 30) <= hm < (8, 15)


def _is_evening_rush(now_et: datetime) -> bool:
    if now_et.weekday() >= 5:
        return False
    return 16 <= now_et.hour < 18


async def smart_refresh() -> None:
    """Called by the 5-min scheduler tick. Only refreshes the relevant
    direction during the corresponding rush window. No-op outside rush."""
    if not _addresses_configured():
        return
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if _is_morning_rush(now_et):
        await refresh_outbound()
    if _is_evening_rush(now_et):
        await refresh_inbound()


def get_tiles() -> list[dict[str, Any] | None]:
    """Return the 4 tiles in fixed order. Missing tiles are None."""
    return [_tiles.get(i) for i in range(4)]


async def fetch_commute_tiles() -> list[dict[str, Any] | None]:
    """Compatibility wrapper for glance_cache. Triggers cold-start fetch
    if no tiles have been populated yet (post-restart)."""
    if not any(_tiles.values()) and _addresses_configured():
        await refresh_all()
    return get_tiles()
