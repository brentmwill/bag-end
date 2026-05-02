# Bag End — Implementation Plan

> Reconstructed 2026-04-29 from `CLAUDE.md` and the working repo after the original
> `~/.claude/plans/bag-end-plan.md` was lost. Living document — update as work lands.

## North star

A web-based household command center for Brent, Danielle, and the baby. Displayed on a
32" portrait monitor (Raspberry Pi kiosk) in the kitchen, also accessible as a PWA via
Tailscale. Four rotating display views plus an interact mode for active use.

## Stack

- **Backend:** Python FastAPI (separate port from `ai-tutoring-system`)
- **Frontend:** React PWA (Vite), portrait-optimized
- **DB:** PostgreSQL
- **LLM:** Claude only (`claude-sonnet-4-6` + `claude-haiku-4-5`)
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

## External integrations

| Integration | Mode | Notes |
|---|---|---|
| Google Calendar | read-only | OAuth token helper landed `fb55512` |
| Google Maps Platform | read-only | commute estimates, 4 tiles |
| Google Photos | read-only | slideshow (Phase 2) |
| Trello | read + mark complete | filtered to dashboard lists |
| AnyList | read + write | via `backend/tools/anylist/push.js` Node helper; protobuf patch required |
| Telegram Bot | read + write | DMs for ratings, group actions |
| ESPN | read-only | sports widget, 8 teams |

## Phase 1 — MVP (status as of 2026-04-29)

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
- [x] APScheduler — 5 of 7 jobs are real:
  - [x] `refresh_commute` (15m)
  - [x] `refresh_glance` (5m)
  - [x] `midnight_reset`
  - [x] `receipt_expiry_cleanup`
  - [x] `post_dinner_prompt`
  - [ ] `generate_digest` — stub (Phase 2)
  - [ ] `weekly_summary` — stub (Phase 2)
- [ ] **Cooking mode** — not started. No router, no view; only `cook_time` / `batch_cookable` field refs

## Phase 2 — Next

In rough priority order:

1. **Morning digest** — fills the 6am scheduler stub, drives Home view's digest snippet
2. **Word of the Day** — Ambient view
3. **Emergency dinner button** — fast pick from freezer/pantry when meal plan derails
4. **Grocery inference** — read context (recipes, freezer, pantry) and suggest adds
5. **Receipt parsing** — ingestion side (cleanup job already exists)
6. **Post-cooking capture** — log what actually happened after dinner
7. **Google Photos slideshow** — Ambient view

## Phase 3 — v2

- Private preference profiles (per-adult, via 1:1 Telegram DMs)
- Baby profile (allergens, milestones, food intros)
- Food logging
- FitBit API
- Monarch API

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

## Open questions / decisions

- Where the kiosk Pi pulls from and how it auto-updates — not yet automated
