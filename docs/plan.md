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

## Chatbot expansion (Telegram-first)

Brent uses Telegram daily and is happy treating it as the primary chatbot surface before
any in-app chat UI. New bots/features sit alongside Chef Sue:

- **Majordomo bot** — general household assistant (sibling to Chef Sue); scope TBD
  (scheduling help, coordination prompts, daily check-ins?). "Majordomo" = Latin for
  head of the house, fits the household-staff register alongside Chef Sue.
- **Backlog idea capture via Telegram** — quick `/idea <text>` or freeform DM that lands
  in a project backlog table, so Brent can dump ideas without needing Claude access
- **Calendar event change notifications** — push DM when a new event is added to the
  shared Google Calendar (and likely on cancellations/edits)
- (further bot ideas to be added as they come up)

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

## Agent loop design pattern

Inspired by OpenClaw's architecture. All AI-driven Telegram interactions — and any
background job that takes a consequential action — should follow this loop rather than
being wired ad hoc:

```
1. GATHER   — fetch relevant context (calendar, meals, freezer, Trello, etc.)
2. REASON   — LLM produces a proposed action or message
3. GATE     — decide: auto-execute (low-risk, reversible) or ask human first
4. EXECUTE  — carry out the action (push to AnyList, update meal plan, etc.)
5. CONFIRM  — send outcome back to user; update persistent household context
6. RECOVER  — on error or rejection, log and either retry or surface to user
```

**The gate (step 3) is the critical design decision.** Default to asking when:
- The action affects external state (AnyList push, Trello update)
- The action is hard to reverse
- Confidence is below a threshold

Default to auto-execute when:
- It's a read-only or display update
- The user has previously approved the same class of action
- It's a scheduled digest (informational only)

This pattern keeps agents useful without letting them act autonomously in ways that
surprise the household. Wire every new agent feature against this loop explicitly — don't
bolt on approval gates later.

## Stolen from OpenClaw — future feature ideas

Ideas captured from studying OpenClaw's most-used patterns. Add to phases as priorities
settle.

### Morning briefing push
Scheduled Telegram message (~7am) synthesizing: today's calendar events, tonight's meal,
commute outlook, any blocked Trello items, and a one-line digest. Proactive push —
doesn't require anyone to look at the dashboard. Feeds the `generate_digest` APScheduler
stub already in Phase 2.

### Multi-agent roles
Rather than one monolithic AI call for complex tasks (e.g. weekly meal planning), split
into coordinated specialist agents:
- **Planner agent** — proposes the week's meals given constraints
- **Grocery differ agent** — diffs the plan against AnyList + freezer, surfaces what to buy
- **Notifier agent** — formats and pushes Telegram messages at the right time

Agents share the persistent household context (see below) rather than each re-fetching
everything independently.

### Persistent household context
A live context object (DB-backed) that accumulates signals over time so AI calls don't
start from scratch:
- Current week of pregnancy + active dietary constraints
- Who's home / expected home (from calendar)
- Freezer state snapshot
- Last 7 days of dinner ratings (from post-dinner DM flow)
- Energy/mood signals (can seed from Telegram messages over time)

Household context is updated by the confirm step of the agent loop and queried at the
gather step. Replaces the current pattern of re-fetching everything on each API call.

### Human-in-the-loop approval gates (Telegram)
Telegram-native approval flow for consequential actions:
- Inline keyboard buttons (Approve / Reject / Modify) on proposed changes
- Timeout fallback (e.g. no response in 2h → auto-cancel and notify)
- Audit log of approvals/rejections in DB for context in future AI calls

This is the concrete implementation of step 3 in the agent loop above. Majordomo bot is
the natural home for this.

## Open questions / decisions

- Where the kiosk Pi pulls from and how it auto-updates — not yet automated
