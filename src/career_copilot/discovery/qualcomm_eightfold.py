"""Qualcomm careers provider — Eightfold.ai's public unauthenticated search API.

M7's earlier research noted Qualcomm "migrated to Eightfold.ai" and left it
for M8 to determine whether an Eightfold-hosted page happens to be
scrapable. A real live spike (July 2026) against `careers.qualcomm.com`
found a plain, unauthenticated JSON API behind it -- confirmed by watching
Playwright's own network traffic, then reproduced with zero Playwright
involvement via a bare `httpx.get()`:
`GET https://careers.qualcomm.com/api/pcsx/search?domain=qualcomm.com&query=intern&start=0`.
No login, no session cookie, no CSRF token required for this endpoint.

Eightfold is a real multi-tenant ATS platform (many companies run their
careers site on it, each under their own `domain`), so `domain` is a
constructor argument here rather than hardcoded, the same reusability call
already made for `WorkdayAdapter`/`OracleFusionAdapter`.

Response shape confirmed live: `data.data.positions[*]` with `id`, `name`
(title), `locations` (a list -- joined here since `Listing.location` is a
single string), `postedTs` (epoch *seconds*, unlike Lever's milliseconds),
`positionUrl` (a relative path, joined against the site's own origin), and
`department`. The search-*list* endpoint doesn't include a description at
all -- the full text only exists behind a separate per-posting
`position_details` request, confirmed live but intentionally not called
here for the same low-request-volume reason `SmartRecruitersAdapter`/
`WorkdayAdapter` skip their own per-posting detail calls.

Only the first page (Eightfold hard-caps page size at 10 regardless of any
`num`/`limit`/`pageSize`/`rows` param tried live) is fetched, same
single-page-only precedent as `WorkdayAdapter`.
"""

import logging
from datetime import UTC, datetime

import httpx

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

EIGHTFOLD_SEARCH_URL = "https://careers.{domain}/api/pcsx/search"
EIGHTFOLD_PUBLIC_URL = "https://careers.{domain}{position_url}"
REQUEST_TIMEOUT = 10.0
SEARCH_KEYWORD = "intern"


class QualcommEightfoldAdapter:
    """Fetches listings from an Eightfold-hosted careers search API.

    `domain` is the company's own domain as Eightfold expects it (e.g.
    `"qualcomm.com"`), used both as a query param and to build the
    `careers.{domain}` origin for public URLs.
    """

    def __init__(self, company: str, domain: str) -> None:
        self.company = company
        self.domain = domain
        self.name = f"{company} (eightfold)"

    def fetch(self) -> list[Listing]:
        url = EIGHTFOLD_SEARCH_URL.format(domain=self.domain)
        params = {"domain": self.domain, "query": SEARCH_KEYWORD, "start": 0}
        try:
            response = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            positions = data["data"]["positions"]
            return [
                Listing(
                    id=str(job["id"]),
                    title=job["name"],
                    company=self.company,
                    location=", ".join(job.get("locations", [])),
                    url=EIGHTFOLD_PUBLIC_URL.format(
                        domain=self.domain, position_url=job["positionUrl"]
                    ),
                    updated_at=_epoch_s_to_iso(job.get("postedTs")),
                    description="",
                    source="eightfold",
                )
                for job in positions
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []


def _epoch_s_to_iso(epoch_s: int | None) -> str:
    if epoch_s is None:
        return ""
    return datetime.fromtimestamp(epoch_s, tz=UTC).isoformat()
