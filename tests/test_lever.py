import logging
from datetime import UTC, datetime

import httpx

from career_copilot.discovery.lever import LeverAdapter
from career_copilot.discovery.models import Listing


def _make_response(payload: list | dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    created_at_ms = 1751328000000  # 2025-07-01T00:00:00Z
    payload = [
        {
            "id": "abc-123",
            "text": "Software Engineer, Intern",
            "categories": {"location": "Remote"},
            "hostedUrl": "https://jobs.lever.co/anthropic/abc-123",
            "description": "&lt;p&gt;Build cool things&lt;/p&gt;",
            "createdAt": created_at_ms,
        }
    ]
    monkeypatch.setattr(
        "career_copilot.discovery.lever.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    adapter = LeverAdapter(company="Anthropic", token="anthropic")
    listings = adapter.fetch()

    expected_updated_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC).isoformat()
    assert listings == [
        Listing(
            id="abc-123",
            title="Software Engineer, Intern",
            company="Anthropic",
            location="Remote",
            url="https://jobs.lever.co/anthropic/abc-123",
            updated_at=expected_updated_at,
            description="Build cool things",
            source="lever",
        )
    ]


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, params, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.lever.httpx.get", raise_http_error)

    adapter = LeverAdapter(company="Anthropic", token="anthropic")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Postings missing "text" entirely -> KeyError inside fetch().
    payload = [{"id": "abc-123", "categories": {"location": "Remote"}}]
    monkeypatch.setattr(
        "career_copilot.discovery.lever.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    adapter = LeverAdapter(company="Anthropic", token="anthropic")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
