# NEXT — Pivot: Email-based Job Matching

## Why

Original pipeline (scrape JD URL → tailor resume → auto-apply) is too fragile
(site scraping, ToS risk) and rewriting the resume per-job adds noise without
real value. Pivot to: **search job offers already sitting in the mailbox**
(LinkedIn/Indeed/WTTJ/Glassdoor alert digests, recruiter emails), score them
against a fixed profile, surface matches in a GUI. No resume rewriting.

## Scope changes

### Drop
- `src/tailor.py` — Ollama resume rewriting. Removed entirely.
- `src/pdf_generator.py` — no per-job tailored PDF anymore.
- `src/apply_bot.py` — no auto-apply. Out of scope (re-evaluate later if
  matchmaking proves useful).
- `src/jd_analyzer.py` web-scraping path (Playwright fetch of job pages) —
  superseded by email parsing. Keep site-specific extraction *logic* (regex/
  HTML parsing for LinkedIn/Indeed/WTTJ structure) but feed it from email
  HTML bodies instead of fetched pages.

### Keep / reuse
- `src/parser.py` — resume → structured profile JSON. Profile is now a
  one-time input, computed once, reused for all matches.
- `src/matcher.py` — scoring engine (Ollama → embeddings → keyword fallback).
  Reused as-is: profile JSON vs. extracted job posting JSON → fit score +
  skill gaps.
- `src/tracker.py` — SQLite log. Extend schema: source email (message-id,
  folder), extracted job fields, match score, status
  (`new` / `interesting` / `discarded` / `applied` / `interview` / ...).

### New

1. **`src/email_search.py`** — IMAP search over the mailbox via the
   `protonesk` MCP server (or direct `imapflow`, same bridge). Responsibilities:
   - Search by sender domain (LinkedIn jobs, Indeed alerts, WTTJ, Glassdoor,
     recruiter ToS patterns) and subject keywords.
   - Pull message bodies (HTML) for matching messages.
   - Dedupe against `tracker.db` by message-id.

2. **`src/jd_email_extractor.py`** — parse one or many job postings out of a
   single alert-digest email (these emails often bundle 5-20 postings per
   message). Reuses LinkedIn/Indeed/WTTJ HTML structure knowledge from old
   `jd_analyzer.py`. Output: list of job posting JSON (title, company,
   location, link, raw description snippet).

3. **`src/main.py` (rewritten)** — pipeline becomes:
   ```
   profile.json (parsed once from resume)
        ↓
   [1] email_search   → candidate messages (IMAP search via protonesk)
        ↓
   [2] jd_email_extractor → job postings (1..N per email)
        ↓
   [3] matcher        → fit score + gaps per posting
        ↓
   [4] tracker        → upsert into jobber.db (dedupe by message-id+job link)
        ↓
   [5] GUI            → browse, sort by score, mark status
   ```

4. **GUI** — local web dashboard (SvelteKit, consistent with existing
   front-end stack/css-base). Views:
   - Inbox of matched postings, sorted by score, filter by status/source.
   - Detail view: posting text, score breakdown, skill gaps, link to email
     (deep link into webmail or `mailto:`), status buttons.
   - Profile view: current parsed resume profile (read-only, re-parse button).
   - Manual "run search" trigger (calls pipeline, shows progress).

5. **Skill: `imap-job-search`** (methodology/strategy, lives under
   `.claude/skills/` or shared skills dir) — captures the *non-code*
   knowledge needed to do this well:
   - Known sender domains/subject patterns per job board (kept up to date as
     boards change their templates).
   - IMAP search query recipes (`SINCE`, `FROM`, `SUBJECT` combos) and which
     folder/label these alerts typically land in.
   - How to handle digest emails (multiple postings per message) vs.
     single-posting recruiter emails.
   - Heuristics for what counts as "interesting enough to surface" before
     running the (slower) matcher — cheap pre-filter.
   - Workflow guidance for an agent: when to re-run search (e.g. daily),
     how to avoid reprocessing, how to summarize new matches to the user.

## Dependencies on proton-mail-bridge

- `protonesk` MCP server (`D:\development\proton-mail-bridge`) already
  exposes `search_messages`, `list_messages`, `get_message` over hydroxide's
  IMAP bridge — this is the intended access path for `email_search.py`
  (avoid duplicating IMAP client code; call MCP tools or import the same
  `imapflow` config pattern from `src/mail/imap.ts` if a Python client is
  needed instead).
- Requires hydroxide running + authenticated (existing Scheduled Task).

## Migration steps

1. Remove `tailor.py`, `pdf_generator.py`, `apply_bot.py` (or move to
   `bmad/legacy/` like proton-mail-bridge did with its old Python approach —
   keep as reference, mark stale).
2. Extend `tracker.py` schema for email-sourced postings.
3. Build `email_search.py` against protonesk MCP (or imapflow direct).
4. Refactor `jd_analyzer.py` extraction logic into `jd_email_extractor.py`,
   feed from email HTML instead of fetched pages.
5. Rewrite `main.py` pipeline per diagram above.
6. Scaffold GUI (SvelteKit + css-base).
7. Write `imap-job-search` skill doc.
8. Update README/CHANGELOG, archive old pipeline docs in `bmad/`.
