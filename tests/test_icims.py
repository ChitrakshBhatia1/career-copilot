import logging

from career_copilot.discovery.icims import ICIMSAdapter


def test_fetch_always_returns_empty_list_without_raising():
    adapter = ICIMSAdapter(company="SomeCompany")

    listings = adapter.fetch()

    assert listings == []


def test_fetch_logs_that_playwright_is_needed(caplog):
    adapter = ICIMSAdapter(company="SomeCompany")

    with caplog.at_level(logging.WARNING):
        adapter.fetch()

    assert any(record.levelno == logging.WARNING for record in caplog.records)
