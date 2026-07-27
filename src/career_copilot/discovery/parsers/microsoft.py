"""Microsoft careers parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here). Two
findings from that spike drove the config in `sources.toml`:

1. `careers.microsoft.com` redirects to `apply.careers.microsoft.com`, and
   that redirect chain drops any `?query=` string on the way -- deep-linking
   a search must target `apply.careers.microsoft.com/careers?query=...`
   directly (confirmed via `curl -sIL`) rather than the public-facing
   `jobs.careers.microsoft.com` host.
2. Zero listing cards are present in the DOM at `wait_until="domcontentloaded"`
   (data loads via a client-side XHR after the React app bootstraps) --
   `wait_until = "networkidle"` is set for this source in `sources.toml`,
   same fix already proven for Unstop.

Each result is a `<div class="cardContainer-GcY1a">`. Note: Microsoft's
frontend uses CSS-modules-style hashed class suffixes (e.g. `-GcY1a`,
`-1aNJK`) that a future redeploy could change -- more fragile than
Internshala's semantic class names, but this is what's actually on the page
today, confirmed live rather than guessed.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

MICROSOFT_BASE_URL = "https://apply.careers.microsoft.com"


def parse_microsoft(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Microsoft careers search-results page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select("div.cardContainer-GcY1a"):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        title = card.select_one(".title-1aNJK").get_text(strip=True)
        link = card.select_one("a.r-link")
        detail_url = urljoin(MICROSOFT_BASE_URL, link["href"])

        location_el = card.select_one(".fieldValue-3kEar")
        location = location_el.get_text(strip=True) if location_el else ""

        # e.g. "Posted an hour ago" / "Posted 13 minutes ago" -- a relative
        # string, not a stable absolute date, so it's kept in `description`
        # rather than `updated_at` (which is reserved for a real parseable
        # timestamp elsewhere in this codebase).
        posted_el = card.select_one(".subData-13Lm1")
        description = posted_el.get_text(strip=True) if posted_el else ""
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("microsoft: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        # No separate structured ID field confirmed on the card -- the
        # absolute detail URL is unique and stable, so it doubles as the id.
        id=detail_url,
        title=title,
        company="Microsoft",
        location=location,
        url=detail_url,
        # No stable absolute-date field was confirmed in the spike (only the
        # relative "Posted an hour ago" string, captured in `description`
        # above) -- same deliberate "" left as Internshala/Unstop/Google.
        updated_at="",
        description=description,
        source="microsoft",
    )
