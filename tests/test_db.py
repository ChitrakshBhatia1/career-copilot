import sqlite3

from career_copilot.db import init_db, save_new_listings
from career_copilot.discovery import Listing


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
