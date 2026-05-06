#!/usr/bin/env python3
"""
One-off importer for Houston's Hawaiian Ribeye recipe.

Run on the server:
    cd /home/eluse/projects/bag-end/backend
    source .venv/bin/activate
    python scripts/import_houstons_ribeye.py
"""
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


RECIPE = {
    "name": "Houston's Hawaiian Ribeye",
    "categories": ["Dinner", "High Protein", "Grill"],
    "rating": 5,
    "prep_time": "30 mins",
    "cook_time": "15 mins",
    "servings": "2",
    "source_url": "https://www.food.com/recipe/houston-s-hawaiian-ribeye-507801",
    "source_author": "pickman",
    "notes": None,
    "nutrition": (
        "Per serving: 336 kcal, 0.2g fat, 0g sat fat, 0mg cholesterol, "
        "4269mg sodium, 77.5g carbs, 1.3g fiber, 64.3g sugar, 7.2g protein"
    ),
    "photo_path": "https://img.sndimg.com/food/image/upload/q_92,fl_progressive,w_1200,c_scale/v1/img/recipes/50/78/01/XiYlCJUQHqFUPaGfZs28_image.jpg",
    "pregnancy_safe": True,
    "baby_friendly": False,
    "batch_cookable": False,
    "freezable": False,
    "ingredients": [
        {"quantity": "2", "display_text": "2 thick cut rib eye steaks"},
        {"quantity": "1 cup", "display_text": "1 cup low sodium soy sauce (do NOT use regular! it will ruin your steak!)"},
        {"quantity": "2", "display_text": "2 garlic cloves, minced"},
        {"quantity": "1/2 cup", "display_text": "1/2 cup brown sugar"},
        {"quantity": "6 ounces", "display_text": "6 ounces pineapple juice"},
        {"quantity": "1/3 cup", "display_text": "1/3 cup apple cider vinegar"},
        {"quantity": "2 teaspoons", "display_text": "2 teaspoons fresh ginger, minced"},
    ],
    "directions": [
        "Add soy sauce, garlic, brown sugar, pineapple juice and apple cider vinegar to a small pot. Bring to a boil then simmer over low heat for 2 minutes. Remove from heat and pour the marinade into a large shallow dish (to marinate steaks later). Set aside until it's cooled, or to speed up the process, cover and place it in the fridge until it's cool.",
        "Add steak into the dish with marinade. Cover and place in fridge for 1 hour. Flip sides and cover for another 1 hour in the fridge. I prefer to marinate over night.",
        "20 minutes before starting the grill, take dish with steaks out (still covered) to cool to room temperature. Heat grill.",
        "Heat grill to high and grill steaks for 5 minutes. Flip and continue to grill for 4 minutes (for medium-rare to medium). Use an internal thermometer (135F for medium-rare and 140F for medium). Transfer steaks to a platter and tent with foil to let rest for 5 minutes. Grill some pineapple slices along with the steaks for garnish.",
    ],
}


def get_db_url() -> str:
    load_dotenv(Path(__file__).parent.parent / ".env")
    url = os.getenv("DATABASE_URL", "")
    if not url:
        sys.exit("DATABASE_URL not set in backend/.env")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def main():
    engine = create_engine(get_db_url())
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        existing = session.execute(
            text("SELECT id FROM recipes WHERE name = :name"),
            {"name": RECIPE["name"]},
        ).fetchone()
        if existing:
            print(f"Already exists: {RECIPE['name']} (id={existing[0]})")
            return

        recipe_id = uuid.uuid4()
        session.execute(
            text("""
                INSERT INTO recipes (
                    id, name, categories, rating, prep_time, cook_time, servings,
                    source_url, source_author, notes, nutrition, photo_path,
                    pregnancy_safe, baby_friendly, batch_cookable, freezable
                ) VALUES (
                    :id, :name, :categories, :rating, :prep_time, :cook_time, :servings,
                    :source_url, :source_author, :notes, :nutrition, :photo_path,
                    :pregnancy_safe, :baby_friendly, :batch_cookable, :freezable
                )
            """),
            {
                "id": recipe_id,
                "name": RECIPE["name"],
                "categories": RECIPE["categories"],
                "rating": RECIPE["rating"],
                "prep_time": RECIPE["prep_time"],
                "cook_time": RECIPE["cook_time"],
                "servings": RECIPE["servings"],
                "source_url": RECIPE["source_url"],
                "source_author": RECIPE["source_author"],
                "notes": RECIPE["notes"],
                "nutrition": RECIPE["nutrition"],
                "photo_path": RECIPE["photo_path"],
                "pregnancy_safe": RECIPE["pregnancy_safe"],
                "baby_friendly": RECIPE["baby_friendly"],
                "batch_cookable": RECIPE["batch_cookable"],
                "freezable": RECIPE["freezable"],
            },
        )

        for i, step in enumerate(RECIPE["directions"], start=1):
            session.execute(
                text("""
                    INSERT INTO recipe_steps (id, recipe_id, step_number, instruction)
                    VALUES (:id, :recipe_id, :step_number, :instruction)
                """),
                {"id": uuid.uuid4(), "recipe_id": recipe_id, "step_number": i, "instruction": step},
            )

        for ing in RECIPE["ingredients"]:
            session.execute(
                text("""
                    INSERT INTO recipe_ingredients (id, recipe_id, quantity, display_text)
                    VALUES (:id, :recipe_id, :quantity, :display_text)
                """),
                {
                    "id": uuid.uuid4(),
                    "recipe_id": recipe_id,
                    "quantity": ing["quantity"],
                    "display_text": ing["display_text"],
                },
            )

        session.commit()
        print(f"Imported: {RECIPE['name']} (id={recipe_id})")


if __name__ == "__main__":
    main()
