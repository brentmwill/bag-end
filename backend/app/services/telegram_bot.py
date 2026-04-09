import asyncio
import logging
import threading
from datetime import date

from telegram import Bot, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------
ASK_NAME, ASK_DIETARY, ASK_VETOES, ASK_CUISINE, CONFIRM_ADULT = range(5)
ASK_BABY_NAME, ASK_BABY_DOB, ASK_BABY_ALLERGENS, CONFIRM_BABY = range(10, 14)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_bot_thread: threading.Thread | None = None
_bot_loop: asyncio.AbstractEventLoop | None = None
_application: Application | None = None


def get_bot() -> Bot | None:
    if _application:
        return _application.bot
    return None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
async def _is_known_user(telegram_user_id: int) -> bool:
    from app.database import AsyncSessionLocal
    from app.models.users import UserProfile
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Adult onboarding handlers
# ---------------------------------------------------------------------------
async def onboard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if await _is_known_user(user.id):
        await update.message.reply_text("You're already registered. Welcome back!")
        return ConversationHandler.END

    await update.message.reply_text(
        f"Hey {user.first_name}! I don't know you yet — let's set up your profile.\n\n"
        "What's your name?"
    )
    return ASK_NAME


async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print(f"DEBUG got_name called: {update.message.text}", flush=True)
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "Any dietary restrictions? (e.g. vegetarian, gluten-free) — or say 'none'."
    )
    return ASK_DIETARY


async def got_dietary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["dietary"] = update.message.text.strip()
    await update.message.reply_text(
        "Any ingredients or foods you won't eat? List them comma-separated — or say 'none'."
    )
    return ASK_VETOES


async def got_vetoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["vetoes"] = update.message.text.strip()
    await update.message.reply_text(
        "Any cuisine preferences? (e.g. 'more Asian, less red meat') — or say 'none'."
    )
    return ASK_CUISINE


async def got_cuisine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["cuisine"] = update.message.text.strip()
    d = context.user_data
    await update.message.reply_text(
        f"Here's your profile:\n"
        f"  Name: {d['name']}\n"
        f"  Dietary: {d['dietary']}\n"
        f"  Won't eat: {d['vetoes']}\n"
        f"  Cuisine prefs: {d['cuisine']}\n\n"
        "Reply 'yes' to save, anything else to cancel."
    )
    return CONFIRM_ADULT


async def confirm_adult(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.strip().lower() != "yes":
        await update.message.reply_text("Cancelled. Send /start to try again.")
        return ConversationHandler.END

    d = context.user_data
    telegram_user_id = update.effective_user.id

    from app.database import AsyncSessionLocal
    from app.models.users import UserProfile, StaticPreference

    async with AsyncSessionLocal() as session:
        profile = UserProfile(
            name=d["name"],
            role="adult",
            telegram_user_id=telegram_user_id,
        )
        session.add(profile)
        await session.flush()

        prefs = []
        if d["dietary"].lower() != "none":
            prefs.append(StaticPreference(
                user_profile_id=profile.id,
                pref_type="dietary_restriction",
                value=d["dietary"],
            ))
        if d["vetoes"].lower() != "none":
            for veto in d["vetoes"].split(","):
                v = veto.strip()
                if v:
                    prefs.append(StaticPreference(
                        user_profile_id=profile.id,
                        pref_type="veto",
                        value=v,
                    ))
        if d["cuisine"].lower() != "none":
            prefs.append(StaticPreference(
                user_profile_id=profile.id,
                pref_type="cuisine_pref",
                value=d["cuisine"],
            ))

        session.add_all(prefs)
        await session.commit()

    await update.message.reply_text(f"Profile saved! Welcome, {d['name']}.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Baby onboarding handlers
# ---------------------------------------------------------------------------
async def add_baby_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Let's add the baby's profile. What's the baby's name?")
    return ASK_BABY_NAME


async def got_baby_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["baby_name"] = update.message.text.strip()
    await update.message.reply_text("What's the baby's date of birth? (YYYY-MM-DD)")
    return ASK_BABY_DOB


async def got_baby_dob(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        date.fromisoformat(text)
    except ValueError:
        await update.message.reply_text("Invalid format — please use YYYY-MM-DD.")
        return ASK_BABY_DOB

    context.user_data["baby_dob"] = text
    await update.message.reply_text(
        "Any known allergens? List them comma-separated — or say 'none'."
    )
    return ASK_BABY_ALLERGENS


async def got_baby_allergens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["baby_allergens"] = update.message.text.strip()
    d = context.user_data
    await update.message.reply_text(
        f"Baby profile:\n"
        f"  Name: {d['baby_name']}\n"
        f"  DOB: {d['baby_dob']}\n"
        f"  Allergens: {d['baby_allergens']}\n\n"
        "Reply 'yes' to save, anything else to cancel."
    )
    return CONFIRM_BABY


async def confirm_baby(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.strip().lower() != "yes":
        await update.message.reply_text("Cancelled. Send /add_baby to try again.")
        return ConversationHandler.END

    d = context.user_data

    from app.database import AsyncSessionLocal
    from app.models.users import UserProfile, StaticPreference

    async with AsyncSessionLocal() as session:
        profile = UserProfile(
            name=d["baby_name"],
            role="baby",
            telegram_user_id=None,
            dob=date.fromisoformat(d["baby_dob"]),
        )
        session.add(profile)
        await session.flush()

        prefs = []
        if d["baby_allergens"].lower() != "none":
            for allergen in d["baby_allergens"].split(","):
                a = allergen.strip()
                if a:
                    prefs.append(StaticPreference(
                        user_profile_id=profile.id,
                        pref_type="allergen",
                        value=a,
                    ))

        session.add_all(prefs)
        await session.commit()

    await update.message.reply_text(f"Baby profile saved for {d['baby_name']}!")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Fallback / utility handlers
# ---------------------------------------------------------------------------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Meal planning coming soon!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Bag End commands:\n"
        "/start — set up your profile\n"
        "/add_baby — add the baby's profile\n"
        "/plan — suggest meals for the week\n"
        "/help — show this message"
    )


async def unknown_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"DEBUG unknown_user_prompt: {update.message.text if update.message else 'no msg'}", flush=True)
    if update.effective_user and not await _is_known_user(update.effective_user.id):
        await update.message.reply_text(
            "Hey! I don't know you yet. Send /start to set up your profile."
        )


async def debug_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"DEBUG all_messages: {update.message.text if update.message else repr(update)}", flush=True)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram bot error", exc_info=context.error)


# ---------------------------------------------------------------------------
# Bot runner — dedicated thread + event loop
# ---------------------------------------------------------------------------
async def _run_bot(token: str) -> None:
    global _application

    adult_onboarding = ConversationHandler(
        entry_points=[CommandHandler("start", onboard_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            ASK_DIETARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_dietary)],
            ASK_VETOES: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_vetoes)],
            ASK_CUISINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_cuisine)],
            CONFIRM_ADULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_adult)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    baby_onboarding = ConversationHandler(
        entry_points=[CommandHandler("add_baby", add_baby_start)],
        states={
            ASK_BABY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_baby_name)],
            ASK_BABY_DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_baby_dob)],
            ASK_BABY_ALLERGENS: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_baby_allergens)],
            CONFIRM_BABY: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_baby)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, debug_all), group=-1)
    app.add_handler(adult_onboarding)
    app.add_handler(baby_onboarding)
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_user_prompt))
    app.add_error_handler(error_handler)

    _application = app

    async with app:
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot polling started")
        # Block until the stop event is set
        await _stop_event.wait()
        await app.updater.stop()
        await app.stop()
        logger.info("Telegram bot stopped")


_stop_event: asyncio.Event | None = None


def _thread_main(token: str) -> None:
    global _bot_loop, _stop_event
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _bot_loop = loop
    _stop_event = asyncio.Event()
    try:
        loop.run_until_complete(_run_bot(token))
    except Exception:
        logger.exception("Telegram bot thread crashed")
    finally:
        loop.close()


def start_bot() -> None:
    global _bot_thread
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot will not start")
        return

    _bot_thread = threading.Thread(target=_thread_main, args=(settings.telegram_bot_token,), daemon=True)
    _bot_thread.start()
    logger.info("Telegram bot thread started")


def stop_bot() -> None:
    global _bot_loop, _stop_event
    if _bot_loop and _stop_event:
        _bot_loop.call_soon_threadsafe(_stop_event.set)
    if _bot_thread:
        _bot_thread.join(timeout=10)
    logger.info("Telegram bot thread joined")
