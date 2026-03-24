import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.recipe import Recipe

router = APIRouter()


class RecipeCreate(BaseModel):
    name: str
    categories: List[str] = []
    rating: Optional[int] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[str] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    notes: Optional[str] = None
    nutrition: Optional[str] = None
    photo_path: Optional[str] = None
    pregnancy_safe: bool = True
    baby_friendly: bool = True
    batch_cookable: bool = True
    freezable: bool = True
    last_made_date: Optional[date] = None


class RecipeUpdate(BaseModel):
    # Additional fields can be added here as needed
    rating: Optional[int] = None
    notes: Optional[str] = None


@router.get("/api/recipes")
async def list_recipes(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    pregnancy_safe: Optional[bool] = Query(None),
    baby_friendly: Optional[bool] = Query(None),
    batch_cookable: Optional[bool] = Query(None),
    freezable: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Recipe)
    if search:
        stmt = stmt.where(Recipe.name.ilike(f"%{search}%"))
    if category is not None:
        stmt = stmt.where(Recipe.categories.any(category))
    if pregnancy_safe is not None:
        stmt = stmt.where(Recipe.pregnancy_safe == pregnancy_safe)
    if baby_friendly is not None:
        stmt = stmt.where(Recipe.baby_friendly == baby_friendly)
    if batch_cookable is not None:
        stmt = stmt.where(Recipe.batch_cookable == batch_cookable)
    if freezable is not None:
        stmt = stmt.where(Recipe.freezable == freezable)
    result = await db.execute(stmt)
    recipes = result.scalars().all()
    return recipes


@router.get("/api/recipes/{recipe_id}")
async def get_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("/api/recipes", status_code=201)
async def create_recipe(data: RecipeCreate, db: AsyncSession = Depends(get_db)):
    recipe = Recipe(**data.model_dump())
    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@router.patch("/api/recipes/{recipe_id}")
async def update_recipe(
    recipe_id: uuid.UUID, data: RecipeUpdate, db: AsyncSession = Depends(get_db)
):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(recipe, field, value)
    await db.commit()
    await db.refresh(recipe)
    return recipe


@router.delete("/api/recipes/{recipe_id}", status_code=204)
async def delete_recipe(recipe_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    recipe = await db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.delete(recipe)
    await db.commit()


class ClipRequest(BaseModel):
    url: str


@router.post("/api/recipes/clip", status_code=501)
async def clip_recipe(data: ClipRequest):
    # TODO: use recipe-scrapers to scrape the given URL and return pre-filled recipe data
    # Example: scraper = scrape_me(data.url); return {name: scraper.title(), ...}
    raise HTTPException(status_code=501, detail="Recipe clipping not yet implemented")
