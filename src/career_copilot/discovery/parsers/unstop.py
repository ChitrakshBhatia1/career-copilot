"""Unstop parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here): Unstop's
`/internships` page is a client-side rendered Angular SPA -- zero listing
cards are present at `wait_until="domcontentloaded"` (data loads via a
client-side XHR after JS bootstraps), so this source is configured in
`sources.toml` with `wait_until = "networkidle"` to give the SPA time to
render before `page.content()` is captured.

Each real internship card is an `<a itemprop="itemListElement" ...>` inside
an `<app-competition-listing>` element. Unstop's `/internships` page also
renders a handful of "Featured" `<app-featured-opportunity-tile>` cards
(sponsored competitions, not internships) -- those deliberately lack the
`itemprop="itemListElement"` attribute, so selecting on it naturally
excludes them without needing a separate tag/text check.
"""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

UNSTOP_BASE_URL = "https://unstop.com"

_WHITESPACE_RE = re.compile(r"\s+")


def parse_unstop(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Unstop internship-search page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the whole
    page's worth of results, since real HTML across ~20 different postings
    is expected to have some structural inconsistencies.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select('a[itemprop="itemListElement"]'):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        title_el = card.select_one('[itemprop="name"]')
        title = title_el.get_text(strip=True)
        detail_url = urljoin(UNSTOP_BASE_URL, card["href"])

        # Unstop is the job board, not the employer -- the actual hiring
        # company lives in its own element. Easy mistake to make: `company`
        # here must NOT be "Unstop".
        company = card.select_one("p.single-wrap").get_text(strip=True)

        location_el = card.select_one("span.job_location")
        # Raw text looks like "In Office |  Noida" or "Work from Home" --
        # collapse the internal whitespace runs left by Angular's rendered
        # whitespace/comment nodes rather than guessing a fixed split point.
        location = _WHITESPACE_RE.sub(" ", location_el.get_text(" ", strip=True))

        # No full job-description text is present on the listing card itself
        # (only skill-tag chips) -- join those as a lightweight substitute
        # rather than fabricating a description that isn't there.
        description = ", ".join(
            tag.get_text(strip=True) for tag in card.select("div.skill_list span.chip_text")
        )
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("unstop: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        # Unstop's card HTML doesn't expose a separate structured ID field --
        # the absolute detail URL is already unique and stable, so it doubles
        # as the id.
        id=detail_url,
        title=title,
        company=company,
        location=location,
        url=detail_url,
        # No stable per-posting date field was confirmed in the spike -- same
        # deliberate "" left as Internshala/SmartRecruiters/Workday.
        updated_at="",
        description=description,
        source="unstop",
    )
