"""Registry mapping `sources.toml`'s `parser` field to a pure parser function.

Keeps `discovery/__init__.py`'s adapter factory from having to import each
site-specific parser module by name -- adding a new Playwright-based source
means adding one entry here (and one `parse_x.py` module), nothing else in
the factory needs to change.
"""

from collections.abc import Callable

from career_copilot.discovery.models import Listing
from career_copilot.discovery.parsers.amazon import parse_amazon
from career_copilot.discovery.parsers.apple import parse_apple
from career_copilot.discovery.parsers.chargebee import parse_chargebee
from career_copilot.discovery.parsers.google import parse_google
from career_copilot.discovery.parsers.internshala import parse_internshala
from career_copilot.discovery.parsers.meta import parse_meta
from career_copilot.discovery.parsers.microsoft import parse_microsoft
from career_copilot.discovery.parsers.unstop import parse_unstop

PARSERS: dict[str, Callable[[str], list[Listing]]] = {
    "internshala": parse_internshala,
    "unstop": parse_unstop,
    "chargebee": parse_chargebee,
    "google": parse_google,
    "microsoft": parse_microsoft,
    "amazon": parse_amazon,
    "apple": parse_apple,
    "meta": parse_meta,
}

__all__ = ["PARSERS"]
