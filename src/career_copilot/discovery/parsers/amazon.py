"""Amazon careers parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here) against
`https://www.amazon.jobs/en/search?base_query=software+engineer+intern`.
Zero listing cards are present at `wait_until="domcontentloaded"` (the
initial response is a lightweight shell; listings load via a client-side
XHR) -- `wait_until = "networkidle"` is set for this source in
`sources.toml`, same fix already proven for Unstop/Microsoft.

Each result is a `<div class="job-tile">`, with semantic (non-hashed) class
names -- closer to Internshala's markup than Microsoft's CSS-modules
classes. Notably, Amazon is the only one of the five M8 Big Tech sources
that exposes a real, stable, absolute posted-date string per card (e.g.
"Posted May 13, 2026"), so `updated_at` is populated here rather than left
blank.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

AMAZON_BASE_URL = "https://www.amazon.jobs"


def parse_amazon(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Amazon Jobs search-results page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select("div.job-tile"):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        link = card.select_one("h3.job-title a.job-link")
        title = link.get_text(strip=True)
        detail_url = urljoin(AMAZON_BASE_URL, link["href"])

        # Unlike the other four M8 sources, Amazon exposes a real structured
        # job ID via `data-job-id` on the inner `div.job` -- confirmed via
        # the spike -- so it's used as `id` directly rather than falling
        # back to the detail URL.
        job_id = card.select_one("div.job")["data-job-id"]

        # The first `li.text-nowrap` in the location list is always the
        # primary location -- confirmed via the spike across multi-location
        # cards (e.g. "Berlin, BE, DEU + 3 other locations"), where the
        # "+N other locations" and "Job ID: ..." siblings deliberately lack
        # that class.
        location_el = card.select_one(".location-and-id li.text-nowrap")
        location = location_el.get_text(strip=True) if location_el else ""

        description_el = card.select_one("div.qualifications-preview")
        description = description_el.get_text(" ", strip=True) if description_el else ""

        # A real absolute date string (e.g. "Posted May 13, 2026") -- unlike
        # Internshala/Unstop/Google/Microsoft, kept as-is rather than left
        # blank, since it's an actually confirmed stable field here.
        posted_el = card.select_one("span.posting-date")
        updated_at = posted_el.get_text(strip=True) if posted_el else ""
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("amazon: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        id=job_id,
        title=title,
        company="Amazon",
        location=location,
        url=detail_url,
        updated_at=updated_at,
        description=description,
        source="amazon",
    )
