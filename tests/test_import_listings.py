import json
import logging

from career_copilot import db
from career_copilot.cli import _build_listing_from_dict, run_import_listings
from career_copilot.discovery import Listing


def _use_tmp_db(monkeypatch, tmp_path):
    # Same isolation pattern as tests/test_db.py: db.py resolves DB_DIR/DB_FILE
    # at call time via module attribute lookup, so patching both redirects
    # every read/write in the module under test to tmp_path instead of the
    # real project data/ directory.
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("career_copilot.db.DB_DIR", tmp_path)
    monkeypatch.setattr("career_copilot.db.DB_FILE", db_file)
    return db_file


VALID_ENTRY = {
    "id": "abc123",
    "title": "Software Engineer, Intern",
    "company": "Anthropic",
    "location": "Remote",
    "url": "https://example.com/1",
    "updated_at": "2026-07-01T00:00:00Z",
    "description": "Build cool things.",
    "source": "linkedin",
}


def test_build_listing_from_dict_builds_correct_listing_with_all_fields():
    listing = _build_listing_from_dict(0, VALID_ENTRY)

    assert listing == Listing(
        id="abc123",
        title="Software Engineer, Intern",
        company="Anthropic",
        location="Remote",
        url="https://example.com/1",
        updated_at="2026-07-01T00:00:00Z",
        description="Build cool things.",
        source="linkedin",
    )


def test_build_listing_from_dict_defaults_id_to_deterministic_hash_of_url():
    data = {
        "title": "Software Engineer, Intern",
        "company": "Anthropic",
        "location": "Remote",
        "url": "https://example.com/no-id",
    }

    first = _build_listing_from_dict(0, data)
    second = _build_listing_from_dict(0, data)

    assert first is not None
    assert first.id == second.id
    assert first.id != ""


def test_build_listing_from_dict_defaults_updated_at_to_today():
    import datetime

    data = {
        "title": "Software Engineer, Intern",
        "company": "Anthropic",
        "location": "Remote",
        "url": "https://example.com/no-updated-at",
    }

    listing = _build_listing_from_dict(0, data)

    assert listing is not None
    assert listing.updated_at == datetime.date.today().isoformat()


def test_build_listing_from_dict_returns_none_when_required_field_missing(caplog):
    data = {
        "company": "Anthropic",
        "location": "Remote",
        "url": "https://example.com/missing-title",
    }

    with caplog.at_level(logging.ERROR):
        listing = _build_listing_from_dict(0, data)

    assert listing is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_build_listing_from_dict_returns_none_when_required_field_wrong_type(caplog):
    data = {
        "title": 12345,
        "company": "Anthropic",
        "location": "Remote",
        "url": "https://example.com/bad-title-type",
    }

    with caplog.at_level(logging.ERROR):
        listing = _build_listing_from_dict(0, data)

    assert listing is None
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_run_import_listings_persists_only_valid_entries_and_logs_error_for_bad_one(
    monkeypatch, tmp_path, caplog
):
    _use_tmp_db(monkeypatch, tmp_path)

    entries = [
        {
            "title": "Software Engineer, Intern",
            "company": "Anthropic",
            "location": "Remote",
            "url": "https://example.com/1",
        },
        {
            "title": "Backend Intern",
            "company": "Stripe",
            "location": "Bengaluru",
            "url": "https://example.com/2",
        },
        {
            # Missing "title" -> should be skipped and logged as an error.
            "company": "Missing Title Corp",
            "location": "Remote",
            "url": "https://example.com/3",
        },
    ]
    path = tmp_path / "import.json"
    path.write_text(json.dumps(entries), encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        run_import_listings(str(path))

    stored = db.get_all_listings()
    assert len(stored) == 2
    assert {listing.url for listing in stored} == {
        "https://example.com/1",
        "https://example.com/2",
    }
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_run_import_listings_is_idempotent_on_rerun(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)

    entries = [
        {
            "title": "Software Engineer, Intern",
            "company": "Anthropic",
            "location": "Remote",
            "url": "https://example.com/1",
        },
    ]
    path = tmp_path / "import.json"
    path.write_text(json.dumps(entries), encoding="utf-8")

    run_import_listings(str(path))
    assert len(db.get_all_listings()) == 1

    # Re-importing the same file must not create duplicates: save_new_listings
    # dedups by URL, so the second run should persist 0 additional listings.
    run_import_listings(str(path))

    stored = db.get_all_listings()
    assert len(stored) == 1


def test_run_import_listings_handles_missing_file_gracefully(monkeypatch, tmp_path, caplog):
    _use_tmp_db(monkeypatch, tmp_path)

    missing_path = tmp_path / "does-not-exist.json"

    with caplog.at_level(logging.ERROR):
        run_import_listings(str(missing_path))  # must not raise

    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_run_import_listings_handles_invalid_json_gracefully(monkeypatch, tmp_path, caplog):
    _use_tmp_db(monkeypatch, tmp_path)

    path = tmp_path / "invalid.json"
    path.write_text("{not valid json", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        run_import_listings(str(path))  # must not raise

    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_run_import_listings_handles_non_list_top_level_gracefully(monkeypatch, tmp_path, caplog):
    _use_tmp_db(monkeypatch, tmp_path)

    path = tmp_path / "not_a_list.json"
    path.write_text(json.dumps({"title": "not a list"}), encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        run_import_listings(str(path))  # must not raise

    assert any(record.levelno == logging.ERROR for record in caplog.records)
