"""Job-listing discovery: source adapters + shared filtering + orchestration.

`Listing` and `SourceAdapter` are re-exported here so existing call sites
(`from career_copilot.discovery import Listing`) keep working unchanged now
that the single-file `discovery.py` module has become this package.
"""

import logging
import tomllib
from collections.abc import Callable
from pathlib import Path

from career_copilot.discovery.base import SourceAdapter
from career_copilot.discovery.filtering import matches_keywords
from career_copilot.discovery.greenhouse import GreenhouseAdapter
from career_copilot.discovery.ibm_careers import IBMCareersAdapter
from career_copilot.discovery.icims import ICIMSAdapter
from career_copilot.discovery.lever import LeverAdapter
from career_copilot.discovery.models import Listing
from career_copilot.discovery.oracle_fusion import OracleFusionAdapter
from career_copilot.discovery.parsers import PARSERS
from career_copilot.discovery.playwright_adapter import PlaywrightAdapter
from career_copilot.discovery.qualcomm_eightfold import QualcommEightfoldAdapter
from career_copilot.discovery.smartrecruiters import SmartRecruitersAdapter
from career_copilot.discovery.workday import WorkdayAdapter
from career_copilot.discovery.zerodha import ZerodhaAdapter

logger = logging.getLogger(__name__)

DEFAULT_SOURCES_CONFIG_PATH = Path("config/sources.toml")

__all__ = ["Listing", "SourceAdapter", "matches_keywords", "discover"]


def _build_greenhouse(entry: dict) -> SourceAdapter:
    return GreenhouseAdapter(company=entry["name"], token=entry["token"])


def _build_lever(entry: dict) -> SourceAdapter:
    return LeverAdapter(company=entry["name"], token=entry["token"])


def _build_smartrecruiters(entry: dict) -> SourceAdapter:
    # The API identifier and the display name coincide often enough to
    # default to `name`, but `token` (if present) lets a source override
    # the identifier independently, same as the other adapters.
    return SmartRecruitersAdapter(company=entry.get("token", entry["name"]))


def _build_workday(entry: dict) -> SourceAdapter:
    return WorkdayAdapter(
        company=entry["name"],
        tenant=entry["tenant"],
        wd_number=entry["wd_number"],
        site=entry["site"],
    )


def _build_icims(entry: dict) -> SourceAdapter:
    return ICIMSAdapter(company=entry["name"])


def _build_oracle_fusion(entry: dict) -> SourceAdapter:
    return OracleFusionAdapter(
        company=entry["name"],
        api_base_url=entry["api_base_url"],
        site_number=entry["site_number"],
        public_url_base=entry["public_url_base"],
    )


def _build_ibm_careers(entry: dict) -> SourceAdapter:
    return IBMCareersAdapter(company=entry["name"])


def _build_qualcomm_eightfold(entry: dict) -> SourceAdapter:
    return QualcommEightfoldAdapter(company=entry["name"], domain=entry["domain"])


def _build_zerodha(entry: dict) -> SourceAdapter:
    return ZerodhaAdapter(company=entry["name"])


def _build_playwright(entry: dict) -> SourceAdapter:
    # `entry["parser"]` looks up the pure `parse_x(html) -> list[Listing]`
    # function to pair with the fetch -- both this lookup and `entry["url"]`
    # raise `KeyError` on a malformed config entry, caught the same generic
    # way `_build_adapter()` already handles every other adapter's missing
    # required fields.
    parser = PARSERS[entry["parser"]]
    # `wait_until` is optional -- absent for sources like Internshala whose
    # listings are already present at `domcontentloaded`; sources that render
    # client-side (e.g. Unstop's Angular SPA) set it explicitly to
    # `"networkidle"` in `sources.toml`.
    return PlaywrightAdapter(
        name=entry["name"],
        url=entry["url"],
        parser=parser,
        wait_until=entry.get("wait_until", "domcontentloaded"),
    )


_ADAPTER_BUILDERS: dict[str, Callable[[dict], SourceAdapter]] = {
    "greenhouse": _build_greenhouse,
    "lever": _build_lever,
    "smartrecruiters": _build_smartrecruiters,
    "workday": _build_workday,
    "icims": _build_icims,
    "playwright": _build_playwright,
    "oracle-fusion": _build_oracle_fusion,
    "ibm-careers": _build_ibm_careers,
    "eightfold": _build_qualcomm_eightfold,
    "zerodha-api": _build_zerodha,
}


def _load_sources(config_path: Path) -> list[dict]:
    if not config_path.exists():
        logger.error("%s not found — no sources configured", config_path)
        return []
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.error("Failed to read %s: %s", config_path, exc)
        return []
    return data.get("source", [])


def _build_adapter(entry: dict) -> SourceAdapter | None:
    adapter_type = entry.get("adapter")
    builder = _ADAPTER_BUILDERS.get(adapter_type)
    if builder is None:
        logger.error(
            "%s: unknown or missing adapter type %r — skipping",
            entry.get("name", "?"),
            adapter_type,
        )
        return None
    try:
        return builder(entry)
    except KeyError as exc:
        logger.error(
            "%s: source config missing required field %s for adapter %r — skipping",
            entry.get("name", "?"),
            exc,
            adapter_type,
        )
        return None


def discover(config_path: Path = DEFAULT_SOURCES_CONFIG_PATH) -> list[Listing]:
    entries = _load_sources(config_path)
    all_listings: list[Listing] = []
    for entry in entries:
        adapter = _build_adapter(entry)
        if adapter is None:
            continue
        try:
            listings = adapter.fetch()
        except Exception as exc:
            # Belt-and-suspenders: each adapter already catches its own
            # httpx/parsing errors internally, but one bad source must never
            # crash the whole discover() run even if an adapter's own
            # handling has a gap.
            logger.error("%s: adapter raised unexpectedly: %s", adapter.name, exc)
            listings = []
        logger.info("%s: found %d listings", adapter.name, len(listings))
        all_listings.extend(listings)

    filtered = [listing for listing in all_listings if matches_keywords(listing)]
    logger.info(
        "discover: %d listings found across %d sources, %d passed keyword filter",
        len(all_listings),
        len(entries),
        len(filtered),
    )
    return filtered
