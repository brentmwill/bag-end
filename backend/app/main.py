import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import init_db
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.routers import glance, interact, recipes, meal_plan, baby, freezer, calendar, wotd
from app.services.telegram_bot import start_bot, stop_bot

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    start_bot()

    yield

    stop_bot()
    stop_scheduler()


app = FastAPI(title="Bag End Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glance.router)
app.include_router(interact.router)
app.include_router(recipes.router)
app.include_router(meal_plan.router)
app.include_router(baby.router)
app.include_router(freezer.router)
app.include_router(calendar.router)
app.include_router(wotd.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve React PWA — must come after all API routes
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
