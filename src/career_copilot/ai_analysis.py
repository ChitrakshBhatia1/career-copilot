"""Orchestration layer for running the configured AI provider over listings.

Separate from the `ai/` package, which holds only the provider abstraction
(Protocol, schema/prompt, and the four concrete provider implementations).
"""

import logging

from career_copilot.ai.factory import load_provider
from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 40


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
        if analysis is not None:
            results[listing.url] = analysis

    logger.info("AI analysis: %d of %d listings analyzed", len(results), len(batch))
    return results
