from typing import Protocol

from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing


class AIProvider(Protocol):
    """Structural type for a swappable AI backend.

    Same idiom M7's `SourceAdapter` will later use — any class with a
    matching `analyze_listing` method satisfies this Protocol without
    inheriting from it (structural typing, unlike Java's `implements`).
    """

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None: ...
