"""Tests for `parse_microsoft()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/microsoft_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.microsoft import parse_microsoft

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "microsoft_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_microsoft(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_microsoft(_load_fixture_html())

    first = listings[0]
    assert first.title == "Software Engineer II & Senior Software Engineer"
    # Microsoft is a single-employer source (unlike Internshala/Unstop's
    # per-card employer extraction) -- hardcoded, not parsed from the card.
    assert first.company == "Microsoft"
    assert first.location == "United States, Washington, Redmond"
    # Only a relative "Posted N ago" string is available, kept in
    # `description` rather than fabricated into `updated_at`.
    assert first.description == "Posted 7 days ago"
    assert first.source == "microsoft"


def test_builds_absolute_url_from_relative_href():
    listings = parse_microsoft(_load_fixture_html())

    first = listings[0]
    assert first.url == "https://apply.careers.microsoft.com/careers/job/1970393556939573"


def test_id_is_derived_from_the_detail_url():
    listings = parse_microsoft(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_second_listing_fields_extracted_correctly():
    listings = parse_microsoft(_load_fixture_html())

    second = listings[1]
    assert second.title == "Software Engineer / Senior Software Engineer - .NET Libraries"
    assert second.location == "Czech Republic, Prague, Prague"


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_microsoft(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Nowhere" in listing.location for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_microsoft(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_microsoft("<html><body></body></html>") == []
