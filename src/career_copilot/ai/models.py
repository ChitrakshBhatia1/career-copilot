from dataclasses import dataclass


@dataclass(frozen=True)
class AIAnalysis:
    visa_sponsorship_mentioned: bool
    likely_summer_2027_eligible: bool
    notes: str
