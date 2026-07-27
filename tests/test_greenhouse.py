import logging

import httpx

from career_copilot.discovery.greenhouse import GreenhouseAdapter
from career_copilot.discovery.models import Listing


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
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
        "career_copilot.discovery.greenhouse.httpx.get",
        lambda url, timeout: _make_response(payload),
    )

    adapter = GreenhouseAdapter(company="Anthropic", token="anthropic")
    listings = adapter.fetch()

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


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.greenhouse.httpx.get", raise_http_error)

    adapter = GreenhouseAdapter(company="Anthropic", token="anthropic")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing the "jobs" key entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.greenhouse.httpx.get",
        lambda url, timeout: _make_response({"meta": {}}),
    )

    adapter = GreenhouseAdapter(company="Stripe", token="stripe")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
