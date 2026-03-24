from typing import Any


async def fetch_calendar_events(days_ahead: int = 7) -> list[dict[str, Any]]:
    # TODO: Implement using google-api-python-client with a service account.
    # - Load credentials from settings.google_calendar_credentials_path
    # - Build a service: googleapiclient.discovery.build("calendar", "v3", credentials=creds)
    # - Fetch events from each calendar ID in settings.google_calendar_id_list
    # - Query timeMin=now(), timeMax=now()+timedelta(days=days_ahead)
    # - Return a flat list of event dicts with keys: id, summary, start, end, calendar_id
    return []
