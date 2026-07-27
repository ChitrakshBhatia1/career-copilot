"""PlaywrightAdapter -- composes a rendered-HTML fetch with a pure HTML parser.

Keeps the same fetch/parse split named in the M8 plan: `fetch_rendered_html`
(browser I/O, untestable without a real browser) and a site-specific
`parse_x(html) -> list[Listing]` function (pure, testable against fixture
HTML with zero real browser involved) are independent pieces; this class
just wires one fetch call to one parser call per configured source, with
the same try/except-log-and-return-empty-list resilience every other
`SourceAdapter` in this package already follows.
"""

import logging
from collections.abc import Callable

from playwright.sync_api import Error as PlaywrightError

from career_copilot.discovery.models import Listing
from career_copilot.discovery.playwright_source import fetch_rendered_html

logger = logging.getLogger(__name__)


class PlaywrightAdapter:
    """Fetches `url` via a real headless browser, then hands the HTML to `parser`.

    `parser` is a pure `Callable[[str], list[Listing]]` (e.g.
    `parse_internshala`) -- this class owns none of the site-specific
    extraction logic itself, only the fetch-then-parse composition and
    error handling.

    `wait_until` defaults to `"domcontentloaded"` (Internshala's proven
    behavior, unchanged) but can be overridden per-source -- e.g. Unstop
    needs `"networkidle"` since its listings only exist in the DOM after its
    Angular SPA finishes a client-side data fetch.
    """

    def __init__(
        self,
        name: str,
        url: str,
        parser: Callable[[str], list[Listing]],
        wait_until: str = "domcontentloaded",
    ) -> None:
        self.name = name
        self.url = url
        self.parser = parser
        self.wait_until = wait_until

    def fetch(self) -> list[Listing]:
        try:
            html = fetch_rendered_html(self.url, wait_until=self.wait_until)
        except PlaywrightError as exc:
            # Covers both a plain navigation failure and
            # `playwright.sync_api.TimeoutError` (a subclass of `Error`).
            logger.error("%s: Playwright navigation failed: %s", self.name, exc)
            return []

        try:
            return self.parser(html)
        except Exception as exc:
            # Arbitrary third-party HTML can fail parsing in many ways not
            # worth enumerating individually -- log clearly and degrade to
            # an empty result rather than crashing the whole discover() run.
            logger.error("%s: parser raised unexpectedly: %s", self.name, exc)
            return []
