import logging

from career_copilot.cli import build_parser, main


def test_build_parser_parses_discover_command():
    parser = build_parser()
    args = parser.parse_args(["discover"])
    assert args.command == "discover"


def test_build_parser_parses_import_listings_command():
    parser = build_parser()
    args = parser.parse_args(["import-listings", "listings.json"])
    assert args.command == "import-listings"
    assert args.path == "listings.json"


def test_build_parser_parses_export_matches_command_with_options():
    parser = build_parser()
    args = parser.parse_args(["export-matches", "--top", "5", "--out", "out.md"])
    assert args.command == "export-matches"
    assert args.top == 5
    assert args.out == "out.md"


def test_build_parser_parses_export_matches_command_with_defaults():
    parser = build_parser()
    args = parser.parse_args(["export-matches"])
    assert args.command == "export-matches"
    assert args.top == 20
    assert args.out is None


def test_main_runs_discover_without_error():
    main(["discover"])


def test_main_configures_logging():
    main(["discover"])
    assert logging.getLogger().handlers
