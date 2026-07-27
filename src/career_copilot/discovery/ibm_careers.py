"""IBM Careers provider — public unauthenticated search API behind the SPA.

M7's earlier research called `ibm.com/careers/search` "a JS-rendered SPA
with no inspectable API." A real live spike (July 2026) found this only
half true: the *page itself* is indeed client-rendered, but it works by
calling a plain, unauthenticated, CORS-open REST endpoint --
`POST https://www-api.ibm.com/search/api/v2` -- confirmed live by watching
Playwright's own network traffic once past the page's cookie-consent
overlay, then reproduced with zero Playwright involvement via a bare
`httpx.post()` from a fresh, cookie-less client. This is IBM's own
in-house search index (an Elasticsearch-shaped query/response, not a
named third-party ATS platform), so unlike Oracle Fusion/Workday this
adapter isn't a reusable multi-tenant client -- it's IBM-specific.

Request shape confirmed live: a plain Elasticsearch `bool`/`must`/`match`
query restricted to the `title` field (`{"match": {"title": "intern"}}`) --
this is a precise title-only match, unlike Oracle's full-document substring
search, so no relevance-sort workaround is needed here. Response shape:
`data["hits"]["hits"][*]["_source"]` with `title`, `url` (a real candidate-
facing `careers.ibm.com/careers/JobDetail?jobId=...` permalink),
`description` (a real, if truncated, plain-text summary), and
`field_keyword_19` (confirmed live across multiple real postings to be the
location string, e.g. "Hyderabad, IN", "Singapore, SG" -- IBM's field names
are opaque numbered facet codes, not descriptive labels). No stable
per-posting date field was found in this response shape, so `updated_at` is
deliberately left `""`, same call as `SmartRecruitersAdapter`/
`WorkdayAdapter` when a list endpoint has no equivalent field.
"""

import logging

import httpx

from career_copilot.discovery.models import Listing

logger = logging.getLogger(__name__)

IBM_SEARCH_URL = "https://www-api.ibm.com/search/api/v2"
REQUEST_TIMEOUT = 10.0
PAGE_SIZE = 30
SEARCH_KEYWORD = "intern"
SOURCE_FIELDS = ["_id", "title", "url", "description", "field_keyword_19"]


class IBMCareersAdapter:
    """Fetches listings from IBM's own in-house careers search API."""

    def __init__(self, company: str) -> None:
        self.company = company
        self.name = f"{company} (ibm-careers)"

    def fetch(self) -> list[Listing]:
        payload = {
            "appId": "careers",
            "scopes": ["careers2"],
            "query": {"bool": {"must": [{"match": {"title": SEARCH_KEYWORD}}]}},
            "size": PAGE_SIZE,
            "sort": [{"_score": "desc"}],
            "lang": "zz",
            "localeSelector": {},
            "sm": {"query": SEARCH_KEYWORD, "lang": "zz"},
            "_source": SOURCE_FIELDS,
        }
        try:
            response = httpx.post(IBM_SEARCH_URL, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            hits = data["hits"]["hits"]
            return [
                Listing(
                    id=hit["_id"],
                    title=hit["_source"]["title"],
                    company=self.company,
                    location=hit["_source"].get("field_keyword_19", ""),
                    url=hit["_source"]["url"],
                    updated_at="",
                    description=hit["_source"].get("description", ""),
                    source="ibm-careers",
                )
                for hit in hits
            ]
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch listings for %s: %s", self.company, exc)
            return []
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Failed to parse listings for %s: %s", self.company, exc)
            return []
