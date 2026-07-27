import sqlite3

from career_copilot.ai.models import AIAnalysis
from career_copilot.db import (
    get_all_listings,
    get_all_listings_with_analysis,
    get_unanalyzed_listings,
    init_db,
    save_ai_analysis,
    save_new_listings,
)
from career_copilot.discovery import Listing

OLD_CREATE_LISTINGS_TABLE = """
CREATE TABLE listings (
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    updated_at TEXT NOT NULL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _use_tmp_db(monkeypatch, tmp_path):
    # db.py resolves both DB_DIR (for mkdir) and DB_FILE (for the sqlite3
    # connection) at call time via module attribute lookup, so patching both
    # here redirects every read/write in the module under test to tmp_path
    # instead of the real project data/ directory.
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("career_copilot.db.DB_DIR", tmp_path)
    monkeypatch.setattr("career_copilot.db.DB_FILE", db_file)
    return db_file


def _make_listing(url: str, title: str = "Software Engineer, Intern") -> Listing:
    return Listing(
        id="1",
        title=title,
        company="Anthropic",
        location="Remote",
        url=url,
        updated_at="2026-07-01T00:00:00Z",
    )


def test_init_db_is_idempotent_and_creates_db_file(monkeypatch, tmp_path):
    db_file = _use_tmp_db(monkeypatch, tmp_path)

    init_db()

    assert db_file.exists()

    # Calling again must not raise (CREATE TABLE IF NOT EXISTS).
    init_db()

    assert db_file.exists()


def test_save_new_listings_inserts_new_listings_and_returns_them(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    listings = [
        _make_listing("https://example.com/1"),
        _make_listing("https://example.com/2"),
    ]

    new_listings = save_new_listings(listings)

    assert new_listings == listings


def test_save_new_listings_dedups_by_url_not_by_other_fields(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    first = _make_listing("https://example.com/1", title="Software Engineer, Intern")
    save_new_listings([first])

    # Same URL, different title -> the dedup key must be the URL, not
    # object/field identity, so this must not come back as "new".
    updated = _make_listing("https://example.com/1", title="Senior Software Engineer")

    new_listings = save_new_listings([updated])

    assert new_listings == []


def test_data_persists_across_separate_connections(monkeypatch, tmp_path):
    db_file = _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    listing = _make_listing("https://example.com/1")
    save_new_listings([listing])

    # Simulate a process restart: open a brand new connection directly,
    # rather than reusing anything cached by save_new_listings.
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT url, title FROM listings").fetchall()

    assert rows == [(listing.url, listing.title)]

    # A subsequent call in a "new process" must still recognize the URL as
    # already seen and not report it as new again.
    new_listings = save_new_listings([listing])

    assert new_listings == []


def test_save_new_listings_returns_only_brand_new_from_mixed_batch(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    already_seen = _make_listing("https://example.com/1")
    save_new_listings([already_seen])

    brand_new = _make_listing("https://example.com/2")

    new_listings = save_new_listings([already_seen, brand_new])

    assert new_listings == [brand_new]


def test_init_db_migrates_pre_existing_db_missing_new_columns(monkeypatch, tmp_path):
    # Simulate a database created before M5 added description/source: build
    # the OLD 7-column schema by hand and insert a row directly via raw SQL,
    # bypassing db.py entirely so nothing here depends on the new columns.
    db_file = _use_tmp_db(monkeypatch, tmp_path)
    with sqlite3.connect(db_file) as conn:
        conn.execute(OLD_CREATE_LISTINGS_TABLE)
        conn.execute(
            "INSERT INTO listings (id, title, company, location, url, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                "1",
                "Software Engineer, Intern",
                "Anthropic",
                "Remote",
                "https://example.com/1",
                "2026-07-01T00:00:00Z",
            ),
        )
        conn.commit()

    # init_db() must not raise when run against this pre-existing, old-shape
    # database, and must add the missing columns via ALTER TABLE.
    init_db()

    with sqlite3.connect(db_file) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(listings)")}
        assert "description" in columns
        assert "source" in columns

        row = conn.execute(
            "SELECT id, title, description, source FROM listings WHERE id = ?", ("1",)
        ).fetchone()

    # The pre-existing row is untouched, and the new columns backfill to
    # their declared defaults for it.
    assert row == ("1", "Software Engineer, Intern", "", "unknown")


def test_save_and_get_all_listings_round_trips_description_and_source(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    listing = Listing(
        id="1",
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
        description="Build cool things with a great team.",
        source="greenhouse",
    )

    save_new_listings([listing])

    assert get_all_listings() == [listing]


def test_get_unanalyzed_listings_only_returns_rows_missing_ai_analyzed_at(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    analyzed = _make_listing("https://example.com/1")
    unanalyzed = _make_listing("https://example.com/2")
    save_new_listings([analyzed, unanalyzed])

    save_ai_analysis(
        analyzed.url,
        AIAnalysis(
            visa_sponsorship_mentioned=True,
            likely_summer_2027_eligible=True,
            notes="Great fit.",
        ),
    )

    remaining = get_unanalyzed_listings()

    assert remaining == [unanalyzed]


def test_save_ai_analysis_round_trips_through_get_all_listings_with_analysis(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    init_db()

    analyzed = _make_listing("https://example.com/1")
    unanalyzed = _make_listing("https://example.com/2")
    save_new_listings([analyzed, unanalyzed])

    analysis = AIAnalysis(
        visa_sponsorship_mentioned=True,
        likely_summer_2027_eligible=False,
        notes="Mentions sponsorship but timeline unclear.",
    )
    save_ai_analysis(analyzed.url, analysis)

    pairs = get_all_listings_with_analysis()
    results_by_url = {listing.url: listing_analysis for listing, listing_analysis in pairs}

    assert results_by_url[analyzed.url] == analysis
    assert results_by_url[unanalyzed.url] is None
