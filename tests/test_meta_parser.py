"""Tests for `parse_meta()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/meta_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance, including
why this parser selects structurally (`href` pattern + tag name) rather
than by class, unlike every other M8 parser.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.meta import parse_meta

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "meta_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_meta(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_meta(_load_fixture_html())

    first = listings[0]
    assert first.title == "Software Engineer, Databases"
    # Meta is a single-employer source (unlike Internshala/Unstop's
    # per-card employer extraction) -- hardcoded, not parsed from the card.
    assert first.company == "Meta"
    assert first.location == "Bellevue, WA +1 locations"
    assert first.source == "meta"


def test_id_is_extracted_from_the_job_details_url():
    listings = parse_meta(_load_fixture_html())

    first = listings[0]
    assert first.id == "2342974003201767"
    assert first.url == "https://www.metacareers.com/profile/job_details/2342974003201767"


def test_second_listing_fields_extracted_correctly():
    listings = parse_meta(_load_fixture_html())

    second = listings[1]
    assert second.title == "Software Engineer, Sensors & Computer Vision"
    assert second.location == "Sunnyvale, CA"


def test_bullet_separator_span_not_mistaken_for_location():
    # The "⋅" separator span between location and category tags must not be
    # picked up as the location text.
    listings = parse_meta(_load_fixture_html())

    assert all(listing.location != "⋅" for listing in listings)


def test_no_description_snippet_on_card_left_blank_deliberately():
    listings = parse_meta(_load_fixture_html())

    assert all(listing.description == "" for listing in listings)


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_meta(_load_fixture_html())

    assert len(listings) == 2
    assert not any(listing.location == "Nowhere" for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_meta(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_meta("<html><body></body></html>") == []
