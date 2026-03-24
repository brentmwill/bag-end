import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.meal_plan import MealPlanSlot

router = APIRouter()


class MealPlanSlotCreate(BaseModel):
    date: date
    meal_type: str
    recipe_id: Optional[uuid.UUID] = None
    source: str = "planned"


@router.get("/api/meal-plan")
async def list_meal_plan(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MealPlanSlot)
    if start:
        stmt = stmt.where(MealPlanSlot.date >= start)
    if end:
        stmt = stmt.where(MealPlanSlot.date <= end)
    stmt = stmt.order_by(MealPlanSlot.date)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/api/meal-plan", status_code=201)
async def create_meal_plan_slot(data: MealPlanSlotCreate, db: AsyncSession = Depends(get_db)):
    slot = MealPlanSlot(**data.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.delete("/api/meal-plan/{slot_id}", status_code=204)
async def delete_meal_plan_slot(slot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    slot = await db.get(MealPlanSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Meal plan slot not found")
    await db.delete(slot)
    await db.commit()
