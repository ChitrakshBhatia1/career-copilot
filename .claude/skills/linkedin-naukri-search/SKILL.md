---
name: linkedin-naukri-search
description: Interactively search LinkedIn Jobs or Naukri for internship/new-grad listings using the user's own logged-in Chrome session (via claude-in-chrome), then import the results into Career Copilot. On-demand only — never run this unattended or as part of a scheduled job.
---

# LinkedIn / Naukri interactive search

Career Copilot's automated `discover`/`morning` pipeline deliberately does **not** touch LinkedIn or Naukri. Both require a logged-in session to show meaningful results and both have real anti-bot enforcement history (LinkedIn in particular has litigated scraping cases). Automating them headlessly and unattended, with a stored session, would be a real account-restriction risk. This skill exists instead as an **interactive-only** workflow: it drives the user's own already-logged-in Chrome tab via `claude-in-chrome`, runs only when the user explicitly asks for it in a live session, and never runs on a schedule.

## Non-negotiable rules

- **Never attempt to log in.** Never enter, request, paste, or reference a username, password, OTP, or any other credential for LinkedIn or Naukri, under any circumstance. Operate only on whatever session state the user's Chrome browser already has from their own normal, manual login.
- **On-demand only.** This skill is invoked because the user asked for it in this session, right now. Never suggest scheduling it, never wire it into `career-copilot morning`, never run it as a background/cron task.
- **No auto-apply.** This skill only collects listing data for the user to review and apply to manually later — consistent with the hard rule in this project's `CLAUDE.md` ("any code path that could submit an application ... must include an explicit human-review/approval step — do not design 'auto-submit' flows"). Never click "Apply," never fill out an application form, never submit anything.
- If at any point the browser shows a login page, a CAPTCHA, or any other authentication/verification challenge, **stop and tell the user** rather than trying to work around it.

## Steps

1. **Read `config/preferences.toml`** (in the Career Copilot project root) for `[role].keywords` — use a handful of the most relevant terms (e.g. "Software Engineer Intern", "SDE Intern", "Software Engineer") to build search queries. Don't try every keyword in the list; 2-4 targeted searches is enough.

2. **Use `claude-in-chrome`** to open and search:
   - **LinkedIn Jobs**: `https://www.linkedin.com/jobs/search/?keywords=<url-encoded keyword>` — LinkedIn defaults to the location tied to the logged-in account, so no separate location parameter is needed.
   - **Naukri**: `https://www.naukri.com/<url-encoded-keyword-with-hyphens>-jobs-in-india` (e.g. `software-engineer-intern-jobs-in-india`).

   If the browser is not already logged in to one or both sites, tell the user and skip that site — do not attempt to log in yourself (see the non-negotiable rules above).

3. **For each real listing that looks relevant**, extract:
   - `title` — the job/internship title.
   - `company` — the hiring company (not "LinkedIn"/"Naukri").
   - `location`.
   - `url` — the actual job-posting permalink, not a search-results redirect link. On LinkedIn this usually means the `/jobs/view/<id>` URL, not the `currentJobId` query-param link from the search results list.
   - `description` (optional) — a short excerpt if easily visible, not required.
   - `source` — literally `"linkedin"` or `"naukri"` depending on which site the listing came from.

4. **Write the collected listings** as a JSON array to `data/tier3_import_<today's date, YYYY-MM-DD>.json` in the Career Copilot project root, in this exact shape (matching what `career-copilot import-listings` expects):
   ```json
   [
     {
       "title": "Software Engineer Intern",
       "company": "Example Corp",
       "location": "Bengaluru, India",
       "url": "https://www.linkedin.com/jobs/view/1234567890",
       "source": "linkedin"
     }
   ]
   ```
   `id` and `updated_at` don't need to be included — `import-listings` fills in sensible defaults (a stable hash of the URL, and today's date) if they're absent.

5. **Tell the user to run**: `uv run career-copilot import-listings data/tier3_import_<date>.json` (from the Career Copilot project root) to actually persist the results — this skill does not run that command itself, so the user stays in control of what gets added to their tracked listings.

## What this skill deliberately does not do

- It does not run automatically or on any kind of schedule.
- It does not store or reuse any LinkedIn/Naukri credentials.
- It does not apply to anything on the user's behalf.
- It does not re-run the keyword filter that the automated sources use (`discovery.matches_keywords()`) — by the time a listing gets into the import JSON, a human (via this interactive session) has already judged it relevant.
