"""Cross-persona shared logs: conversation_log + food_log.

ConversationLog captures every inbound + outbound DM, with the persona that
handled it. Drives stickiness lookups and cross-persona context.

FoodLog captures meal intake. Chef Sue writes; Health reads (Brent-only,
enforced at the query layer in Phase 1.5 step 5).
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConversationLog(Base):
    """Every inbound + outbound DM. Required for stickiness routing and
    cross-persona context retrieval.

    telegram_user_id is the raw Telegram id and is always present, so we can log
    messages from people who haven't registered yet. user_profile_id is filled
    in once the sender is resolved.
    """
    __tablename__ = "conversation_log"
    __table_args__ = (
        Index("ix_conversation_log_tg_user_time", "telegram_user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    direction: Mapped[str] = mapped_column(Text, nullable=False)  # 'in' | 'out'
    persona: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class FoodLog(Base):
    """One row per meal eaten. recipe_id links to a known recipe when available;
    otherwise freeform_description captures what was eaten. CHECK ensures at
    least one is set.
    """
    __tablename__ = "food_log"
    __table_args__ = (
        CheckConstraint(
            "recipe_id IS NOT NULL OR freeform_description IS NOT NULL",
            name="ck_food_log_recipe_or_description",
        ),
        Index("ix_food_log_user_time", "user_profile_id", "eaten_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recipe_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    freeform_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grams: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    est_calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    est_macros: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
