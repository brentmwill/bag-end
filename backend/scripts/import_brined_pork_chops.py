#!/usr/bin/env python3
"""
One-off importer for Molly Baz's Pan-Roasted Brined Pork Chops (Bon Appetit).

Run on the server:
    cd /home/eluse/projects/bag-end/backend
    source .venv/bin/activate
    python scripts/import_brined_pork_chops.py
"""
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


RECIPE = {
    "name": "Pan-Roasted Brined Pork Chops",
    "categories": ["Dinner", "High Protein", "Skillet"],
    "rating": None,
    "prep_time": "10 mins (+ 8-12 hr brine)",
    "cook_time": "30 mins",
    "servings": "2",
    "source_url": "https://youtu.be/hM_BYbi3vPI",
    "source_author": "Molly Baz / Bon Appetit",
    "notes": None,
    "nutrition": (
        "Per serving: 660 kcal, 43g fat, 17g sat fat, 145mg cholesterol, "
        "5870mg sodium, 42g carbs, 1g fiber, 36g sugar, 31g protein"
    ),
    "photo_path": None,
    "pregnancy_safe": True,
    "baby_friendly": False,
    "batch_cookable": False,
    "freezable": False,
    "ingredients": [
        {"quantity": "1/2 cup", "display_text": "1/2 cup kosher salt"},
        {"quantity": "1/2 cup", "display_text": "1/2 cup sugar"},
        {"quantity": "1 teaspoon", "display_text": "1 teaspoon juniper berries"},
        {"quantity": "1/2 teaspoon", "display_text": "1/2 teaspoon whole black peppercorns"},
        {"quantity": "1 head", "display_text": "1 head of garlic, halved crosswise, plus 2 unpeeled cloves for basting"},
        {"quantity": "2 sprigs", "display_text": "2 large sprigs thyme"},
        {"quantity": "1", "display_text": "1 2\" thick bone-in pork chop (2 ribs; about 1 1/4 lb.)"},
        {"quantity": "2 tablespoons", "display_text": "2 tablespoons grapeseed or vegetable oil"},
        {"quantity": "3 tablespoons", "display_text": "3 tablespoons unsalted butter"},
        {"quantity": None, "display_text": "Flaky or coarse sea salt"},
    ],
    "directions": [
        "Bring 2 cups water to a boil in a medium saucepan. Add kosher salt, sugar, juniper berries, peppercorns, halved head of garlic, and 1 thyme sprig; stir to dissolve salt and sugar. Transfer to a medium bowl and add 5 cups ice cubes. Stir until brine is cool. Add pork chop; cover and chill for at least 8 and up to 12 hours.",
        "Preheat oven to 450°. Set a wire rack inside a rimmed baking sheet. Remove chop from brine; pat dry. Heat oil over medium-high heat in a large cast-iron or other oven-proof skillet. Cook chop until beginning to brown, 3-4 minutes. Turn and cook until second side is beginning to brown, about 2 minutes. Keep turning chop every 2 minutes until both sides are deep golden brown, 10-12 minutes total.",
        "Transfer skillet to oven and roast chop, turning every 2 minutes to prevent it from browning too quickly, until an instant-read thermometer inserted horizontally into center of meat registers 135°, about 14 minutes. (Chop will continue to cook during basting and resting.)",
        "Carefully drain fat from skillet and place over medium heat. Add butter, 2 unpeeled garlic cloves, and remaining thyme sprig; cook until butter is foamy. Carefully tip skillet and, using a large spoon, baste chop repeatedly with butter until butter is brown and smells nutty, 2-3 minutes.",
        "Transfer pork chop to prepared rack and let rest, turning often to ensure juices are evenly distributed, for 15 minutes. Cut pork from bones, slice, and sprinkle with sea salt.",
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
