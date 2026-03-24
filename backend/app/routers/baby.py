import uuid
from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.baby import BabyMealSlot

router = APIRouter()


class BabyMealSlotCreate(BaseModel):
    date: date_type
    slot_type: str
    description: Optional[str] = None


@router.get("/api/baby/slots")
async def get_baby_slots(
    date: Optional[date_type] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    target_date = date or date_type.today()
    stmt = (
        select(BabyMealSlot)
        .where(BabyMealSlot.date == target_date)
        .order_by(BabyMealSlot.logged_at)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/api/baby/slots", status_code=201)
async def create_baby_slot(data: BabyMealSlotCreate, db: AsyncSession = Depends(get_db)):
    slot = BabyMealSlot(**data.model_dump())
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return slot


@router.delete("/api/baby/slots/{slot_id}", status_code=204)
async def delete_baby_slot(slot_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    slot = await db.get(BabyMealSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Baby meal slot not found")
    await db.delete(slot)
    await db.commit()
