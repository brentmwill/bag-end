import uuid
from datetime import date, datetime
from sqlalchemy import Text, BigInteger, Date, ForeignKey, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from typing import List, Optional
from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # 'adult' | 'baby'
    telegram_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    dob: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    preference_events: Mapped[List["UserPreferenceEvent"]] = relationship(
        "UserPreferenceEvent", back_populates="user_profile", cascade="all, delete-orphan"
    )
    static_preferences: Mapped[List["StaticPreference"]] = relationship(
        "StaticPreference", back_populates="user_profile", cascade="all, delete-orphan"
    )


class UserPreferenceEvent(Base):
    __tablename__ = "user_preference_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    user_profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="preference_events")


class StaticPreference(Base):
    __tablename__ = "static_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    # pref_type: 'veto' | 'allergen' | 'dietary_restriction' | 'cuisine_pref'
    pref_type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    user_profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="static_preferences")
