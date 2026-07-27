"""Apple careers parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here). Two
findings from that spike drove the config in `sources.toml`:

1. `jobs.apple.com/en-us/search?search=...` alone silently ignores the
   `search` query param and renders the generic unfiltered/default listing
   (confirmed: navigating with only `?search=...` returned unrelated retail
   roles). Adding `&sort=relevance` is required for the search term to
   actually take effect -- confirmed by re-navigating directly to
   `?search=...&sort=relevance` and seeing real, relevant results.
2. Listings are present server-side at `wait_until="domcontentloaded"` (same
   behavior as Internshala/Google) -- no `wait_until` override needed.

Each result is a `<div class="job-list-item job-title">`.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

APPLE_BASE_URL = "https://jobs.apple.com"


def parse_apple(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Apple Jobs search-results page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select("div.job-list-item.job-title"):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        link = card.select_one("h3 a")
        title = link.get_text(strip=True)
        detail_url = urljoin(APPLE_BASE_URL, link["href"])

        # The location block always contains a visually-hidden "Location"
        # a11y label alongside the actual location text -- strip it out
        # (via `.extract()`, mutating this parse-local copy of the tag only)
        # rather than trying to guess which text node is the real value.
        location = ""
        location_el = card.select_one(".job-title-location")
        if location_el is not None:
            a11y_label = location_el.select_one(".a11y")
            if a11y_label is not None:
                a11y_label.extract()
            location = location_el.get_text(strip=True)

        # A real absolute date string (e.g. "Jul 15, 2026") -- kept as-is,
        # same treatment as Amazon's `posting-date`.
        posted_el = card.select_one(".job-posted-date")
        updated_at = posted_el.get_text(strip=True) if posted_el else ""
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("apple: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        # No separate structured ID field confirmed on the card -- the
        # absolute detail URL is unique and stable, so it doubles as the id.
        id=detail_url,
        title=title,
        company="Apple",
        location=location,
        url=detail_url,
        updated_at=updated_at,
        # No description/summary snippet is present on the search-results
        # card itself (only title, team, location, and posted date) --
        # deliberately left blank rather than fabricated, same treatment as
        # Internshala/Unstop leave `updated_at` blank when a field isn't
        # really there.
        description="",
        source="apple",
    )
