import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TRELLO_API = "https://api.trello.com/1"
DASHBOARD_LISTS = {"Recurring Daily Tasks", "Home Improvement", "Miscellaneous"}


def _auth() -> dict:
    return {"key": settings.trello_api_key, "token": settings.trello_token}


async def fetch_tasks() -> list[dict[str, Any]]:
    if not settings.trello_api_key or not settings.trello_token or not settings.trello_board_id:
        return []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Fetch lists so we can include list name on each card
            lists_resp = await client.get(
                f"{TRELLO_API}/boards/{settings.trello_board_id}/lists",
                params={**_auth(), "filter": "all"},
            )
            lists_resp.raise_for_status()
            list_map = {lst["id"]: lst["name"] for lst in lists_resp.json()}

            cards_resp = await client.get(
                f"{TRELLO_API}/boards/{settings.trello_board_id}/cards",
                params={**_auth(), "filter": "open", "fields": "id,name,due,labels,idList"},
            )
            cards_resp.raise_for_status()

        return [
            {
                "id": c["id"],
                "name": c["name"],
                "due": c.get("due"),
                "labels": [lb["name"] for lb in c.get("labels", [])],
                "list_name": list_map.get(c["idList"], ""),
            }
            for c in cards_resp.json()
            if list_map.get(c["idList"]) in DASHBOARD_LISTS
        ]
    except Exception:
        logger.exception("Failed to fetch Trello tasks")
        return []


async def complete_task(card_id: str) -> bool:
    if not settings.trello_api_key or not settings.trello_token:
        return False

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.put(
                f"{TRELLO_API}/cards/{card_id}",
                params={**_auth(), "closed": "true"},
            )
            resp.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to complete Trello card %s", card_id)
        return False
