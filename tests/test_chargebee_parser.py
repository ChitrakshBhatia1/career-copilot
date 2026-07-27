"""Tests for `parse_chargebee()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/chargebee_sample.html`, a trimmed real excerpt
(2 normal rows + 1 deliberately structurally broken row) captured during the
M8 spike against jobs.chargebee.com -- see that file's header comment for
provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.chargebee import parse_chargebee

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chargebee_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_rows():
    listings = parse_chargebee(_load_fixture_html())

    # 3 rows in the fixture, 1 deliberately broken -- only the 2 valid ones
    # should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_chargebee(_load_fixture_html())

    first = listings[0]
    assert first.title == "Account Executive 1 - Enterprise"
    # Chargebee is the employer itself -- unlike Internshala (a job board),
    # this is a single-employer source, so `company` is always "Chargebee".
    assert first.company == "Chargebee"
    assert first.location == "Remote, US"
    assert first.source == "chargebee"


def test_builds_absolute_url_from_relative_href():
    listings = parse_chargebee(_load_fixture_html())

    first = listings[0]
    assert first.url == (
        "https://jobs.chargebee.com/job/Remote-Account-Executive-1-Enterprise/56776344/"
    )


def test_id_is_derived_from_the_detail_url():
    listings = parse_chargebee(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_second_listing_fields_extracted_correctly():
    listings = parse_chargebee(_load_fixture_html())

    second = listings[1]
    assert second.title == "Enterprise Technical Consultant"
    assert second.location == "Chennai, India"
    assert second.url == (
        "https://jobs.chargebee.com/job/Chennai-India-Enterprise-Technical-Consultant/33449644/"
    )


def test_skips_broken_row_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_chargebee(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Mystery" in listing.location for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_chargebee(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_no_description_on_listing_page_left_blank_deliberately():
    listings = parse_chargebee(_load_fixture_html())

    assert all(listing.description == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_chargebee("<html><body></body></html>") == []
