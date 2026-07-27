"""Workday provider — CXS ("Candidate Experience Site") public search API.

Verified via real live unauthenticated POST requests (July 2026) against two
real Workday-hosted career sites (`workday.wd5.myworkdayjobs.com/Workday`
and `salesforce.wd12.myworkdayjobs.com/External_Career_Site`):
`POST https://{tenant}.{wd_number}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
with JSON body `{"appliedFacets": {}, "limit": N, "offset": 0, "searchText": ""}`
returns `{"total": N, "jobPostings": [{"title", "externalPath",
"locationsText", "postedOn", "bulletFields": [...]}]}`.

There is no description field and no absolute URL in this list response.
The public URL is reconstructed from `externalPath` — confirmed live by
also hitting a real per-posting detail endpoint
(`.../wday/cxs/{tenant}/{site}{externalPath}`), whose own `externalUrl`
field matches exactly `{tenant}.{wd_number}.myworkdayjobs.com/{site}` +
`externalPath`. `description` is intentionally left `""` here rather than
making a second, per-posting detail request for every listing (same
low-request-volume call as `SmartRecruitersAdapter`).

The `wd{N}` subdomain pod number varies per company and isn't derivable
from the tenant name alone (confirmed: `nike.wd1/.wd3/.wd5` all failed a
real probe) — it's a required constructor argument. The follow-up research
pass has to discover the tenant/wd_number/site triple per company, e.g. by
loading the company's real careers page and reading it out of the URL.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

WORKDAY_JOBS_API_BASE = (
    "https://{tenant}.{wd_number}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
)
WORKDAY_PUBLIC_BASE = "https://{tenant}.{wd_number}.myworkdayjobs.com/{site}"
REQUEST_TIMEOUT = 10.0
# Workday's CXS API hard-caps `limit` at 20 -- confirmed live (25+ returns a
# 400 with no explanatory message, just {"errorCode": "HTTP_400"}).
PAGE_SIZE = 20


class WorkdayAdapter:
    """Fetches listings from a company's Workday CXS job-search API.

    `tenant` is the Workday subdomain slug (e.g. "nike"), `wd_number` is the
    numbered pod subdomain segment (e.g. "wd1", "wd5" — varies per company),
    and `site` is the CXS career-site id (e.g. "External"). `company` is the
    human-readable display name stored on each `Listing` — Workday's list
    API doesn't return one.
    """

    def __init__(self, company: str, tenant: str, wd_number: str, site: str) -> None:
        self.company = company
        self.tenant = tenant
        self.wd_number = wd_number
        self.site = site
        self.name = f"{company} (workday)"

    def fetch(self) -> list[Listing]:
        url = WORKDAY_JOBS_API_BASE.format(
            tenant=self.tenant, wd_number=self.wd_number, site=self.site
        )
        public_base = WORKDAY_PUBLIC_BASE.format(
            tenant=self.tenant, wd_number=self.wd_number, site=self.site
        )
        payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": 0, "searchText": ""}
        try:
            response = httpx.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            postings = data["jobPostings"]
            return [
                Listing(
                    id=_posting_id(job),
                    title=job["title"],
                    company=self.company,
                    location=job.get("locationsText", ""),
                    url=public_base + job["externalPath"],
                    updated_at=job.get("postedOn", ""),
                    description="",
                    source="workday",
                )
                for job in postings
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []


def _posting_id(job: dict) -> str:
    bullet_fields = job.get("bulletFields") or []
    return str(bullet_fields[0]) if bullet_fields else str(job["externalPath"])
