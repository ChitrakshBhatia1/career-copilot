"""Chargebee parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here). Chargebee's
own marketing careers page (chargebee.com/careers/) only links out to
LinkedIn as M7 found -- but a separate subdomain, `jobs.chargebee.com`, runs
a real SAP SuccessFactors-backed career site with its own listings. The
listing page (`/search/`) already contains the job table server-side
(visible in `page.content()` right after `wait_until="domcontentloaded"`),
same as Internshala -- no extra wait needed.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

CHARGEBEE_BASE_URL = "https://jobs.chargebee.com"


def parse_chargebee(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered jobs.chargebee.com/search/ page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each row is parsed independently; a row missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for row in soup.select("tr.data-row"):
        listing = _parse_row(row)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_row(row) -> Listing | None:
    try:
        title_link = row.select_one("td.colTitle a.jobTitle-link")
        title = title_link.get_text(strip=True)
        detail_url = urljoin(CHARGEBEE_BASE_URL, title_link["href"])

        # `.jobLocation`/`.jobFacility` each appear twice per row (a
        # desktop-column version and a phone-only version inside
        # `td.colTitle`) -- scoping to `td.colLocation`/`td.colFacility`
        # picks the desktop column specifically and avoids ambiguity.
        location = row.select_one("td.colLocation span.jobLocation").get_text(strip=True)
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("chargebee: skipping a row with unexpected structure: %s", exc)
        return None

    return Listing(
        # No separate structured ID field exposed -- the absolute detail
        # URL is already unique and stable, so it doubles as the id.
        id=detail_url,
        title=title,
        # Chargebee is the employer itself here (unlike Internshala) --
        # single-employer source, hardcoded per the M8 pattern.
        company="Chargebee",
        location=location,
        url=detail_url,
        # No stable per-posting date field was confirmed in the spike --
        # same deliberate "" left as Internshala/SmartRecruiters/Workday.
        updated_at="",
        # The listing/search page doesn't expose a job description --
        # that only lives on the individual job detail page, one extra
        # fetch per listing this milestone's fetch/parse split doesn't
        # cover, so left blank deliberately (same shape as `updated_at`).
        description="",
        source="chargebee",
    )
