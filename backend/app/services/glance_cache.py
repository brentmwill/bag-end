import asyncio
from datetime import datetime, timezone
from app.services import weather as weather_svc
from app.services import google_calendar as calendar_svc
from app.services import google_maps as maps_svc
from app.services import trello as trello_svc
from app.services import anylist as anylist_svc
from app.config import settings

_cache: dict = {}
_refresh_lock = asyncio.Lock()


def get_cache() -> dict:
    return _cache


def set_cache(data: dict) -> None:
    global _cache
    _cache = {**data, "cached_at": datetime.now(timezone.utc)}


async def refresh_glance() -> dict:
    if _refresh_lock.locked():
        return _cache

    async with _refresh_lock:
        # TODO: fetch weather data
        weather = await weather_svc.fetch_weather(settings.weather_lat, settings.weather_lon)

        # TODO: fetch today's calendar events for home view
        calendar_events = await calendar_svc.fetch_calendar_events(days_ahead=1)

        # TODO: fetch full week of calendar events for planning view
        calendar_week = await calendar_svc.fetch_calendar_events(days_ahead=7)

        # TODO: fetch commute tiles (Brent and Danielle home/work)
        commute_tiles = await maps_svc.fetch_commute_tiles()

        # TODO: fetch Trello household tasks
        trello_tasks = await trello_svc.fetch_tasks()

        # TODO: fetch AnyList grocery list
        grocery_list = await anylist_svc.fetch_grocery_list()  # noqa: F841

        # TODO: fetch tonight's meal plan slot from DB
        tonight_meal = None

        # TODO: fetch baby meal slots for today from DB
        baby_meal_slots = []

        # TODO: fetch freezer inventory from DB
        freezer_items = []

        # TODO: fetch or generate word of the day from WordOfDayCache
        word_of_day = None

        # TODO: fetch digest snippet from DigestCache for today
        digest_snippet = None

        # TODO: fetch meal plan for the current week from DB
        meal_plan_week = []

        data = {
            "home": {
                "weather": weather,
                "tonight_meal": tonight_meal,
                "calendar_events": calendar_events,
                "commute_tiles": commute_tiles,
                "digest_snippet": digest_snippet,
            },
            "planning": {
                "meal_plan_week": meal_plan_week,
                "calendar_week": calendar_week,
            },
            "household": {
                "trello_tasks": trello_tasks,
                "baby_meal_slots": baby_meal_slots,
                "freezer_items": freezer_items,
            },
            "ambient": {
                "word_of_day": word_of_day,
            },
        }

        set_cache(data)
        return _cache
