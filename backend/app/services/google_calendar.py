import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _build_service():
    import json
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from app.config import settings

    token_path = Path(settings.google_calendar_token_path)
    if not token_path.exists():
        raise FileNotFoundError(f"Google OAuth token not found at {token_path}")

    with open(token_path) as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist refreshed token
        token_data["token"] = creds.token
        with open(token_path, "w") as f:
            import json as _json
            _json.dump(token_data, f, indent=2)

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


async def fetch_calendar_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    from app.config import settings

    calendar_ids = settings.google_calendar_id_list
    if not calendar_ids:
        return []

    try:
        service = _build_service()
    except Exception:
        logger.exception("Failed to build Google Calendar service")
        return []

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    events = []
    for cal_id in calendar_ids:
        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            ).execute()

            for e in result.get("items", []):
                start = e.get("start", {})
                end = e.get("end", {})
                events.append({
                    "id": e.get("id"),
                    "summary": e.get("summary", "(No title)"),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "all_day": "date" in start,
                    "calendar_id": cal_id,
                })
        except Exception:
            logger.exception("Failed to fetch events for calendar %s", cal_id)

    events.sort(key=lambda e: e["start"] or "")
    return events
