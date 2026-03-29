import json
import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic
from app.config import settings
from app.database import get_db
from app.models.recipe import Recipe, RecipeStep, RecipeIngredient

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
    raise HTTPException(status_code=501, detail="Recipe clipping not yet implemented")


class GenerateRequest(BaseModel):
    categories: List[str] = []
    pregnancy_safe: Optional[bool] = None
    baby_friendly: Optional[bool] = None
    freezable: Optional[bool] = None
    save: bool = False  # if True, persist to DB immediately


GENERATE_SYSTEM = """You are a helpful family meal planner. Generate a single recipe that fits the requested criteria.
Respond with ONLY valid JSON in this exact shape:
{
  "name": "Recipe Name",
  "prep_time": "15 mins",
  "cook_time": "30 mins",
  "servings": "4",
  "ingredients": [
    {"quantity": "1 lb", "display_text": "1 lb ground beef"},
    {"quantity": "2 cloves", "display_text": "2 cloves garlic, minced"}
  ],
  "directions": ["Step one...", "Step two..."],
  "notes": "Optional tips"
}
No markdown, no explanation — JSON only."""


@router.post("/api/recipes/generate")
async def generate_recipe(data: GenerateRequest, db: AsyncSession = Depends(get_db)):
    constraints = []
    if data.categories:
        constraints.append(f"Categories/cuisine/style: {', '.join(data.categories)}")
    if data.pregnancy_safe:
        constraints.append("Must be pregnancy-safe (no raw fish, deli meat, soft cheeses, etc.)")
    if data.baby_friendly:
        constraints.append("Must be baby/toddler-friendly (soft textures, mild flavors, finger-food or easily mashed)")
    if data.freezable:
        constraints.append("Must freeze well for batch cooking")

    prompt = "Generate a dinner recipe"
    if constraints:
        prompt += " with these requirements:\n" + "\n".join(f"- {c}" for c in constraints)
    else:
        prompt += "."

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=GENERATE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        recipe_data = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError, KeyError):
        raise HTTPException(status_code=502, detail="Failed to parse generated recipe")

    if data.save:
        recipe = Recipe(
            name=recipe_data["name"],
            prep_time=recipe_data.get("prep_time"),
            cook_time=recipe_data.get("cook_time"),
            servings=recipe_data.get("servings"),
            notes=recipe_data.get("notes"),
            categories=data.categories,
            pregnancy_safe=data.pregnancy_safe or False,
            baby_friendly=data.baby_friendly or False,
            freezable=data.freezable or False,
        )
        db.add(recipe)
        await db.flush()

        for i, step in enumerate(recipe_data.get("directions", []), start=1):
            db.add(RecipeStep(recipe_id=recipe.id, step_number=i, instruction=step))

        for ing in recipe_data.get("ingredients", []):
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                quantity=ing.get("quantity"),
                display_text=ing["display_text"],
            ))

        await db.commit()
        await db.refresh(recipe)
        recipe_data["id"] = str(recipe.id)
        recipe_data["saved"] = True
    else:
        recipe_data["saved"] = False

    return recipe_data
