import logging

import httpx

from career_copilot.discovery import Listing, discover, fetch_source, matches_keywords


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_source_maps_fields_correctly(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": 12345,
                "title": "Software Engineer, Intern",
                "absolute_url": "https://boards.greenhouse.io/anthropic/jobs/12345",
                "location": {"name": "San Francisco, CA"},
                "updated_at": "2026-07-01T00:00:00Z",
                # Greenhouse's real "content" field comes back double-HTML-entity
                # escaped; this fixture exercises that the field mapping runs it
                # through strip_html rather than storing it verbatim.
                "content": "&lt;p&gt;Build cool things&lt;/p&gt;",
            }
        ],
        "meta": {"total": 1},
    }
    monkeypatch.setattr(
        "career_copilot.discovery.httpx.get",
        lambda url, timeout: _make_response(payload),
    )

    listings = fetch_source("Anthropic", "anthropic")

    assert listings == [
        Listing(
            id="12345",
            title="Software Engineer, Intern",
            company="Anthropic",
            location="San Francisco, CA",
            url="https://boards.greenhouse.io/anthropic/jobs/12345",
            updated_at="2026-07-01T00:00:00Z",
            description="Build cool things",
            source="greenhouse",
        )
    ]


def test_matches_keywords_matches_intern_title():
    listing = Listing(
        id="1",
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
    )

    assert matches_keywords(listing) is True


def test_matches_keywords_rejects_unrelated_title():
    listing = Listing(
        id="2",
        title="Senior Backend Engineer",
        company="Stripe",
        location="Remote",
        url="https://example.com/2",
        updated_at="2026-07-01T00:00:00Z",
    )

    assert matches_keywords(listing) is False


def test_matches_keywords_rejects_substring_false_positive():
    # "International" contains "intern" as a substring; the word-boundary
    # regex must not treat that as a match.
    listing = Listing(
        id="3",
        title="International Audit Lead",
        company="Stripe",
        location="Remote",
        url="https://example.com/3",
        updated_at="2026-07-01T00:00:00Z",
    )

    assert matches_keywords(listing) is False


def test_fetch_source_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.httpx.get", raise_http_error)

    with caplog.at_level(logging.ERROR):
        listings = fetch_source("Anthropic", "anthropic")

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_source_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing the "jobs" key entirely -> KeyError inside fetch_source.
    monkeypatch.setattr(
        "career_copilot.discovery.httpx.get",
        lambda url, timeout: _make_response({"meta": {}}),
    )

    with caplog.at_level(logging.ERROR):
        listings = fetch_source("Stripe", "stripe")

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_discover_continues_past_a_failing_source(monkeypatch):
    def fake_get(url, timeout):
        if "anthropic" in url:
            raise httpx.HTTPError("network down")
        return _make_response(
            {
                "jobs": [
                    {
                        "id": 999,
                        "title": "New Grad Software Engineer 2027",
                        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/999",
                        "location": {"name": "Remote"},
                        "updated_at": "2026-07-02T00:00:00Z",
                    }
                ],
                "meta": {"total": 1},
            }
        )

    monkeypatch.setattr("career_copilot.discovery.httpx.get", fake_get)

    listings = discover()

    assert listings == [
        Listing(
            id="999",
            title="New Grad Software Engineer 2027",
            company="Stripe",
            location="Remote",
            url="https://boards.greenhouse.io/stripe/jobs/999",
            updated_at="2026-07-02T00:00:00Z",
            source="greenhouse",
        )
    ]
