import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.discovery.zerodha import ZerodhaAdapter


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    payload = {
        "success": True,
        "count": 1,
        "data": [
            {
                "name": "software-engineer-backend",
                "job_title": "Software Engineer - Backend",
                "location": "Bangalore",
                "location_type": "onsite",
                "description": "<p>Build and scale our trading platform.</p>",
            }
        ],
    }
    monkeypatch.setattr(
        "career_copilot.discovery.zerodha.httpx.get",
        lambda url, timeout: _make_response(payload),
    )

    adapter = ZerodhaAdapter(company="Zerodha")
    listings = adapter.fetch()

    assert listings == [
        Listing(
            id="software-engineer-backend",
            title="Software Engineer - Backend",
            company="Zerodha",
            location="Bangalore",
            # No per-job permalink exists -- "Apply" opens an in-page modal,
            # not a page -- so the careers page itself is used.
            url="https://careers.zerodha.com/",
            updated_at="",
            description="Build and scale our trading platform.",
            source="zerodha-api",
        )
    ]


def test_fetch_returns_empty_list_when_no_openings(monkeypatch):
    # Confirmed live (July 2026): the endpoint is real and reachable, it
    # currently just has zero postings -- this must not be logged as an
    # error, only as a normal empty result.
    monkeypatch.setattr(
        "career_copilot.discovery.zerodha.httpx.get",
        lambda url, timeout: _make_response({"count": 0, "data": [], "success": True}),
    )

    adapter = ZerodhaAdapter(company="Zerodha")
    listings = adapter.fetch()

    assert listings == []


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.zerodha.httpx.get", raise_http_error)

    adapter = ZerodhaAdapter(company="Zerodha")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing "data" entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.zerodha.httpx.get",
        lambda url, timeout: _make_response({"success": True}),
    )

    adapter = ZerodhaAdapter(company="Zerodha")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
