import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.discovery.workday import PAGE_SIZE, WorkdayAdapter


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("POST", "https://example.com"))


def test_fetch_maps_fields_correctly(monkeypatch):
    payload = {
        "total": 1,
        "jobPostings": [
            {
                "title": "Software Engineer, Intern",
                "externalPath": "/job/Remote/Software-Engineer--Intern_R12345",
                "locationsText": "Remote",
                "postedOn": "Posted 3 Days Ago",
                "bulletFields": ["R12345"],
            }
        ],
    }
    monkeypatch.setattr(
        "career_copilot.discovery.workday.httpx.post",
        lambda url, json, timeout: _make_response(payload),
    )

    adapter = WorkdayAdapter(company="Nike", tenant="nike", wd_number="wd1", site="External")
    listings = adapter.fetch()

    assert listings == [
        Listing(
            id="R12345",
            title="Software Engineer, Intern",
            company="Nike",
            location="Remote",
            # Deliberately constructed from {base}/{site} + externalPath --
            # confirmed live to match the detail endpoint's own externalUrl.
            url=(
                "https://nike.wd1.myworkdayjobs.com/External"
                "/job/Remote/Software-Engineer--Intern_R12345"
            ),
            updated_at="Posted 3 Days Ago",
            # Workday's list endpoint doesn't include a description at all;
            # left "" deliberately rather than making a per-posting detail
            # request.
            description="",
            source="workday",
        )
    ]


def test_fetch_falls_back_to_external_path_when_bullet_fields_empty(monkeypatch):
    payload = {
        "total": 1,
        "jobPostings": [
            {
                "title": "Software Engineer, Intern",
                "externalPath": "/job/Remote/Software-Engineer--Intern_R99999",
                "locationsText": "Remote",
                "postedOn": "Posted 1 Day Ago",
                "bulletFields": [],
            }
        ],
    }
    monkeypatch.setattr(
        "career_copilot.discovery.workday.httpx.post",
        lambda url, json, timeout: _make_response(payload),
    )

    adapter = WorkdayAdapter(company="Nike", tenant="nike", wd_number="wd1", site="External")
    listings = adapter.fetch()

    assert listings[0].id == "/job/Remote/Software-Engineer--Intern_R99999"


def test_page_size_stays_within_workdays_confirmed_limit_cap():
    # Confirmed live against a real Workday tenant: the CXS API's `limit`
    # param 400s above 20 with no explanatory message beyond
    # {"errorCode": "HTTP_400"} -- this locks that constraint in so it can't
    # silently regress back to a larger, broken page size.
    assert PAGE_SIZE <= 20


def test_fetch_sends_page_size_as_the_request_limit(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return _make_response({"total": 0, "jobPostings": []})

    monkeypatch.setattr("career_copilot.discovery.workday.httpx.post", fake_post)

    adapter = WorkdayAdapter(company="Nike", tenant="nike", wd_number="wd1", site="External")
    adapter.fetch()

    assert captured["json"]["limit"] == PAGE_SIZE


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, json, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.workday.httpx.post", raise_http_error)

    adapter = WorkdayAdapter(company="Nike", tenant="nike", wd_number="wd1", site="External")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing the "jobPostings" key entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.workday.httpx.post",
        lambda url, json, timeout: _make_response({"total": 0}),
    )

    adapter = WorkdayAdapter(company="Nike", tenant="nike", wd_number="wd1", site="External")
    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
