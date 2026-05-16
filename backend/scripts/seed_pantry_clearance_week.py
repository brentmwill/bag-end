"""
One-off seed for the 2026-05-16 → 2026-05-22 Pantry Clearance Week.
Inserts 6 recipes + steps + ingredients + meal_plan_slots (Sat-Thu dinners,
Fri left open), then pushes 3 produce items to AnyList.
Nutrition estimates are generated per-recipe via Claude Haiku.
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

import anthropic
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.models.recipe import Recipe, RecipeStep, RecipeIngredient  # noqa: E402
from app.models.meal_plan import MealPlanSlot  # noqa: E402
from app.services.anylist import push_ingredients  # noqa: E402


START_DATE = date(2026, 5, 16)  # Saturday
PLAN_LABEL = "pantry clearance week"
SLOT_SOURCE = "planned"
MEAL_TYPE = "dinner"

NUTRITION_MODEL = "claude-haiku-4-5-20251001"


RECIPES = [
    {
        "day_offset": 0,  # Sat 5/16
        "name": "Sous Vide Chicken with Panko Crust + Mac",
        "categories": ["Dinner", "High Protein", "Pasta"],
        "prep_time": "15 min",
        "cook_time": "90 min",
        "servings": "4",
        "batch_cookable": True,
        "freezable": False,
        "ingredients": [
            ("1.5 lb chicken tenderloins", "1.5", "lb"),
            ("1 cup Italian panko bread crumbs", "1", "cup"),
            ("2 eggs", "2", "whole"),
            ("2 cups bonza chickpea shells", "2", "cups"),
            ("1 cup shredded cheese", "1", "cup"),
            ("2 tbsp cream cheese", "2", "tbsp"),
            ("0.5 cup almond milk", "0.5", "cup"),
            ("0.5 cup frozen peas", "0.5", "cup"),
        ],
        "steps": [
            "Sous vide tenders 145F for 1.5 hr. Reserve extras for lunches.",
            "Dredge tenders in egg, then panko. Sear in hot oil 60-90 sec per side until golden.",
            "Cook shells. Make sauce: warm almond milk + cream cheese + shredded cheese until smooth.",
            "Toss shells with sauce and peas. Serve tenders alongside.",
        ],
    },
    {
        "day_offset": 1,  # Sun 5/17
        "name": "Sheet-Pan Mediterranean Salmon with Orzo",
        "categories": ["Mediterranean", "Dinner", "High Protein"],
        "prep_time": "10 min",
        "cook_time": "25 min",
        "servings": "4",
        "batch_cookable": False,
        "freezable": False,
        "ingredients": [
            ("4 Mediterranean salmon fillets", "4", "fillets"),
            ("1.5 cups orzo", "1.5", "cups"),
            ("0.25 cup sun-dried tomatoes", "0.25", "cup"),
            ("0.25 cup Kalamata olives", "0.25", "cup"),
            ("1 tbsp capers", "1", "tbsp"),
            ("1 cup frozen peas", "1", "cup"),
            ("0.5 cup Greek yogurt", "0.5", "cup"),
            ("2 tbsp dill", "2", "tbsp"),
            ("1 lemon", "1", "whole"),
            ("2 cloves garlic", "2", "cloves"),
        ],
        "steps": [
            "Cook orzo per package. Drain, toss with olive oil, sun-dried tomatoes, peas.",
            "Bake salmon at 400F until just cooked through, ~12-15 min.",
            "Whisk yogurt with dill, lemon zest, grated garlic, salt.",
            "Serve salmon over orzo; spoon sauce on top. Add chopped olives/capers to adult plates only.",
        ],
    },
    {
        "day_offset": 2,  # Mon 5/18
        "name": "Chicken Biryani Night",
        "categories": ["Dinner", "High Protein"],
        "prep_time": "10 min",
        "cook_time": "30 min",
        "servings": "4",
        "batch_cookable": True,
        "freezable": True,
        "ingredients": [
            ("1 biryani kit", "1", "kit"),
            ("1 lb chicken tenderloins", "1", "lb"),
            ("1 cup frozen peas", "1", "cup"),
            ("1 cup Greek yogurt", "1", "cup"),
            ("1 tbsp dill", "1", "tbsp"),
            ("2 tbsp pinenuts", "2", "tbsp"),
            ("4 pieces naan", "4", "pieces"),
            ("1 cucumber", "1", "whole"),
        ],
        "steps": [
            "Follow biryani kit instructions; add diced chicken tenderloins and peas.",
            "Make raita: yogurt + grated cucumber + dill + pinch salt.",
            "Warm naan. Toddler portion: plain biryani with naan strips and raita on side.",
        ],
    },
    {
        "day_offset": 3,  # Tue 5/19
        "name": "Naan Pizza Assembly Night",
        "categories": ["Dinner", "Baby"],
        "prep_time": "10 min",
        "cook_time": "10 min",
        "servings": "4",
        "batch_cookable": False,
        "freezable": False,
        "ingredients": [
            ("4 pieces naan", "4", "pieces"),
            ("1 cup pizza sauce", "1", "cup"),
            ("1.5 cups shredded cheese", "1.5", "cups"),
            ("1 cup Perdue chicken breast strips", "1", "cup"),
            ("0.25 cup Kalamata olives", "0.25", "cup"),
            ("0.25 cup sun-dried tomatoes", "0.25", "cup"),
        ],
        "steps": [
            "Preheat oven to 425F.",
            "Toddler assembles their own naan with sauce + cheese + chicken.",
            "Bake on sheet pan 8-10 min until cheese bubbles.",
        ],
    },
    {
        "day_offset": 4,  # Wed 5/20
        "name": "Tuscan White Bean & Pasta Soup",
        "categories": ["Soups and Stews", "Dinner", "Pasta", "Freezes Well"],
        "prep_time": "10 min",
        "cook_time": "25 min",
        "servings": "6",
        "batch_cookable": True,
        "freezable": True,
        "ingredients": [
            ("2 cans cannellini beans", "2", "cans"),
            ("1 cup bonza chickpea shells", "1", "cup"),
            ("4 cups beef broth", "4", "cups"),
            ("1 cup tomato puree", "1", "cup"),
            ("0.25 cup sun-dried tomatoes", "0.25", "cup"),
            ("2 stalks celery", "2", "stalks"),
            ("0.5 cup shredded cheese", "0.5", "cup"),
            ("1 onion", "1", "whole"),
            ("3 cloves garlic", "3", "cloves"),
            ("2 carrots", "2", "whole"),
        ],
        "steps": [
            "Saute diced onion, celery, carrots, garlic until soft.",
            "Add broth, tomato puree, sun-dried tomatoes, beans. Simmer 15 min.",
            "Add pasta shells; cook until al dente.",
            "Serve with shredded cheese on top. Toddler-safe as-is.",
        ],
    },
    {
        "day_offset": 5,  # Thu 5/21
        "name": "Madras Lentils with Naan and Yogurt",
        "categories": ["Dinner", "High Protein"],
        "prep_time": "5 min",
        "cook_time": "10 min",
        "servings": "4",
        "batch_cookable": False,
        "freezable": False,
        "ingredients": [
            ("2 pouches Madras lentils", "2", "pouches"),
            ("4 pieces naan", "4", "pieces"),
            ("0.5 cup Greek yogurt", "0.5", "cup"),
            ("0.5 cup frozen peas", "0.5", "cup"),
            ("2 tbsp walnuts", "2", "tbsp"),
        ],
        "steps": [
            "Heat lentils per pouch instructions; stir in peas at the end.",
            "Warm naan.",
            "Serve with yogurt dollop. Toddler gets plain; adults add toasted walnuts.",
        ],
    },
    # Fri 5/22 intentionally left open
]


SHOPPING_LIST = [
    {"name": "cucumber", "notes": PLAN_LABEL},
    {"name": "carrots", "notes": PLAN_LABEL},
    {"name": "parsley", "notes": PLAN_LABEL},
]


async def estimate_nutrition(client: anthropic.AsyncAnthropic, recipe: dict) -> str:
    ingredients_text = "\n".join(f"- {ing[0]}" for ing in recipe["ingredients"])
    prompt = (
        f"Estimate the per-serving nutrition for this recipe. "
        f"Servings: {recipe['servings']}.\n\n"
        f"Recipe: {recipe['name']}\n\nIngredients:\n{ingredients_text}\n\n"
        "Return ONLY a single line in this exact pipe-separated format, no preamble, no explanation:\n"
        "Calories: X | Carbohydrates: Yg | Protein: Zg | Fat: Wg | Sodium: Vmg\n"
        "Round to the nearest whole number."
    )
    msg = await client.messages.create(
        model=NUTRITION_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip().splitlines()[0].strip()


async def main():
    print(f"Seeding pantry clearance week starting {START_DATE}...")

    async with AsyncSessionLocal() as db:
        names = [r["name"] for r in RECIPES]
        existing = (await db.execute(select(Recipe.name).where(Recipe.name.in_(names)))).scalars().all()
        if existing:
            print(f"ABORT: recipes with these names already exist: {list(existing)}")
            return 1

        existing_slots = (
            await db.execute(
                select(MealPlanSlot).where(
                    MealPlanSlot.date.between(START_DATE, date(2026, 5, 22)),
                    MealPlanSlot.meal_type == MEAL_TYPE,
                )
            )
        ).scalars().all()
        if existing_slots:
            print(f"ABORT: {len(existing_slots)} dinner slots already exist in 5/16-5/22.")
            return 1

    print("Generating nutrition estimates via Claude Haiku (parallel)...")
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    nutrition_values = await asyncio.gather(
        *(estimate_nutrition(client, r) for r in RECIPES)
    )
    for r, n in zip(RECIPES, nutrition_values):
        r["nutrition"] = n
        print(f"  {r['name'][:50]:<52} {n}")

    async with AsyncSessionLocal() as db:
        async with db.begin():
            for r in RECIPES:
                recipe = Recipe(
                    name=r["name"],
                    categories=r["categories"],
                    prep_time=r["prep_time"],
                    cook_time=r["cook_time"],
                    servings=r["servings"],
                    notes=PLAN_LABEL,
                    nutrition=r["nutrition"],
                    pregnancy_safe=True,
                    baby_friendly=True,
                    batch_cookable=r["batch_cookable"],
                    freezable=r["freezable"],
                )
                db.add(recipe)
                await db.flush()

                for i, step in enumerate(r["steps"], start=1):
                    db.add(RecipeStep(recipe_id=recipe.id, step_number=i, instruction=step))

                for display, qty, unit in r["ingredients"]:
                    db.add(RecipeIngredient(
                        recipe_id=recipe.id,
                        quantity=qty,
                        unit=unit,
                        display_text=display,
                    ))

                slot_date = date.fromordinal(START_DATE.toordinal() + r["day_offset"])
                db.add(MealPlanSlot(
                    date=slot_date,
                    meal_type=MEAL_TYPE,
                    recipe_id=recipe.id,
                    source=SLOT_SOURCE,
                    notes=PLAN_LABEL,
                ))
                print(f"  + {slot_date} {r['name']}")

    print("DB insert complete. Pushing produce to AnyList...")
    try:
        result = await push_ingredients(SHOPPING_LIST)
        print(f"AnyList result: added={result.get('added')} skipped={result.get('skipped')}")
    except Exception as e:
        print(f"AnyList push failed: {e}")
        print("DB seed already committed; add cucumber/carrots/parsley manually.")
        return 2

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
