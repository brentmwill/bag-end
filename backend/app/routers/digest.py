from fastapi import APIRouter, HTTPException
from app.services import digest as digest_svc

router = APIRouter()


@router.post("/api/digest/regenerate")
async def regenerate_digest():
    """Force-generate a new digest for today and return it. Does not send."""
    try:
        row = await digest_svc.ensure_today_digest(force_regenerate=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Digest generation failed: {e}")
    return digest_svc.serialize(row)


@router.post("/api/digest/send")
async def send_digest():
    """DM today's cached digest to the configured recipient. Generates first
    if no row exists for today."""
    try:
        row = await digest_svc.ensure_today_digest(force_regenerate=False)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Digest generation failed: {e}")

    snippet = (row.content or {}).get("snippet")
    if not snippet:
        raise HTTPException(status_code=500, detail="Cached digest has no snippet")

    sent = await digest_svc.send_digest_dm(snippet)
    return {"sent": sent, "digest": digest_svc.serialize(row)}
