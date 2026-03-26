#!/usr/bin/env python3
"""
Import recipes from a Paprika HTML export directory into the bag-end database.

Usage:
    python scripts/import_paprika.py
    python scripts/import_paprika.py --dir "/path/to/recipes"
    python scripts/import_paprika.py --dir "/path/to/recipes" --db-url "postgresql://..."
"""
import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

DEFAULT_EXPORT_DIR = "C:/Users/eluse/OneDrive/Desktop/Export 2026-03-07 21.24.24/Recipes"


def parse_args():
    parser = argparse.ArgumentParser(description="Import Paprika HTML export into bag-end DB")
    parser.add_argument("--dir", default=DEFAULT_EXPORT_DIR, help="Path to Paprika recipe export directory")
    parser.add_argument("--db-url", default=None, help="PostgreSQL connection URL (defaults to DATABASE_URL in .env)")
    return parser.parse_args()


def get_db_url(override: Optional[str]) -> str:
    if override:
        return override
    load_dotenv(Path(__file__).parent.parent / ".env")
    url = os.getenv("DATABASE_URL", "")
    if not url:
        sys.exit("DATABASE_URL not set. Provide --db-url or set it in .env")
    # Convert asyncpg URL to sync psycopg2 URL for scripts
    return url.replace("postgresql+asyncpg://", "postgresql://")


def parse_rating(soup: BeautifulSoup) -> Optional[int]:
    tag = soup.find("p", itemprop="aggregateRating")
    if not tag:
        return None
    value = tag.get("value")
    if value and int(value) > 0:
        return int(value)
    return None


def parse_time_servings(soup: BeautifulSoup):
    prep_time = cook_time = servings = None
    for b in soup.find_all("b"):
        label = b.get_text(strip=True)
        span = b.find_next_sibling("span")
        if not span:
            continue
        value = span.get_text(strip=True)
        if "Prep Time" in label:
            prep_time = value
        elif "Cook Time" in label:
            cook_time = value
        elif "Servings" in label:
            servings = value
    return prep_time, cook_time, servings


def parse_ingredients(soup: BeautifulSoup) -> list[dict]:
    ingredients = []
    for p in soup.find_all("p", itemprop="recipeIngredient"):
        strong = p.find("strong")
        if strong:
            quantity = strong.get_text(strip=True)
            strong.extract()
            display = p.get_text(" ", strip=True)
            ingredients.append({"quantity": quantity, "display_text": f"{quantity} {display}".strip()})
        else:
            display = p.get_text(" ", strip=True)
            if display:
                ingredients.append({"quantity": None, "display_text": display})
    return ingredients


def parse_directions(soup: BeautifulSoup) -> list[str]:
    instructions_div = soup.find("div", itemprop="recipeInstructions")
    if not instructions_div:
        return []
    steps = []
    for p in instructions_div.find_all("p", class_="line"):
        text = p.get_text(strip=True)
        if text:
            steps.append(text)
    return steps


def parse_recipe(html_path: Path) -> dict:
    with open(html_path, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    name_tag = soup.find("h1", itemprop="name")
    name = name_tag.get_text(strip=True) if name_tag else html_path.stem

    categories_tag = soup.find("p", itemprop="recipeCategory")
    categories = []
    if categories_tag:
        raw = categories_tag.get_text(strip=True)
        categories = [c.strip() for c in raw.split(",") if c.strip()]

    rating = parse_rating(soup)
    prep_time, cook_time, servings = parse_time_servings(soup)

    url_tag = soup.find("a", itemprop="url")
    source_url = url_tag["href"] if url_tag and url_tag.get("href") else None

    author_tag = soup.find("span", itemprop="author")
    source_author = author_tag.get_text(strip=True) if author_tag else None

    notes_div = soup.find("div", class_="notes")
    notes = notes_div.get_text(strip=True) if notes_div else None

    nutrition_div = soup.find("div", class_="nutrition")
    nutrition = nutrition_div.get_text(strip=True) if nutrition_div else None

    photo_tag = soup.find("img", class_="photo")
    photo_url = None
    if photo_tag:
        parent_a = photo_tag.find_parent("a")
        if parent_a and parent_a.get("href"):
            photo_url = parent_a["href"]

    cat_set = {c.lower() for c in categories}
    freezable = "freezes well" in cat_set
    baby_friendly = "baby" in cat_set

    ingredients = parse_ingredients(soup)
    directions = parse_directions(soup)

    return {
        "name": name,
        "categories": categories,
        "rating": rating,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "servings": servings,
        "source_url": source_url,
        "source_author": source_author,
        "notes": notes,
        "nutrition": nutrition,
        "photo_path": photo_url,
        "freezable": freezable,
        "baby_friendly": baby_friendly,
        "ingredients": ingredients,
        "directions": directions,
    }


def insert_recipe(session: Session, data: dict) -> bool:
    existing = session.execute(
        text("SELECT id FROM recipes WHERE name = :name"), {"name": data["name"]}
    ).fetchone()
    if existing:
        return False

    recipe_id = uuid.uuid4()
    session.execute(
        text("""
            INSERT INTO recipes (
                id, name, categories, rating, prep_time, cook_time, servings,
                source_url, source_author, notes, nutrition, photo_path,
                freezable, baby_friendly
            ) VALUES (
                :id, :name, :categories, :rating, :prep_time, :cook_time, :servings,
                :source_url, :source_author, :notes, :nutrition, :photo_path,
                :freezable, :baby_friendly
            )
        """),
        {
            "id": recipe_id,
            "name": data["name"],
            "categories": data["categories"],
            "rating": data["rating"],
            "prep_time": data["prep_time"],
            "cook_time": data["cook_time"],
            "servings": data["servings"],
            "source_url": data["source_url"],
            "source_author": data["source_author"],
            "notes": data["notes"],
            "nutrition": data["nutrition"],
            "photo_path": data["photo_path"],
            "freezable": data["freezable"],
            "baby_friendly": data["baby_friendly"],
        },
    )

    for i, step in enumerate(data["directions"], start=1):
        session.execute(
            text("""
                INSERT INTO recipe_steps (id, recipe_id, step_number, instruction)
                VALUES (:id, :recipe_id, :step_number, :instruction)
            """),
            {"id": uuid.uuid4(), "recipe_id": recipe_id, "step_number": i, "instruction": step},
        )

    for ing in data["ingredients"]:
        session.execute(
            text("""
                INSERT INTO recipe_ingredients (id, recipe_id, quantity, display_text)
                VALUES (:id, :recipe_id, :quantity, :display_text)
            """),
            {
                "id": uuid.uuid4(),
                "recipe_id": recipe_id,
                "quantity": ing.get("quantity"),
                "display_text": ing["display_text"],
            },
        )

    return True


def main():
    args = parse_args()
    db_url = get_db_url(args.db_url)
    export_dir = Path(args.dir)

    if not export_dir.is_dir():
        sys.exit(f"Export directory not found: {export_dir}")

    html_files = list(export_dir.glob("*.html"))
    if not html_files:
        sys.exit(f"No .html files found in: {export_dir}")

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    total = len(html_files)
    imported = 0
    skipped = 0

    with SessionLocal() as session:
        for html_file in html_files:
            try:
                data = parse_recipe(html_file)
                inserted = insert_recipe(session, data)
                if inserted:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ERROR parsing {html_file.name}: {e}")
                skipped += 1
        session.commit()

    print(f"Imported {imported} / {total} recipes. Skipped {skipped} duplicates.")


if __name__ == "__main__":
    main()
