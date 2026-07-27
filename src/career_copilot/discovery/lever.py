"""Lever provider — public unauthenticated postings API.

Verified via a real live unauthenticated request against Lever's own public
demo board (`GET https://api.lever.co/v0/postings/leverdemo?mode=json`, 388
postings returned, July 2026): each posting is a flat JSON object with
`text` (title), `categories.location`, `hostedUrl` (candidate-facing apply
page), `description` (HTML), `id`, and `createdAt` (epoch milliseconds).
This confirms the plan's expectation that Lever's field names differ from
Greenhouse's (`title`/`location.name`/`absolute_url`). One correction versus
the plan's assumption: across all 388 real postings inspected there is no
`updatedAt` field at all (only `createdAt`) — so `createdAt`, converted to
an ISO-8601 string, is used as the closest available stand-in for
`Listing.updated_at`.
"""

import logging
from datetime import UTC, datetime

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.htmltext import strip_html

logger = logging.getLogger(__name__)

LEVER_API_BASE = "https://api.lever.co/v0/postings/{token}"
REQUEST_TIMEOUT = 10.0


class LeverAdapter:
    """Fetches listings from Lever's public unauthenticated postings API."""

    def __init__(self, company: str, token: str) -> None:
        self.company = company
        self.token = token
        self.name = f"{company} (lever)"

    def fetch(self) -> list[Listing]:
        url = LEVER_API_BASE.format(token=self.token)
        try:
            response = httpx.get(url, params={"mode": "json"}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            jobs = response.json()
            return [
                Listing(
                    id=str(job["id"]),
                    title=job["text"],
                    company=self.company,
                    location=job["categories"]["location"],
                    url=job["hostedUrl"],
                    updated_at=_epoch_ms_to_iso(job["createdAt"]),
                    description=strip_html(job.get("description", "")),
                    source="lever",
                )
                for job in jobs
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []


def _epoch_ms_to_iso(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC).isoformat()
