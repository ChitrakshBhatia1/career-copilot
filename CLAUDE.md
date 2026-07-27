# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Career Copilot is an AI-powered career management platform for software engineering students, built as a Python application. It is being developed from scratch with Claude Code, and this file should be kept up to date as real architecture, commands, and conventions come into existence.

The approved v0.1 MVP roadmap (see `/Users/chitrakshbhatia/.claude/plans/starry-tickling-llama.md`), scoped to project foundation, discovery from a small number of sources, SQLite persistence, rule-based resume matching, and daily notifications, has now shipped in full — `career-copilot morning` is the resulting daily-use command. The rest of the vision below remains deferred/aspirational until explicitly picked back up.

The initial focus is Summer 2027 internship and new-grad opportunity discovery, primarily for the Indian market with openness to opportunities abroad. Planned capabilities, roughly in order of build-out:

1. **Opportunity discovery** — finding internship/new-grad listings relevant to the user.
2. **Browser automation** — visiting company career pages, extracting listing data, and determining eligibility/fit automatically.
3. **Resume matching and scoring** — evaluating a listing against the user's stated preferences (target role/internship type, to be specified in detail later).
4. **AI-powered resume tailoring** — rewording resume content to reflect keywords pulled from a specific job listing.
5. **Cover letter generation**.
6. **Application tracking**.
7. **Daily summaries and notifications**.
8. **Multi-agent orchestration** — separate AI agents own separate responsibilities across the pipeline (discovery, matching, tailoring, tracking, etc.), with the user able to review and approve output at each stage before anything proceeds — especially before any actual application submission. No stage should auto-submit without explicit user review.

## Current state

M0 (project foundation) is complete: a `uv`-managed `src/` layout package (`src/career_copilot/`) with an `argparse`-based CLI (`cli.py`), centralized logging (`logging_config.py` — console INFO+, rotating file DEBUG+ under `logs/`), a `pytest` suite (`tests/`), and `ruff` for linting/formatting. `hello.py` and the old plain `.venv` are gone. Significant technical decisions are logged in `docs/engineering-decisions.md` as they're made. Do not assume any of the architecture below already exists in code beyond what's described here — treat the rest as the direction to build toward. As real modules, dependencies, and tooling are added, update this file so it stays accurate rather than aspirational.

M1 (discovery from a small number of sources) is also complete: a new `discovery.py` module fetches live listings from the public Greenhouse Boards API for two hardcoded sources (Anthropic and Stripe), filters them down to internship/2027-relevant titles with a word-boundary keyword regex, and returns them as frozen `Listing` dataclasses. Per-source fetch failures (network errors, malformed JSON) are caught and logged rather than crashing the whole run. The `career-copilot discover` command now calls this module and prints the surviving listings instead of the old stub. This pulled in `httpx` as a new dependency for outbound HTTP requests; see `docs/engineering-decisions.md` for why `httpx` was chosen over `requests` and why Greenhouse/Anthropic/Stripe were chosen as the initial sources.

M2 (SQLite persistence) is also complete: a new `db.py` module uses raw stdlib `sqlite3` to persist discovered listings to a `listings` table (SQLite file under `data/`, gitignored), with `url` as a UNIQUE constraint acting as the dedup key. `init_db()` idempotently creates the `data/` directory and table; `save_new_listings()` inserts via `INSERT OR IGNORE` and returns only the listings that were genuinely new. `career-copilot discover` now calls both after `discovery.discover()`, so re-running the command on the same day correctly reports 0 new listings instead of re-showing ones already seen. See `docs/engineering-decisions.md` for why raw `sqlite3` (over a wrapper like `sqlite-utils`) was chosen.

M3 (rule-based resume matching) is also complete: a new `config/preferences.toml` holds the user's target-role keywords, priority India cities, and seniority exclude terms, and a new `matching.py` module (`load_preferences()`, using stdlib `tomllib`) scores each stored listing by counting how many role keywords match its title plus a bonus if its location is a priority city, while dropping the listing entirely if its title matches any exclude keyword. The new `career-copilot match` command reads all listings from SQLite via `db.get_all_listings()`, scores/ranks them against `config/preferences.toml`, and prints them highest-score-first. Note: scoring currently only looks at each listing's title and location, not its full job-description text, so it can't yet detect true Summer 2027 date windows or visa-sponsorship-for-abroad-roles — those are keyword-proxied (e.g. matching on "2027", "Summer Internship") rather than actually verified for now. See `docs/engineering-decisions.md` for why TOML/`tomllib` was chosen for the preferences file.

M4 (daily notifications) is also complete: a new `env.py` module provides a minimal stdlib-only `.env` file loader (`load_dotenv()`), used so a `DISCORD_WEBHOOK_URL` secret can live in a gitignored `.env` file during local/cron runs without pulling in `python-dotenv`; real shell-exported env vars still take precedence over the file. A new `notify.py` module builds the daily notification text (`build_morning_message()` — new-listing count plus top-N ranked matches, or an explicit "0 new listings" message so silence never means "did it even run?") and sends it to a Discord webhook (`send_discord_notification()`), logging an error and returning `False` rather than crashing if the webhook URL is unset, the request fails, or Discord returns a non-2xx status; over-long messages are truncated to Discord's 2000-character limit. The new `career-copilot morning` command chains `discovery.discover()` → `db.save_new_listings()` → `matching.rank_listings()` (ranking only today's new listings, not the whole historical DB) → `notify.build_morning_message()` → `notify.send_discord_notification()`, and always prints the built message to stdout regardless of whether the Discord send succeeded — so the command degrades gracefully and exits 0 even when `DISCORD_WEBHOOK_URL` isn't configured, since discovery/persistence/matching still did real work. See `docs/engineering-decisions.md` for why Discord webhook (over Slack/Telegram/email) and a custom `.env` loader (over `python-dotenv`) were chosen.

With M4 complete, the v0.1 MVP is done: all four scoped milestones (M0–M4 — foundation, discovery, persistence, matching, notifications) are built and tested, and `career-copilot morning` is the intended daily-use command going forward. The "Deferred: post-MVP roadmap" items from the planning doc — an AI client layer, LLM-powered resume tailoring, cover letter generation, application tracking, browser automation, multi-agent orchestration, RAG, and a dashboard — remain explicitly out of scope until revisited.

Work has now picked back up with a v0.2 upgrade (M5–M9) building on top of the shipped v0.1 MVP, adding job-description-based filtering, many more discovery sources, browser automation, and an AI enrichment layer. M5 (job description text + DB/schema foundation) is complete: a new `htmltext.py` module's `strip_html()` strips a job description down to plain text using `beautifulsoup4` (`html.parser` backend, no `lxml` — see `docs/engineering-decisions.md` for why this is only the second stdlib-first exception in the project after `httpx`). Worth keeping visible here, not just in the decision log: Greenhouse's job `content` field comes back **double HTML-entity-escaped** (the raw string literally contains `&lt;h2&gt;` rather than a real `<h2>` tag), so `strip_html()` calls `html.unescape()` before handing the string to BeautifulSoup — any future code touching `discovery.py`'s handling of this field needs to account for the same double-escaping or parsing will silently produce garbage instead of an obvious error. `discovery.py`'s `fetch_source()` now requests `?content=true` from Greenhouse and populates two new `Listing` fields: `description: str = ""` (the stripped plain-text description) and `source: str = "unknown"` (set to `"greenhouse"` for every listing this adapter produces, so M7's upcoming multi-ATS adapters can each stamp their own value) — both are defaulted specifically so the ~35 pre-existing `Listing(...)` test call sites across the suite didn't need mechanical updates for this plumbing-only milestone. `db.py` gained an idempotent `_add_column_if_missing(conn, table, column, coltype)` helper (checks `PRAGMA table_info`, runs `ALTER TABLE ... ADD COLUMN` only if missing), used by `init_db()` to add the new `description`/`source` columns to the `listings` table; this was verified against a real pre-existing `data/career_copilot.db` left over from the M0–M4 session, not just a fresh empty DB, confirming the same idempotent-schema-change approach M2 established still holds up on real data.

M6 (AI enrichment layer, provider-agnostic) is also complete: a new `ai/` package (`ai/base.py`'s `AIProvider` — a `typing.Protocol` with one method, `analyze_listing(listing) -> AIAnalysis | None`) with four concrete implementations — `openrouter.py`, `anthropic_provider.py`, `gemini_provider.py`, `ollama_provider.py` — each talking to its provider's REST API directly via `httpx`, no vendor SDK dependency added for any of them. `ai/factory.py` is the only module that imports all four concrete provider classes by name; it reads the new `config/ai.toml` and returns the configured provider, or `None` (never raises) if the required credential/local service isn't available. A new `config/ai.toml` holds one section per provider (model name + either an `api_key_env` var name or, for Ollama, a `base_url`) — model names live only in this file, never in application code — defaulting to `provider = "openrouter"` with `model = "openai/gpt-oss-20b:free"`; see `docs/engineering-decisions.md` for the full provider-agnostic-design and model-choice reasoning, including the mid-planning pivot away from an originally Anthropic-only M6. `db.py` gained nullable `ai_visa_sponsorship`/`ai_summer_2027_eligible`/`ai_notes`/`ai_analyzed_at` columns (via M5's migration helper) plus `get_unanalyzed_listings()` (the idempotency mechanism — a listing is never re-analyzed once it has an `ai_analyzed_at`), `save_ai_analysis()`, and `get_all_listings_with_analysis()` (a read path kept separate from `get_all_listings()` so `matching.rank_listings()` stays completely untouched — the AI layer is additive display enrichment, it never feeds the rule-based score). A new `career-copilot analyze` command (`--batch-size`, default 40 — comfortably under OpenRouter's 50-request/day free cap) runs deliberate backfills over unanalyzed listings; `career-copilot morning` now also AI-analyzes that day's new listings automatically as part of the daily run (bounded to that day's batch, not the full backlog), and both the Discord notification (`notify.build_morning_message()`, now taking an optional `analysis_by_url` parameter) and `career-copilot match`'s printed output show AI flags next to each listing (e.g. `[visa✓ | 2027-likely✓]`) when analysis is available. Graceful degradation follows the same pattern M4 established for the Discord webhook: if no provider is configured or reachable (missing `config/ai.toml`, missing API key env var, unreachable local Ollama server), analysis is skipped with a logged warning and `discover`/`match`/`morning` all continue to work normally. Note: `config/ai.toml` currently points at OpenRouter by default, which needs an `OPENROUTER_API_KEY` in a gitignored `.env` file to actually run — same external-credential pattern as M4's `DISCORD_WEBHOOK_URL`, and not yet configured as of this milestone's completion (a follow-up step, not part of M6 itself).

Because the pipeline above naturally decomposes into distinct stages (discovery, automation, matching, tailoring, generation, tracking, notification) with a multi-agent design explicitly called out, favor a modular package layout from the start (e.g. one package/module per pipeline stage) rather than a single monolithic script, even while functionality is still minimal.

## Working conventions

- **Python best practices**: use type hints, keep functions small and single-purpose, prefer standard library and well-established packages, follow PEP 8, and use a `.venv`-based environment (already present at `.venv/`) rather than global installs.
- **Small, incremental commits**: build one small feature at a time rather than large multi-feature changes. Prefer several small, reviewable commits over one large one.
- **Git-based workflow**: work happens on `develop` off `main`. Only commit when explicitly asked (see global instructions); never force-push or rewrite shared history without asking first.
- **User approval before irreversible actions**: given the eventual scope (browser automation against real company career pages, AI-generated application materials, and actual submissions), any code path that could submit an application, send an email, or otherwise act on the user's behalf on an external site must include an explicit human-review/approval step — do not design "auto-submit" flows.
- **Teaching while building**: the user is an experienced Java engineer who is new to Python and to this project's problem domain (AI agents, browser automation, resume/NLP tooling). When introducing a Python idiom, library, or agentic-AI concept that doesn't have a direct Java equivalent, briefly explain the "why," and prefer calling it out inline over silently doing something unfamiliar. No need to explain basic programming concepts — focus explanations on what's Python-specific, AI/agent-specific, or new to this domain.
- **After finishing a new feature/task, run the full check suite** (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`) and confirm it's clean before moving on to the next one.

## Commands

```bash
uv sync                        # install/update dependencies into .venv
uv run career-copilot --help   # run the CLI
uv run career-copilot discover # run a subcommand
uv run pytest                  # run the test suite
uv run ruff check .            # lint
uv run ruff format .           # auto-format (drop --check to actually rewrite)```

## Default Working Style

Assume you are the primary implementation engineer.

When given an approved milestone:

- Execute the milestone independently.
- Break work into logical commits.
- Run tests after each significant change.
- Update documentation.
- Update engineering decisions.
- Explain only important design decisions.
- Ask for input only when a real architectural decision exists.
- Otherwise continue autonomously.

Prefer progress over conversation.

Do not stop to explain anything unless I explicitly ask.

Only interrupt me when:

- external credentials are needed,
- or a change conflicts with previous engineering decisions.
- or details regarding rules/policies are needed.

Never merge to main without my approval, anything else is fine.
