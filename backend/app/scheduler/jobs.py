import logging
from datetime import date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _job_refresh_commute():
    """Smart-tick: only fetches the relevant direction during rush windows
    (Mon–Fri 6:30–8:15am outbound, 4–6pm inbound). No-op outside windows."""
    try:
        from app.services.google_maps import smart_refresh, get_tiles
        from app.services.glance_cache import get_cache, set_cache
        await smart_refresh()
        cache = get_cache()
        if cache and cache.get("home") is not None:
            cache["home"]["commute_tiles"] = get_tiles()
            set_cache(cache)
    except Exception:
        logger.exception("refresh_commute job failed")


async def _job_refresh_glance():
    try:
        from app.services.glance_cache import refresh_glance
        await refresh_glance()
    except Exception:
        logger.exception("refresh_glance job failed")


async def _job_generate_digest():
    try:
        logger.info("TODO: generate daily digest")
    except Exception:
        logger.exception("generate_digest job failed")


async def _job_generate_wotd():
    try:
        from app.services.word_of_day import ensure_today_wotd
        await ensure_today_wotd()
    except Exception:
        logger.exception("generate_wotd job failed")


async def _job_midnight_reset():
    try:
        from app.services.glance_cache import set_cache
        from app.database import AsyncSessionLocal
        from app.models.feedback import PendingRating
        from sqlalchemy import delete
        from datetime import datetime, timezone

        set_cache({})
        logger.info("midnight_reset: glance cache invalidated for new day")

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(PendingRating).where(PendingRating.expires_at < datetime.now(timezone.utc))
            )
            await session.commit()
            logger.info("midnight_reset: cleared %d expired pending ratings", result.rowcount)
    except Exception:
        logger.exception("midnight_reset job failed")


async def _job_receipt_expiry_cleanup():
    try:
        from app.database import AsyncSessionLocal
        from app.models.pantry import Receipt
        from sqlalchemy import delete
        today = date.today()
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Receipt).where(Receipt.expiry_date < today))
            await session.commit()
        logger.info("receipt_expiry_cleanup: expired receipts removed")
    except Exception:
        logger.exception("receipt_expiry_cleanup job failed")


async def _job_post_dinner_prompt():
    """DM each registered adult user asking them to rate tonight's dinner."""
    try:
        from app.services.telegram_bot import get_bot
        from app.database import AsyncSessionLocal
        from app.models.meal_plan import MealPlanSlot
        from app.models.recipe import Recipe
        from app.models.users import UserProfile
        from app.models.feedback import PendingRating
        from sqlalchemy import select
        from datetime import datetime, timedelta, time as dtime
        from zoneinfo import ZoneInfo

        bot = get_bot()
        if not bot:
            return

        eastern = ZoneInfo("America/New_York")
        now_eastern = datetime.now(eastern)
        midnight_eastern = datetime.combine(
            now_eastern.date() + timedelta(days=1), dtime(0, 0), tzinfo=eastern
        )
        today = now_eastern.date()

        async with AsyncSessionLocal() as session:
            slot_result = await session.execute(
                select(MealPlanSlot)
                .where(MealPlanSlot.date == today, MealPlanSlot.meal_type == "dinner")
                .limit(1)
            )
            slot = slot_result.scalar_one_or_none()
            if not slot or not slot.recipe_id:
                return

            recipe_result = await session.execute(
                select(Recipe).where(Recipe.id == slot.recipe_id)
            )
            recipe = recipe_result.scalar_one_or_none()
            if not recipe:
                return

            users_result = await session.execute(
                select(UserProfile).where(
                    UserProfile.role == "adult",
                    UserProfile.telegram_user_id.is_not(None),
                )
            )
            users = users_result.scalars().all()

            for user in users:
                existing_result = await session.execute(
                    select(PendingRating).where(
                        PendingRating.user_id == user.id,
                        PendingRating.slot_id == slot.id,
                    )
                )
                if not existing_result.scalar_one_or_none():
                    session.add(PendingRating(
                        user_id=user.id,
                        slot_id=slot.id,
                        state="awaiting_rating",
                        expires_at=midnight_eastern,
                    ))
            await session.commit()

        for user in users:
            try:
                await bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"How was {recipe.name} tonight? Reply with a rating 1–5, or 'skip'.",
                )
            except Exception:
                logger.exception("Failed to DM user %s for dinner rating", user.telegram_user_id)

    except Exception:
        logger.exception("post_dinner_prompt job failed")


async def _job_weekly_summary():
    try:
        logger.info("TODO: send weekly summary via Telegram")
    except Exception:
        logger.exception("weekly_summary job failed")


def start_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _job_refresh_commute,
        trigger=IntervalTrigger(minutes=5),
        id="refresh_commute",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_refresh_glance,
        trigger=IntervalTrigger(minutes=5),
        id="refresh_glance",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_generate_digest,
        trigger=CronTrigger(hour=6, minute=0),
        id="generate_digest",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_midnight_reset,
        trigger=CronTrigger(hour=0, minute=0),
        id="midnight_reset",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_receipt_expiry_cleanup,
        trigger=CronTrigger(hour=2, minute=0),
        id="receipt_expiry_cleanup",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_post_dinner_prompt,
        trigger=CronTrigger(hour=19, minute=0),
        id="post_dinner_prompt",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_weekly_summary,
        trigger=CronTrigger(day_of_week="sun", hour=19, minute=0),
        id="weekly_summary",
        replace_existing=True,
    )
    _scheduler.add_job(
        _job_generate_wotd,
        trigger=CronTrigger(hour=5, minute=30, timezone="America/New_York"),
        id="generate_wotd",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
