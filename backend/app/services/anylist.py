from typing import Any


async def fetch_grocery_list() -> list[dict[str, Any]]:
    # TODO: Implement via AnyList MCP server at C:\Users\eluse\Projects\anylist-mcp
    # Note: the anylist-mcp server requires a protobuf patch to run correctly.
    # Use the MCP client interface to call mcp__anylist__get_list_items.
    # Return list of dicts with keys: id, name, checked, category, notes
    return []


async def add_item(name: str, notes: str = "") -> bool:
    # TODO: Implement via AnyList MCP server.
    # Call mcp__anylist__add_item_to_list with list_id and item name/notes.
    return False


async def check_item(item_id: str) -> bool:
    # TODO: Implement via AnyList MCP server.
    # Call the appropriate MCP tool to mark item as checked.
    return False
