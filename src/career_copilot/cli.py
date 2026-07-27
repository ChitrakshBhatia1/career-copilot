import argparse
import hashlib
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

from career_copilot import ai_analysis, db, discovery, matching, notify
from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing
from career_copilot.env import load_dotenv
from career_copilot.logging_config import setup_logging

logger = logging.getLogger(__name__)

DEFAULT_ANALYZE_BATCH_SIZE = 20
DEFAULT_EXPORT_TOP = 20
EXPORTS_DIR = Path("data/exports")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-copilot",
        description="AI-powered career management platform for software engineering students.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Search configured sources for new opportunities.")
    subparsers.add_parser("match", help="Rank stored listings against your preferences.")
    subparsers.add_parser(
        "morning", help="Run discover, persist, match, and send a daily notification."
    )
    analyze_parser = subparsers.add_parser(
        "analyze", help="Run AI analysis on stored listings that haven't been analyzed yet."
    )
    analyze_parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_ANALYZE_BATCH_SIZE,
        help=f"Max listings to analyze in this run (default: {DEFAULT_ANALYZE_BATCH_SIZE}).",
    )
    import_parser = subparsers.add_parser(
        "import-listings",
        help="Import a JSON array of listings (e.g. from an interactive LinkedIn/Naukri session).",
    )
    import_parser.add_argument("path", help="Path to the JSON file to import.")
    export_parser = subparsers.add_parser(
        "export-matches",
        help="Export the top-ranked stored listings to a markdown file for manual follow-up.",
    )
    export_parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_EXPORT_TOP,
        help=f"Number of top-ranked listings to export (default: {DEFAULT_EXPORT_TOP}).",
    )
    export_parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output markdown file path (default: data/exports/matches_<today>.md).",
    )
    return parser


def _format_ai_flags(analysis: AIAnalysis | None) -> str:
    if analysis is None:
        return ""

    flags = []
    if analysis.visa_sponsorship_mentioned:
        flags.append("visa✓")
    if analysis.likely_summer_2027_eligible:
        flags.append("2027-likely✓")

    return f" [{' | '.join(flags)}]" if flags else ""


def run_discover() -> None:
    db.init_db()
    listings = discovery.discover()
    new_listings = db.save_new_listings(listings)

    logger.info("discover: %d new listings out of %d fetched", len(new_listings), len(listings))
    if not new_listings:
        logger.info("No new listings found.")
        return

    for listing in new_listings:
        print(f"{listing.title} — {listing.company} ({listing.location})\n  {listing.url}")


def _rank_with_analysis() -> tuple[list[tuple[Listing, int, AIAnalysis | None]], int]:
    """Fetch all stored listings, rank them against preferences, and pair each
    ranked listing with its AI analysis (if any).

    Shared by `run_match` and `run_export_matches` so both commands rank
    stored listings identically. Returns `(ranked, total_stored)` — `total_stored`
    is the count of all stored listings before preference-based filtering, so
    callers can distinguish "nothing stored" from "everything got filtered out".
    """
    listings_with_analysis = db.get_all_listings_with_analysis()
    if not listings_with_analysis:
        return [], 0

    analysis_by_url = {listing.url: analysis for listing, analysis in listings_with_analysis}
    listings = [listing for listing, _ in listings_with_analysis]

    preferences = matching.load_preferences()
    ranked = matching.rank_listings(listings, preferences)

    ranked_with_analysis = [
        (listing, score, analysis_by_url.get(listing.url)) for listing, score in ranked
    ]
    return ranked_with_analysis, len(listings)


def run_match() -> None:
    db.init_db()
    ranked, total = _rank_with_analysis()
    if total == 0:
        logger.info("No stored listings yet — run `career-copilot discover` first.")
        return

    logger.info("match: %d of %d stored listings ranked", len(ranked), total)
    for listing, score, analysis in ranked:
        flags = _format_ai_flags(analysis)
        print(
            f"[{score}] {listing.title} — {listing.company} ({listing.location}){flags}"
            f"\n  {listing.url}"
        )


def _analyze_and_save(
    listings: list[Listing], batch_size: int = DEFAULT_ANALYZE_BATCH_SIZE
) -> dict[str, AIAnalysis]:
    results = ai_analysis.analyze_new_listings(listings, batch_size=batch_size)
    for url, analysis in results.items():
        db.save_ai_analysis(url, analysis)
    return results


def run_analyze(batch_size: int = DEFAULT_ANALYZE_BATCH_SIZE) -> None:
    db.init_db()
    listings = db.get_unanalyzed_listings()
    if not listings:
        logger.info("analyze: nothing to analyze")
        return

    results = _analyze_and_save(listings, batch_size=batch_size)
    logger.info("analyze: %d analyzed out of %d unanalyzed", len(results), len(listings))


_REQUIRED_IMPORT_FIELDS = ("title", "company", "location", "url")


def _build_listing_from_dict(index: int, data: dict[str, Any]) -> Listing | None:
    """Build a `Listing` from one entry of an imported JSON array.

    Returns `None` (after logging a clear error) instead of raising, so one bad
    entry doesn't abort the whole import — the same per-entry resilience used
    throughout `discovery.py`'s adapters and `db.py`.
    """
    missing = [key for key in _REQUIRED_IMPORT_FIELDS if key not in data]
    if missing:
        logger.error(
            "import-listings: entry %d missing required field(s) %s — skipping", index, missing
        )
        return None

    non_string_required = [key for key in _REQUIRED_IMPORT_FIELDS if not isinstance(data[key], str)]
    if non_string_required:
        logger.error(
            "import-listings: entry %d has non-string value(s) for %s — skipping",
            index,
            non_string_required,
        )
        return None

    url = data["url"]
    listing_id = data.get("id") or hashlib.sha256(url.encode()).hexdigest()[:16]
    updated_at = data.get("updated_at") or date.today().isoformat()
    description = data.get("description", "")
    source = data.get("source", "unknown")

    optional_fields = {
        "id": listing_id,
        "updated_at": updated_at,
        "description": description,
        "source": source,
    }
    non_string_optional = [
        key for key, value in optional_fields.items() if not isinstance(value, str)
    ]
    if non_string_optional:
        logger.error(
            "import-listings: entry %d has non-string value(s) for %s — skipping",
            index,
            non_string_optional,
        )
        return None

    return Listing(
        id=listing_id,
        title=data["title"],
        company=data["company"],
        location=data["location"],
        url=url,
        updated_at=updated_at,
        description=description,
        source=source,
    )


def run_import_listings(path: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            raw_entries = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("import-listings: could not read/parse %s: %s", path, exc)
        return

    if not isinstance(raw_entries, list):
        logger.error(
            "import-listings: expected a JSON array of objects in %s, got %s",
            path,
            type(raw_entries).__name__,
        )
        return

    listings: list[Listing] = []
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            logger.error("import-listings: entry %d is not a JSON object — skipping", index)
            continue
        listing = _build_listing_from_dict(index, entry)
        if listing is not None:
            listings.append(listing)

    db.init_db()
    new_listings = db.save_new_listings(listings)

    logger.info(
        "import-listings: %d entries in file, %d parsed successfully, %d genuinely new",
        len(raw_entries),
        len(listings),
        len(new_listings),
    )
    print(
        f"Imported {len(new_listings)} new listing(s) "
        f"({len(listings)} parsed from {len(raw_entries)} entries in {path})"
    )


def run_export_matches(top: int = DEFAULT_EXPORT_TOP, out: str | None = None) -> None:
    db.init_db()
    ranked, total = _rank_with_analysis()
    if total == 0:
        logger.info("No stored listings yet — run `career-copilot discover` first.")
        return

    top_ranked = ranked[:top]

    out_path = Path(out) if out else EXPORTS_DIR / f"matches_{date.today().isoformat()}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Career Copilot — Top {len(top_ranked)} Matches", ""]
    for listing, score, analysis in top_ranked:
        flags = _format_ai_flags(analysis)
        lines.append(f"## {listing.title} — {listing.company}")
        lines.append(f"- Location: {listing.location}")
        lines.append(f"- Score: {score}{flags}")
        lines.append(f"- Apply: {listing.url}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("export-matches: wrote %d listings to %s", len(top_ranked), out_path)
    print(f"Exported {len(top_ranked)} listings to {out_path}")


def run_morning() -> None:
    db.init_db()
    listings = discovery.discover()
    new_listings = db.save_new_listings(listings)

    analysis_by_url = _analyze_and_save(new_listings)
    logger.info(
        "morning: %d of %d new listings AI-analyzed", len(analysis_by_url), len(new_listings)
    )

    preferences = matching.load_preferences()
    ranked_new = matching.rank_listings(new_listings, preferences)

    message = notify.build_morning_message(new_listings, ranked_new, analysis_by_url)
    sent = notify.send_discord_notification(message)

    print(message)

    if sent:
        logger.info("morning: %d new listings, notification sent", len(new_listings))
    else:
        logger.info("morning: %d new listings, notification failed — see above", len(new_listings))


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        run_discover()
    elif args.command == "match":
        run_match()
    elif args.command == "morning":
        run_morning()
    elif args.command == "analyze":
        run_analyze(batch_size=args.batch_size)
    elif args.command == "import-listings":
        run_import_listings(args.path)
    elif args.command == "export-matches":
        run_export_matches(top=args.top, out=args.out)


if __name__ == "__main__":
    main()
