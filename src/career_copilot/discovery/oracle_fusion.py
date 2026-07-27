"""Oracle Fusion Recruiting Cloud provider — public unauthenticated requisition-search API.

M7's earlier research assumed Oracle "runs its own Fusion Cloud Recruiting"
with no usable structured API, budgeting it into M8 (Playwright) instead. A
real live spike against `careers.oracle.com` (July 2026) found the opposite:
the page's *initial*, non-JS-rendered HTML already contains a static
`<base ... data-apibaseurl="https://eeho.fa.us2.oraclecloud.com:443"
data-sitenumber="CX_45001">` tag -- a plain `httpx.get()` with no browser
returns it -- and the Fusion HCM recruiting REST endpoint it points at
(`GET {api_base_url}/hcmRestApi/resources/latest/recruitingCEJobRequisitions`)
is itself unauthenticated JSON, confirmed live with `onlyData=true` +
`expand=requisitionList.secondaryLocations,flexFieldsFacet.values` +
a `finder=findReqs;siteNumber=...` string. No Playwright needed at all.

This is a real multi-tenant ATS platform (many companies run Oracle Fusion
Recruiting Cloud, each with their own `api_base_url`/`site_number`/public
vanity URL), so this adapter is parameterized the same way `WorkdayAdapter`
is for Workday's own multi-tenant CXS API, rather than hardcoding Oracle's
own values inline.

Field mapping confirmed live against real requisitions: `Id`, `Title`,
`PrimaryLocation`, `PostedDate` (already ISO `YYYY-MM-DD`), and
`ShortDescriptionStr` (a real, if often brief, description -- every real
posting inspected had `ExternalResponsibilitiesStr`/
`ExternalQualificationsStr` as `null` in this list-endpoint shape, so
`ShortDescriptionStr` is the only usable description field without a
second per-posting detail request).

One real gotcha worth recording: Oracle's own `keyword` search parameter
matches substrings across the *entire* document, not just the title -- e.g.
searching `keyword=intern` also matches "**Intern**ational Observational
Studies" and "Search Engine **Intern**als", sorted by posting date this
noise dominates the first page. Requesting `sortBy=RELEVANCE` instead
pushes genuine title matches to the top of a single page of results; the
existing shared `matches_keywords()` word-boundary regex in `discover()`
still does the final, precise filtering downstream, same as every other
adapter -- this adapter's `keyword` search is only a pre-filter to keep a
single request's page size sane against Oracle's genuinely huge (2000+)
total requisition count, not a substitute for it.

The candidate-facing job URL isn't returned by this API at all; it's
reconstructed from the site's own client-side router config (confirmed by
reading the site's own minified JS bundle: `"job-full-view":{parent:
"search",url:"/job/{jobId}", ...}`), so `{public_url_base}/job/{Id}` is
used directly.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

REQUISITIONS_PATH = "/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
REQUEST_TIMEOUT = 10.0
# A single page kept modest -- Oracle's total requisition count runs into the
# thousands, and `SEARCH_KEYWORD` + `sortBy=RELEVANCE` below already narrows
# results to a relevant slice rather than needing deep pagination.
PAGE_SIZE = 25
# See module docstring: a pre-filter to keep the single page relevant, not a
# substitute for `matches_keywords()`'s precise word-boundary filtering.
SEARCH_KEYWORD = "intern"
FACETS_LIST = (
    "LOCATIONS;LOB;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;"
    "ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS"
)


class OracleFusionAdapter:
    """Fetches listings from a company's Oracle Fusion Recruiting Cloud API.

    `api_base_url` (e.g. `https://eeho.fa.us2.oraclecloud.com`) and
    `site_number` (e.g. `CX_45001`) are read off the company's own careers
    page (its static `data-apibaseurl`/`data-sitenumber` attributes).
    `public_url_base` is the candidate-facing careers site base (e.g.
    `https://careers.oracle.com/en/sites/jobsearch`), used to build real
    per-posting URLs.
    """

    def __init__(
        self, company: str, api_base_url: str, site_number: str, public_url_base: str
    ) -> None:
        self.company = company
        self.api_base_url = api_base_url.rstrip("/")
        self.site_number = site_number
        self.public_url_base = public_url_base.rstrip("/")
        self.name = f"{company} (oracle-fusion)"

    def fetch(self) -> list[Listing]:
        url = self.api_base_url + REQUISITIONS_PATH
        finder = (
            f"findReqs;siteNumber={self.site_number},facetsList={FACETS_LIST},"
            f"limit={PAGE_SIZE},offset=0,keyword={SEARCH_KEYWORD},sortBy=RELEVANCE"
        )
        params = {
            "onlyData": "true",
            "expand": "requisitionList.secondaryLocations,flexFieldsFacet.values",
            "finder": finder,
        }
        try:
            response = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            requisitions = data["items"][0].get("requisitionList") or []
            return [
                Listing(
                    id=str(job["Id"]),
                    title=job["Title"],
                    company=self.company,
                    location=job.get("PrimaryLocation", ""),
                    url=f"{self.public_url_base}/job/{job['Id']}",
                    updated_at=job.get("PostedDate") or "",
                    description=job.get("ShortDescriptionStr") or "",
                    source="oracle-fusion",
                )
                for job in requisitions
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []
