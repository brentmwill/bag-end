#!/usr/bin/env python3
"""
One-off importer for Valerie's Kitchen Homemade Salisbury Steak.

Run on the server:
    cd /home/eluse/projects/bag-end/backend
    source .venv/bin/activate
    python scripts/import_salisbury_steak.py
"""
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


RECIPE = {
    "name": "Homemade Salisbury Steak",
    "categories": ["Dinner", "Skillet", "Beef"],
    "rating": None,
    "prep_time": "15 mins",
    "cook_time": "15 mins",
    "servings": "4",
    "source_url": "https://www.fromvalerieskitchen.com/salisbury-steak-recipe/",
    "source_author": "Valerie Brunmeier / Valerie's Kitchen",
    "notes": (
        "Variations: replace up to half the beef with ground pork or turkey; "
        "omit onions from the gravy for finicky eaters; add heavy cream or "
        "half-and-half to the gravy for richness; garnish with parsley or thyme. "
        "Freezer: freeze uncooked patties on parchment for 2 hours, then bag; "
        "store gravy separately. Good for 2-3 months. Thaw overnight before cooking."
    ),
    "nutrition": (
        "Per serving: 486 kcal, 26g fat (8g sat, 2g poly, 13g mono, 1g trans), "
        "152mg cholesterol, 986mg sodium, 1202mg potassium, 20g carbs, 2g fiber, "
        "5g sugar, 42g protein, 134IU vit A, 3mg vit C, 80mg calcium, 5mg iron"
    ),
    "photo_path": None,
    "pregnancy_safe": True,
    "baby_friendly": True,
    "batch_cookable": False,
    "freezable": True,
    "ingredients": [
        # Patties
        {"quantity": "1", "display_text": "1 egg"},
        {"quantity": "1/2 cup", "display_text": "1/2 cup Italian seasoned Panko breadcrumbs"},
        {"quantity": "1 tablespoon", "display_text": "1 tablespoon ketchup or tomato paste"},
        {"quantity": "2 teaspoons", "display_text": "2 teaspoons Dijon mustard"},
        {"quantity": "2 teaspoons", "display_text": "2 teaspoons Worcestershire sauce"},
        {"quantity": "1/4 teaspoon", "display_text": "1/4 teaspoon salt"},
        {"quantity": None, "display_text": "Freshly ground black pepper, to taste"},
        {"quantity": "1 1/2 pounds", "display_text": "1 1/2 pounds 85% to 90% lean ground beef"},
        {"quantity": "2 tablespoons", "display_text": "2 tablespoons olive oil, or as needed, divided"},
        # Mushroom onion gravy
        {"quantity": "1 small", "display_text": "1 small sweet yellow onion, halved and thinly sliced"},
        {"quantity": "8 ounces", "display_text": "8 ounces cremini mushrooms, sliced"},
        {"quantity": "2 cups", "display_text": "2 cups low sodium beef broth"},
        {"quantity": "1 tablespoon", "display_text": "1 tablespoon ketchup or tomato paste"},
        {"quantity": "1 tablespoon", "display_text": "1 tablespoon low sodium soy sauce"},
        {"quantity": "1 teaspoon", "display_text": "1 teaspoon Worcestershire sauce"},
        {"quantity": "1 teaspoon", "display_text": "1 teaspoon Dijon mustard"},
        {"quantity": "2 teaspoons", "display_text": "2 teaspoons cornstarch"},
        {"quantity": "2 teaspoons", "display_text": "2 teaspoons water"},
        {"quantity": None, "display_text": "Browning sauce like Kitchen Bouquet, a few drops for color (optional)"},
        {"quantity": None, "display_text": "Salt and freshly ground black pepper, to taste"},
        {"quantity": None, "display_text": "Fresh Italian parsley, or other fresh herbs (optional garnish)"},
    ],
    "directions": [
        "In a large bowl, whisk the egg with a fork. Stir in the bread crumbs, ketchup (or tomato paste), Dijon, Worcestershire sauce, salt and pepper. Add the ground beef and mix well. Form into 4 to 6 oval patties no more than 1/2-inch thick.",
        "Add 1 tablespoon oil to a large, deep nonstick skillet or sauté pan and place it over medium-high heat. Add the patties and cook until browned on both sides and cooked through with an internal temperature of 150 to 155°F. Transfer the patties to a plate and set aside.",
        "Pour off any grease from the skillet and place it over medium heat (wipe out any big burned bits with a paper towel). Add the sliced onions and cook until softened and just beginning to get brown around the edges, about 3 to 4 minutes. Add the mushrooms and cook for a few more minutes until softened. Season with a pinch of black pepper.",
        "Add the beef broth, ketchup (or tomato paste), soy sauce, Worcestershire sauce, and mustard and stir to combine. In a small bowl whisk the cornstarch with water and add the slurry to the skillet. Stir for a minute or two until the sauce thickens. For richer color and deeper flavor, add a few drops of browning sauce. Taste and season with additional salt and pepper, only if needed.",
        "Add the beef patties back to the skillet and spoon the mushroom and onion gravy over the top. Garnish with parsley and serve over mashed potatoes.",
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
