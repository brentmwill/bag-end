from typing import Any


async def fetch_commute_tiles() -> list[dict[str, Any]]:
    # TODO: Implement using Google Maps Distance Matrix API with settings.google_maps_api_key.
    # 4 tiles to compute:
    #   1. Brent: home -> work
    #   2. Brent: work -> home
    #   3. Danielle: home -> work
    #   4. Danielle: work -> home
    # Origins and destinations should be configured as env vars (add to config.py when ready).
    # Return a list of dicts with keys: label, origin, destination, duration_text, traffic_text
    return []
