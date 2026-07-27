"""Selects and instantiates the configured AIProvider.

This is the only module in the codebase that imports all four provider
classes by name — everything else only ever sees the AIProvider Protocol
and the AIAnalysis dataclass, so switching providers/models is a one-line
config edit, never a code change.
"""

import logging
import os
import tomllib
from pathlib import Path

import httpx

from career_copilot.ai.anthropic_provider import AnthropicProvider
from career_copilot.ai.base import AIProvider
from career_copilot.ai.gemini_provider import GeminiProvider
from career_copilot.ai.ollama_provider import OllamaProvider
from career_copilot.ai.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config/ai.toml")
OLLAMA_REACHABILITY_TIMEOUT = 2.0


def _load_openrouter(section: dict) -> AIProvider | None:
    api_key = os.environ.get(section["api_key_env"])
    if not api_key:
        logger.warning(
            "%s is not set — skipping AI analysis (provider: openrouter)", section["api_key_env"]
        )
        return None
    return OpenRouterProvider(model=section["model"], api_key=api_key)


def _load_anthropic(section: dict) -> AIProvider | None:
    api_key = os.environ.get(section["api_key_env"])
    if not api_key:
        logger.warning(
            "%s is not set — skipping AI analysis (provider: anthropic)", section["api_key_env"]
        )
        return None
    return AnthropicProvider(model=section["model"], api_key=api_key)


def _load_gemini(section: dict) -> AIProvider | None:
    api_key = os.environ.get(section["api_key_env"])
    if not api_key:
        logger.warning(
            "%s is not set — skipping AI analysis (provider: gemini)", section["api_key_env"]
        )
        return None
    return GeminiProvider(model=section["model"], api_key=api_key)


def _load_ollama(section: dict) -> AIProvider | None:
    base_url = section["base_url"]
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=OLLAMA_REACHABILITY_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Ollama at %s is not reachable — skipping AI analysis: %s", base_url, exc)
        return None
    return OllamaProvider(model=section["model"], base_url=base_url)


_LOADERS = {
    "openrouter": _load_openrouter,
    "anthropic": _load_anthropic,
    "gemini": _load_gemini,
    "ollama": _load_ollama,
}


def load_provider(config_path: Path = DEFAULT_CONFIG_PATH) -> AIProvider | None:
    if not config_path.exists():
        logger.warning("%s not found — skipping AI analysis", config_path)
        return None

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.warning("Failed to read %s — skipping AI analysis: %s", config_path, exc)
        return None

    ai_config = data.get("ai", {})
    provider_name = ai_config.get("provider")
    loader = _LOADERS.get(provider_name)
    if loader is None:
        logger.warning(
            "Unknown or unconfigured AI provider %r — skipping AI analysis", provider_name
        )
        return None

    section = ai_config.get(provider_name)
    if not section:
        logger.warning(
            "Missing [ai.%s] section in %s — skipping AI analysis", provider_name, config_path
        )
        return None

    return loader(section)
