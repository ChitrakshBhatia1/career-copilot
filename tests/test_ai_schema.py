import logging

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.schema import build_prompt, parse_analysis_response
from career_copilot.discovery import Listing


def _make_listing() -> Listing:
    return Listing(
        id="1",
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
        description="Build cool things with a great team.",
    )


def test_build_prompt_includes_listing_fields():
    listing = _make_listing()

    prompt = build_prompt(listing)

    assert listing.title in prompt
    assert listing.company in prompt
    assert listing.description in prompt


def test_parse_analysis_response_parses_valid_json():
    raw = (
        '{"visa_sponsorship_mentioned": true, "likely_summer_2027_eligible": false, '
        '"notes": "Looks promising."}'
    )

    result = parse_analysis_response(raw)

    assert result == AIAnalysis(
        visa_sponsorship_mentioned=True,
        likely_summer_2027_eligible=False,
        notes="Looks promising.",
    )


def test_parse_analysis_response_strips_markdown_code_fence():
    raw = (
        "```json\n"
        '{"visa_sponsorship_mentioned": false, "likely_summer_2027_eligible": true, '
        '"notes": "Fits well."}\n'
        "```"
    )

    result = parse_analysis_response(raw)

    assert result == AIAnalysis(
        visa_sponsorship_mentioned=False,
        likely_summer_2027_eligible=True,
        notes="Fits well.",
    )


def test_parse_analysis_response_returns_none_on_malformed_text(caplog):
    with caplog.at_level(logging.ERROR):
        result = parse_analysis_response("not json at all")

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_parse_analysis_response_returns_none_on_missing_required_field(caplog):
    # Missing "notes" entirely -> KeyError inside parse_analysis_response.
    raw = '{"visa_sponsorship_mentioned": true, "likely_summer_2027_eligible": true}'

    with caplog.at_level(logging.ERROR):
        result = parse_analysis_response(raw)

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)
