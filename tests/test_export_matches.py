import logging
from datetime import date

from career_copilot import cli, db
from career_copilot.cli import _rank_with_analysis, run_export_matches
from career_copilot.discovery import Listing
from career_copilot.matching import Preferences

# Independent of config/preferences.toml on purpose, same rationale as
# test_matching.py: constructing Preferences directly keeps these tests
# working even if the user edits their real preferences file later.
PREFS = Preferences(
    role_keywords=["Software Engineer", "Intern"],
    priority_cities=["Bengaluru"],
    priority_weight=3,
    exclude_keywords=["Senior"],
)


def _use_tmp_db(monkeypatch, tmp_path):
    # Same isolation pattern as tests/test_db.py.
    db_file = tmp_path / "test.db"
    monkeypatch.setattr("career_copilot.db.DB_DIR", tmp_path)
    monkeypatch.setattr("career_copilot.db.DB_FILE", db_file)
    return db_file


def _make_listing(
    id_: str, title: str = "Software Engineer, Intern", location: str = "Remote"
) -> Listing:
    return Listing(
        id=id_,
        title=title,
        company="Anthropic",
        location=location,
        url=f"https://example.com/{id_}",
        updated_at="2026-07-01T00:00:00Z",
    )


def test_rank_with_analysis_returns_empty_when_no_stored_listings(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()

    ranked, total = _rank_with_analysis()

    assert ranked == []
    assert total == 0


def test_rank_with_analysis_returns_ranked_results_with_total_stored_count(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()
    monkeypatch.setattr("career_copilot.matching.load_preferences", lambda: PREFS)

    listings = [
        _make_listing("1", title="Software Engineer, Intern", location="Bengaluru"),
        _make_listing("2", title="Marketing Coordinator", location="Remote"),
    ]
    db.save_new_listings(listings)

    ranked, total = _rank_with_analysis()

    assert total == 2
    # Both listings are kept (only exclude_keywords drop a listing entirely);
    # the marketing listing merely scores 0 and sorts last.
    assert len(ranked) == 2
    top_listing, top_score, top_analysis = ranked[0]
    assert top_listing.id == "1"
    assert top_score > 0
    assert top_analysis is None


def test_run_export_matches_writes_to_default_path_when_out_is_none(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()
    monkeypatch.setattr("career_copilot.matching.load_preferences", lambda: PREFS)
    exports_dir = tmp_path / "exports"
    monkeypatch.setattr(cli, "EXPORTS_DIR", exports_dir)

    db.save_new_listings([_make_listing("1")])

    run_export_matches(top=20, out=None)

    expected_path = exports_dir / f"matches_{date.today().isoformat()}.md"
    assert expected_path.exists()


def test_run_export_matches_respects_explicit_out_path(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()
    monkeypatch.setattr("career_copilot.matching.load_preferences", lambda: PREFS)

    db.save_new_listings([_make_listing("1")])

    out_path = tmp_path / "custom" / "my-matches.md"
    run_export_matches(top=20, out=str(out_path))

    assert out_path.exists()


def test_run_export_matches_respects_top_limit(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()
    monkeypatch.setattr("career_copilot.matching.load_preferences", lambda: PREFS)

    listings = [
        _make_listing(str(i), title="Software Engineer, Intern", location="Bengaluru")
        for i in range(5)
    ]
    db.save_new_listings(listings)

    out_path = tmp_path / "top-limited.md"
    run_export_matches(top=2, out=str(out_path))

    content = out_path.read_text(encoding="utf-8")
    heading_lines = [line for line in content.splitlines() if line.startswith("## ")]
    assert len(heading_lines) == 2


def test_run_export_matches_with_zero_stored_listings_does_not_create_file(
    monkeypatch, tmp_path, caplog
):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()

    out_path = tmp_path / "should-not-exist.md"

    with caplog.at_level(logging.INFO):
        run_export_matches(top=20, out=str(out_path))

    assert not out_path.exists()
    assert any(record.levelno == logging.INFO for record in caplog.records)


def test_run_export_matches_content_includes_listing_url(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    db.init_db()
    monkeypatch.setattr("career_copilot.matching.load_preferences", lambda: PREFS)

    listing = _make_listing("1", title="Software Engineer, Intern", location="Bengaluru")
    db.save_new_listings([listing])

    out_path = tmp_path / "matches.md"
    run_export_matches(top=20, out=str(out_path))

    content = out_path.read_text(encoding="utf-8")
    assert listing.url in content
