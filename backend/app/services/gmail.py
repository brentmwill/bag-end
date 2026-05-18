"""Gmail fetch helper for the Inbox persona, via IMAP + app password.

Why IMAP, not the Gmail API: gmail.readonly is a restricted OAuth scope.
Publishing the app would require CASA security verification (weeks + cost),
and Testing-mode tokens expire every 7 days. App-password IMAP sidesteps both
issues and is well-suited to a single-user personal project.

Credentials live in .env as GMAIL_EMAIL + GMAIL_APP_PASSWORD. Generate the app
password at https://myaccount.google.com/security (requires 2-step verification).
"""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from imap_tools import AND, MailBox

from app.config import settings

logger = logging.getLogger(__name__)

# How much body we keep as a "snippet" — enough for Haiku to spot action items
# without paying the full body cost per email.
_SNIPPET_CHARS = 400

_WHITESPACE = re.compile(r"\s+")


def _make_snippet(body: str) -> str:
    """Collapse whitespace and truncate. IMAP gives us full text; we don't
    want to feed the entire MIME tree to Haiku for a triage decision."""
    if not body:
        return ""
    collapsed = _WHITESPACE.sub(" ", body).strip()
    if len(collapsed) <= _SNIPPET_CHARS:
        return collapsed
    return collapsed[:_SNIPPET_CHARS].rstrip() + "…"


def _normalize_date(d: Any) -> datetime:
    """msg.date is usually a tz-aware datetime; coerce edge cases to UTC."""
    if isinstance(d, datetime):
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d
    return datetime.now(timezone.utc)


def _fetch_sync(
    *,
    email: str,
    password: str,
    host: str,
    since: datetime | None,
    max_messages: int,
) -> list[dict[str, Any]]:
    """Synchronous IMAP fetch. Runs in a thread; do not call directly from
    an async handler — use `fetch_recent_messages` instead."""
    out: list[dict[str, Any]] = []

    criteria = AND(date_gte=since.date()) if since else AND(all=True)

    with MailBox(host).login(email, password, "INBOX") as mailbox:
        for msg in mailbox.fetch(
            criteria,
            reverse=True,
            limit=max_messages,
            mark_seen=False,
            bulk=True,
        ):
            body = msg.text or msg.html or ""
            out.append({
                "message_id": msg.uid,
                "subject": msg.subject or "(no subject)",
                "sender": msg.from_ or "",
                "snippet": _make_snippet(body),
                "internal_date": _normalize_date(msg.date),
                "flags": list(msg.flags) if msg.flags else [],
            })

    # imap-tools' `date_gte` is date-precision; tighten to the actual datetime
    # boundary so polling windows don't double-count yesterday's tail.
    if since is not None:
        out = [m for m in out if m["internal_date"] >= since]

    return out


async def fetch_recent_messages(
    since: datetime | None = None,
    *,
    max_messages: int = 50,
) -> list[dict[str, Any]]:
    """Fetch recent INBOX messages newer than `since`, newest first.

    Returns normalized dicts: message_id (IMAP UID), subject, sender, snippet,
    internal_date, flags. Newsletter / category filtering is intentionally
    deferred to the Haiku triage step — keeps this layer simple and lets the
    classifier own the "is this actionable?" decision.
    """
    if not settings.gmail_email or not settings.gmail_app_password:
        logger.warning("Gmail IMAP credentials not configured; returning no messages")
        return []

    try:
        return await asyncio.to_thread(
            _fetch_sync,
            email=settings.gmail_email,
            password=settings.gmail_app_password,
            host=settings.gmail_imap_host,
            since=since,
            max_messages=max_messages,
        )
    except Exception:
        logger.exception("Gmail IMAP fetch failed")
        return []
