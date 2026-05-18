"""One-off smoke test for the Gmail IMAP fetch helper.

Run from the project root with the backend's venv activated:
    cd backend && python ../scripts/smoke_gmail.py

Prints the latest 5 inbox messages (subject, sender, snippet). Confirms that
GMAIL_EMAIL + GMAIL_APP_PASSWORD are wired correctly. Delete this script
once the Inbox persona is in regular use.
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from project root or backend dir.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.gmail import fetch_recent_messages  # noqa: E402


async def main() -> None:
    since = datetime.now(timezone.utc) - timedelta(days=2)
    msgs = await fetch_recent_messages(since=since, max_messages=5)
    print(f"Fetched {len(msgs)} messages since {since.isoformat()}\n")
    for m in msgs:
        print(f"[{m['internal_date'].astimezone().isoformat(timespec='minutes')}]")
        print(f"  From:    {m['sender']}")
        print(f"  Subject: {m['subject']}")
        print(f"  Snippet: {m['snippet'][:200]}")
        print(f"  Flags:   {m['flags']}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
