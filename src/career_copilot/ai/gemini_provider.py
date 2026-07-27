"""Gemini provider — REST generateContent API via raw httpx (no google-genai SDK).

Verified via web search (July 2026): `POST
https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`,
body `contents: [{"parts": [{"text": ...}]}]` plus
`generationConfig.responseMimeType`/`responseSchema` for structured output.
Gemini's schema format is an OpenAPI-3.0 subset that doesn't document
`additionalProperties` support, so it's dropped from the schema sent here
rather than risk a 400.
"""

import json
import logging

import httpx

from career_copilot.ai.models import AIAnalysis
from career_copilot.ai.schema import ANALYSIS_SCHEMA, build_prompt, parse_analysis_response
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT = 15.0


def _gemini_response_schema() -> dict:
    schema = dict(ANALYSIS_SCHEMA)
    schema.pop("additionalProperties", None)
    return schema


class GeminiProvider:
    def __init__(self, model: str, api_key: str) -> None:
        self.model = model
        self.api_key = api_key

    def analyze_listing(self, listing: Listing) -> AIAnalysis | None:
        url = GEMINI_API_BASE.format(model=self.model)
        payload = {
            "contents": [{"parts": [{"text": build_prompt(listing)}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _gemini_response_schema(),
            },
        }
        try:
            response = httpx.post(
                url, params={"key": self.api_key}, json=payload, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return parse_analysis_response(text)
        except httpx.HTTPError as exc:
            logger.error("Gemini request failed (model=%s): %s", self.model, exc)
            return None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.error("Gemini response malformed (model=%s): %s", self.model, exc)
            return None
