"""Tests for `parse_apple()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/apple_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.apple import parse_apple

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "apple_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_apple(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_apple(_load_fixture_html())

    first = listings[0]
    assert first.title == "Sr. Software Engineering Manager, Internal Tools"
    # Apple is a single-employer source (unlike Internshala/Unstop's
    # per-card employer extraction) -- hardcoded, not parsed from the card.
    assert first.company == "Apple"
    # The visually-hidden "Location" a11y label must not leak into the
    # extracted location text.
    assert first.location == "San Diego"
    assert first.source == "apple"


def test_builds_absolute_url_from_relative_href():
    listings = parse_apple(_load_fixture_html())

    first = listings[0]
    assert first.url == (
        "https://jobs.apple.com/en-us/details/200672467-3543/"
        "sr-software-engineering-manager-internal-tools?team=SFTWR"
    )


def test_id_is_derived_from_the_detail_url():
    listings = parse_apple(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_real_posted_date_is_kept_in_updated_at():
    listings = parse_apple(_load_fixture_html())

    assert listings[0].updated_at == "Jul 15, 2026"


def test_second_listing_fields_extracted_correctly():
    listings = parse_apple(_load_fixture_html())

    second = listings[1]
    assert second.title == "Mac Product Design Intern"
    assert second.location == "Shanghai"


def test_no_description_snippet_on_card_left_blank_deliberately():
    listings = parse_apple(_load_fixture_html())

    assert all(listing.description == "" for listing in listings)


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_apple(_load_fixture_html())

    assert len(listings) == 2
    assert not any(listing.location == "Nowhere" for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_empty_html_returns_empty_list():
    assert parse_apple("<html><body></body></html>") == []
