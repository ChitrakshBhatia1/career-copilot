"""SmartRecruiters provider — public unauthenticated postings-list API.

Verified via real live unauthenticated requests (July 2026) against
`GET https://api.smartrecruiters.com/v1/companies/{company}/postings`
(confirmed against Equinox, a real SmartRecruiters-hosted company — 679
total postings): the response shape is
`{"offset", "limit", "totalFound", "content": [...]}`, and each item in
`content` has `id`, `name` (title), `location.fullLocation`, `releasedDate`,
and `company.name` (the human-readable company name), but critically **no
description** — the postings-*list* endpoint omits it entirely. The full
description only exists behind a second, per-posting detail request
(`GET .../postings/{id}`, also confirmed live: `jobAd.sections.*.text`).
Given this project's low-request-volume principle, this adapter does not
make that N+1 detail request per listing — `description` is intentionally
left `""` here rather than guessed at (same call as `WorkdayAdapter`).

The list payload's `ref` field is an internal API URL, not a page a human
should be linked to. The real candidate-facing URL
(`https://jobs.smartrecruiters.com/{company}/{id}`) was confirmed live to
resolve correctly without needing the detail request's `postingUrl` slug,
so it's constructed directly here.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

SMARTRECRUITERS_API_BASE = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
SMARTRECRUITERS_PUBLIC_URL = "https://jobs.smartrecruiters.com/{company}/{posting_id}"
REQUEST_TIMEOUT = 10.0


class SmartRecruitersAdapter:
    """Fetches listings from SmartRecruiters' public unauthenticated postings API.

    `company` doubles as both the URL identifier used to query the API and
    the fallback display name — SmartRecruiters' own response conveniently
    includes a proper `company.name` per posting, which is preferred when
    present.
    """

    def __init__(self, company: str) -> None:
        self.company = company
        self.name = f"{company} (smartrecruiters)"

    def fetch(self) -> list[Listing]:
        url = SMARTRECRUITERS_API_BASE.format(company=self.company)
        try:
            response = httpx.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            postings = data["content"]
            return [
                Listing(
                    id=str(job["id"]),
                    title=job["name"],
                    company=job.get("company", {}).get("name", self.company),
                    location=job["location"]["fullLocation"],
                    url=SMARTRECRUITERS_PUBLIC_URL.format(
                        company=self.company, posting_id=job["id"]
                    ),
                    updated_at=job["releasedDate"],
                    description="",
                    source="smartrecruiters",
                )
                for job in postings
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []
