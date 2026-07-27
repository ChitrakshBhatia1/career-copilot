import logging
from datetime import UTC, datetime

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.discovery.qualcomm_eightfold import QualcommEightfoldAdapter


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    posted_ts = 1784160000  # 2026-07-16T00:00:00Z (epoch seconds, not ms)
    payload = {
        "data": {
            "positions": [
                {
                    "id": 446719785836,
                    "name": "Interim Engineering Intern_2027_SW",
                    "locations": ["Bangalore, India", "Hyderabad, India"],
                    "postedTs": posted_ts,
                    "department": "Interim Engineering Intern - SW",
                    "positionUrl": "/careers/job/446719785836",
                }
            ]
        }
    }
    monkeypatch.setattr(
        "career_copilot.discovery.qualcomm_eightfold.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    adapter = QualcommEightfoldAdapter(company="Qualcomm", domain="qualcomm.com")
    listings = adapter.fetch()

    expected_updated_at = datetime.fromtimestamp(posted_ts, tz=UTC).isoformat()
    assert listings == [
        Listing(
            id="446719785836",
            title="Interim Engineering Intern_2027_SW",
            company="Qualcomm",
            location="Bangalore, India, Hyderabad, India",
            url="https://careers.qualcomm.com/careers/job/446719785836",
            updated_at=expected_updated_at,
            # The search-list endpoint doesn't include a description at all;
            # left "" deliberately rather than making a per-posting detail
            # request (same call as SmartRecruiters/Workday).
            description="",
            source="eightfold",
        )
    ]


def test_fetch_handles_missing_posted_ts(monkeypatch):
    payload = {
        "data": {
            "positions": [
                {
                    "id": 1,
                    "name": "Intern",
                    "locations": ["Remote"],
                    "positionUrl": "/careers/job/1",
                }
            ]
        }
    }
    monkeypatch.setattr(
        "career_copilot.discovery.qualcomm_eightfold.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    adapter = QualcommEightfoldAdapter(company="Qualcomm", domain="qualcomm.com")
    listings = adapter.fetch()

    assert listings[0].updated_at == ""


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, params, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.qualcomm_eightfold.httpx.get", raise_http_error)

    adapter = QualcommEightfoldAdapter(company="Qualcomm", domain="qualcomm.com")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing "data" entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.qualcomm_eightfold.httpx.get",
        lambda url, params, timeout: _make_response({}),
    )

    adapter = QualcommEightfoldAdapter(company="Qualcomm", domain="qualcomm.com")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
