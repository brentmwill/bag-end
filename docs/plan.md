# Bag End — Implementation Plan

> Reconstructed 2026-04-29 from `CLAUDE.md` and working repo. Restructured 2026-05-14
> around the persona/router architecture (see "Architecture" below). Living document —
> update as work lands.

## North star

A web-based household command center for Brent, Danielle, and the baby. Displayed on a
32" portrait monitor (Raspberry Pi kiosk) in the kitchen, also accessible as a PWA via
Tailscale. Four rotating display views plus an interact mode for active use.

A growing set of specialist personas (Chef Sue, Majordomo, Health, Finance, Inbox,
Chores) talks to the household via Telegram and contributes to the kitchen dashboard.

## Architecture

### Three layers

| Layer | What | How it changes over time |
|---|---|---|
| **Display** | Kitchen PWA, 4-view rotation, glance cache | Mostly built. Persona-agnostic dumb renderers. |
| **Persona / chat** | Telegram routing + specialists + shared logs | **New work.** Built incrementally per persona. |
| **Contributors** | Cron jobs that emit signals (digest pieces, glance refresh, WOTD) | Mostly built. Refactor so each persona owns one. |

The dashboard doesn't need to know personas exist. Some contributors (WOTD, calendar
notifier) don't need a chat persona behind them — not everything needs to be a persona.

### Routing pattern

Implements Anthropic's "Routing" pattern (Building Effective Agents, Dec 2024).

- Inbound Telegram DM → **slash command** (explicit) **OR** **Haiku classifier** (freeform) → specialist Sonnet call
- Slash commands first (`/chef`, `/finance`, `/health`, `/inbox`, `/chores`, `/note`); classifier added later
- **Stickiness window** (~10 min): follow-up DM routes to same persona without re-classifying
- Each specialist call loads: persona system prompt + `context.md` + relevant slice of `notes.md` + last N rows of `conversation_log` + scoped DB query results
- Specialists can hand off explicitly when a question is out of scope

### Persona structure

```
backend/app/personas/<name>/
  context.md          ← hand-curated baseline (voice, principles, stable prefs)
  notes.md            ← persona auto-appends observations over time
  prompt.py           ← system prompt assembly
  handler.py          ← chat handler (optional)
  contributor.py      ← morning_contribution() (optional)
  tools.py            ← scoped DB queries / external API calls
```

### Shared infrastructure

- **`conversation_log`** — every inbound + outbound DM, with `persona`, `user_id`, timestamps. Cross-persona state.
- **`food_log`** — meal intake. Chef Sue writes, Health reads.
- **`backlog_items`** — friction capture. Schema-enforced; written via Haiku normalizer.
- **`persona_session`** — in-memory routing state (last persona per user, stickiness expiry).
- **User-scoped data partitioning** — DB helpers that auto-scope by `requesting_user_id` so Health data can't leak across users even if the classifier mis-routes.

## Stack

- **Backend:** Python FastAPI (separate port from `ai-tutoring-system`)
- **Frontend:** React PWA (Vite), portrait-optimized
- **DB:** PostgreSQL
- **LLM:** Claude only (`claude-sonnet-4-6` specialist, `claude-haiku-4-5` router/normalizer)
- **Scheduler:** APScheduler (in-process, AsyncIO)
- **Server:** Ubuntu home server, Tailscale-only, served via FastAPI static mount

## Four display views

1. **Home** — Weather, tonight's meal, calendar events, 4 commute tiles, digest snippet
2. **Planning** — Week meal plan (left) + Google Calendar (right)
3. **Household** — Trello tasks, baby meal slots, freezer inventory
4. **Ambient** — Google Photos fullscreen, Word of the Day

## API aggregation layer

- `GET /api/glance` — full payload for all four display views, server-cached
- `GET /api/interact` — full data for interact mode (recipes, meal plan, tasks, grocery, freezer)
- `POST /api/digest/regenerate`, `POST /api/digest/send` — Majordomo composer test endpoints

## External integrations

| Integration | Mode | Owning persona | Notes |
|---|---|---|---|
| Google Calendar | read-only | Majordomo | OAuth token helper `fb55512` |
| Google Maps | read-only | (display) | commute estimates, 4 tiles |
| Google Photos | read-only | (display) | slideshow (Phase 3) |
| Gmail | read-only | Inbox | OAuth, Brent-only — **new, Phase 2.1**. Danielle's inbox deferred indefinitely. |
| Trello | read + mark complete | Chores (transitional) | filtered to dashboard lists; deprecation arc, see Chores |
| AnyList | read + write | Chef Sue | via `backend/tools/anylist/push.js`; protobuf patch required |
| Telegram Bot | read + write | (all personas) | shared bot, multi-voice |
| ESPN | read-only | (display) | sports widget, 8 teams |
| FitBit | read-only | Health (Brent-only) | OAuth, Brent-scoped — **new, Phase 2.4** |
| Monarch | read-only | Finance | API is notoriously thin — **new, Phase 2.5** |

## Phase 1 — MVP (closed 2026-05-01)

- [x] Dashboard shell + 4-view rotation
- [x] Google Calendar integration (incl. full-screen daily/weekly/monthly modes)
- [x] Google Maps commute tiles
- [x] Trello integration (interactive, list-filtered)
- [x] Native recipe DB + Paprika import + editing + category flags
- [x] Meal planner (drag-drop week schedule, filters, AnyList push, recipe generator)
- [x] AnyList integration (push, category inference + backfill, multi-recipe attribution, quantity)
- [x] Baby meal slots (Finger Food filter)
- [x] Telegram bot skeleton + onboarding + post-dinner DM rating flow
- [x] Sports widget (ESPN, 8 teams)
- [x] Theme picker (team / auto)
- [x] PWA served from FastAPI static mount
- [x] Freezer log (CRUD router + `FreezerItem` model)
- [x] Cooking mode (recipe detail modal + "Cook this now" trigger)
- [x] APScheduler — all 7 jobs scheduled; `generate_digest` shipped 2026-05-07 as monolith (refactor pending)

## Phase 1.5 — Foundation (architecture transition)

The persona/router architecture requires this scaffolding before persona MVPs land.
Build in this order; each subsequent step builds on the previous.

1. **`backlog_items` table + normalizer** — schema (`area`, `severity`, `description`, `repro_or_context`, `proposed_fix`, `created_by_persona`, `created_at`) + Haiku reshaping function. Capture architecture decisions and future friction from here forward.
2. **Persona scaffolding convention** — `backend/app/personas/<name>/` layout, system-prompt loader, context-file injection helper, `notes.md` append helper.
3. **`conversation_log` table** — every inbound + outbound DM logged with `persona`, `user_id`, timestamps. Required for stickiness and cross-persona context.
4. **`food_log` table** — schema (`user_id`, `eaten_at`, `recipe_id`, `freeform_description`, `grams`, `est_calories`, `est_macros`). Chef Sue writes; Health reads.
5. **User-scoped data partitioning** — DB query helpers that require `requesting_user_id`. Pulled forward from Phase 3 "private preference profiles."
6. **Routing layer (slash commands first)** — slash command parser routes `/chef`, `/finance`, etc. directly to specialists; freeform messages fall back to old single-bot handler until classifier lands.

Foundation can land before any Phase 2 persona ships. Once it's in place, personas are
incremental.

## Phase 2 — Persona MVPs

Priority order chosen to extract patterns from a clean greenfield persona (Inbox)
before retrofitting the heaviest existing code (Chef Sue), then standing up the
coordinator (Majordomo) once there are multiple voices to coordinate.

### 2.1 — Inbox persona (greenfield, first extraction)

- **Scope:** Gmail triage; extract action items from school, doctor, daycare, billing emails. **Brent's inbox only** — Danielle's inbox is deferred indefinitely, not on the near-term roadmap.
- **Voice:** terse, headline-style — "Daycare wants signup by Friday"
- **First 30-day actions:**
  - `morning_contribution()` — surface up to 2 high-priority items in the morning digest
  - `/inbox` chat — "what needs my attention?" pulls latest action items
  - Mark as handled via reply
- **Surfaces:** digest contributor + chat
- **Dependencies:** Phase 1.5 foundation; Gmail OAuth (mirrors Calendar setup); persona scaffolding
- **Status:** greenfield

### 2.2 — Chef Sue persona (retrofit)

- **Scope:** recipes, meal plan, freezer, AnyList push/read, post-dinner ratings, food intake logging, emergency dinner suggestions, grocery inference
- **Voice:** warm + practical kitchen register
- **First 30-day actions:**
  - `morning_contribution()` — tonight's meal + prep heads-up ("brine's been in since last night")
  - `/chef` chat — grocery add via DM, freezer query, "I ate X" food log, dinner suggestions
  - Fix dinner rating trigger (currently fires at 19:00 clock; should fire post-meal-log)
  - Emergency dinner button (Phase 2 #3 in old plan) — `/chef emergency` returns 3 picks from freezer/pantry
  - Grocery inference (Phase 2 #4 in old plan) — scan recipes/freezer/pantry, suggest adds
  - Post-cooking capture (Phase 2 #6 in old plan) — `/chef cooked X` writes notes
- **Surfaces:** digest + chat + display (cooking mode)
- **Dependencies:** Phase 1.5 foundation; `food_log`; refactor existing dinner-rating job onto post-meal-log trigger
- **Status:** significant existing code (rating flow, meal plan, AnyList, freezer) — retrofit into persona shape concurrent with the digest-composer rebuild in 2.3

### 2.3 — Majordomo persona (router + composer)

- **Scope:** intent classification, digest composition, calendar change notifications, cross-persona handoff
- **Voice:** plain, coordinator, no personality of its own
- **First 30-day actions:**
  - Haiku classifier for freeform DMs (slash commands already work from Phase 1.5)
  - Compose morning digest from persona `morning_contribution` rows (refactor current monolithic digest)
  - Calendar change notifier — DM on add/cancel/edit to shared Google Calendar
  - Explicit override flow ("no, that was a finance question")
- **Surfaces:** routing layer + digest composer + targeted DMs
- **Dependencies:** Phase 1.5 foundation; at least one other persona shipping a `morning_contribution()` (Inbox or Chef Sue)
- **Status:** routing infra is Phase 1.5; composer + classifier are 2.3

### 2.4 — Health persona (Brent-only)

- **Scope:** FitBit data (steps, sleep, weight), `food_log` reads, calorie/exercise pattern tracking, encouragement
- **Voice:** encouraging, terse, never advisory beyond "you said you wanted X, you're at Y"
- **Privacy:** **Brent-only** — every query scoped at the DB layer to Brent's `user_id`. Classifier mis-route must not leak.
- **First 30-day actions:**
  - `morning_contribution()` — "down 0.4 lb week-over-week; on track" (Brent's digest only)
  - Evening cron — nudge on missed-activity patterns or calorie overage streaks
  - `/health` chat — "how am I doing this week?"
- **Surfaces:** digest + chat, **Brent only**
- **Dependencies:** Phase 1.5 (user-scoped partitioning especially); FitBit OAuth; `food_log`
- **Status:** greenfield; gated on user-scoped data partitioning

### 2.5 — Finance persona

- **Scope:** Monarch reads, category classification fixes, weekly/monthly spending insights
- **Voice:** matter-of-fact, comparative ("up $50 from last month")
- **First 30-day actions:**
  - Weekly digest line — "eating-at-work up $50 vs last week, mostly Cava"
  - `/finance` chat — "this week's spending"; category-fix flow ("that wasn't groceries, it was a gift")
- **Surfaces:** digest + chat
- **Dependencies:** Phase 1.5 foundation; Monarch API integration
- **Status:** greenfield; Monarch's API is thin — expect API issues to drive scope

### 2.6 — Chores persona

- **Scope:** recurring chore tracking, seasonal reminders (AC filter, lawn fertilizer, gutters, registration renewals)
- **Voice:** practical, scheduled
- **First 30-day actions:**
  - `morning_contribution()` on relevant days — "AC filter due this weekend"
  - `/chores` chat — "what's on my list this week", mark done
  - Recurrence engine (every N days / monthly / annually / seasonal)
- **Surfaces:** digest + chat + display (eventually replaces Trello on Household view)
- **Trello deprecation arc:** stay on Trello while Chores is greenfield → migrate active items once Chores reaches parity → deprecate Trello integration. Don't rush; Trello works today.
- **Dependencies:** Phase 1.5 foundation
- **Status:** greenfield

## Phase 3 — Extension / scale

Items currently outside MVP scope; revisit after Phase 2 personas stabilize.

- **Multi-user privacy expansion** — if Danielle wants her own private data (Health, Finance), extend the user-scoping layer to support per-user partitions for additional personas
- **Baby persona** — allergens, vaccines, foods introduced, milestones; overlaps Chef Sue (baby meal slots are already Chef Sue's)
- **Google Photos slideshow** — Ambient view
- **Receipt parsing** — pantry ingestion side (cleanup job already exists)
- **Voice surface** — beyond Telegram, if it matters

## Cron contributors (non-persona)

These don't need a chat persona, just an emitter:

- `refresh_commute` (5m) ✓
- `refresh_glance` (5m) ✓
- `midnight_reset` ✓
- `receipt_expiry_cleanup` ✓
- `generate_wotd` (5:30am ET) ✓
- `generate_digest` — needs composer refactor in Phase 2.3
- `weekly_summary` — stub; revisit during Phase 2.3 (likely becomes Majordomo's job)

## Meal planning defaults

- Pregnancy-safe (expires 2026-10-15 — stored as configurable date, drops automatically)
- Baby finger-food friendly
- Batch / slow-cooker friendly
- Freezable

## AnyList notes convention

All items pushed to AnyList carry recipe source in the notes field:

- Multi-recipe: `"White Bean Soup; Carrot Soup"`
- Manual add: `"added without notes by user"`

## Hard constraints

- **Anthropic only.** No OpenAI, no other providers.
- Tailscale-only. No public internet exposure.
- Read-only for Google Calendar (do not write).
- Do not auto-double grocery quantities (was a one-time session decision).
- Don't mix venv or port with `ai-tutoring-system`.
- AnyList Node helper: protobuf patch (`item.js` `quantity` → `deprecatedQuantity`) must be reapplied after every `npm install`.
- **Health data is Brent-only** at the DB layer until explicitly expanded in Phase 3.

## Tooling backlog

- **Allow domain-scoped WebFetch for sub-agents.** Sub-agents can't prompt for permission, so research agents currently can't pull from `anthropic.com`, `raw.githubusercontent.com`, etc. Add narrow allow rules to `~/.claude/settings.json` (`WebFetch(domain:anthropic.com)`, `WebFetch(domain:github.com)`, `WebFetch(domain:raw.githubusercontent.com)`). Workaround in place: anthropic-cookbook cloned to `C:\Users\eluse\Projects\_reference\anthropic-cookbook` for local reads.

## Open questions / decisions

- Where the kiosk Pi pulls from and how it auto-updates — not yet automated
- When freeform Haiku classifier ships vs. staying on slash commands forever — defer until slash commands feel insufficient in practice
- Whether `persona_session` stickiness should be in-memory (simpler, lost on restart) or DB-backed (durable) — start in-memory; promote if it becomes annoying
