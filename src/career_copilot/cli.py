import argparse
import logging

from career_copilot import discovery
from career_copilot.logging_config import setup_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-copilot",
        description="AI-powered career management platform for software engineering students.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("discover", help="Search configured sources for new opportunities.")
    return parser


def run_discover() -> None:
    listings = discovery.discover()
    for listing in listings:
        print(f"{listing.title} — {listing.company} ({listing.location})\n  {listing.url}")


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        run_discover()


if __name__ == "__main__":
    main()
