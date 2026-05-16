# Personas

Each specialist persona lives in its own directory under this package. New personas
are created by making the directory and dropping in whatever files they need —
nothing is required, but the conventions below let the loader help you out.

## Layout

```
backend/app/personas/<name>/
  context.md      hand-curated baseline: voice, principles, stable preferences
  notes.md        persona auto-appends observations over time (gitignored)
  prompt.py       system-prompt assembly; calls assemble_system_prompt()
  handler.py      Telegram chat handler (optional)
  contributor.py  morning_contribution() for the digest (optional)
  tools.py        scoped DB queries / external API calls (optional)
```

Only the files a persona actually uses need to exist. A pure cron-contributor
persona may have just `context.md` + `contributor.py`.

## Storage choices

| File | Where | Why |
|---|---|---|
| `context.md` | Source-controlled | Authored intentionally; should ship with deploys; reviewable. |
| `notes.md` | Server-local, gitignored | Append-heavy and runtime-generated; not worth a git commit per observation. Migrate to a `persona_notes` table if durability becomes important. |
| Structured memory | Shared DB tables | `conversation_log`, `food_log`, etc. Use these for anything queryable across personas. |

## Helpers

```python
from app.personas import (
    read_context,           # str | None — content of <persona>/context.md
    append_note,            # (persona, note) — timestamped append to notes.md
    read_notes,             # (persona, max_lines=50) — tail of notes.md
    assemble_system_prompt, # (persona, base_prompt, ...) — base + context + notes
)
```

`append_note` raises `FileNotFoundError` if the persona dir doesn't exist —
config errors should be loud, not silently papered over.

## Note format

`append_note` writes one line per observation, prefixed with an ISO UTC timestamp:

```
[2026-05-15T03:29:25+00:00] Brent rated the white-bean soup 4; flagged "too much lemon"
```

Personas are free to embed structure inside the note text (tags, JSON, whatever),
but the timestamp prefix is always present.
