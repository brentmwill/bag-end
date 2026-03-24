from typing import Any


async def fetch_tasks() -> list[dict[str, Any]]:
    # TODO: Implement using Trello REST API.
    # GET https://api.trello.com/1/boards/{board_id}/cards
    # Auth: settings.trello_api_key, settings.trello_token as query params
    # Filter to open cards only; return list with keys: id, name, due, labels, list_name
    return []


async def complete_task(card_id: str) -> bool:
    # TODO: Implement using Trello REST API.
    # PUT https://api.trello.com/1/cards/{card_id}?closed=true
    # Auth: settings.trello_api_key, settings.trello_token as query params
    return False
