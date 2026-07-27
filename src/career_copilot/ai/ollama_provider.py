"""Ollama provider — local REST API via raw httpx. No API key.

Verified via web search (July 2026): local Ollama servers expose `POST
{base_url}/api/chat` with `messages` and a `format` field that accepts a
full JSON Schema object for structured output (in addition to the older
`format: "json"` mode). Reachability is checked separately in
`ai/factory.py` via `GET {base_url}/api/tags`.
"""

import json
import logging

import httpx

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.schema import ANALYSIS_SCHEMA, build_prompt, parse_analysis_response
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15.0


class OllamaProvider:
    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": build_prompt(listing)}],
            "stream": False,
            "format": ANALYSIS_SCHEMA,
            "options": {"temperature": 0},
        }
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            text = data["message"]["content"]
            return parse_analysis_response(text)
        except httpx.HTTPError as exc:
            logger.error("Ollama request failed (model=%s): %s", self.model, exc)
            return None
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.error("Ollama response malformed (model=%s): %s", self.model, exc)
            return None
