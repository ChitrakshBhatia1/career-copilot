"""Canonical JSON schema and prompt template for AI listing analysis.

Both live in this one file (not split across a schema module and a prompt
module) because the prompt text directly references the schema's field
names and semantics — splitting them would just mean keeping two files in
sync by hand.
"""

import json
import logging
import re

from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

# The canonical schema every provider adapter translates into its own
# structured-output request shape (OpenRouter's response_format.json_schema,
# Anthropic's output_config.format, Gemini's generationConfig.responseSchema,
# Ollama's format).
ANALYSIS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "visa_sponsorship_mentioned": {
            "type": "boolean",
            "description": (
                "Whether the listing description mentions visa sponsorship "
                "for international candidates."
            ),
        },
        "likely_summer_2027_eligible": {
            "type": "boolean",
            "description": (
                "Whether the listing is likely eligible for a Summer 2027 "
                "internship (roughly May-July 2027, allowing some flexibility "
                "in exact start/end dates)."
            ),
        },
        "notes": {
            "type": "string",
            "description": "One-sentence note summarizing anything notable about the listing.",
        },
    },
    "required": ["visa_sponsorship_mentioned", "likely_summer_2027_eligible", "notes"],
    "additionalProperties": False,
}

# Some models wrap JSON in a ```json ... ``` fence despite instructions not
# to — strip that before parsing rather than failing on it.
_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def build_prompt(listing: Listing) -> str:
    return (
        "You are analyzing a job listing for a software engineering student "
        "targeting a Summer 2027 internship or new-grad role.\n\n"
        f"Title: {listing.title}\n"
        f"Company: {listing.company}\n"
        f"Location: {listing.location}\n"
        f"Description:\n{listing.description}\n\n"
        "Answer these questions about the listing above:\n"
        "1. Does the description mention visa sponsorship for international candidates?\n"
        "2. Is the listing likely eligible for a Summer 2027 internship "
        "(roughly May-July 2027, allowing for some flexibility in exact dates)?\n"
        "3. Write one sentence summarizing anything notable about this listing.\n\n"
        "Respond with JSON matching the required schema only — no other text."
    )


def parse_analysis_response(raw_text: str) -> AIAnalysis | None:
    """Parse a model's raw text response into an AIAnalysis.

    Shared by every provider so each one only has to extract its own raw
    text field before handing off here. Never raises — logs and returns
    None on any malformed/unparseable/missing-field output, matching
    discovery.fetch_source()'s established error-handling pattern.
    """
    cleaned = _CODE_FENCE_PATTERN.sub("", raw_text).strip()
    try:
        data = json.loads(cleaned)
        return AIAnalysis(
            visa_sponsorship_mentioned=bool(data["visa_sponsorship_mentioned"]),
            likely_summer_2027_eligible=bool(data["likely_summer_2027_eligible"]),
            notes=str(data["notes"]),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.error("Failed to parse AI analysis response: %s — raw text: %.200s", exc, raw_text)
        return None
