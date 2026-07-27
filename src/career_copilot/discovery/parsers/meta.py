"""Meta careers parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here) against
`https://www.metacareers.com/jobs?q=software+engineer+intern`. Two findings
drove this parser's approach:

1. Zero listing cards are present at `wait_until="domcontentloaded"` --
   `wait_until = "networkidle"` is set for this source in `sources.toml`,
   same fix already proven for Unstop/Microsoft/Amazon.
2. Meta's frontend renders every element's `class` attribute as a long list
   of meaningless atomic/utility hashes (Meta's internal "StyleX"-style CSS,
   e.g. `class="x1i10hfl x1qjc9v5 xjbqb8w ..."`) with no semantic class name
   anywhere in the card -- unlike every other M8 source (Google/Microsoft/
   Amazon/Apple/Internshala/Unstop), which all have at least one stable,
   human-readable class or `data-testid` to select on. Selecting by class is
   not viable here at all. Instead this parser selects structurally: each
   listing is an `<a href="/profile/job_details/<id>">` (a stable URL
   pattern, confirmed live), with the title in its first `<h3>` and the
   location in the first non-empty `<span>` inside it. More fragile than
   the other four parsers in principle (a URL-pattern or DOM-order change
   would break it, where the others would at least survive a class rename),
   but it's what's actually reliably present today.
"""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

META_BASE_URL = "https://www.metacareers.com"

_JOB_ID_RE = re.compile(r"/profile/job_details/(\d+)")


def parse_meta(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Meta Careers search-results page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select('a[href*="/profile/job_details/"]'):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        href = card["href"]
        job_id_match = _JOB_ID_RE.search(href)
        job_id = job_id_match.group(1)
        detail_url = urljoin(META_BASE_URL, href)

        title = card.select_one("h3").get_text(strip=True)

        # The first non-empty `<span>` inside the card is always the
        # location (e.g. "Bellevue, WA +1 locations") -- confirmed via the
        # spike across several cards; later spans are job-category/team tags
        # duplicated for accessibility, not additional location data.
        location = ""
        for span in card.select("span"):
            text = span.get_text(strip=True)
            if text and text != "⋅":
                location = text
                break
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("meta: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        id=job_id,
        title=title,
        company="Meta",
        location=location,
        url=detail_url,
        # No stable per-posting date field was confirmed in the spike --
        # same deliberate "" left as Internshala/Unstop/Google/Apple's
        # relative-only equivalents.
        updated_at="",
        # No description/summary snippet is present on the search-results
        # card itself (only title, location, and category tags) --
        # deliberately left blank rather than fabricated.
        description="",
        source="meta",
    )
