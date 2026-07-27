import logging

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai_analysis import analyze_new_listings
from career_copilot.discovery import Listing


def _make_listing(id_: str) -> Listing:
    return Listing(
        id=id_,
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url=f"https://example.com/{id_}",
        updated_at="2026-07-01T00:00:00Z",
    )


class _AlwaysSucceedsProvider:
    def __init__(self):
        self.seen: list[Listing] = []

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        self.seen.append(listing)
        return AIAnalysis(
            visa_sponsorship_mentioned=True,
            likely_summer_2027_eligible=True,
            notes="ok",
        )


class _PartialFailureProvider:
    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        if listing.id == "fail":
            return None
        return AIAnalysis(
            visa_sponsorship_mentioned=False,
            likely_summer_2027_eligible=False,
            notes="fine",
        )


def test_analyze_new_listings_returns_empty_dict_when_no_provider_available(monkeypatch, caplog):
    monkeypatch.setattr("career_copilot.ai_analysis.load_provider", lambda: None)

    called = []

    class _ShouldNeverBeCalledProvider:
        def analyze_listing(self, listing):
            called.append(listing)
            return None

    # Sanity: nothing should even attempt to construct/call a provider here,
    # since load_provider() already returned None.
    with caplog.at_level(logging.WARNING):
        result = analyze_new_listings([_make_listing("1")])

    assert result == {}
    assert called == []
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_analyze_new_listings_respects_batch_size(monkeypatch):
    provider = _AlwaysSucceedsProvider()
    monkeypatch.setattr("career_copilot.ai_analysis.load_provider", lambda: provider)

    listings = [_make_listing(str(i)) for i in range(10)]

    result = analyze_new_listings(listings, batch_size=4)

    assert len(provider.seen) == 4
    assert len(result) == 4


def test_analyze_new_listings_skips_listings_where_provider_returns_none(monkeypatch):
    monkeypatch.setattr(
        "career_copilot.ai_analysis.load_provider", lambda: _PartialFailureProvider()
    )

    failing = _make_listing("fail")
    succeeding = _make_listing("succeed")

    result = analyze_new_listings([failing, succeeding])

    assert failing.url not in result
    assert succeeding.url in result
    assert result[succeeding.url] == AIAnalysis(
        visa_sponsorship_mentioned=False,
        likely_summer_2027_eligible=False,
        notes="fine",
    )
