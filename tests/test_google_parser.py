"""Tests for `parse_google()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/google_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.google import parse_google

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "google_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_google(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_google(_load_fixture_html())

    first = listings[0]
    assert first.title == "Software Engineering Intern, MS, Summer 2027"
    # Google is a single-employer source (unlike Internshala/Unstop's
    # per-card employer extraction) -- hardcoded, not parsed from the card.
    assert first.company == "Google"
    assert "Mountain View, CA, USA" in first.location
    assert "Pursuing a Master's degree" in first.description
    assert first.source == "google"


def test_builds_absolute_url_from_relative_href():
    listings = parse_google(_load_fixture_html())

    first = listings[0]
    assert first.url == (
        "https://www.google.com/about/careers/applications/"
        "jobs/results/95141459539174086-software-engineering-intern-ms-summer-2027"
        "?q=software+engineer+intern"
    )


def test_id_is_derived_from_the_detail_url():
    listings = parse_google(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_second_listing_fields_extracted_correctly():
    listings = parse_google(_load_fixture_html())

    second = listings[1]
    assert second.title == "Software Engineering Intern, BS, Summer 2027"
    assert second.location == "Sunnyvale, CA, USA"


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_google(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Mystery" in listing.title for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_google(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_google("<html><body></body></html>") == []
