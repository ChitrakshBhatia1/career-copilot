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
from career_copilot.discovery.icims import ICIMSAdapter
from career_copilot.discovery.lever import LeverAdapter
from career_copilot.discovery.models import Listing
from career_copilot.discovery.smartrecruiters import SmartRecruitersAdapter
from career_copilot.discovery.workday import WorkdayAdapter

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


_ADAPTER_BUILDERS: dict[str, Callable[[dict], SourceAdapter]] = {
    "greenhouse": _build_greenhouse,
    "lever": _build_lever,
    "smartrecruiters": _build_smartrecruiters,
    "workday": _build_workday,
    "icims": _build_icims,
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
