"""Registry mapping `sources.toml`'s `parser` field to a pure parser function.

Keeps `discovery/__init__.py`'s adapter factory from having to import each
site-specific parser module by name -- adding a new Playwright-based source
means adding one entry here (and one `parse_x.py` module), nothing else in
the factory needs to change.
"""

from collections.abc import Callable

from career_copilot.discovery.models import Listing
from career_copilot.discovery.parsers.internshala import parse_internshala

PARSERS: dict[str, Callable[[str], list[Listing]]] = {
    "internshala": parse_internshala,
}

__all__ = ["PARSERS"]
