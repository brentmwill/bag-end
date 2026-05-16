"""Persona scaffolding helpers.

Each persona lives in `backend/app/personas/<name>/`:

    context.md      — hand-curated voice / principles / stable prefs (committed)
    notes.md        — persona auto-appends observations (gitignored, server-local)
    prompt.py       — system prompt assembly (calls assemble_system_prompt)
    handler.py      — optional Telegram chat handler
    contributor.py  — optional morning_contribution()
    tools.py        — optional scoped DB queries / external API calls

The loader treats context.md and notes.md as files because they're hand-edited or
freely append-only. Personas that want structured memory should use shared DB
tables (conversation_log, food_log, etc.) instead.
"""
from datetime import datetime, timezone
from pathlib import Path

_PERSONAS_DIR = Path(__file__).resolve().parent


def _persona_dir(persona: str) -> Path:
    return _PERSONAS_DIR / persona


def read_context(persona: str) -> str | None:
    """Return the persona's context.md content, or None if missing."""
    path = _persona_dir(persona) / "context.md"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def append_note(persona: str, note: str) -> None:
    """Append a timestamped observation to the persona's notes.md.

    Persona dir must already exist; missing dir signals a config error rather
    than a runtime issue worth silently fixing.
    """
    pdir = _persona_dir(persona)
    if not pdir.is_dir():
        raise FileNotFoundError(f"persona dir not found: {pdir}")
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{ts}] {note.strip()}\n"
    with (pdir / "notes.md").open("a", encoding="utf-8") as f:
        f.write(line)


def read_notes(persona: str, max_lines: int = 50) -> list[str]:
    """Return the last `max_lines` lines from the persona's notes.md.

    Empty list if no notes exist. Lines retain their trailing newline stripped.
    """
    path = _persona_dir(persona) / "notes.md"
    if not path.exists():
        return []
    lines = [ln.rstrip("\n") for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return lines[-max_lines:]


def assemble_system_prompt(
    persona: str,
    base_prompt: str,
    *,
    include_context: bool = True,
    notes_lines: int = 50,
) -> str:
    """Glue a persona's base prompt together with its context.md and recent notes.

    Sections are joined with blank lines and labeled headings so the model can tell
    them apart. Missing context or empty notes are silently omitted.
    """
    parts: list[str] = [base_prompt.strip()]

    if include_context:
        ctx = read_context(persona)
        if ctx:
            parts.append(f"## Persona context\n\n{ctx}")

    notes = read_notes(persona, max_lines=notes_lines)
    if notes:
        joined = "\n".join(notes)
        parts.append(f"## Recent observations\n\n{joined}")

    return "\n\n".join(parts)
