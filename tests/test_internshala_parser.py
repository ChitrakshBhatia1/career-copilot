"""Tests for `parse_internshala()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/internshala_sample.html`, a trimmed real
excerpt (2 normal cards + 1 deliberately structurally broken card) captured
during the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.internshala import parse_internshala

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "internshala_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_internshala(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_internshala(_load_fixture_html())

    first = listings[0]
    assert first.title == "Business Development (Sales)"
    # The hiring company, not "Internshala" -- Internshala is the job board,
    # not the employer. Easy mistake to make, explicitly checked here.
    assert first.company == "Alpever Technologies LLP"
    assert first.company != "Internshala"
    assert first.location == "Jaipur"
    assert "Scout for the leads" in first.description
    assert first.source == "internshala"


def test_builds_absolute_url_from_relative_href():
    listings = parse_internshala(_load_fixture_html())

    first = listings[0]
    assert first.url.startswith("https://internshala.com/internship/detail/")
    assert first.url == (
        "https://internshala.com/internship/detail/"
        "business-development-sales-internship-in-jaipur-at-alpever-technologies-llp1784713757"
    )


def test_id_is_derived_from_the_detail_url():
    listings = parse_internshala(_load_fixture_html())

    first = listings[0]
    assert first.id == first.url


def test_second_listing_fields_extracted_correctly():
    listings = parse_internshala(_load_fixture_html())

    second = listings[1]
    assert second.title == "Data Analytics"
    assert second.company == "Venkatesh"
    # The location `<a>` tag's own text shouldn't pick up trailing sibling
    # text like "(Hybrid)" that lives outside the tag.
    assert second.location == "Secunderabad, Hyderabad"


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_internshala(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Mystery" in listing.title for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_no_stable_updated_at_field_left_blank_deliberately():
    listings = parse_internshala(_load_fixture_html())

    assert all(listing.updated_at == "" for listing in listings)


def test_empty_html_returns_empty_list():
    assert parse_internshala("<html><body></body></html>") == []
