from typing import Protocol

from career_copilot.discovery.models import Listing


class SourceAdapter(Protocol):
    """Structural type for a swappable job-listing source.

    Same idiom as `ai.base.AIProvider` — any class with a `name` attribute
    and a matching `fetch` method satisfies this Protocol without
    inheriting from it (structural typing, unlike Java's `implements`).
    """

    name: str

    def fetch(self) -> list[Listing]: ...
