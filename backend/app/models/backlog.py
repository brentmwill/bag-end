import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BacklogItem(Base):
    """Active friction / architecture-decision capture. Resolved rows move to BacklogArchive."""
    __tablename__ = "backlog_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repro_or_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_persona: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class BacklogArchive(Base):
    """Resolved or won't-fix backlog items. Move target for BacklogItem on resolution."""
    __tablename__ = "backlog_archive"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    repro_or_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_persona: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    resolution: Mapped[str] = mapped_column(Text, nullable=False)
