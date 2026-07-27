"""Minimal .env file loader.

Python has no stdlib .env support (unlike e.g. Spring Boot's built-in
application.properties/env handling in Java). Rather than pull in
python-dotenv, this project follows its existing pattern of preferring
small stdlib-only implementations (argparse, sqlite3, tomllib) over
third-party dependencies where the need is simple.
"""

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path(".env")


def load_dotenv(path: Path = DEFAULT_ENV_PATH) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        # setdefault means a real shell-exported env var always wins over
        # the file — important for CI/cron overrides later.
        os.environ.setdefault(key.strip(), value.strip())
