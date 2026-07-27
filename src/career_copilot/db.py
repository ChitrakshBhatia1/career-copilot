import logging
import sqlite3
from pathlib import Path

from career_copilot.discovery import Listing

logger = logging.getLogger(__name__)

DB_DIR = Path("data")
DB_FILE = DB_DIR / "career_copilot.db"

CREATE_LISTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    updated_at TEXT NOT NULL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

INSERT_LISTING = """
INSERT OR IGNORE INTO listings (id, title, company, location, url, updated_at)
VALUES (?, ?, ?, ?, ?, ?)
"""

SELECT_ALL_LISTINGS = """
SELECT id, title, company, location, url, updated_at FROM listings
"""


def init_db() -> None:
    DB_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(CREATE_LISTINGS_TABLE)


def save_new_listings(listings: list[Listing]) -> list[Listing]:
    new_listings: list[Listing] = []
    with sqlite3.connect(DB_FILE) as conn:
        for listing in listings:
            cursor = conn.execute(
                INSERT_LISTING,
                (
                    listing.id,
                    listing.title,
                    listing.company,
                    listing.location,
                    listing.url,
                    listing.updated_at,
                ),
            )
            if cursor.rowcount:
                new_listings.append(listing)
        conn.commit()
    return new_listings


def get_all_listings() -> list[Listing]:
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(SELECT_ALL_LISTINGS).fetchall()
    return [Listing(*row) for row in rows]
