import logging
from pathlib import Path

from career_copilot.discovery import discover, matches_keywords
from career_copilot.discovery.models import Listing


def _make_listing(title: str) -> Listing:
    return Listing(
        id="1",
        title=title,
        company="Stripe",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
    )


def _write_sources(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(content)
    return config_path


# --- matches_keywords ----------------------------------------------------


def test_matches_keywords_matches_intern_title():
    assert matches_keywords(_make_listing("Software Engineer, Intern")) is True


def test_matches_keywords_matches_2027_title():
    assert matches_keywords(_make_listing("New Grad Software Engineer 2027")) is True


def test_matches_keywords_rejects_unrelated_title():
    assert matches_keywords(_make_listing("Senior Backend Engineer")) is False


def test_matches_keywords_rejects_substring_false_positive():
    # "International" contains "intern" as a substring; the word-boundary
    # regex must not treat that as a match.
    assert matches_keywords(_make_listing("International Audit Lead")) is False


# --- discover() orchestration ---------------------------------------------


def test_discover_builds_adapter_types_from_config(monkeypatch, tmp_path):
    content = """
[[source]]
name = "Anthropic"
adapter = "greenhouse"
token = "anthropic"

[[source]]
name = "SomeLeverCo"
adapter = "lever"
token = "someleverco"
"""
    config_path = _write_sources(tmp_path, content)
    built_types: list[str] = []

    class FakeGreenhouseAdapter:
        def __init__(self, company, token):
            self.name = f"{company} (greenhouse)"
            built_types.append("greenhouse")

        def fetch(self):
            return [_make_listing("Greenhouse Intern")]

    class FakeLeverAdapter:
        def __init__(self, company, token):
            self.name = f"{company} (lever)"
            built_types.append("lever")

        def fetch(self):
            return [_make_listing("Lever Intern")]

    monkeypatch.setattr("career_copilot.discovery.GreenhouseAdapter", FakeGreenhouseAdapter)
    monkeypatch.setattr("career_copilot.discovery.LeverAdapter", FakeLeverAdapter)

    listings = discover(config_path=config_path)

    assert built_types == ["greenhouse", "lever"]
    assert {listing.title for listing in listings} == {"Greenhouse Intern", "Lever Intern"}


def test_discover_applies_keyword_filter(monkeypatch, tmp_path):
    content = """
[[source]]
name = "Anthropic"
adapter = "greenhouse"
token = "anthropic"
"""
    config_path = _write_sources(tmp_path, content)

    class FakeGreenhouseAdapter:
        def __init__(self, company, token):
            self.name = f"{company} (greenhouse)"

        def fetch(self):
            return [
                _make_listing("Software Engineer, Intern"),
                _make_listing("Senior Backend Engineer"),
            ]

    monkeypatch.setattr("career_copilot.discovery.GreenhouseAdapter", FakeGreenhouseAdapter)

    listings = discover(config_path=config_path)

    assert [listing.title for listing in listings] == ["Software Engineer, Intern"]


def test_discover_continues_past_a_failing_source(monkeypatch, tmp_path, caplog):
    content = """
[[source]]
name = "Anthropic"
adapter = "greenhouse"
token = "anthropic"

[[source]]
name = "Stripe"
adapter = "lever"
token = "stripe"
"""
    config_path = _write_sources(tmp_path, content)

    class FailingGreenhouseAdapter:
        def __init__(self, company, token):
            self.name = f"{company} (greenhouse)"

        def fetch(self):
            raise RuntimeError("simulated adapter failure")

    class WorkingLeverAdapter:
        def __init__(self, company, token):
            self.name = f"{company} (lever)"

        def fetch(self):
            return [_make_listing("New Grad Software Engineer 2027")]

    monkeypatch.setattr("career_copilot.discovery.GreenhouseAdapter", FailingGreenhouseAdapter)
    monkeypatch.setattr("career_copilot.discovery.LeverAdapter", WorkingLeverAdapter)

    with caplog.at_level(logging.ERROR):
        listings = discover(config_path=config_path)

    assert listings == [
        Listing(
            id="1",
            title="New Grad Software Engineer 2027",
            company="Stripe",
            location="Remote",
            url="https://example.com/1",
            updated_at="2026-07-01T00:00:00Z",
        )
    ]
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_discover_skips_entry_with_unknown_adapter(tmp_path, caplog):
    content = """
[[source]]
name = "Mystery Co"
adapter = "not-a-real-adapter"
"""
    config_path = _write_sources(tmp_path, content)

    with caplog.at_level(logging.ERROR):
        listings = discover(config_path=config_path)

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_discover_returns_empty_list_when_config_missing(tmp_path, caplog):
    config_path = tmp_path / "does-not-exist.toml"

    with caplog.at_level(logging.ERROR):
        listings = discover(config_path=config_path)

    assert listings == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)
