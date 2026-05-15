"""Backlog capture service — Haiku normalizer + persistence.

Friction notes and architecture decisions arrive as freeform text. The Haiku
normalizer reshapes them into the schema (area / severity / description /
repro_or_context / proposed_fix). Resolution moves rows to backlog_archive so
default reads stay small.
"""
import json
import logging
import uuid
from typing import Any, Optional

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.backlog import BacklogArchive, BacklogItem

logger = logging.getLogger(__name__)

VALID_SEVERITY = {"low", "med", "high"}
VALID_RESOLUTION = {"done", "wontfix"}

# Areas are advisory — Haiku is told the current set but free-text is fine so
# new subsystems don't require a code change.
KNOWN_AREAS = [
    "chef", "inbox", "majordomo", "health", "finance", "chores",
    "routing", "display", "infra", "data", "telegram", "other",
]

NORMALIZER_SYSTEM_PROMPT = """You are reshaping a freeform friction note from a household dashboard project into a structured backlog item.

Return ONLY a JSON object with these exact keys:
- area: which subsystem this touches. Pick from: {areas}. Use "other" if nothing fits.
- severity: one of "low", "med", "high"
  - low: minor annoyance, cosmetic, nice-to-have
  - med: working but degraded, real friction in daily use
  - high: broken, blocking, or data-integrity risk
- description: one-sentence summary, imperative or declarative
- repro_or_context: how to reproduce OR the surrounding context (1-3 sentences). Null if not applicable.
- proposed_fix: a concrete fix if the note suggests one. Null if no fix was proposed.

No prose outside the JSON. No code fences."""


def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


async def normalize_freeform(text: str) -> dict[str, Any]:
    """Call Haiku to reshape a freeform note into backlog schema fields.

    Returns a dict with keys: area, severity, description, repro_or_context, proposed_fix.
    repro_or_context and proposed_fix may be None.
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = NORMALIZER_SYSTEM_PROMPT.format(areas=", ".join(KNOWN_AREAS))
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text if message.content else ""
    cleaned = _strip_code_fence(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Backlog normalizer JSON parse failed. Raw: %r", raw)
        raise ValueError(f"Backlog normalizer JSON parse failed: {e}") from e

    if not parsed.get("description"):
        raise ValueError(f"Normalizer returned no description: {raw!r}")
    if parsed.get("severity") not in VALID_SEVERITY:
        raise ValueError(f"Normalizer returned invalid severity {parsed.get('severity')!r}: {raw!r}")
    if not parsed.get("area"):
        parsed["area"] = "other"
    return parsed


async def create_item(
    session: AsyncSession,
    *,
    freeform_text: str,
    created_by_persona: str,
) -> BacklogItem:
    """Normalize freeform_text via Haiku and persist a BacklogItem. Caller commits."""
    fields = await normalize_freeform(freeform_text)
    item = BacklogItem(
        area=fields["area"],
        severity=fields["severity"],
        description=fields["description"],
        repro_or_context=fields.get("repro_or_context"),
        proposed_fix=fields.get("proposed_fix"),
        created_by_persona=created_by_persona,
    )
    session.add(item)
    return item


async def resolve_item(
    session: AsyncSession,
    *,
    item_id: uuid.UUID,
    resolution: str,
) -> Optional[BacklogArchive]:
    """Move an active item to backlog_archive. Returns the archive row, or None
    if the id was not found. Caller commits."""
    if resolution not in VALID_RESOLUTION:
        raise ValueError(f"resolution must be one of {VALID_RESOLUTION}, got {resolution!r}")

    item = (await session.execute(
        select(BacklogItem).where(BacklogItem.id == item_id)
    )).scalar_one_or_none()
    if item is None:
        return None

    archived = BacklogArchive(
        id=item.id,
        area=item.area,
        severity=item.severity,
        description=item.description,
        repro_or_context=item.repro_or_context,
        proposed_fix=item.proposed_fix,
        created_by_persona=item.created_by_persona,
        created_at=item.created_at,
        resolution=resolution,
    )
    session.add(archived)
    await session.delete(item)
    return archived
