import uuid
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.meal_plan import MealPlanSlot
from app.models.recipe import RecipeIngredient
from app.services import anylist as anylist_service

router = APIRouter()


class MealPlanSlotCreate(BaseModel):
    date: date
    meal_type: str
    recipe_id: Optional[uuid.UUID] = None
    source: str = "planned"


class MealPlanSlotUpdate(BaseModel):
    recipe_id: Optional[uuid.UUID] = None


def slot_to_dict(slot: MealPlanSlot) -> dict:
    return {
        "id": slot.id,
        "date": slot.date,
        "meal_type": slot.meal_type,
        "source": slot.source,
        "recipe_id": slot.recipe_id,
        "recipe_name": slot.recipe.name if slot.recipe else None,
        "recipe_photo": slot.recipe.photo_path if slot.recipe else None,
    }


@router.get("/api/meal-plan")
async def list_meal_plan(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MealPlanSlot).options(selectinload(MealPlanSlot.recipe))
    if start:
        stmt = stmt.where(MealPlanSlot.date >= start)
    if end:
        stmt = stmt.where(MealPlanSlot.date <= end)
    stmt = stmt.order_by(MealPlanSlot.date)
    result = await db.execute(stmt)
    return [slot_to_dict(s) for s in result.scalars().all()]


@router.post("/api/meal-plan", status_code=201)
async def create_meal_plan_slot(data: MealPlanSlotCreate, db: AsyncSession = Depends(get_db)):
    slot = MealPlanSlot(**data.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot, ["recipe"])
    return slot_to_dict(slot)


@router.put("/api/meal-plan/{slot_id}")
async def update_meal_plan_slot(
    slot_id: uuid.UUID, data: MealPlanSlotUpdate, db: AsyncSession = Depends(get_db)
):
    stmt = select(MealPlanSlot).where(MealPlanSlot.id == slot_id).options(selectinload(MealPlanSlot.recipe))
    result = await db.execute(stmt)
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=404, detail="Meal plan slot not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(slot, field, value)
    await db.commit()
    await db.refresh(slot, ["recipe"])
    return slot_to_dict(slot)


@router.delete("/api/meal-plan/{slot_id}", status_code=204)
async def delete_meal_plan_slot(slot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    slot = await db.get(MealPlanSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Meal plan slot not found")
    await db.delete(slot)
    await db.commit()


class PushToAnyListRequest(BaseModel):
    week_start: date  # Monday of the week to push
    list_name: str = "Groceries"


@router.post("/api/meal-plan/push-to-anylist")
async def push_to_anylist(data: PushToAnyListRequest, db: AsyncSession = Depends(get_db)):
    week_end = data.week_start + timedelta(days=6)

    # Load all dinner slots for the week with their recipes + ingredients
    stmt = (
        select(MealPlanSlot)
        .where(MealPlanSlot.date >= data.week_start, MealPlanSlot.date <= week_end)
        .where(MealPlanSlot.recipe_id.is_not(None))
        .options(selectinload(MealPlanSlot.recipe).selectinload("ingredients"))
    )
    result = await db.execute(stmt)
    slots = result.scalars().all()

    if not slots:
        raise HTTPException(status_code=404, detail="No recipes planned for this week")

    # Collect unique ingredients across all recipes, with recipe names as notes
    seen: set[str] = set()
    ingredients: list[dict] = []
    for slot in slots:
        recipe = slot.recipe
        if not recipe:
            continue
        for ing in recipe.ingredients:
            key = ing.display_text.lower()
            if key not in seen:
                seen.add(key)
                ingredients.append({"name": ing.display_text, "notes": recipe.name})

    try:
        result = await anylist_service.push_ingredients(ingredients, list_name=data.list_name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "week": {"start": data.week_start, "end": week_end},
        "recipes": [s.recipe.name for s in slots if s.recipe],
        "ingredients_total": len(ingredients),
        **result,
    }
