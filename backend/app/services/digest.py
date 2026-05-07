import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import anthropic
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.cache import DigestCache
from app.models.meal_plan import MealPlanSlot
from app.services import google_calendar as calendar_svc
from app.services import weather as weather_svc

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo("America/New_York")

SYSTEM_PROMPT = """You are writing a private morning digest for one person, delivered as a Telegram DM at 6am.

Voice: plain and direct. Warm but spare. Like a thoughtful note from someone who knows the household well.

Synthesize, don't list. The reader can already see their calendar — your job is to give a feel for the shape of the day in 2-3 sentences.

Rules:
- 2-3 sentences total. No more.
- Mention the day's calendar in shape, not in detail (e.g. "three meetings this morning" not "9am standup, 10am one-on-one, 11am review").
- Include tonight's dinner only if there is one planned, in a natural phrase.
- Mention weather in lifestyle terms when relevant (e.g. "light jacket weather", "rain by afternoon"), not raw numbers.
- Include one forward-looking hook (tomorrow's first event or tomorrow's dinner) only if it's notable. Skip if it would feel like filler.
- No greeting, no sign-off, no emoji, no markdown.
- If the day looks light or empty, say so plainly. Don't pad.

Return ONLY a JSON object: {"snippet": "..."}

No prose outside the JSON. No code fences."""


def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.endswith("```"):
            s = s[: -3]
    return s.strip()


def _format_event(event: dict[str, Any]) -> str:
    title = event.get("title") or "(untitled)"
    start = event.get("start") or ""
    if event.get("all_day"):
        return f"{title} (all day)"
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        local = dt.astimezone(EASTERN)
        time_str = local.strftime("%I:%M %p").lstrip("0")
        return f"{title} at {time_str}"
    except Exception:
        return f"{title} at {start}"


def _split_events_by_day(events: list[dict[str, Any]], today: date, tomorrow: date) -> tuple[list, list]:
    today_events = []
    tomorrow_events = []
    for e in events:
        start = e.get("start") or ""
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            local_date = dt.astimezone(EASTERN).date()
        except Exception:
            # all-day events have date-only strings; parse as date
            try:
                local_date = date.fromisoformat(start[:10])
            except Exception:
                continue
        if local_date == today:
            today_events.append(e)
        elif local_date == tomorrow:
            tomorrow_events.append(e)
    return today_events, tomorrow_events


def _summarize_weather(weather: dict[str, Any] | None, today_iso: str) -> dict[str, Any] | None:
    if not weather:
        return None
    current = weather.get("current") or {}
    today_forecast = next(
        (f for f in weather.get("forecast", []) if f.get("date") == today_iso),
        None,
    )
    return {
        "current_temp_f": current.get("temp"),
        "current_weathercode": current.get("weathercode"),
        "high_f": (today_forecast or {}).get("max"),
        "low_f": (today_forecast or {}).get("min"),
        "precip_prob_pct": (today_forecast or {}).get("precip_prob"),
        "weathercode": (today_forecast or {}).get("code"),
    }


async def gather_inputs() -> dict[str, Any]:
    """Pull everything the digest prompt needs: today's events, tonight's
    dinner, weather, tomorrow's first event + dinner."""
    now_eastern = datetime.now(EASTERN)
    today = now_eastern.date()
    tomorrow = today + timedelta(days=1)

    # Calendar — span just enough to cover tomorrow in Eastern time
    raw_events = await calendar_svc.fetch_calendar_events(days_ahead=2)
    today_events_raw, tomorrow_events_raw = _split_events_by_day(raw_events, today, tomorrow)
    today_events = [_format_event(e) for e in today_events_raw]
    tomorrow_first = _format_event(tomorrow_events_raw[0]) if tomorrow_events_raw else None

    # Weather
    try:
        weather_raw = await weather_svc.fetch_weather(settings.weather_lat, settings.weather_lon)
    except Exception:
        logger.exception("digest: weather fetch failed")
        weather_raw = None
    weather = _summarize_weather(weather_raw, today.isoformat())

    # Meal plan — tonight + tomorrow's dinner
    tonight_dinner: str | None = None
    tomorrow_dinner: str | None = None
    async with AsyncSessionLocal() as db:
        stmt = (
            select(MealPlanSlot)
            .where(
                MealPlanSlot.date.in_([today, tomorrow]),
                MealPlanSlot.meal_type == "dinner",
            )
            .options(selectinload(MealPlanSlot.recipe))
        )
        result = await db.execute(stmt)
        for slot in result.scalars().all():
            name = slot.recipe.name if slot.recipe else (slot.notes or None)
            if not name:
                continue
            if slot.date == today:
                tonight_dinner = name
            elif slot.date == tomorrow:
                tomorrow_dinner = name

    return {
        "today": {
            "date": today.isoformat(),
            "weekday": today.strftime("%A"),
            "events": today_events,
            "dinner": tonight_dinner,
            "weather": weather,
        },
        "tomorrow": {
            "date": tomorrow.isoformat(),
            "weekday": tomorrow.strftime("%A"),
            "first_event": tomorrow_first,
            "dinner": tomorrow_dinner,
        },
    }


async def generate_digest(inputs: dict[str, Any]) -> dict[str, Any]:
    """Call Sonnet to generate today's digest snippet. Returns {"snippet": "..."}."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_prompt = (
        "Here's today's context. Write the digest.\n\n"
        f"{json.dumps(inputs, indent=2)}"
    )
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text if message.content else ""
    cleaned = _strip_code_fence(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Digest JSON parse failed. Raw response: %r", raw)
        raise ValueError(f"Digest JSON parse failed: {e}") from e
    if not parsed.get("snippet"):
        raise ValueError(f"Digest response missing 'snippet': {raw!r}")
    return {"snippet": parsed["snippet"].strip()}


async def get_today_digest(db) -> DigestCache | None:
    today = datetime.now(EASTERN).date()
    stmt = select(DigestCache).where(DigestCache.date == today)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def ensure_today_digest(force_regenerate: bool = False) -> DigestCache:
    """Generate today's digest if missing (or always, when force_regenerate=True).
    DigestCache.date is unique, so regen updates the existing row in place."""
    async with AsyncSessionLocal() as db:
        existing = await get_today_digest(db)
        if existing and not force_regenerate:
            return existing

        inputs = await gather_inputs()
        content = await generate_digest(inputs)

        if existing:
            existing.content = content
            existing.generated_at = datetime.now(timezone.utc)
            row = existing
        else:
            row = DigestCache(
                date=datetime.now(EASTERN).date(),
                content=content,
                generated_at=datetime.now(timezone.utc),
            )
            db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("Digest generated for %s", row.date)
        return row


async def send_digest_dm(snippet: str) -> bool:
    """DM the digest snippet to the configured recipient. Returns True if sent."""
    from app.services.telegram_bot import get_bot

    recipient = settings.digest_recipient_telegram_id
    if not recipient:
        logger.warning("digest: DIGEST_RECIPIENT_TELEGRAM_ID not configured; skipping DM")
        return False

    bot = get_bot()
    if not bot:
        logger.warning("digest: telegram bot not running; skipping DM")
        return False

    try:
        await bot.send_message(chat_id=recipient, text=snippet)
        return True
    except Exception:
        logger.exception("digest: failed to DM recipient %s", recipient)
        return False


def serialize(row: DigestCache | None) -> dict[str, Any] | None:
    if not row:
        return None
    content = row.content or {}
    return {
        "date": row.date.isoformat(),
        "snippet": content.get("snippet"),
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }
