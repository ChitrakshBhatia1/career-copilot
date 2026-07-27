"""Greenhouse provider — public unauthenticated Job Board API.

Unchanged from the original single-file `discovery.py`'s `fetch_source()`,
just reshaped into a class implementing `SourceAdapter`.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.htmltext import strip_html

logger = logging.getLogger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
REQUEST_TIMEOUT = 10.0


class GreenhouseAdapter:
    """Fetches listings from Greenhouse's public unauthenticated Job Board API."""

    def __init__(self, company: str, token: str) -> None:
        self.company = company
        self.token = token
        self.name = f"{company} (greenhouse)"

    def fetch(self) -> list[Listing]:
        url = GREENHOUSE_API_BASE.format(token=self.token) + "?content=true"
        try:
            response = httpx.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            jobs = data["jobs"]
            return [
                Listing(
                    id=str(job["id"]),
                    title=job["title"],
                    company=self.company,
                    location=job["location"]["name"],
                    url=job["absolute_url"],
                    updated_at=job["updated_at"],
                    description=strip_html(job.get("content", "")),
                    source="greenhouse",
                )
                for job in jobs
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []
