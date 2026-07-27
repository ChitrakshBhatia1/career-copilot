"""Tests for `PlaywrightAdapter`'s error handling.

`fetch_rendered_html()` itself is deliberately not unit-tested here -- it's
real browser I/O (launches Chromium, navigates a real page), which is
exactly why it's kept this thin: there's nothing to unit-test beyond "does
it call Playwright correctly," and that's already covered by the live
`career-copilot discover` smoke-check against the real Internshala site.
What *is* unit-testable, and matters more for this project's resilience
guarantees, is that `PlaywrightAdapter.fetch()` degrades to `[]` (logged,
not raised) when the browser fetch or the parser blows up -- the same
contract every other `SourceAdapter` in this package already honors.
"""

import logging

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from career_copilot.discovery.models import Listing
from career_copilot.discovery.playwright_adapter import PlaywrightAdapter


def _fake_parser(html: str) -> list[Listing]:
    return [
        Listing(
            id="1",
            title="Fake Internship",
            company="Fake Co",
            location="Remote",
            url="https://example.com/1",
            updated_at="",
        )
    ]


def test_fetch_returns_parsed_listings_on_success(monkeypatch):
    monkeypatch.setattr(
        "career_copilot.discovery.playwright_adapter.fetch_rendered_html",
        lambda url: "<html></html>",
    )
    adapter = PlaywrightAdapter(name="FakeSource", url="https://example.com", parser=_fake_parser)

    listings = adapter.fetch()

    assert listings == _fake_parser("")


def test_fetch_returns_empty_list_when_fetch_rendered_html_raises_timeout(monkeypatch, caplog):
    def _raise_timeout(url: str) -> str:
        raise PlaywrightTimeoutError("Timeout 20000ms exceeded")

    monkeypatch.setattr(
        "career_copilot.discovery.playwright_adapter.fetch_rendered_html", _raise_timeout
    )
    adapter = PlaywrightAdapter(name="FakeSource", url="https://example.com", parser=_fake_parser)

    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_when_fetch_rendered_html_raises_generic_playwright_error(
    monkeypatch, caplog
):
    def _raise_error(url: str) -> str:
        raise PlaywrightError("Navigation failed")

    monkeypatch.setattr(
        "career_copilot.discovery.playwright_adapter.fetch_rendered_html", _raise_error
    )
    adapter = PlaywrightAdapter(name="FakeSource", url="https://example.com", parser=_fake_parser)

    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_fetch_returns_empty_list_when_parser_raises(monkeypatch, caplog):
    monkeypatch.setattr(
        "career_copilot.discovery.playwright_adapter.fetch_rendered_html",
        lambda url: "<html></html>",
    )

    def _broken_parser(html: str) -> list[Listing]:
        raise ValueError("totally unexpected HTML shape")

    adapter = PlaywrightAdapter(name="FakeSource", url="https://example.com", parser=_broken_parser)

    with caplog.at_level(logging.ERROR):
        listings = adapter.fetch()

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
