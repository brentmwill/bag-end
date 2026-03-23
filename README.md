# Home Dashboard

A web-based household command center displayed on a 32" portrait monitor in the kitchen. Built for Brent and Danielle's family.

## What It Does

- Four rotating display views: Home, Planning, Household, Ambient
- Integrates Google Calendar, Google Maps commute, Trello tasks, AnyList grocery list
- Native recipe database (migrated from Paprika), weekly meal planner, cooking mode
- Telegram bot for grocery adds, recipe clipping, receipt parsing, and household coordination
- Claude-powered morning digest, meal suggestions, and grocery inference

## Stack

- **Backend:** Python FastAPI
- **Frontend:** React PWA (portrait-optimized, installable via Tailscale)
- **Database:** PostgreSQL
- **LLM:** Claude (Anthropic)

## Access

Accessible on local network and via Tailscale VPN only. No public internet exposure.

## Docs

See `C:\Users\eluse\.claude\plans\home-dashboard-plan.md` for full implementation plan.
