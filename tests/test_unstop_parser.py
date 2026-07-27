"""Tests for `parse_unstop()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/unstop_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.unstop import parse_unstop

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "unstop_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_unstop(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_unstop(_load_fixture_html())

    first = listings[0]
    assert first.title == "Business Development Internship"
    # The hiring company, not "Unstop" -- Unstop is the job board, not the
    # employer. Easy mistake to make, explicitly checked here.
    assert first.company == "Nexaris"
    assert first.company != "Unstop"
    assert first.location == "In Office | Ahmedabad, Mumbai"
    assert "Negotiation" in first.description
    assert "B2B Sales" in first.description
    assert first.source == "unstop"


def test_builds_absolute_url_from_relative_href():
    listings = parse_unstop(_load_fixture_html())

    first = listings[0]
    assert first.url.startswith("https://unstop.com/internships/")
    assert first.url == (
        "https://unstop.com/internships/business-development-internship-nexaris-1726361"
    )


def test_id_is_derived_from_the_detail_url():
    listings = parse_unstop(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_second_listing_fields_extracted_correctly():
    listings = parse_unstop(_load_fixture_html())

    second = listings[1]
    assert second.title == "HR Internship"
    assert second.company == "ILP Overseas"
    assert second.location == "Work from Home"
    assert second.description == "Talent Acquisition, Human Resources (HR), Undergraduate"


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_unstop(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Mystery" in listing.title for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_unstop(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_unstop("<html><body></body></html>") == []
