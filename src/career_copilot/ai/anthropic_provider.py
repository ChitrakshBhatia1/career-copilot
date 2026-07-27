"""Anthropic provider — Messages API via raw httpx (no `anthropic` SDK).

Verified against the Anthropic Messages API (via the `claude-api` skill,
July 2026): `POST https://api.anthropic.com/v1/messages` with headers
`x-api-key`, `anthropic-version: 2023-06-01`, `content-type:
application/json`. Structured output is requested via
`output_config: {"format": {"type": "json_schema", "schema": {...}}}`,
which guarantees the first response content block is text containing
valid JSON matching the schema. `claude-haiku-4-5` (this project's
configured default) is a current, supported model for structured outputs.
"""

import json
import logging

import httpx

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.schema import ANALYSIS_SCHEMA, build_prompt, parse_analysis_response
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
REQUEST_TIMEOUT = 15.0
MAX_TOKENS = 1024


class AnthropicProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        payload = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": build_prompt(listing)}],
            "output_config": {
                "format": {"type": "json_schema", "schema": ANALYSIS_SCHEMA},
            },
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            response = httpx.post(
                ANTHROPIC_API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            text = data["content"][0]["text"]
            return parse_analysis_response(text)
        except httpx.HTTPError as exc:
            logger.error("Anthropic request failed (model=%s): %s", self.model, exc)
            return None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.error("Anthropic response malformed (model=%s): %s", self.model, exc)
            return None
