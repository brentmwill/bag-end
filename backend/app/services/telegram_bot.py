import asyncio
import json
import logging
import threading
from datetime import date, datetime, timezone

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
# Bot-thread-local DB session factory
# Initialized inside _run_bot so it binds to the bot's event loop, not uvicorn's.
# ---------------------------------------------------------------------------
_BotSession = None


def _get_bot_session():
    if _BotSession is None:
        raise RuntimeError("Bot DB session not initialized")
    return _BotSession()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
async def _is_known_user(telegram_user_id: int) -> bool:
    from app.models.users import UserProfile
    from sqlalchemy import select

    async with _get_bot_session() as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none() is not None


async def _resolve_user_profile_id(telegram_user_id: int):
    """Look up a registered user's profile id; None if not yet registered."""
    from app.models.users import UserProfile
    from sqlalchemy import select

    async with _get_bot_session() as session:
        result = await session.execute(
            select(UserProfile.id).where(UserProfile.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()


async def _log_message(
    *,
    telegram_user_id: int,
    user_profile_id,
    direction: str,
    persona: str | None,
    body: str,
) -> None:
    """Append one row to conversation_log. Best-effort: swallow errors so a
    logging failure never breaks the user-facing reply."""
    from app.models.logs import ConversationLog

    try:
        async with _get_bot_session() as session:
            session.add(ConversationLog(
                telegram_user_id=telegram_user_id,
                user_profile_id=user_profile_id,
                direction=direction,
                persona=persona,
                body=body,
            ))
            await session.commit()
    except Exception:
        logger.exception("conversation_log write failed (persona=%s, dir=%s)", persona, direction)


# ---------------------------------------------------------------------------
# Haiku classification helpers
# ---------------------------------------------------------------------------
async def _classify_feedback(recipe_name: str, feedback: str) -> dict:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"You are analyzing post-dinner feedback from a family member.\n\n"
        f"Dinner: {recipe_name}\n"
        f'Feedback: "{feedback}"\n\n'
        "Classify this feedback and return JSON only (no markdown):\n"
        "{\n"
        '  "recipe_note": "<concise note for this recipe, or null>",\n'
        '  "preference_update": "<personal preference to add to profile, or null>",\n'
        '  "needs_clarification": <true or false>,\n'
        '  "clarifying_question": "<question to ask, or null>"\n'
        "}\n\n"
        "Rules:\n"
        "- recipe_note: something specific to improve this recipe next time (e.g. 'reduce lemon', 'add more garlic')\n"
        "- preference_update: ONLY set this if the person clearly expresses a general aversion or dislike (e.g. 'I hate tilapia', 'I can't stand cilantro', 'I don't like spicy food'). A request to tweak a recipe (e.g. 'more cheese', 'less salt') is NOT a general preference — leave preference_update null.\n"
        "- needs_clarification=true only if it's genuinely ambiguous whether this is a one-time recipe note or a strong personal aversion\n"
        "- If clearly recipe-specific: recipe_note set, preference_update null, needs_clarification false\n"
        "- If clearly a personal aversion: preference_update set, recipe_note may also be set, needs_clarification false"
    )
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


async def _resolve_clarification(recipe_name: str, original_note: str, clarification_answer: str) -> dict:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"You are finalizing feedback classification after a clarifying answer.\n\n"
        f"Dinner: {recipe_name}\n"
        f'Original feedback: "{original_note}"\n'
        f'Clarification answer: "{clarification_answer}"\n\n'
        "Return JSON only (no markdown):\n"
        "{\n"
        '  "recipe_note": "<concise note for this recipe, or null>",\n'
        '  "preference_update": "<personal preference to add to profile, or null>"\n'
        "}"
    )
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


async def _store_feedback_result(session, user_profile_id, recipe_id, telegram_user_id: int, result: dict) -> None:
    """Persist recipe_note and/or preference_update from a classification result."""
    from app.models.feedback import RecipeFeedback
    from app.services.preferences import append_preference

    if result.get("recipe_note") and recipe_id:
        session.add(RecipeFeedback(
            user_id=user_profile_id,
            recipe_id=recipe_id,
            note=result["recipe_note"],
        ))
    if result.get("preference_update"):
        append_preference(telegram_user_id, result["preference_update"])


# ---------------------------------------------------------------------------
# Rating state machine — handles incoming DM text
# ---------------------------------------------------------------------------
async def handle_dm_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Routes incoming private DMs through the rating state machine.
    Falls through to unknown-user prompt if no active pending rating.
    """
    user = update.effective_user
    if not user or not update.message:
        return

    text = update.message.text.strip()
    now_utc = datetime.now(timezone.utc)

    # Log inbound freeform DM. persona=None — this path is the legacy rating
    # state machine, not a routed persona. user_profile_id is resolved before
    # the log call so unknown senders still get captured.
    await _log_message(
        telegram_user_id=user.id,
        user_profile_id=await _resolve_user_profile_id(user.id),
        direction="in",
        persona=None,
        body=text,
    )

    from app.models.feedback import PendingRating, RecipeFeedback
    from app.models.meal_plan import MealPlanSlot
    from app.models.recipe import Recipe
    from app.models.users import UserProfile
    from sqlalchemy import select

    async with _get_bot_session() as session:
        user_result = await session.execute(
            select(UserProfile).where(UserProfile.telegram_user_id == user.id)
        )
        user_profile = user_result.scalar_one_or_none()

        if not user_profile:
            await update.message.reply_text(
                "Hey! I don't know you yet. Send /start to set up your profile."
            )
            return

        pr_result = await session.execute(
            select(PendingRating).where(
                PendingRating.user_id == user_profile.id,
                PendingRating.state != "complete",
                PendingRating.expires_at > now_utc,
            ).limit(1)
        )
        pr = pr_result.scalar_one_or_none()

        if not pr:
            # Known user, nothing pending — ignore
            return

        # Resolve recipe context
        slot_result = await session.execute(
            select(MealPlanSlot).where(MealPlanSlot.id == pr.slot_id)
        )
        slot = slot_result.scalar_one_or_none()
        recipe_name = "tonight's dinner"
        recipe_id = None
        if slot and slot.recipe_id:
            recipe_result = await session.execute(
                select(Recipe).where(Recipe.id == slot.recipe_id)
            )
            recipe = recipe_result.scalar_one_or_none()
            if recipe:
                recipe_name = recipe.name
                recipe_id = recipe.id

        # --- State: awaiting_rating ---
        if pr.state == "awaiting_rating":
            if text.lower() == "skip":
                pr.state = "complete"
                await session.commit()
                await update.message.reply_text("No problem, skipping tonight's rating.")
                return

            try:
                rating = int(text)
                if not 1 <= rating <= 5:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("Please reply with a number 1–5, or 'skip'.")
                return

            pr.rating = rating
            pr.state = "awaiting_feedback"
            await session.commit()
            await update.message.reply_text("Thanks! Anything you'd change about it? (or say 'no')")

        # --- State: awaiting_feedback ---
        elif pr.state == "awaiting_feedback":
            if text.lower() in ("no", "nope", "nothing", "n", "nah"):
                pr.state = "complete"
                await session.commit()
                await update.message.reply_text("Got it!")
                return

            try:
                result = await _classify_feedback(recipe_name, text)
            except Exception:
                logger.exception("Haiku classification failed")
                pr.state = "complete"
                await session.commit()
                await update.message.reply_text("Thanks, I've noted that.")
                return

            if result.get("needs_clarification"):
                pr.pending_note = text
                pr.state = "awaiting_clarification"
                await session.commit()
                await update.message.reply_text(result["clarifying_question"])
            else:
                await _store_feedback_result(session, user_profile.id, recipe_id, user.id, result)
                pr.state = "complete"
                await session.commit()
                await update.message.reply_text("Got it, I've noted that for next time!")

        # --- State: awaiting_clarification ---
        elif pr.state == "awaiting_clarification":
            try:
                result = await _resolve_clarification(recipe_name, pr.pending_note or "", text)
            except Exception:
                logger.exception("Haiku clarification resolution failed")
                pr.state = "complete"
                await session.commit()
                await update.message.reply_text("Thanks, I've noted that.")
                return

            await _store_feedback_result(session, user_profile.id, recipe_id, user.id, result)
            pr.state = "complete"
            await session.commit()
            await update.message.reply_text("Got it, I've noted that for next time!")


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

    from app.models.users import UserProfile, StaticPreference

    async with _get_bot_session() as session:
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

    from app.models.users import UserProfile, StaticPreference

    async with _get_bot_session() as session:
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


# ---------------------------------------------------------------------------
# Persona slash-command router (Phase 1.5 step 6)
# ---------------------------------------------------------------------------
PERSONA_NAMES = ("chef", "inbox", "health", "finance", "chores", "note")

# Stub replies until each persona's handler.py ships. Keep these honest about
# which phase wires up the real implementation.
PERSONA_STUB = {
    "chef": "Chef Sue isn't fully wired up yet — Phase 2.2 retrofits the existing meal/AnyList code into a persona.",
    "inbox": "Inbox isn't built yet — Phase 2.1, first greenfield persona.",
    "health": "Health isn't built yet — Phase 2.4 (Brent-only).",
    "finance": "Finance isn't built yet — Phase 2.5.",
    "chores": "Chores isn't built yet — Phase 2.6.",
    "note": "Note capture isn't wired yet.",
}


def _make_persona_handler(persona_name: str):
    """Return a Telegram command handler bound to one persona name.

    Logs the inbound command + body, dispatches to the registered handler if
    one exists, otherwise replies with the stub. Outbound reply is also logged.
    Once a persona ships its real handler, swap PERSONA_STUB[name] for a call
    into that handler module.
    """
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        tg_user_id = update.effective_user.id
        user_profile_id = await _resolve_user_profile_id(tg_user_id)
        inbound = update.message.text or ""

        await _log_message(
            telegram_user_id=tg_user_id,
            user_profile_id=user_profile_id,
            direction="in",
            persona=persona_name,
            body=inbound,
        )

        reply = PERSONA_STUB[persona_name]
        await update.message.reply_text(reply)

        await _log_message(
            telegram_user_id=tg_user_id,
            user_profile_id=user_profile_id,
            direction="out",
            persona=persona_name,
            body=reply,
        )

    return handler


async def backlog_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/backlog <freeform>` to capture, `/backlog list` to view open items,
    `/backlog done <id-prefix>` or `/backlog wontfix <id-prefix>` to archive."""
    if not update.message:
        return

    from sqlalchemy import select
    from app.models.backlog import BacklogItem
    from app.services.backlog import create_item, resolve_item

    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Usage:\n"
            "/backlog <freeform note>  — capture friction\n"
            "/backlog list             — show open items\n"
            "/backlog done <id-prefix> — archive as resolved\n"
            "/backlog wontfix <id-prefix>"
        )
        return

    sub = args[0].lower()

    if sub == "list":
        async with _get_bot_session() as session:
            result = await session.execute(
                select(BacklogItem).order_by(BacklogItem.created_at.desc()).limit(20)
            )
            items = result.scalars().all()
        if not items:
            await update.message.reply_text("Backlog is empty.")
            return
        lines = [
            f"`{str(i.id)[:8]}` [{i.severity}/{i.area}] {i.description}"
            for i in items
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if sub in ("done", "wontfix"):
        if len(args) < 2:
            await update.message.reply_text(f"Usage: /backlog {sub} <id-prefix>")
            return
        prefix = args[1]
        async with _get_bot_session() as session:
            result = await session.execute(
                select(BacklogItem).where(
                    sa_cast_uuid_text(BacklogItem.id).like(f"{prefix}%")
                )
            )
            matches = result.scalars().all()
            if not matches:
                await update.message.reply_text(f"No open item matching `{prefix}`.")
                return
            if len(matches) > 1:
                await update.message.reply_text(
                    f"Prefix `{prefix}` matches {len(matches)} items — be more specific."
                )
                return
            archived = await resolve_item(session, item_id=matches[0].id, resolution=sub)
            await session.commit()
        await update.message.reply_text(
            f"Archived as {sub}: {archived.description}" if archived else "Item gone."
        )
        return

    # Anything else: treat the entire message text after "/backlog " as the freeform note.
    full_text = update.message.text or ""
    freeform = full_text.partition(" ")[2].strip()
    if not freeform:
        await update.message.reply_text("Add a note after /backlog.")
        return

    try:
        async with _get_bot_session() as session:
            item = await create_item(
                session,
                freeform_text=freeform,
                created_by_persona="system",
            )
            await session.commit()
            await session.refresh(item)
    except Exception:
        logger.exception("Backlog capture failed")
        await update.message.reply_text("Couldn't capture that — Haiku normalizer failed.")
        return

    await update.message.reply_text(
        f"Logged `{str(item.id)[:8]}` [{item.severity}/{item.area}]: {item.description}",
        parse_mode="Markdown",
    )


def sa_cast_uuid_text(col):
    """Postgres-only: cast a UUID column to text for LIKE comparisons."""
    from sqlalchemy import cast, Text
    return cast(col, Text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Bag End commands:\n"
        "/start — set up your profile\n"
        "/add_baby — add the baby's profile\n"
        "/plan — suggest meals for the week\n"
        "/backlog — capture or browse friction notes\n"
        "\n"
        "Personas (stubs for now, real handlers landing in Phase 2):\n"
        "/chef — Chef Sue (recipes, meal plan, AnyList, food log)\n"
        "/inbox — Inbox (Gmail triage)\n"
        "/health — Health (Brent-only)\n"
        "/finance — Finance (Monarch)\n"
        "/chores — Chores (recurring tasks)\n"
        "/note — quick capture\n"
        "\n"
        "/help — show this message"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram bot error", exc_info=context.error)


# ---------------------------------------------------------------------------
# Bot runner — dedicated thread + event loop
# ---------------------------------------------------------------------------
async def _run_bot(token: str) -> None:
    global _application, _BotSession
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.config import settings as _settings

    _bot_engine = create_async_engine(_settings.database_url, echo=False)
    _BotSession = async_sessionmaker(
        bind=_bot_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

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
    app.add_handler(adult_onboarding)
    app.add_handler(baby_onboarding)
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("backlog", backlog_command))
    for _persona in PERSONA_NAMES:
        app.add_handler(CommandHandler(_persona, _make_persona_handler(_persona)))
    app.add_handler(CommandHandler("help", help_command))
    # Rating state machine — handles DM text for registered users.
    # Unknown users get the registration prompt from inside handle_dm_text.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_dm_text,
    ))
    app.add_error_handler(error_handler)

    _application = app

    async with app:
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot polling started")
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
