# Home Dashboard

A web-based household command center for Brent, Danielle, and their baby. Displayed on a 32" portrait monitor (Raspberry Pi kiosk) in the kitchen. Also accessible as a PWA via Tailscale.

## Full Plan
`C:\Users\eluse\.claude\plans\home-dashboard-plan.md`

## Stack
- **Backend:** Python FastAPI, separate port from ai-tutoring-system
- **Frontend:** React PWA, portrait-optimized, four-view cycle
- **Database:** PostgreSQL
- **LLM:** Claude (Anthropic API only — claude-sonnet-4-6 + claude-haiku-4-5)
- **Scheduler:** APScheduler (background jobs)

## Key External Dependencies
- Google Calendar API (read-only)
- Google Maps Platform API (commute estimates)
- Google Photos API (read-only, slideshow)
- Trello API (read + mark complete)
- AnyList MCP server: `C:\Users\eluse\Projects\anylist-mcp`
  - Config: `C:\Users\eluse\.mcp.json`
  - **Protobuf patch:** `node_modules/anylist/lib/item.js` ~line 71: `quantity` → `deprecatedQuantity`. Reapply after any `npm install`.
- Telegram Bot API

## Server
- Ubuntu home server — same machine as ai-tutoring-system, different port
- Tailscale IP: `100.104.206.14`
- No public internet exposure

## API Endpoints (aggregation layer)
- `GET /api/glance` — full payload for all four display views, cached server-side
- `GET /api/interact` — full data for interact mode (recipes, meal plan, tasks, grocery, freezer)

## Four Display Views
1. **Home** — Weather, tonight's meal, calendar events, 4 commute tiles, digest snippet
2. **Planning** — Week meal plan (left) + Google Calendar (right)
3. **Household** — Trello tasks, baby meal slots, freezer inventory
4. **Ambient** — Google Photos fullscreen, Word of the Day

## Meal Planning Defaults
- Pregnancy-safe (expires 2026-10-15 — stored as configurable date, drops automatically)
- Baby finger-food friendly
- Batch/slow-cooker friendly
- Freezable

## AnyList Notes Convention
All items pushed to AnyList include recipe source in notes field:
- Multi-recipe: `"White Bean Soup; Carrot Soup"`
- Manual add: `"added without notes by user"`

## Phase 1 Scope (current)
Dashboard shell, Calendar, Trello, recipe DB (Paprika import + editing), meal planner,
freezer log, cooking mode, AnyList integration, baby slots, Telegram group actions, APScheduler.

## Phase 2 (next)
Morning digest, Word of Day, emergency dinner button, grocery inference,
receipt parsing, post-cooking capture, Google Photos.

## Phase 3 (v2)
Private preference profiles (1:1 Telegram DMs), baby profile, food logging, FitBit API, Monarch.

## Do Not
- Commit API keys or credentials
- Mix this project's venv or port with ai-tutoring-system
- Auto-double grocery quantities (was a one-time session decision)
- Write to Google Calendar (read-only integration)
