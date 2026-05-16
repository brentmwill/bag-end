"""User-scoped read helpers for personal data.

The contract: any read of personal data (food intake, message history, future
per-user resources) MUST go through a helper in this module. Each helper takes
the requesting user's id as a required keyword-only argument and bakes that
filter into the WHERE clause at the DB layer.

Why: the Haiku router may mis-classify a DM. If Danielle asks a health question
and the classifier routes it to Health, Health's tools must still only see
Danielle's data — never Brent's. The substrate lives here; persona-level
authorization (e.g. "Health refuses to answer for anyone except Brent") goes
in each persona's tools.py.

Writes are intentionally not gated — the code adding a row owns its
user_profile_id and there's no read-leak risk. Use SQLAlchemy directly.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.logs import ConversationLog, FoodLog


async def food_log_for_user(
    session: AsyncSession,
    *,
    requesting_user_profile_id: uuid.UUID,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> list[FoodLog]:
    """Return FoodLog rows scoped to a single user, newest first.

    `requesting_user_profile_id` is required and keyword-only — there is no
    "read all users' food" path through this module.
    """
    stmt = select(FoodLog).where(FoodLog.user_profile_id == requesting_user_profile_id)
    if since is not None:
        stmt = stmt.where(FoodLog.eaten_at >= since)
    if until is not None:
        stmt = stmt.where(FoodLog.eaten_at < until)
    stmt = stmt.order_by(FoodLog.eaten_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def conversation_log_for_user(
    session: AsyncSession,
    *,
    requesting_telegram_user_id: int,
    persona: Optional[str] = None,
    limit: int = 50,
) -> list[ConversationLog]:
    """Return ConversationLog rows for a single Telegram user, newest first.

    Scoping uses telegram_user_id because that's the always-present key; an
    unregistered sender has no user_profile_id but still has a chat history
    that's theirs alone.

    Pass `persona` to filter to that persona's portion of the conversation
    (useful for in-persona context windows).
    """
    stmt = select(ConversationLog).where(
        ConversationLog.telegram_user_id == requesting_telegram_user_id
    )
    if persona is not None:
        stmt = stmt.where(ConversationLog.persona == persona)
    stmt = stmt.order_by(ConversationLog.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
