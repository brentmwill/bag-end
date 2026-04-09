import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.routers import glance, interact, recipes, meal_plan, baby, freezer
from app.services.telegram_bot import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()

    telegram_app = build_application()
    if telegram_app:
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()

    yield

    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

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


@app.get("/health")
async def health():
    return {"status": "ok"}
