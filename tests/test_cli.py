import logging

from career_copilot.cli import build_parser, main


def test_build_parser_parses_discover_command():
    parser = build_parser()
    args = parser.parse_args(["discover"])
    assert args.command == "discover"


def test_main_runs_discover_without_error():
    main(["discover"])


def test_main_configures_logging():
    main(["discover"])
    assert logging.getLogger().handlers
