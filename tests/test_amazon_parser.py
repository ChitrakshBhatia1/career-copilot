"""Tests for `parse_amazon()` -- a pure function, no I/O involved.

Runs against `tests/fixtures/amazon_sample.html`, a trimmed real excerpt
(2 normal cards + 1 deliberately structurally broken card) captured during
the M8 spike -- see that file's header comment for provenance.
"""

import logging
from pathlib import Path

from career_copilot.discovery.parsers.amazon import parse_amazon

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "amazon_sample.html"


def _load_fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parses_expected_number_of_valid_cards():
    listings = parse_amazon(_load_fixture_html())

    # 3 cards in the fixture, 1 deliberately broken -- only the 2 valid
    # ones should come back.
    assert len(listings) == 2


def test_extracts_correct_fields_for_first_listing():
    listings = parse_amazon(_load_fixture_html())

    first = listings[0]
    assert first.title == "2027 Software Dev Engineer Intern"
    # Amazon is a single-employer source (unlike Internshala/Unstop's
    # per-card employer extraction) -- hardcoded, not parsed from the card.
    assert first.company == "Amazon"
    assert first.location == "Dublin, IRL"
    assert "Basic qualifications" in first.description
    assert first.source == "amazon"


def test_id_uses_the_real_structured_job_id_not_the_url():
    listings = parse_amazon(_load_fixture_html())

    first = listings[0]
    # Unlike the other four M8 sources, Amazon exposes a real `data-job-id`
    # attribute -- used directly as `id` rather than falling back to the
    # detail URL.
    assert first.id == "10418355"
    assert first.id != first.url


def test_builds_absolute_url_from_relative_href():
    listings = parse_amazon(_load_fixture_html())

    first = listings[0]
    assert first.url == "https://www.amazon.jobs/en/jobs/10418355/2027-software-dev-engineer-intern"


def test_second_listing_fields_extracted_correctly():
    listings = parse_amazon(_load_fixture_html())

    second = listings[1]
    assert second.title == (
        "SEED Engineer Program - Software Development Engineer Intern, 2026 Shenzhen"
    )
    assert second.location == "Shenzhen, CHN"


def test_real_posted_date_is_kept_in_updated_at():
    # Unlike Internshala/Unstop/Google/Microsoft/Apple/Meta, Amazon exposes a
    # real, stable, absolute posted-date string -- confirmed via the spike,
    # so `updated_at` is populated rather than left blank.
    listings = parse_amazon(_load_fixture_html())

    assert listings[0].updated_at == "Posted May 13, 2026"
    assert listings[1].updated_at == "Posted March 26, 2026"


def test_skips_broken_card_without_crashing_and_logs_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        listings = parse_amazon(_load_fixture_html())

    assert len(listings) == 2
    assert not any("Mystery" in listing.title for listing in listings)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_empty_html_returns_empty_list():
    assert parse_amazon("<html><body></body></html>") == []
