from fastapi import APIRouter, HTTPException
from app.services import google_maps as maps_svc
from app.services.glance_cache import get_cache, set_cache

router = APIRouter()


@router.post("/api/commute/refresh")
async def refresh_commute():
    """Force-refresh all 4 commute tiles (manual button)."""
    try:
        await maps_svc.refresh_all()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Commute refresh failed: {e}")

    tiles = maps_svc.get_tiles()
    cache = get_cache()
    if cache and cache.get("home") is not None:
        cache["home"]["commute_tiles"] = tiles
        set_cache(cache)

    return {"commute_tiles": tiles}
