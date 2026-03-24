import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.meal_plan import FreezerItem

router = APIRouter()


class FreezerItemCreate(BaseModel):
    recipe_id: uuid.UUID
    servings: int
    date_frozen: date
    notes: Optional[str] = None


class FreezerItemUpdate(BaseModel):
    servings: int


@router.get("/api/freezer")
async def list_freezer(db: AsyncSession = Depends(get_db)):
    stmt = select(FreezerItem).order_by(FreezerItem.date_frozen)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/api/freezer", status_code=201)
async def add_freezer_item(data: FreezerItemCreate, db: AsyncSession = Depends(get_db)):
    item = FreezerItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/api/freezer/{item_id}")
async def update_freezer_item(
    item_id: uuid.UUID, data: FreezerItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(FreezerItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Freezer item not found")
    item.servings = data.servings
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/api/freezer/{item_id}", status_code=204)
async def delete_freezer_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(FreezerItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Freezer item not found")
    await db.delete(item)
    await db.commit()
