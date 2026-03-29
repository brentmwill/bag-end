import uuid
from datetime import date, datetime
from sqlalchemy import (
    String, Text, SmallInteger, Integer, Boolean, Date, ForeignKey,
    DateTime, ARRAY, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship
from typing import Optional, List, TYPE_CHECKING
from app.database import Base

if TYPE_CHECKING:
    from app.models.meal_plan import FreezerItem, MealPlanSlot
    from app.models.pantry import ReceiptItem


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    categories: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}")
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), server_default="{}")
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    prep_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cook_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    servings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nutrition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pregnancy_safe: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    baby_friendly: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    batch_cookable: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    freezable: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    last_made_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    steps: Mapped[List["RecipeStep"]] = relationship(
        "RecipeStep", back_populates="recipe", cascade="all, delete-orphan", order_by="RecipeStep.step_number"
    )
    ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    freezer_items: Mapped[List["FreezerItem"]] = relationship(
        "FreezerItem", back_populates="recipe"
    )
    meal_plan_slots: Mapped[List["MealPlanSlot"]] = relationship(
        "MealPlanSlot", back_populates="recipe"
    )


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="steps")


class IngredientCanonical(Base):
    __tablename__ = "ingredients_canonical"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recipe_ingredients: Mapped[List["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="canonical"
    )
    receipt_items: Mapped[List["ReceiptItem"]] = relationship(
        "ReceiptItem", back_populates="canonical"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_canonical_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingredients_canonical.id"), nullable=True
    )
    quantity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
    canonical: Mapped[Optional["IngredientCanonical"]] = relationship(
        "IngredientCanonical", back_populates="recipe_ingredients"
    )
