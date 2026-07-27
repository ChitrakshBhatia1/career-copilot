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

---

## 2026-07-27 — HTTP client library: httpx

**Decision:** Use `httpx` for outbound HTTP requests to source APIs (starting with Greenhouse).

**Alternatives considered:**
- `requests` — more ubiquitous, simpler sync-only mental model, would've been marginally easier for someone new to Python.

**Rationale:** chosen to keep the door open for async I/O later (e.g. once M1 grows past 2 hardcoded sources and fetching sequentially becomes slow, or once multi-agent orchestration in the deferred roadmap wants concurrent fetches), and its API is close enough to `requests` that the learning cost is low.

**Trade-offs accepted:** one more concept than `requests` would have introduced this early (though M1 itself uses it synchronously, not `async`/`await`, so the immediate cost is minimal); slightly smaller community/StackOverflow surface than `requests`.

---

## 2026-07-27 — ATS + initial sources: Greenhouse Boards API, Anthropic + Stripe

**Decision:** Fetch listings from the public Greenhouse Boards API (`boards-api.greenhouse.io/v1/boards/{token}/jobs`), starting with two sources: Anthropic and Stripe.

**Alternatives considered:**
- Lever API (`jobs.lever.co`) as the ATS — also public/no-auth, but Greenhouse was picked first since it's the more common ATS among target companies; other company pairs (e.g. Figma+Coinbase, Palantir+Plaid) were considered but not required for M1's "≥2 sources" bar.

**Rationale:** `boards-api.greenhouse.io/v1/boards/{token}/jobs` requires no authentication, returns a simple, fully-documented-by-observation JSON shape (`{"jobs": [...], "meta": {...}}`, no pagination), and both companies were confirmed live during implementation to actually return real, current listings (Stripe currently has a live "Software Engineer, Intern" Bengaluru posting matching the keyword filter; Anthropic currently returns zero intern/2027 matches, which is an expected empty-result state, not a bug).

**Trade-offs accepted:** hardcoded to exactly these two companies/board tokens for now — no config file or dynamic source list yet (that's implicitly deferred to whenever sources need to become user-configurable, not explicitly scheduled); Lever's slightly different JSON shape is untested by this implementation.

---

## 2026-07-27 — SQLite access: raw stdlib `sqlite3`, with a repository-function pattern

**Decision:** Use the standard library's `sqlite3` module for persistence, with all SQL isolated in a single new module (`db.py`) exposing repository-style functions (`init_db()`, `save_new_listings()`) rather than raw SQL scattered across call sites.

**Alternatives considered:**
- A thin wrapper library (e.g. `sqlite-utils`) — nicer ergonomics (dict-based inserts, automatic schema management) at the cost of a new dependency.

**Rationale:** consistent with this project's stdlib-first bias (mirrors the `argparse` and `logging` decisions from M0) — `sqlite3` is fully sufficient for a single-table, single-process CLI tool with no concurrent writers, and isolating all SQL in one module keeps the option open to swap in a wrapper or a different backend later without touching call sites elsewhere.

**Trade-offs accepted:** more verbose than a wrapper would be (raw SQL strings, manual cursor/rowcount handling for detecting which rows were newly inserted); no automatic migrations — schema changes will need to be hand-written as the table evolves (e.g. when M3 adds a `score` column, if that's how matching gets wired in).
