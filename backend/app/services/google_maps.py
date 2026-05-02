import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

# Per-tile config: (label, origin_setting, destination_setting, avoid_tolls)
# Order matters — frontend reads commute_tiles[0..3] by index.
TILE_CONFIG: dict[int, dict[str, Any]] = {
    0: {"label": "Brent → Work",    "origin": "home_address",          "destination": "brent_work_address",    "avoid_tolls": True},
    1: {"label": "Brent ← Work",    "origin": "brent_work_address",    "destination": "home_address",          "avoid_tolls": True},
    2: {"label": "Danielle → Work", "origin": "home_address",          "destination": "danielle_work_address", "avoid_tolls": False},
    3: {"label": "Danielle ← Work", "origin": "danielle_work_address", "destination": "home_address",          "avoid_tolls": False},
}

OUTBOUND_TILES = (0, 2)  # home → work
INBOUND_TILES = (1, 3)   # work → home

# In-memory cache of last good tile data, keyed by tile index.
_tiles: dict[int, dict[str, Any]] = {}

# Direction words bolded in html_instructions that aren't road names.
_DIRECTION_WORDS = {
    "left", "right", "north", "south", "east", "west",
    "northwest", "northeast", "southwest", "southeast",
    "slight left", "slight right", "sharp left", "sharp right",
    "u-turn", "northbound", "southbound", "eastbound", "westbound",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _addresses_configured() -> bool:
    return bool(
        settings.google_maps_api_key
        and settings.home_address
        and settings.brent_work_address
        and settings.danielle_work_address
    )


def _extract_route_summary(steps: list[dict], max_roads: int = 4, min_meters: int = 480) -> list[str]:
    """Build an ordered list of the longest meaningful road segments along the route.

    Returns roads sorted by route order (not by distance). Filters out direction
    words, exit numbers (purely numeric/dash), and segments shorter than min_meters."""
    distances: dict[str, int] = {}
    first_seen: dict[str, int] = {}

    for i, step in enumerate(steps):
        instr = step.get("html_instructions", "")
        if not instr:
            continue
        # Drop the trailing destination div if present
        instr_clean = re.sub(r"<div[^>]*>.*?</div>", "", instr)
        bolded = re.findall(r"<b>([^<]+)</b>", instr_clean)
        if not bolded:
            continue
        # Take the FIRST bolded road-like token. Skip direction words and pure
        # exit numbers (digits + letters + dashes, no spaces).
        road = None
        for b in bolded:
            stripped = b.strip()
            if not stripped:
                continue
            if stripped.lower() in _DIRECTION_WORDS:
                continue
            # Skip exit numbers like "327-328B-A" (no internal spaces, contains digit + dash)
            if re.fullmatch(r"[0-9A-Z\-]+", stripped) and any(c.isdigit() for c in stripped):
                continue
            road = stripped
            break
        if not road:
            continue
        dist_m = step.get("distance", {}).get("value", 0)
        if road not in first_seen:
            first_seen[road] = i
        distances[road] = distances.get(road, 0) + dist_m

    meaningful = [(r, d) for r, d in distances.items() if d >= min_meters]
    meaningful.sort(key=lambda x: x[1], reverse=True)
    top = meaningful[:max_roads]
    top.sort(key=lambda x: first_seen[x[0]])
    return [r for r, _ in top]


async def _fetch_tile(idx: int) -> dict[str, Any] | None:
    cfg = TILE_CONFIG[idx]
    origin = getattr(settings, cfg["origin"])
    destination = getattr(settings, cfg["destination"])
    if not (origin and destination and settings.google_maps_api_key):
        return None
    params: dict[str, Any] = {
        "origin": origin,
        "destination": destination,
        "departure_time": "now",
        "key": settings.google_maps_api_key,
    }
    if cfg["avoid_tolls"]:
        params["avoid"] = "tolls"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DIRECTIONS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Directions API request failed for tile %d", idx)
        return None
    if data.get("status") != "OK" or not data.get("routes"):
        logger.warning("Directions non-OK for tile %d: %s", idx, data.get("status"))
        return None
    route = data["routes"][0]
    leg = route["legs"][0]
    duration = leg.get("duration_in_traffic") or leg.get("duration")
    distance = leg.get("distance")
    if not duration or not distance:
        return None
    return {
        "label": cfg["label"],
        "duration_min": round(duration["value"] / 60),
        "distance_km": round(distance["value"] / 1000, 2),
        "route_summary": _extract_route_summary(leg.get("steps", [])),
        "updated_at": _now_iso(),
    }


async def _refresh_indices(indices: tuple[int, ...]) -> None:
    if not _addresses_configured():
        return
    results = await asyncio.gather(*(_fetch_tile(i) for i in indices))
    for idx, tile in zip(indices, results):
        if tile:
            _tiles[idx] = tile


async def refresh_outbound() -> None:
    await _refresh_indices(OUTBOUND_TILES)


async def refresh_inbound() -> None:
    await _refresh_indices(INBOUND_TILES)


async def refresh_all() -> None:
    """Refresh all 4 tiles. Used for cold-start and manual button press."""
    await _refresh_indices((0, 1, 2, 3))


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
    """5-min scheduler tick: refresh only the active direction during rush windows."""
    if not _addresses_configured():
        return
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if _is_morning_rush(now_et):
        await refresh_outbound()
    if _is_evening_rush(now_et):
        await refresh_inbound()


def get_tiles() -> list[dict[str, Any] | None]:
    return [_tiles.get(i) for i in range(4)]


async def fetch_commute_tiles() -> list[dict[str, Any] | None]:
    """Compatibility wrapper for glance_cache. Triggers a cold-start fetch
    if no tiles have been populated yet (post-restart)."""
    if not any(_tiles.values()) and _addresses_configured():
        await refresh_all()
    return get_tiles()
