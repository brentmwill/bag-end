import logging
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
EASTERN = ZoneInfo("America/New_York")

# (theme_id, display_label, sport, league, espn_team_id)
TRACKED_TEAMS = [
    ("phillies",   "Phillies",   "baseball",  "mlb",              "22"),
    ("eagles",     "Eagles",     "football",  "nfl",              "21"),
    ("sixers",     "Sixers",     "basketball", "nba",             "20"),
    ("flyers",     "Flyers",     "hockey",    "nhl",              "19"),
    ("packers",    "Packers",    "football",  "nfl",              "9"),
    ("stars",      "Stars",      "hockey",    "nhl",              "25"),
    ("ohio-state", "Ohio State", "football",  "college-football", "194"),
    ("penn-state", "Penn State", "football",  "college-football", "213"),
]


def _parse_game(event: dict, our_team_id: str) -> Optional[dict]:
    comp = (event.get("competitions") or [None])[0]
    if not comp:
        return None

    competitors = comp.get("competitors", [])
    us = next((c for c in competitors if c["team"]["id"] == our_team_id), None)
    them = next((c for c in competitors if c["team"]["id"] != our_team_id), None)
    if not us or not them:
        return None

    status = comp.get("status", {}).get("type", {})
    completed = status.get("completed", False)

    raw_date = event.get("date", "")
    try:
        dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        dt_eastern = dt_utc.astimezone(EASTERN)
    except Exception:
        dt_eastern = None

    result: dict[str, Any] = {
        "opponent": them["team"].get("abbreviation", ""),
        "opponent_name": them["team"].get("displayName", them["team"].get("abbreviation", "")),
        "home": us.get("homeAway") == "home",
        "completed": completed,
        "date": dt_eastern.date().isoformat() if dt_eastern else None,
        "time": dt_eastern.strftime("%-I:%M %p") if dt_eastern else None,
    }

    if completed:
        try:
            our_score = int(float(us.get("score", 0)))
            their_score = int(float(them.get("score", 0)))
            result["score"] = f"{our_score}-{their_score}"
            result["won"] = our_score > their_score
        except (ValueError, TypeError):
            pass

    return result


async def fetch_sports() -> list[dict[str, Any]]:
    results = []

    async with httpx.AsyncClient(timeout=10) as client:
        for theme_id, label, sport, league, team_id in TRACKED_TEAMS:
            try:
                url = f"{ESPN_BASE}/{sport}/{league}/teams/{team_id}/schedule"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                events = data.get("events", [])
                past: list[dict] = []
                upcoming: list[dict] = []

                for event in events:
                    comp = (event.get("competitions") or [None])[0]
                    if not comp:
                        continue
                    if comp.get("status", {}).get("type", {}).get("completed"):
                        past.append(event)
                    else:
                        upcoming.append(event)

                last_game = _parse_game(past[-1], team_id) if past else None
                next_game = _parse_game(upcoming[0], team_id) if upcoming else None

                results.append({
                    "id": theme_id,
                    "label": label,
                    "last_game": last_game,
                    "next_game": next_game,
                })
            except Exception:
                logger.exception("Failed to fetch sports data for %s", label)
                results.append({"id": theme_id, "label": label, "last_game": None, "next_game": None})

    return results
