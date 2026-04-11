from datetime import datetime, timezone
from fastapi import APIRouter, Query
from app.services.google_calendar import fetch_calendar_events

router = APIRouter()


@router.get("/api/calendar")
async def get_calendar(
    days: int = Query(45, ge=1, le=180),
    from_date: str | None = Query(None, description="YYYY-MM-DD start date (UTC). Defaults to today."),
):
    time_min: datetime | None = None
    if from_date:
        try:
            time_min = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    events = await fetch_calendar_events(days_ahead=days, time_min=time_min)
    return {"events": events}
