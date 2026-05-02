import json
import logging
from datetime import date, datetime, timezone
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.cache import WordOfDayCache

logger = logging.getLogger(__name__)

DEDUPE_WINDOW = 365

SYSTEM_PROMPT = """You are the curator of a Word of the Day for a household kitchen dashboard.

Pick a word that is:
- Uncommon but useful — something an educated reader might not know yet but would actually want to use, not pure obscurity
- Playful or literary in flavor — words with a story, a pleasing sound, a vivid image, or an unexpected English use
- Suitable for a family setting (no slurs, no profanity)

Return ONLY a JSON object with these exact keys:
- word: the headword, lowercase unless it's a proper noun
- pronunciation: phonetic respelling in Merriam-Webster style with stressed syllables in CAPS, wrapped in slashes — e.g. "/PET-ruh-kor/", "/SAR-uh-bin/", "/ee-fem-ER-uhl/". NOT IPA.
- definition: one clear sentence, plain English
- etymology: 1–2 sentences on language of origin and literal meaning
- example: one sentence using the word in a natural, modern context

No prose outside the JSON. No code fences."""


def _build_user_prompt(recent_words: list[str]) -> str:
    if not recent_words:
        return "Give me today's word."
    exclusions = ", ".join(recent_words)
    return f"Give me today's word. Do not repeat any of these recently-used words: {exclusions}"


async def _fetch_recent_words(db: AsyncSession, limit: int = DEDUPE_WINDOW) -> list[str]:
    stmt = (
        select(WordOfDayCache.word)
        .order_by(WordOfDayCache.generated_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [w for (w,) in result.all()]


async def generate_word_of_day(recent_words: list[str]) -> dict[str, Any]:
    """Call Claude haiku to generate one Word of the Day. Returns dict with
    keys: word, pronunciation, definition, etymology, example."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(recent_words)}],
    )
    raw = message.content[0].text.strip()
    parsed = json.loads(raw)
    for key in ("word", "definition"):
        if not parsed.get(key):
            raise ValueError(f"WOTD response missing required field '{key}': {raw!r}")
    return parsed


async def get_today_wotd(db: AsyncSession) -> WordOfDayCache | None:
    """Fetch the active WOTD row for today (most recent if multiple from regen)."""
    today = date.today()
    stmt = (
        select(WordOfDayCache)
        .where(WordOfDayCache.date == today)
        .order_by(WordOfDayCache.generated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def ensure_today_wotd(force_regenerate: bool = False) -> WordOfDayCache:
    """Generate today's WOTD if missing (or always, when force_regenerate=True).
    Replaced rows are kept in-place to remain in the dedupe pool."""
    async with AsyncSessionLocal() as db:
        existing = await get_today_wotd(db)
        if existing and not force_regenerate:
            return existing

        recent_words = await _fetch_recent_words(db)
        data = await generate_word_of_day(recent_words)

        row = WordOfDayCache(
            date=date.today(),
            word=data["word"],
            pronunciation=data.get("pronunciation"),
            definition=data["definition"],
            etymology=data.get("etymology"),
            example=data.get("example"),
            generated_at=datetime.now(timezone.utc),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info("WOTD generated for %s: %s", row.date, row.word)
        return row


def serialize(row: WordOfDayCache | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "word": row.word,
        "pronunciation": row.pronunciation,
        "definition": row.definition,
        "etymology": row.etymology,
        "example": row.example,
    }
