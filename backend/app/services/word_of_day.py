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

# Words used as worked examples in the system prompt — exclude from candidate
# pool defensively in case the model leans on them as suggestions.
SEED_EXCLUDED_WORDS = ["umami", "petrichor", "ephemeral", "saraband", "halcyon"]

SYSTEM_PROMPT = """You are the curator of a Word of the Day for a household kitchen dashboard.

Pick a word that is:
- Uncommon but useful — something an educated reader might not know yet but would actually want to use, not pure obscurity
- Playful or literary in flavor — words with a story, a pleasing sound, a vivid image, or an unexpected English use
- Suitable for a family setting (no slurs, no profanity)

Return ONLY a JSON object with these exact keys:
- word: the headword, lowercase unless it's a proper noun
- pronunciation: phonetic respelling in Merriam-Webster style with stressed syllables in CAPS, wrapped in slashes. NOT IPA.
- definition: one clear sentence, plain English
- etymology: 1–2 sentences on language of origin and literal meaning
- example: one sentence using the word in a natural, modern context

CRITICAL — pronunciation rules:
1. Every consonant in the source word MUST appear in the respelling. Do not drop letters.
2. Mentally read your respelling out loud and confirm it sounds like the source word before returning.
3. Worked examples (FORMAT REFERENCE ONLY — do NOT pick these as today's word):
   - "umami" → "/oo-MAH-mee/"   (NOT "/oo-AH-mee/" — that drops the 'm')
   - "petrichor" → "/PET-ruh-kor/"
   - "ephemeral" → "/ee-FEM-uh-ruhl/"
   - "saraband" → "/SAR-uh-band/"
   - "halcyon" → "/HAL-see-uhn/"

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


def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # remove leading fence + optional language tag
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.endswith("```"):
            s = s[: -3]
    return s.strip()


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
    raw = message.content[0].text if message.content else ""
    cleaned = _strip_code_fence(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("WOTD JSON parse failed. Raw response: %r", raw)
        raise ValueError(f"WOTD JSON parse failed: {e}") from e
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
        # Merge with seed exclusions, preserving order, deduped
        seen = set()
        exclusions: list[str] = []
        for w in recent_words + SEED_EXCLUDED_WORDS:
            lw = w.lower()
            if lw not in seen:
                seen.add(lw)
                exclusions.append(w)
        data = await generate_word_of_day(exclusions)

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
