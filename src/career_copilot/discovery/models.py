from dataclasses import dataclass


@dataclass(frozen=True)
class Listing:
    id: str
    title: str
    company: str
    location: str
    url: str
    updated_at: str
    # Defaulted so the ~35 existing keyword-arg call sites across the test
    # suite don't need touching for this plumbing milestone.
    description: str = ""
    source: str = "unknown"
