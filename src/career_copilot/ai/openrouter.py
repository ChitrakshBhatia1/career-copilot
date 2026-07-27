"""OpenRouter provider — OpenAI-compatible chat completions REST API.

Verified against OpenRouter's current docs (July 2026): the endpoint is
OpenAI-compatible (`POST /api/v1/chat/completions`, `Authorization: Bearer
{key}`), and structured output is requested via a top-level
`response_format: {"type": "json_schema", "json_schema": {...}}` field —
OpenRouter forwards this to providers that support it and otherwise
enforces it via its own JSON-schema validation layer.
"""

import json
import logging

import httpx

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.schema import ANALYSIS_SCHEMA, build_prompt, parse_analysis_response
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 15.0


class OpenRouterProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": build_prompt(listing)}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "listing_analysis",
                    "strict": True,
                    "schema": ANALYSIS_SCHEMA,
                },
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(
                OPENROUTER_API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return parse_analysis_response(text)
        except httpx.HTTPError as exc:
            logger.error("OpenRouter request failed (model=%s): %s", self.model, exc)
            return None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.error("OpenRouter response malformed (model=%s): %s", self.model, exc)
            return None
