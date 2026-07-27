import logging

import httpx

from career_copilot.discovery.ibm_careers import IBMCareersAdapter
from career_copilot.discovery.models import Listing


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("POST", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    payload = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "abc123hash",
                    "_source": {
                        "title": "Application Developer Intern",
                        "url": "https://careers.ibm.com/careers/JobDetail?jobId=109738",
                        "description": "Join the IBM development team...",
                        "field_keyword_19": "Bengaluru, IN",
                    },
                }
            ],
        }
    }
    monkeypatch.setattr(
        "career_copilot.discovery.ibm_careers.httpx.post",
        lambda url, json, timeout: _make_response(payload),
    )

    adapter = IBMCareersAdapter(company="IBM")
    listings = adapter.fetch()

    assert listings == [
        Listing(
            id="abc123hash",
            title="Application Developer Intern",
            company="IBM",
            location="Bengaluru, IN",
            url="https://careers.ibm.com/careers/JobDetail?jobId=109738",
            # No stable per-posting date field was confirmed in this
            # response shape -- deliberately left "".
            updated_at="",
            description="Join the IBM development team...",
            source="ibm-careers",
        )
    ]


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, json, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.ibm_careers.httpx.post", raise_http_error)

    adapter = IBMCareersAdapter(company="IBM")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing "hits" entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.ibm_careers.httpx.post",
        lambda url, json, timeout: _make_response({}),
    )

    adapter = IBMCareersAdapter(company="IBM")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_defaults_missing_location_and_description_to_empty_string(monkeypatch):
    payload = {
        "hits": {
            "hits": [
                {
                    "_id": "xyz",
                    "_source": {
                        "title": "Intern",
                        "url": "https://careers.ibm.com/careers/JobDetail?jobId=1",
                    },
                }
            ]
        }
    }
    monkeypatch.setattr(
        "career_copilot.discovery.ibm_careers.httpx.post",
        lambda url, json, timeout: _make_response(payload),
    )

    adapter = IBMCareersAdapter(company="IBM")
    listings = adapter.fetch()

    assert listings[0].location == ""
    assert listings[0].description == ""
