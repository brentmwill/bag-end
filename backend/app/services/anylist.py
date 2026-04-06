import asyncio
import json
import os
from pathlib import Path
from typing import Any

from app.config import settings

PUSH_SCRIPT = Path(__file__).parent.parent.parent / "tools" / "anylist" / "push.js"


async def push_ingredients(ingredients: list[dict[str, str]], list_name: str = "My Grocery List") -> dict[str, Any]:
    """
    Push a list of ingredients to AnyList via the Node.js helper script.

    Each ingredient dict: {"name": "1 lb ground beef", "notes": "Baked Meatballs"}
    Returns: {"added": [...], "skipped": [...], "unchecked": [...]}

    Requires Node.js on the server and tools/anylist deps installed.
    ANYLIST_EMAIL and ANYLIST_PASSWORD must be in the environment.
    """
    payload = json.dumps({"ingredients": ingredients, "list_name": list_name})

    env = os.environ.copy()
    env["ANYLIST_EMAIL"] = settings.anylist_email
    env["ANYLIST_PASSWORD"] = settings.anylist_password
    proc = await asyncio.create_subprocess_exec(
        "/usr/bin/node", str(PUSH_SCRIPT),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout, stderr = await proc.communicate(input=payload.encode())

    if proc.returncode != 0:
        raise RuntimeError(f"AnyList push failed: {stderr.decode().strip()}")

    return json.loads(stdout.decode().strip())


async def fetch_grocery_list() -> list[dict[str, Any]]:
    # TODO: implement via anylist push.js — call get_lists + get_list_items
    return []


async def add_item(name: str, notes: str = "") -> bool:
    result = await push_ingredients([{"name": name, "notes": notes}])
    return len(result.get("added", [])) > 0


async def check_item(item_id: str) -> bool:
    # TODO: implement via anylist-mcp or a separate Node helper
    return False
