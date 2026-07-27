import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
REQUEST_TIMEOUT = 10.0

SOURCES = [
    ("Anthropic", "anthropic"),
    ("Stripe", "stripe"),
]

KEYWORD_PATTERN = re.compile(r"\b(intern|2027)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Listing:
    id: str
    title: str
    company: str
    location: str
    url: str
    updated_at: str


def fetch_source(company: str, token: str) -> list[Listing]:
    url = GREENHOUSE_API_BASE.format(token=token)
    try:
        response = httpx.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        jobs = data["jobs"]
        return [
            Listing(
                id=str(job["id"]),
                title=job["title"],
                company=company,
                location=job["location"]["name"],
                url=job["absolute_url"],
                updated_at=job["updated_at"],
            )
            for job in jobs
        ]
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch listings for %s: %s", company, exc)
        return []
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Failed to parse listings for %s: %s", company, exc)
        return []


def matches_keywords(listing: Listing) -> bool:
    return bool(KEYWORD_PATTERN.search(listing.title))


def discover() -> list[Listing]:
    all_listings: list[Listing] = []
    for company, token in SOURCES:
        listings = fetch_source(company, token)
        logger.info("%s: found %d listings", company, len(listings))
        all_listings.extend(listings)

    filtered = [listing for listing in all_listings if matches_keywords(listing)]
    logger.info(
        "discover: %d listings found across %d sources, %d passed keyword filter",
        len(all_listings),
        len(SOURCES),
        len(filtered),
    )
    return filtered
