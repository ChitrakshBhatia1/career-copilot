import logging

import httpx

from career_copilot.discovery.models import Listing
from career_copilot.discovery.oracle_fusion import OracleFusionAdapter


def _make_response(payload: dict):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://example.com"))


def _adapter() -> OracleFusionAdapter:
    return OracleFusionAdapter(
        company="Oracle",
        api_base_url="https://eeho.fa.us2.oraclecloud.com",
        site_number="CX_45001",
        public_url_base="https://careers.oracle.com/en/sites/jobsearch",
    )


def test_fetch_maps_fields_correctly(monkeypatch):
    payload = {
        "items": [
            {
                "requisitionList": [
                    {
                        "Id": "341156",
                        "Title": "OCI Software Engineer Intern",
                        "PrimaryLocation": "Bengaluru, India",
                        "PostedDate": "2026-07-27",
                        "ShortDescriptionStr": "Join our cloud engineering team.",
                    }
                ]
            }
        ]
    }
    monkeypatch.setattr(
        "career_copilot.discovery.oracle_fusion.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    listings = _adapter().fetch()

    assert listings == [
        Listing(
            id="341156",
            title="OCI Software Engineer Intern",
            company="Oracle",
            location="Bengaluru, India",
            # Reconstructed from the site's own client-side router config
            # (`/job/{jobId}`) -- Oracle's API doesn't return a URL at all.
            url="https://careers.oracle.com/en/sites/jobsearch/job/341156",
            updated_at="2026-07-27",
            description="Join our cloud engineering team.",
            source="oracle-fusion",
        )
    ]


def test_fetch_handles_missing_requisition_list_as_empty(monkeypatch):
    # A genuinely zero-match search still returns `items: [{...}]` but
    # without a `requisitionList` key at all -- confirmed live.
    monkeypatch.setattr(
        "career_copilot.discovery.oracle_fusion.httpx.get",
        lambda url, params, timeout: _make_response({"items": [{}]}),
    )

    listings = _adapter().fetch()

    assert listings == []


def test_fetch_defaults_missing_description_to_empty_string(monkeypatch):
    payload = {
        "items": [
            {
                "requisitionList": [
                    {
                        "Id": "1",
                        "Title": "Intern",
                        "PrimaryLocation": "Remote",
                        "PostedDate": "2026-07-01",
                        "ShortDescriptionStr": None,
                    }
                ]
            }
        ]
    }
    monkeypatch.setattr(
        "career_copilot.discovery.oracle_fusion.httpx.get",
        lambda url, params, timeout: _make_response(payload),
    )

    listings = _adapter().fetch()

    assert listings[0].description == ""


def test_fetch_returns_empty_list_and_logs_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, params, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.discovery.oracle_fusion.httpx.get", raise_http_error)

    with caplog.at_level(logging.ERROR):
        listings = _adapter().fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_and_logs_on_malformed_payload(monkeypatch, caplog):
    # Missing "items" entirely -> KeyError inside fetch().
    monkeypatch.setattr(
        "career_copilot.discovery.oracle_fusion.httpx.get",
        lambda url, params, timeout: _make_response({}),
    )

    with caplog.at_level(logging.ERROR):
        listings = _adapter().fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
