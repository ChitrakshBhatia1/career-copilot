"""Internshala parser -- pure HTML -> `Listing` extraction, no I/O.

Field locations confirmed via a live spike (not re-derived here): each
listing card is `div.individual_internship`, rendered server-side (visible
in `page.content()` right after `wait_until="domcontentloaded"`, no
scroll/extra wait needed for the first ~50 results), and not blocked by bot
detection.
"""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

INTERNSHALA_BASE_URL = "https://internshala.com"


def parse_internshala(html: str) -> list[Listing]:
    """Extract `Listing`s from a rendered Internshala internship-search page.

    A pure function -- no I/O, no `playwright` import anywhere in this
    module. Each card is parsed independently; a card missing an expected
    element is skipped (logged as a warning) rather than crashing the
    whole page's worth of results, since real HTML across ~50 different
    postings is expected to have some structural inconsistencies.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings: list[Listing] = []
    for card in soup.select("div.individual_internship"):
        listing = _parse_card(card)
        if listing is not None:
            listings.append(listing)
    return listings


def _parse_card(card) -> Listing | None:
    try:
        title_link = card.select_one("a.job-title-href")
        title = title_link.get_text(strip=True)
        detail_url = urljoin(INTERNSHALA_BASE_URL, title_link["href"])

        # Internshala is the job board, not the employer -- the actual
        # hiring company lives in its own element. Easy mistake to make:
        # `company` here must NOT be "Internshala".
        company = card.select_one("p.company-name").get_text(strip=True)

        location_link = card.select_one("div.locations a") or card.select_one(
            ".row-1-item.locations a"
        )
        location = location_link.get_text(strip=True)

        description_el = card.select_one("div.about_job div.text")
        description = description_el.get_text(strip=True)
    except (AttributeError, KeyError, TypeError) as exc:
        logger.warning("internshala: skipping a card with unexpected structure: %s", exc)
        return None

    return Listing(
        # Internshala's card HTML doesn't expose a separate structured ID
        # field -- the absolute detail URL is already unique and stable, so
        # it doubles as the id.
        id=detail_url,
        title=title,
        company=company,
        location=location,
        url=detail_url,
        # No stable per-posting date field was confirmed in the spike --
        # same deliberate "" left as SmartRecruiters/Workday.
        updated_at="",
        description=description,
        source="internshala",
    )
