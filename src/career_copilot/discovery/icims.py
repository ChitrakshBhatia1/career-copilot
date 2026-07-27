"""iCIMS provider — best-effort stub, expected to mostly defer to M8.

Per live research (July 2026): iCIMS mostly serves server-rendered career
pages with no consistent public JSON API. A minority of Jibe-powered iCIMS
career sites happen to expose an unofficial `/api/jobs`-shaped endpoint, but
this isn't a stable or documented pattern that holds across iCIMS-hosted
companies in general, and the real iCIMS Customer/Partner API is
OAuth-gated, issued only to iCIMS's own paying customers — not something
this project can call unauthenticated. Rather than guess at a URL shape
that may not exist for a given company, this adapter is a deliberate no-op:
`fetch()` logs that the company needs Playwright-based scraping and returns
an empty list, so the adapter registry/factory has something to reference
until M8 (Playwright) lands.
"""

import logging

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)


class ICIMSAdapter:
    """Placeholder adapter for iCIMS-fronted career sites.

    No public, unauthenticated API exists for iCIMS in the general case
    (see module docstring) — `fetch()` always returns `[]`. Real support for
    iCIMS-hosted companies is expected to come from M8's Playwright
    adapters instead.
    """

    def __init__(self, company: str) -> None:
        self.company = company
        self.name = f"{company} (icims)"

    def fetch(self) -> list[Listing]:
        logger.warning(
            "%s: iCIMS has no public API — needs Playwright (see M8), skipping", self.company
        )
        return []
