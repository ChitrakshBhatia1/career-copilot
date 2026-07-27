"""Rendered-HTML fetching via a real headless browser.

The only module in the codebase that touches `playwright.sync_api` --
deliberately thin, no parsing logic here at all. `Playwright`'s own
exceptions (e.g. `playwright.sync_api.TimeoutError` on navigation timeout)
are allowed to propagate to the caller rather than being swallowed here,
matching this project's established pattern of each *adapter* owning its
own try/except-log-and-return-empty-list handling (see `greenhouse.py` etc.
for the `httpx` equivalent) rather than a shared fetch helper hiding
failures from its callers.
"""

from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT_MS = 20000


def fetch_rendered_html(
    url: str, timeout_ms: int = DEFAULT_TIMEOUT_MS, wait_until: str = "domcontentloaded"
) -> str:
    """Launch headless Chromium, navigate to `url`, and return its rendered HTML.

    Defaults to `wait_until="domcontentloaded"` rather than waiting for full
    network idle -- confirmed via a live spike against Internshala that the
    listing data of interest is already present server-side at that point,
    so waiting longer just costs time for no extra data.

    `wait_until` is overridable per-source (plumbed through from
    `sources.toml`'s optional `wait_until` field via `PlaywrightAdapter`) for
    sites that don't render listings server-side. Confirmed necessary for
    Unstop during the M8 spike: its Angular SPA has zero listing cards
    present in the DOM at `domcontentloaded` (data loads via a client-side
    XHR call after JS bootstraps), but is fully rendered by the time
    `wait_until="networkidle"` resolves -- a deterministic wait, not an
    arbitrary sleep.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            return page.content()
        finally:
            browser.close()
