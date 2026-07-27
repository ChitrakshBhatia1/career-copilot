import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.discovery.smartrecruiters import SmartRecruitersAdapter


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    payload = {
        "offset": 0,
        "limit": 100,
        "totalFound": 1,
        "content": [
            {
                "id": "98765",
                "name": "Software Engineer, Intern",
                "location": {"fullLocation": "New York, NY, US"},
                "releasedDate": "2026-07-01T00:00:00Z",
                "company": {"name": "Equinox"},
            }
        ],
    }
    monkeypatch.setattr(
        "career_copilot.discovery.smartrecruiters.httpx.get",
        lambda url, timeout: _make_response(payload),
    )

    adapter = SmartRecruitersAdapter(company="equinox")
    listings = adapter.fetch()

    assert listings == [
        Listing(
            id="98765",
            title="Software Engineer, Intern",
            company="Equinox",
            location="New York, NY, US",
            # Deliberately constructed from {company}/{id} rather than the
            # internal API "ref" field -- confirmed live to resolve.
            url="https://jobs.smartrecruiters.com/equinox/98765",
            updated_at="2026-07-01T00:00:00Z",
            # SmartRecruiters' list endpoint doesn't include a description at
            # all; left "" deliberately rather than making a per-posting
            # detail request.
            description="",
            source="smartrecruiters",
        )
    ]


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.smartrecruiters.httpx.get", raise_http_error)

    adapter = SmartRecruitersAdapter(company="equinox")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing the "content" key entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.smartrecruiters.httpx.get",
        lambda url, timeout: _make_response({"offset": 0, "limit": 100, "totalFound": 0}),
    )

    adapter = SmartRecruitersAdapter(company="equinox")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
