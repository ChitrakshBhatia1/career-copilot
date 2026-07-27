import argparse
import logging

from career_copilot import ai_analysis, db, discovery, matching, notify
from career_copilot.ai.models import AIAnalysis
from career_copilot.discovery import Listing
from career_copilot.env import load_dotenv
from career_copilot.logging_config import setup_logging

logger = logging.getLogger(__name__)

DEFAULT_ANALYZE_BATCH_SIZE = 40


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


def run_match() -> None:
    db.init_db()
    listings_with_analysis = db.get_all_listings_with_analysis()
    if not listings_with_analysis:
        logger.info("No stored listings yet — run `career-copilot discover` first.")
        return

    analysis_by_url = {listing.url: analysis for listing, analysis in listings_with_analysis}
    listings = [listing for listing, _ in listings_with_analysis]

    preferences = matching.load_preferences()
    ranked = matching.rank_listings(listings, preferences)

    logger.info("match: %d of %d stored listings ranked", len(ranked), len(listings))
    for listing, score in ranked:
        flags = _format_ai_flags(analysis_by_url.get(listing.url))
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


if __name__ == "__main__":
    main()
