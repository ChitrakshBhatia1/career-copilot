# Engineering Decisions

A log of significant technical decisions made on Career Copilot: what was decided, what else was considered, why, and the trade-offs accepted. Kept alongside the code as both a build log and interview-prep reference.

---

## 2026-07-27 — Package manager: uv

**Decision:** Use `uv` to manage the virtual environment, dependencies, and project metadata (`pyproject.toml` / `uv.lock`).

**Alternatives considered:**
- `pip` + `requirements.txt` — standard library tooling, nothing new to install, matches most tutorials.

**Rationale:** `uv` is fast (Rust-based), replaces `venv` + `pip` + `pyenv` with a single tool, and produces a lockfile by default for reproducible installs — the closest Python equivalent to Maven/Gradle-style dependency resolution.

**Trade-offs accepted:** one more CLI to learn alongside Python itself and everything else being introduced this week; slightly less overlap with pip-based tutorials/Stack Overflow answers encountered while learning.

---

## 2026-07-27 — CLI framework: argparse

**Decision:** Build the CLI (`career-copilot discover`, `career-copilot morning`, etc.) with the standard library's `argparse`.

**Alternatives considered:**
- `typer` — type-hint-driven, very ergonomic, good showcase of Python type hints.
- `click` — long-standing standard for non-trivial Python CLIs, more explicit than typer.

**Rationale:** zero new dependencies, and keeps the foundation milestone's new-concept count low while other new tools (`uv`, `logging`) are already being introduced.

**Trade-offs accepted:** more boilerplate than `typer`/`click` for subcommands and argument definitions; forgoes the type-hint-driven ergonomics `typer` would have shown off.

---

## 2026-07-27 — Logging: stdlib `logging`, console + rotating file handler

**Decision:** Central logging setup using the standard library `logging` module — console handler at INFO+, `RotatingFileHandler` at DEBUG+ writing to `logs/`.

**Alternatives considered:**
- Console-only logging (no file handler) — simpler, one fewer concept (log rotation/file handlers) in the first milestone.

**Rationale:** the project is meant to run unattended every morning; a rotating file gives a persistent, debuggable history of each run without manual log management. No new dependency required.

**Trade-offs accepted:** introduces log rotation/file-handler configuration as an extra concept in the foundation milestone, on top of the CLI and packaging concepts already being introduced.
