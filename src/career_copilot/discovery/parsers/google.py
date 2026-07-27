"""Google careers parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here) against
`https://www.google.com/about/careers/applications/jobs/results?q=software+engineer+intern`.
Unlike the other Big Tech sites in M8, Google's search results are already
present server-side at `wait_until="domcontentloaded"` (same behavior as
Internshala) -- no `wait_until` override needed in `sources.toml`.

Each result is an `<li class="lLd3Je">`. `company` is hardcoded to "Google"
rather than extracted per-card -- unlike Internshala/Unstop (job boards
listing many employers), this source's adapter instance always represents
one employer.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

# Deliberately the `.../applications/` root, not the `/jobs/results` search
# page itself -- each card's `href` is relative to this root (e.g.
# `jobs/results/12345-some-title`), and `urljoin` against the search page's
# own URL would incorrectly collapse the `results` segment. Confirmed via
# the live spike.
GOOGLE_BASE_URL = "https://www.google.com/about/careers/applications/"


def parse_google(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Google careers search-results page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select("li.lLd3Je"):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        title = card.select_one("h3.QJPWVe").get_text(strip=True)
        detail_href = card.select_one("a[href]")["href"]
        detail_url = urljoin(GOOGLE_BASE_URL, detail_href)

        # The location line often lists several offices ("Mountain View, CA,
        # USA; Atlanta, GA, USA; +29 more") -- joined as-is rather than
        # picking one arbitrarily, same tradeoff Internshala's parser
        # doesn't have to make (single-location cards there). The
        # containing `span.pwO9Dc` also wraps a `google-material-icons`
        # `<i>` tag whose ligature text ("place") would otherwise leak into
        # `get_text()` -- extracted out first, same pattern as Apple's a11y
        # label removal in `apple.py`.
        location = ""
        location_el = card.select_one("div.op1BBf span.pwO9Dc")
        if location_el is not None:
            icon = location_el.select_one("i")
            if icon is not None:
                icon.extract()
            location = location_el.get_text(" ", strip=True)

        # "Minimum qualifications" is the only descriptive text present on
        # the card itself (no separate summary/snippet field confirmed).
        description_el = card.select_one("div.Xsxa1e")
        description = description_el.get_text(" ", strip=True) if description_el else ""
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("google: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        # No separate structured ID field confirmed on the card -- the
        # absolute detail URL is unique and stable, so it doubles as the id.
        id=detail_url,
        title=title,
        company="Google",
        location=location,
        url=detail_url,
        # No stable per-posting date field was confirmed in the spike --
        # same deliberate "" left as Internshala/Unstop.
        updated_at="",
        description=description,
        source="google",
    )
