import logging

import httpx

from career_copilot.discovery import Listing
from career_copilot.notify import (
    DISCORD_MESSAGE_LIMIT,
    build_morning_message,
    send_discord_notification,
)


def _make_listing(id_: str, title: str = "Software Engineer, Intern") -> Listing:
    return Listing(
        id=id_,
        title=title,
        company="Anthropic",
        location="Remote",
        url=f"https://example.com/{id_}",
        updated_at="2026-07-01T00:00:00Z",
    )


def test_build_morning_message_with_no_new_listings():
    message = build_morning_message([], [])

    assert "0" in message
    assert "no new" in message.lower() or "nothing new" in message.lower()


def test_build_morning_message_with_listings_but_empty_ranked():
    listings = [_make_listing("1"), _make_listing("2")]

    message = build_morning_message(listings, [])

    assert "2" in message
    assert "Top matches" not in message


def test_build_morning_message_includes_ranked_entries_and_respects_top_n():
    listings = [_make_listing("1"), _make_listing("2"), _make_listing("3")]
    ranked_new = [
        (listings[0], 5),
        (listings[1], 3),
        (listings[2], 1),
    ]

    message = build_morning_message(listings, ranked_new, top_n=2)

    assert "Top matches" in message
    assert listings[0].url in message
    assert listings[1].url in message
    assert listings[2].url not in message


def test_send_discord_notification_returns_false_when_webhook_url_unset(monkeypatch, caplog):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    with caplog.at_level(logging.ERROR):
        result = send_discord_notification("hello")

    assert result is False
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_send_discord_notification_returns_true_on_success(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")

    def fake_post(url, json, timeout):
        return httpx.Response(204, request=httpx.Request("POST", "https://discord.example/webhook"))

    monkeypatch.setattr("career_copilot.notify.httpx.post", fake_post)

    result = send_discord_notification("hello")

    assert result is True


def test_send_discord_notification_returns_false_on_non_2xx_status(monkeypatch, caplog):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")

    def fake_post(url, json, timeout):
        return httpx.Response(404, request=httpx.Request("POST", "https://discord.example/webhook"))

    monkeypatch.setattr("career_copilot.notify.httpx.post", fake_post)

    with caplog.at_level(logging.ERROR):
        result = send_discord_notification("hello")

    assert result is False
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_send_discord_notification_returns_false_on_network_error(monkeypatch, caplog):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")

    def raise_http_error(url, json, timeout):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("career_copilot.notify.httpx.post", raise_http_error)

    with caplog.at_level(logging.ERROR):
        result = send_discord_notification("hello")

    assert result is False
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_send_discord_notification_truncates_over_long_message(monkeypatch, caplog):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    long_message = "x" * (DISCORD_MESSAGE_LIMIT + 500)
    captured = []

    def fake_post(url, json, timeout):
        captured.append(json)
        return httpx.Response(204, request=httpx.Request("POST", "https://discord.example/webhook"))

    monkeypatch.setattr("career_copilot.notify.httpx.post", fake_post)

    with caplog.at_level(logging.WARNING):
        result = send_discord_notification(long_message)

    assert result is True
    assert len(captured) == 1
    assert len(captured[0]["content"]) <= DISCORD_MESSAGE_LIMIT
    assert any(record.levelno == logging.WARNING for record in caplog.records)
