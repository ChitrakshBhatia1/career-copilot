import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from career_copilot.discovery import Listing

DEFAULT_PREFERENCES_PATH = Path("config/preferences.toml")


@dataclass(frozen=True)
class Preferences:
    role_keywords: list[str]
    priority_cities: list[str]
    priority_weight: int
    exclude_keywords: list[str]


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)


@lru_cache(maxsize=None)
def _compiled_patterns(keywords: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    """Compile each keyword into a word-boundary regex, cached per keyword set.

    `rank_listings` calls `score_listing` once per stored listing with the
    same `Preferences` instance, so caching here means the exclude/role
    regexes are compiled once per run instead of once per listing.
    """
    return tuple(_keyword_pattern(kw) for kw in keywords)


def load_preferences(path: Path = DEFAULT_PREFERENCES_PATH) -> Preferences:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    return Preferences(
        role_keywords=data["role"]["keywords"],
        priority_cities=data["location"]["priority_cities"],
        priority_weight=data["location"]["priority_weight"],
        exclude_keywords=data["exclude"]["keywords"],
    )


def score_listing(listing: Listing, preferences: Preferences) -> int | None:
    exclude_patterns = _compiled_patterns(tuple(preferences.exclude_keywords))
    if any(pattern.search(listing.title) for pattern in exclude_patterns):
        return None

    role_patterns = _compiled_patterns(tuple(preferences.role_keywords))
    score = sum(1 for pattern in role_patterns if pattern.search(listing.title))

    if any(city.lower() in listing.location.lower() for city in preferences.priority_cities):
        score += preferences.priority_weight

    return score


def rank_listings(listings: list[Listing], preferences: Preferences) -> list[tuple[Listing, int]]:
    scored = []
    for listing in listings:
        score = score_listing(listing, preferences)
        if score is not None:
            scored.append((listing, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
