from datetime import datetime
from pathlib import Path

PREFS_DIR = Path(__file__).parent.parent.parent / "data" / "preferences"


def append_preference(telegram_user_id: int, note: str) -> None:
    PREFS_DIR.mkdir(parents=True, exist_ok=True)
    path = PREFS_DIR / f"{telegram_user_id}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"- {timestamp}: {note}\n")


def read_preferences(telegram_user_id: int) -> str:
    path = PREFS_DIR / f"{telegram_user_id}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
