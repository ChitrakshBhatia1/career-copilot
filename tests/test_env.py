import os

from career_copilot.env import load_dotenv


def test_load_dotenv_nonexistent_path_is_noop(monkeypatch, tmp_path):
    monkeypatch.delenv("FOO", raising=False)
    before = dict(os.environ)

    load_dotenv(tmp_path / "does-not-exist.env")

    assert dict(os.environ) == before
    assert "FOO" not in os.environ


def test_load_dotenv_sets_env_vars_from_well_formed_file(monkeypatch, tmp_path):
    monkeypatch.delenv("FOO", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=bar\n")

    load_dotenv(env_file)

    assert os.environ["FOO"] == "bar"


def test_load_dotenv_skips_blank_lines_and_comments(monkeypatch, tmp_path):
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("\n# a comment\nFOO=bar\n\n# another comment\nBAZ=qux\n")

    load_dotenv(env_file)

    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux"


def test_load_dotenv_does_not_override_existing_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("FOO", "existing")
    env_file = tmp_path / ".env"
    env_file.write_text("FOO=fromfile\n")

    load_dotenv(env_file)

    assert os.environ["FOO"] == "existing"
