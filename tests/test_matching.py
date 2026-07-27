from pathlib import Path

from career_copilot.discovery import Listing
from career_copilot.matching import (
    Preferences,
    load_preferences,
    rank_listings,
    score_listing,
)

# Independent of config/preferences.toml on purpose: constructing Preferences
# directly here means these scoring tests keep working even if the user edits
# their real preferences file later.
PREFS = Preferences(
    role_keywords=["Software Engineer", "Intern"],
    priority_cities=["Bengaluru", "Bangalore"],
    priority_weight=3,
    exclude_keywords=["Senior", "Manager"],
)


def _make_listing(title: str, location: str = "Remote", id_: str = "1") -> Listing:
    return Listing(
        id=id_,
        title=title,
        company="Anthropic",
        location=location,
        url=f"https://example.com/{id_}",
        updated_at="2026-07-01T00:00:00Z",
    )


def test_score_listing_strong_match_beats_weaker_match():
    strong = _make_listing("Software Engineer, Intern", location="Bengaluru")
    weak = _make_listing("Software Engineer", location="Remote")

    strong_score = score_listing(strong, PREFS)
    weak_score = score_listing(weak, PREFS)

    # 2 role-keyword matches ("Software Engineer" + "Intern") + priority
    # city bonus (3) = 5.
    assert strong_score == 5
    assert strong_score > weak_score


def test_score_listing_no_keyword_match_scores_zero():
    listing = _make_listing("Marketing Coordinator", location="Remote")

    assert score_listing(listing, PREFS) == 0


def test_score_listing_partial_match_counts_keywords_without_location_bonus():
    listing = _make_listing("Summer Intern", location="Remote")

    assert score_listing(listing, PREFS) == 1


def test_score_listing_excludes_on_exclude_keyword():
    listing = _make_listing("Senior Software Engineer", location="Bengaluru")

    assert score_listing(listing, PREFS) is None


def test_score_listing_exclude_keyword_is_word_boundary_not_substring():
    # "Managerial" contains "Manager" as a substring; the word-boundary
    # regex must not treat that as an exclude match (mirrors the same
    # false-positive concern covered for role keywords in test_discovery.py).
    listing = _make_listing("Managerial Software Engineer Intern", location="Remote")

    assert score_listing(listing, PREFS) == 2


def test_rank_listings_drops_excluded_listings_entirely():
    kept = _make_listing("Software Engineer, Intern", location="Remote", id_="1")
    excluded = _make_listing("Senior Software Engineer", location="Remote", id_="2")

    ranked = rank_listings([kept, excluded], PREFS)

    ranked_listings = [listing for listing, _score in ranked]
    assert kept in ranked_listings
    assert excluded not in ranked_listings
    assert len(ranked) == 1


def test_rank_listings_sorts_descending_by_score():
    low = _make_listing("Marketing Coordinator", location="Remote", id_="low")
    high = _make_listing("Software Engineer, Intern", location="Bengaluru", id_="high")
    mid = _make_listing("Intern", location="Remote", id_="mid")

    ranked = rank_listings([low, high, mid], PREFS)

    assert [listing.id for listing, _score in ranked] == ["high", "mid", "low"]
    assert [score for _listing, score in ranked] == [5, 1, 0]


def test_load_preferences_reads_real_config_file():
    repo_root = Path(__file__).resolve().parent.parent
    prefs = load_preferences(repo_root / "config" / "preferences.toml")

    assert len(prefs.role_keywords) > 0
    assert "Intern" in prefs.role_keywords
    assert len(prefs.priority_cities) > 0
    assert "Senior" in prefs.exclude_keywords
