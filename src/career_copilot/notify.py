"""Daily notification delivery via Discord webhook."""

import logging
import os

import httpx

from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL_ENV_VAR = "DISCORD_WEBHOOK_URL"
DISCORD_MESSAGE_LIMIT = 2000
REQUEST_TIMEOUT = 10.0


def build_morning_message(
    new_listings: list[Listing],
    ranked_new: list[tuple[Listing, int]],
    top_n: int = 5,
) -> str:
    if not new_listings:
        return "Career Copilot — 0 new listings found today. Nothing new to review."

    lines = [f"Career Copilot — {len(new_listings)} new listing(s) found today."]

    if ranked_new:
        lines.append("")
        lines.append("Top matches:")
        for listing, score in ranked_new[:top_n]:
            lines.append(
                f"[{score}] {listing.title} — {listing.company} ({listing.location})\n{listing.url}"
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
