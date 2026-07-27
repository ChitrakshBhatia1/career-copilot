"""Orchestration layer for running the configured AI provider over listings.

Separate from the `ai/` package, which holds only the provider abstraction
(Protocol, schema/prompt, and the four concrete provider implementations).
"""

import logging

from career_copilot.ai.factory import load_provider
from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

# A retry-on-parse-failure (below) means a batch can cost up to 2x its size
# in requests worst-case, so this stays well under OpenRouter's 50/day free
# cap even if every listing in the batch needs its retry.
DEFAULT_BATCH_SIZE = 20


def analyze_new_listings(
    listings: list[Listing], batch_size: int = DEFAULT_BATCH_SIZE
) -> dict[str, AIAnalysis]:
    provider = load_provider()
    if provider is None:
        logger.warning("No AI provider configured/available, skipping analysis")
        return {}

    batch = listings[:batch_size]
    results: dict[str, AIAnalysis] = {}
    for listing in batch:
        analysis = provider.analyze_listing(listing)
        if analysis is None:
            # Free-tier models occasionally return malformed JSON (observed
            # live: a corrupted field name on ~1 in 3 real requests to
            # openai/gpt-oss-20b:free) -- one retry recovers most of these
            # without meaningfully affecting the daily request budget.
            analysis = provider.analyze_listing(listing)
        if analysis is not None:
            results[listing.url] = analysis

    logger.info("AI analysis: %d of %d listings analyzed", len(results), len(batch))
    return results
