"""Zerodha careers provider — direct fetch of its own in-house `/api/jobs`.

M7's earlier research flagged Zerodha as running "a fully custom in-house
API" behind a Vite/React SPA, out of scope for M7 but worth a quick check
here per M8's plan. A real live spike (July 2026) confirmed the in-house
API is itself directly fetchable: `GET https://careers.zerodha.com/api/jobs`
returns `{"count", "data", "success"}` with no auth, no session cookie, no
CSRF token -- reproduced with a bare `httpx.get()`, zero Playwright
involvement. This is a plain-httpx adapter, not a `PlaywrightAdapter` +
parser, following the same "API wherever one genuinely exists" call M7
already established for Greenhouse/Lever/SmartRecruiters/Workday.

At spike time, `data` was an empty list -- the site's own rendered page
confirms this isn't a broken request, it displays "There are no job
openings currently." in plain text. The exact per-job field names were
still confirmed by reading Zerodha's own minified frontend JS bundle (the
Vue component that renders `g.value = t.data` from this same endpoint):
each job is rendered via `e.name` (a unique slug, doubling as the apply-flow
id), `e.job_title`, `e.location`, `e.location_type`, and `e.description`
(rendered via `v-html`, so real HTML -- run through `strip_html()` here,
the same treatment Greenhouse/Lever descriptions get). There is no
per-posting date field anywhere in the rendered template, so `updated_at`
is deliberately left `""`, same call as `Internshala`/`SmartRecruiters`.

Zerodha's own "Apply" button doesn't link to a separate per-job page at
all -- it opens an in-page application modal keyed by `e.name` -- so there
is no real per-listing permalink to point `Listing.url` at. The careers
page itself is used for every listing, same spirit as leaving a field
blank when the site genuinely doesn't expose one.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.htmltext import strip_html

logger = logging.getLogger(__name__)

ZERODHA_JOBS_API = "https://careers.zerodha.com/api/jobs"
ZERODHA_CAREERS_URL = "https://careers.zerodha.com/"
REQUEST_TIMEOUT = 10.0


class ZerodhaAdapter:
    """Fetches listings from Zerodha's own in-house careers API."""

    def __init__(self, company: str) -> None:
        self.company = company
        self.name = f"{company} (zerodha-api)"

    def fetch(self) -> list[Listing]:
        try:
            response = httpx.get(ZERODHA_JOBS_API, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            jobs = data["data"]
            return [
                Listing(
                    id=str(job["name"]),
                    title=job["job_title"],
                    company=self.company,
                    location=job.get("location", ""),
                    # No stable per-job permalink exists -- see module
                    # docstring: "Apply" opens an in-page modal, not a page.
                    url=ZERODHA_CAREERS_URL,
                    updated_at="",
                    description=strip_html(job.get("description", "")),
                    source="zerodha-api",
                )
                for job in jobs
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []
