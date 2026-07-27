import logging
import sqlite3
from pathlib import Path

from career_copilot.ai.models import AIAnalysis
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
INSERT OR IGNORE INTO listings
    (id, title, company, location, url, updated_at, description, source)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

SELECT_ALL_LISTINGS = """
SELECT id, title, company, location, url, updated_at, description, source FROM listings
"""

SELECT_UNANALYZED_LISTINGS = """
SELECT id, title, company, location, url, updated_at, description, source
FROM listings WHERE ai_analyzed_at IS NULL
"""

UPDATE_AI_ANALYSIS = """
UPDATE listings
SET ai_visa_sponsorship = ?, ai_summer_2027_eligible = ?, ai_notes = ?,
    ai_analyzed_at = CURRENT_TIMESTAMP
WHERE url = ?
"""

SELECT_ALL_LISTINGS_WITH_ANALYSIS = """
SELECT id, title, company, location, url, updated_at, description, source,
       ai_visa_sponsorship, ai_summer_2027_eligible, ai_notes, ai_analyzed_at
FROM listings
"""


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db() -> None:
    DB_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(CREATE_LISTINGS_TABLE)
        _add_column_if_missing(conn, "listings", "description", "TEXT NOT NULL DEFAULT ''")
        _add_column_if_missing(conn, "listings", "source", "TEXT NOT NULL DEFAULT 'unknown'")
        _add_column_if_missing(conn, "listings", "ai_visa_sponsorship", "INTEGER")
        _add_column_if_missing(conn, "listings", "ai_summer_2027_eligible", "INTEGER")
        _add_column_if_missing(conn, "listings", "ai_notes", "TEXT")
        _add_column_if_missing(conn, "listings", "ai_analyzed_at", "TIMESTAMP")


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
                    listing.description,
                    listing.source,
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


def get_unanalyzed_listings() -> list[Listing]:
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(SELECT_UNANALYZED_LISTINGS).fetchall()
    return [Listing(*row) for row in rows]


def save_ai_analysis(url: str, analysis: AIAnalysis) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            UPDATE_AI_ANALYSIS,
            (
                int(analysis.visa_sponsorship_mentioned),
                int(analysis.likely_summer_2027_eligible),
                analysis.notes,
                url,
            ),
        )
        conn.commit()


def get_all_listings_with_analysis() -> list[tuple[Listing, AIAnalysis | None]]:
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(SELECT_ALL_LISTINGS_WITH_ANALYSIS).fetchall()

    results: list[tuple[Listing, AIAnalysis | None]] = []
    for row in rows:
        listing = Listing(*row[:8])
        ai_visa, ai_2027, ai_notes, ai_analyzed_at = row[8:]
        analysis = (
            AIAnalysis(
                visa_sponsorship_mentioned=bool(ai_visa),
                likely_summer_2027_eligible=bool(ai_2027),
                notes=ai_notes or "",
            )
            if ai_analyzed_at is not None
            else None
        )
        results.append((listing, analysis))
    return results
