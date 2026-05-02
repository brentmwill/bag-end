from fastapi import APIRouter, HTTPException
from app.services import word_of_day as wotd_svc
from app.services.glance_cache import get_cache, set_cache

router = APIRouter()


@router.post("/api/wotd/regenerate")
async def regenerate_wotd():
    """Force-generate a new WOTD for today. The replaced row stays in the
    table so its word remains in the dedupe pool."""
    try:
        row = await wotd_svc.ensure_today_wotd(force_regenerate=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WOTD generation failed: {e}")

    serialized = wotd_svc.serialize(row)

    cache = get_cache()
    if cache and cache.get("ambient") is not None:
        cache["ambient"]["word_of_day"] = serialized
        set_cache(cache)

    return serialized
