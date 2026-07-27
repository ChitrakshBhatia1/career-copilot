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

---

## 2026-07-27 — Preferences config format: TOML (stdlib `tomllib`), keyword-count + location-bonus scoring with hard exclusion

**Decision:** Store the user's matching preferences in `config/preferences.toml` and parse it with the standard library's `tomllib`, with `matching.py` scoring each listing by counting matched role keywords plus a location bonus, and hard-excluding any listing whose title matches a seniority keyword.

**Alternatives considered:**
- YAML — very common for human-edited config, more familiar from other ecosystems.
- JSON — simplest parser, but worse for a hand-edited file — no comments, more punctuation-heavy for humans to maintain.

**Rationale:** `tomllib` is stdlib as of Python 3.11 (read-only, which is fine since this file is hand-edited by the user, not written by the program) — consistent with this project's stdlib-first bias already established for `argparse`, `logging`, and `sqlite3`; TOML's table syntax (`[role]`, `[location]`, `[exclude]`) also maps cleanly onto the three preference categories (keywords/location/exclusions) without extra nesting. The scoring rule itself (keyword-count + location bonus, hard-excluding any seniority-keyword match) was kept intentionally simple/flat per the roadmap's "explainable in one sentence" requirement, rather than building a weighted multi-factor model.

**Trade-offs accepted:** no write support from `tomllib` (fine today since nothing edits this file programmatically, but would need a third-party TOML writer or a format switch if that ever changes); the scoring model doesn't (yet) account for job-description content, real date ranges, or visa sponsorship — see the CLAUDE.md note below.

---

## 2026-07-27 — Notification channel: Discord webhook; `.env` loading via a minimal stdlib-only loader (not `python-dotenv`)

**Decision:** Send the daily notification as a Discord webhook POST (`notify.py`), with the webhook URL read from a `DISCORD_WEBHOOK_URL` environment variable loaded via a new minimal stdlib-only `.env` loader (`env.py`) rather than `python-dotenv`.

**Alternatives considered:**
- Notification channel: Slack webhook (equally simple, Discord preferred by the user), Telegram bot (needs two secrets — bot token + chat ID — instead of one), email via `smtplib` (needs SMTP host/port + an app-specific password, meaningfully more setup).
- `.env` loading: `python-dotenv` — the standard, more feature-complete third-party library for this.

**Rationale:** a Discord webhook needs exactly one secret (the URL) and no bot process to host or maintain, matching this project's bias toward the simplest thing that satisfies "runs unattended every morning." The `.env` loader was kept to ~15 lines of stdlib `os`/`Path` code rather than adding `python-dotenv`, consistent with every prior dependency decision in this project (only `httpx` has been added as an actual new dependency across all four milestones) — `setdefault` semantics mean real shell-exported env vars (e.g. from a cron job's environment) still win over the file.

**Trade-offs accepted:** switching channels later (e.g. to email) means writing a new `notify.py` implementation rather than reconfiguring an existing one — no abstraction over "notification channel" was built since only one was ever needed for the MVP; the custom `.env` loader doesn't handle quoted values, multiline values, or variable interpolation the way `python-dotenv` does, which is fine for a single `DISCORD_WEBHOOK_URL=...` line but would need revisiting if `.env` usage grows more complex.

---

## 2026-07-27 — HTML-to-text: `beautifulsoup4` (stdlib `html.parser` backend), not stdlib-only

**Decision:** Add `beautifulsoup4` as a dependency for stripping job-description HTML down to plain text (`htmltext.py`'s `strip_html()`), configured to use the stdlib `html.parser` backend rather than `lxml`.

**Alternatives considered:**
- Hand-rolling a tag stripper with stdlib `html.parser.HTMLParser` directly — what M1–M4's stdlib-first bias would normally favor, and the more consistent choice on precedent alone.

**Rationale:** rejected the hand-rolled option because M8 (later in this same v0.2 plan) will need real HTML/DOM parsing for Playwright-scraped pages anyway, and having two different ad hoc HTML-handling approaches in the codebase — one hand-rolled for Greenhouse, one real for Playwright — is worse than introducing one well-tested library now that covers both needs. This is the second stdlib-first exception in the project after `httpx` — both were adopted only when the stdlib alternative would mean meaningfully more hand-rolled code for something a small, well-established library does better. Using `beautifulsoup4` with the `html.parser` backend avoids also needing `lxml` (a compiled/C-extension dependency this project doesn't need the extra parsing speed from, given real data volumes are still small).

**Trade-offs accepted:** one more dependency; and a genuine gotcha worth recording here since it's not obvious and cost real debugging effort — Greenhouse's `content` field is double HTML-entity-escaped (the raw string literally contains `&lt;h2&gt;` rather than a real `<h2>` tag), so any future code touching this field must call `html.unescape()` before treating it as HTML, or parsing will silently produce garbage (visible literal tag characters instead of stripped text) rather than an obvious error.

---

## 2026-07-27 — AI provider abstraction: `typing.Protocol` + raw `httpx`, no vendor SDKs, provider-agnostic by design

**Decision:** Build the new `ai/` package around a structural-typing `Protocol` (`ai/base.py`'s `AIProvider`, one method: `analyze_listing(listing) -> AIAnalysis | None`), with four concrete implementations (OpenRouter, Anthropic, Gemini, Ollama) each talking to its provider's REST API directly via `httpx` — no `anthropic` or `google-genai` SDK dependency for any of them. `ai/factory.py` is the only module in the codebase that imports all four concrete provider classes by name; `ai_analysis.py`, `db.py`, and `cli.py` only ever see the `AIProvider` protocol and the `AIAnalysis` dataclass.

Worth stating plainly rather than folding into "alternatives considered" below: this design changed mid-planning, not just mid-implementation. M6 was originally scoped as an Anthropic-only integration. The user decided, before any code was written, that Career Copilot shouldn't be tied to a single AI vendor, and the milestone was redesigned around a provider-agnostic abstraction from that point — a genuine roadmap pivot, not a normal build-time trade-off call.

**Alternatives considered:**
- The original M6 draft: a single hardcoded Anthropic integration, likely via the official `anthropic` SDK — simpler, one provider to implement and test, but rejected outright once the provider-agnostic requirement was set; not a live option by the time implementation started.
- Official vendor SDKs (`anthropic`, `google-genai`) for the respective providers even within a multi-provider design — would mean less hand-rolled resilience/parsing code per provider, at the cost of 2+ new dependencies and an inconsistent codebase (SDK-backed for 2 of 4 providers, raw REST for the other 2, since OpenRouter and Ollama have no first-party Python SDK worth adding).

**Rationale:** all four target providers (OpenRouter, Anthropic, Gemini, Ollama) expose plain REST/JSON APIs, so `httpx` — already a dependency since M1 — covers all of them uniformly, keeping the provider count from also becoming a dependency-count problem. This also mirrors the exact pattern M7 independently needed for its own multi-ATS `SourceAdapter` design (Greenhouse/Lever/SmartRecruiters/Workday, also raw REST, also a `Protocol`) — two unrelated parts of the codebase converged on the same `Protocol`-based "swappable backend" idiom, which is a nice consistency to have discovered rather than planned up front.

**Trade-offs accepted:** no SDK-provided retry, typed-exception, or streaming conveniences — every provider adapter re-implements basic resilience itself (fixed timeout, catch `httpx.HTTPError`, log and return `None`), the same shape `discovery.fetch_source()` already established. Real added testing surface: 4 independent provider adapters each need their own mocked-request test coverage, not just one, and `ai/schema.py`'s shared `parse_analysis_response()` has to defend against each provider's raw text occasionally arriving wrapped in a ```` ```json ```` fence despite instructions not to.

---

## 2026-07-27 — Default AI provider/model: OpenRouter, `openai/gpt-oss-20b:free`

**Decision:** Default `config/ai.toml` to `provider = "openrouter"` with `model = "openai/gpt-oss-20b:free"`.

**Alternatives considered:**
- `meta-llama/llama-3.3-70b-instruct:free` — strong general accuracy, but JSON adherence comes from OpenRouter's `response_format` prompt-level wrapper rather than native structured-output training, and the larger dense model is slower on a rate-limited free tier.
- `qwen/qwen3-coder:free` — the best free model for actual coding tasks, but in real head-to-head testing its "thinking mode" was observed hallucinating JSON and ignoring format constraints, making it unreliable for this milestone's simple classification task specifically.
- `google/gemini-2.0-flash-exp:free` (via OpenRouter) — native structured output support (Gemini's API has first-class `responseSchema`), but an experimental/rotating free slug rather than a stable, durable release.

**Rationale:** `gpt-oss-20b:free` is the only candidate combining native structured-output training (OpenAI's "Harmony" response format, trained specifically for schema-adherent output rather than relying on prompting), an Apache-2.0 open-weight release hosted by multiple OpenRouter providers (meaningfully less likely to disappear than a single vendor's rotating promotional free tier), low latency from its efficient MoE architecture, and empirical evidence — from real comparative testing — of out-performing a comparable reasoning model on structured-JSON reliability specifically. This milestone's task (a 3-field classification: visa-mention yes/no, 2027-eligibility yes/no, one-sentence note) doesn't need frontier-scale capability, just reliable schema adherence, which is exactly what this model is built for.

**Trade-offs accepted:** OpenRouter's free tier caps `:free` models at 50 requests/day (1,000/day after a one-time $10 deposit that unlocks the higher cap without being spent) — a real, low ceiling, not a footnote, and the direct reason `career-copilot analyze` takes a `--batch-size` flag (default 40) rather than processing an unbounded backlog in one run. Free-model lineups on OpenRouter also rotate over time — confirmed via research that both DeepSeek's and Mistral's free variants are gone as of July 2026 — so `gpt-oss-20b:free`'s continued availability isn't guaranteed, only more likely than most alternatives given its Apache-2.0/multi-host status; `config/ai.toml`'s single-line model override is the mitigation for when that changes, not a permanent guarantee it never will.

---

## 2026-07-27 — Discovery source adapters: restructured `discovery.py` into a `discovery/` package with a `Protocol`-based `SourceAdapter` interface, config externalized to `sources.toml`

**Decision:** Restructure the single-file `discovery.py` (which hardcoded a `SOURCES` list with just Anthropic + Stripe, both Greenhouse) into a `discovery/` package: `discovery/base.py`'s `SourceAdapter`, a `typing.Protocol` with a `name` attribute and a `fetch()` method; one adapter module per ATS (`greenhouse.py` — the pre-existing logic reshaped into a class — plus three new adapters built ahead of any real company data being added: `lever.py`, `smartrecruiters.py`, `workday.py`, and a stub `icims.py`); a new `config/sources.toml` externalizing the old hardcoded `SOURCES` list (still just Anthropic + Stripe, both `adapter = "greenhouse"`, migrated unchanged); and `discovery/__init__.py`, which re-exports `Listing`/`SourceAdapter`/`matches_keywords` and holds `discover()`, now loading `sources.toml`, building adapters via a small factory (`_ADAPTER_BUILDERS`), and iterating with the same per-source try/except-log-and-continue resilience `discover()` has had since M1.

**Alternatives considered:**
- Keep `discovery.py` as a single growing file with an if/elif dispatch per ATS type — rejected as unsustainable once it needs to host 5+ ATS integrations (Greenhouse/Lever/SmartRecruiters/Workday/iCIMS) instead of 1.
- An ABC-based adapter base class instead of `Protocol` — rejected for the same reason `ai/base.py`'s `AIProvider` used `Protocol` over an ABC: structural typing, no forced inheritance, consistent idiom across the codebase, now used in two independent places.

**Rationale:** this exactly mirrors the pattern M6 already established one milestone earlier for AI providers — worth noting explicitly that this consistency emerged from two independently-motivated designs converging on the same idiom, not from copying one into the other after the fact. Landing the restructure as its own commit, before any of the 28 new companies were added, keeps "move code around" and "add new sources" independently reviewable and revertable.

**Trade-offs accepted:** this is a larger mechanical diff than most milestones' changes (every existing test importing from the old flat `discovery.py` needed rewriting against the new package paths); real API research surfaced genuine gaps versus the original plan's assumptions (Lever has no `updatedAt`, SmartRecruiters/Workday can't get descriptions without N+1 requests, iCIMS has no usable public API at all) — recorded here since they affect what "broad source coverage" can actually promise for M7's non-Greenhouse companies (some will simply have no description text, unlike Greenhouse's).
