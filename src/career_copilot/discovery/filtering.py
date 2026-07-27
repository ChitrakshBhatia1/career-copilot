"""Shared title-keyword filter, applied to every adapter's output alike.

Not adapter-specific — Greenhouse, Lever, SmartRecruiters, Workday, and
iCIMS listings all pass through this same function in `discover()` rather
than each adapter reimplementing its own filtering.
"""

import re

from career_copilot.discovery.models import Listing

KEYWORD_PATTERN = re.compile(r"\b(intern|2027)\b", re.IGNORECASE)


def matches_keywords(listing: Listing) -> bool:
    return bool(KEYWORD_PATTERN.search(listing.title))
