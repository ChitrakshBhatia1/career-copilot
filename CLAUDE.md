# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Career Copilot is an AI-powered career management platform for software engineering students, built as a Python application. It is being developed from scratch with Claude Code, and this file should be kept up to date as real architecture, commands, and conventions come into existence.

Near-term work follows the approved v0.1 MVP roadmap (see `/Users/chitrakshbhatia/.claude/plans/starry-tickling-llama.md`), scoped to project foundation, discovery from a small number of sources, SQLite persistence, rule-based resume matching, and daily notifications. The rest of the vision below is deferred until v0.1 ships.

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
uv run ruff format .           # auto-format (drop --check to actually rewrite)
```
