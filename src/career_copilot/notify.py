"""Daily notification delivery via Discord webhook."""

import logging
import os

import httpx

from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL_ENV_VAR = "DISCORD_WEBHOOK_URL"
DISCORD_MESSAGE_LIMIT = 2000
REQUEST_TIMEOUT = 10.0


def _format_ai_flags(analysis: AIAnalysis | None) -> str:
    if analysis is None:
        return ""

    flags = []
    if analysis.visa_sponsorship_mentioned:
        flags.append("visa✓")
    if analysis.likely_summer_2027_eligible:
        flags.append("2027-likely✓")

    return f" [{' | '.join(flags)}]" if flags else ""


def build_morning_message(
    new_listings: list[Listing],
    ranked_new: list[tuple[Listing, int]],
    analysis_by_url: dict[str, AIAnalysis] | None = None,
    top_n: int = 5,
) -> str:
    if not new_listings:
        return "Career Copilot — 0 new listings found today. Nothing new to review."

    lines = [f"Career Copilot — {len(new_listings)} new listing(s) found today."]
    analysis_by_url = analysis_by_url or {}

    if ranked_new:
        lines.append("")
        lines.append("Top matches:")
        for listing, score in ranked_new[:top_n]:
            flags = _format_ai_flags(analysis_by_url.get(listing.url))
            lines.append(
                f"[{score}] {listing.title} — {listing.company} ({listing.location}){flags}"
                f"\n{listing.url}"
            )

    return "\n".join(lines)


def send_discord_notification(message: str) -> bool:
    webhook_url = os.environ.get(DISCORD_WEBHOOK_URL_ENV_VAR)
    if not webhook_url:
        logger.error("%s is not set — see README/CLAUDE.md for setup", DISCORD_WEBHOOK_URL_ENV_VAR)
        return False

    if len(message) > DISCORD_MESSAGE_LIMIT:
        logger.warning(
            "Notification message exceeds Discord's %d-character limit — truncating",
            DISCORD_MESSAGE_LIMIT,
        )
        message = message[: DISCORD_MESSAGE_LIMIT - 3] + "..."

    try:
        response = httpx.post(webhook_url, json={"content": message}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Discord webhook returned an error: %s %s — %s",
            exc.response.status_code,
            exc.response.reason_phrase,
            exc.response.text,
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("Failed to send Discord notification: %s", exc)
        return False

    return True
