from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.glance_cache import get_cache, refresh_glance

router = APIRouter()


class HomeView(BaseModel):
    weather: Any = None
    tonight_meal: Any = None
    calendar_events: Any = None
    commute_tiles: Any = None
    digest_snippet: Any = None


class PlanningView(BaseModel):
    meal_plan_week: Any = None
    calendar_week: Any = None


class HouseholdView(BaseModel):
    trello_tasks: Any = None
    baby_meal_slots: Any = None
    freezer_items: Any = None
    sports_teams: Any = None


class AmbientView(BaseModel):
    word_of_day: Any = None


class GlanceResponse(BaseModel):
    home: Optional[HomeView] = None
    planning: Optional[PlanningView] = None
    household: Optional[HouseholdView] = None
    ambient: Optional[AmbientView] = None
    cached_at: Optional[datetime] = None


@router.get("/api/glance", response_model=GlanceResponse)
async def get_glance():
    cache = get_cache()
    if not cache:
        cache = await refresh_glance()
    return GlanceResponse(**cache)
