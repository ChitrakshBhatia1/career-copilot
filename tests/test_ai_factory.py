import logging
from pathlib import Path

import httpx

from career_copilot.ai.anthropic_provider import AnthropicProvider
from career_copilot.ai.factory import load_provider
from career_copilot.ai.gemini_provider import GeminiProvider
from career_copilot.ai.ollama_provider import OllamaProvider
from career_copilot.ai.openrouter import OpenRouterProvider

_FULL_CONFIG = """
[ai]
provider = "openrouter"

[ai.openrouter]
model = "openai/gpt-oss-20b:free"
api_key_env = "TEST_OPENROUTER_KEY"

[ai.anthropic]
model = "claude-haiku-4-5"
api_key_env = "TEST_ANTHROPIC_KEY"

[ai.gemini]
model = "gemini-2.5-flash"
api_key_env = "TEST_GEMINI_KEY"

[ai.ollama]
model = "llama3.2"
base_url = "http://localhost:11434"
"""


def _write_config(tmp_path: Path, content: str, name: str = "ai.toml") -> Path:
    config_path = tmp_path / name
    config_path.write_text(content)
    return config_path


# --- missing / unparseable config -------------------------------------


def test_load_provider_returns_none_when_config_missing(tmp_path, caplog):
    config_path = tmp_path / "does-not-exist.toml"

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)


# --- missing env var -----------------------------------------------------


def test_load_provider_returns_none_when_openrouter_env_var_unset(monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("TEST_OPENROUTER_KEY", raising=False)
    config_path = _write_config(tmp_path, _FULL_CONFIG)

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_load_provider_returns_none_when_anthropic_env_var_unset(monkeypatch, tmp_path, caplog):
    monkeypatch.delenv("TEST_ANTHROPIC_KEY", raising=False)
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "anthropic"')
    config_path = _write_config(tmp_path, content)

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)


# --- successful load -----------------------------------------------------


def test_load_provider_returns_openrouter_provider_when_env_var_set(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_OPENROUTER_KEY", "secret-key")
    config_path = _write_config(tmp_path, _FULL_CONFIG)

    provider = load_provider(config_path=config_path)

    assert isinstance(provider, OpenRouterProvider)
    assert provider.model == "openai/gpt-oss-20b:free"
    assert provider.api_key == "secret-key"


def test_load_provider_returns_anthropic_provider_when_env_var_set(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "secret-key")
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "anthropic"')
    config_path = _write_config(tmp_path, content)

    provider = load_provider(config_path=config_path)

    assert isinstance(provider, AnthropicProvider)


def test_load_provider_returns_gemini_provider_when_env_var_set(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_GEMINI_KEY", "secret-key")
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "gemini"')
    config_path = _write_config(tmp_path, content)

    provider = load_provider(config_path=config_path)

    assert isinstance(provider, GeminiProvider)


# --- unknown provider / missing section -----------------------------------


def test_load_provider_returns_none_when_provider_name_unknown(tmp_path, caplog):
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "not-a-real-provider"')
    config_path = _write_config(tmp_path, content)

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_load_provider_returns_none_when_matching_section_missing(tmp_path, caplog):
    # [ai].provider names anthropic, but no [ai.anthropic] section is defined.
    content = """
[ai]
provider = "anthropic"

[ai.openrouter]
model = "openai/gpt-oss-20b:free"
api_key_env = "TEST_OPENROUTER_KEY"
"""
    config_path = _write_config(tmp_path, content)

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)


# --- ollama reachability ---------------------------------------------------


def test_load_provider_returns_ollama_provider_when_reachable(monkeypatch, tmp_path):
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "ollama"')
    config_path = _write_config(tmp_path, content)

    def fake_get(url, timeout):
        return httpx.Response(200, json={"models": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr("career_copilot.ai.factory.httpx.get", fake_get)

    provider = load_provider(config_path=config_path)

    assert isinstance(provider, OllamaProvider)


def test_load_provider_returns_none_when_ollama_unreachable(monkeypatch, tmp_path, caplog):
    content = _FULL_CONFIG.replace('provider = "openrouter"', 'provider = "ollama"')
    config_path = _write_config(tmp_path, content)

    def raise_http_error(url, timeout):
        raise httpx.HTTPError("connection refused")

    monkeypatch.setattr("career_copilot.ai.factory.httpx.get", raise_http_error)

    with caplog.at_level(logging.WARNING):
        provider = load_provider(config_path=config_path)

    assert provider is None
    assert any(record.levelno == logging.WARNING for record in caplog.records)
