import logging

import httpx

from career_copilot.ai.anthropic_provider import AnthropicProvider
from career_copilot.ai.gemini_provider import GeminiProvider
from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.ollama_provider import OllamaProvider
from career_copilot.ai.openrouter import OpenRouterProvider
from career_copilot.discovery import Listing

_ANALYSIS_JSON = (
    '{"visa_sponsorship_mentioned": true, "likely_summer_2027_eligible": true, '
    '"notes": "Solid fit."}'
)
_EXPECTED_ANALYSIS = AIAnalysis(
    visa_sponsorship_mentioned=True,
    likely_summer_2027_eligible=True,
    notes="Solid fit.",
)


def _make_listing() -> Listing:
    return Listing(
        id="1",
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
        description="Build cool things.",
    )


def _response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code, json=payload, request=httpx.Request("POST", "https://example.com")
    )


# --- OpenRouter ---------------------------------------------------------


def test_openrouter_analyze_listing_returns_parsed_analysis_on_success(monkeypatch):
    payload = {"choices": [{"message": {"content": _ANALYSIS_JSON}}]}

    def fake_post(url, json, headers, timeout):
        return _response(payload)

    monkeypatch.setattr("career_copilot.ai.openrouter.httpx.post", fake_post)

    provider = OpenRouterProvider(model="openai/gpt-oss-20b:free", api_key="test-key")
    result = provider.analyze_listing(_make_listing())

    assert result == _EXPECTED_ANALYSIS


def test_openrouter_analyze_listing_returns_none_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, json, headers, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.ai.openrouter.httpx.post", raise_http_error)

    provider = OpenRouterProvider(model="openai/gpt-oss-20b:free", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_openrouter_analyze_listing_returns_none_on_malformed_response(monkeypatch, caplog):
    # Missing "choices" entirely -> KeyError inside analyze_listing.
    def fake_post(url, json, headers, timeout):
        return _response({"error": "nope"})

    monkeypatch.setattr("career_copilot.ai.openrouter.httpx.post", fake_post)

    provider = OpenRouterProvider(model="openai/gpt-oss-20b:free", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


# --- Anthropic -----------------------------------------------------------


def test_anthropic_analyze_listing_returns_parsed_analysis_on_success(monkeypatch):
    payload = {"content": [{"text": _ANALYSIS_JSON}]}

    def fake_post(url, json, headers, timeout):
        return _response(payload)

    monkeypatch.setattr("career_copilot.ai.anthropic_provider.httpx.post", fake_post)

    provider = AnthropicProvider(model="claude-haiku-4-5", api_key="test-key")
    result = provider.analyze_listing(_make_listing())

    assert result == _EXPECTED_ANALYSIS


def test_anthropic_analyze_listing_returns_none_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, json, headers, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.ai.anthropic_provider.httpx.post", raise_http_error)

    provider = AnthropicProvider(model="claude-haiku-4-5", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_anthropic_analyze_listing_returns_none_on_malformed_response(monkeypatch, caplog):
    # Missing "content" entirely -> KeyError inside analyze_listing.
    def fake_post(url, json, headers, timeout):
        return _response({"error": "nope"})

    monkeypatch.setattr("career_copilot.ai.anthropic_provider.httpx.post", fake_post)

    provider = AnthropicProvider(model="claude-haiku-4-5", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


# --- Gemini ----------------------------------------------------------------


def test_gemini_analyze_listing_returns_parsed_analysis_on_success(monkeypatch):
    payload = {"candidates": [{"content": {"parts": [{"text": _ANALYSIS_JSON}]}}]}

    def fake_post(url, params, json, timeout):
        return _response(payload)

    monkeypatch.setattr("career_copilot.ai.gemini_provider.httpx.post", fake_post)

    provider = GeminiProvider(model="gemini-2.5-flash", api_key="test-key")
    result = provider.analyze_listing(_make_listing())

    assert result == _EXPECTED_ANALYSIS


def test_gemini_analyze_listing_returns_none_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, params, json, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.ai.gemini_provider.httpx.post", raise_http_error)

    provider = GeminiProvider(model="gemini-2.5-flash", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_gemini_analyze_listing_returns_none_on_malformed_response(monkeypatch, caplog):
    # Missing "candidates" entirely -> KeyError inside analyze_listing.
    def fake_post(url, params, json, timeout):
        return _response({"error": "nope"})

    monkeypatch.setattr("career_copilot.ai.gemini_provider.httpx.post", fake_post)

    provider = GeminiProvider(model="gemini-2.5-flash", api_key="test-key")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


# --- Ollama ------------------------------------------------------------


def test_ollama_analyze_listing_returns_parsed_analysis_on_success(monkeypatch):
    payload = {"message": {"content": _ANALYSIS_JSON}}

    def fake_post(url, json, timeout):
        return _response(payload)

    monkeypatch.setattr("career_copilot.ai.ollama_provider.httpx.post", fake_post)

    provider = OllamaProvider(model="llama3.2", base_url="http://localhost:11434")
    result = provider.analyze_listing(_make_listing())

    assert result == _EXPECTED_ANALYSIS


def test_ollama_analyze_listing_returns_none_on_http_error(monkeypatch, caplog):
    def raise_http_error(url, json, timeout):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("career_copilot.ai.ollama_provider.httpx.post", raise_http_error)

    provider = OllamaProvider(model="llama3.2", base_url="http://localhost:11434")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_ollama_analyze_listing_returns_none_on_malformed_response(monkeypatch, caplog):
    # Missing "message" entirely -> KeyError inside analyze_listing.
    def fake_post(url, json, timeout):
        return _response({"error": "nope"})

    monkeypatch.setattr("career_copilot.ai.ollama_provider.httpx.post", fake_post)

    provider = OllamaProvider(model="llama3.2", base_url="http://localhost:11434")
    with caplog.at_level(logging.ERROR):
        result = provider.analyze_listing(_make_listing())

    assert result is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)
