# Jobber — Status Report

> Jobber is a local-first Python tool that automatically tailors your resume to any job posting and submits the application for you — no cloud services, no subscriptions, just paste a URL and let it run.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Product Overview

  Progress   [███████░░░] 75%   Phase: development

### Features & Capabilities

  | Feature | Status | What it means for users |
  |---------|--------|------------------------|
  | Resume parsing | ✅ Shipped | Upload your PDF or Word CV — it's instantly structured and ready to use |
  | Job description scraper | ✅ Shipped | Paste any job URL (LinkedIn, Indeed, WTTJ, or any site) and get the full JD extracted |
  | Resume–JD matching | ✅ Shipped | See a fit score, matched skills, and skill gaps before applying |
  | Resume tailoring | 🔨 Building | Automatically rewrite your summary and bullet points to match the job |
  | PDF export | 📋 Planned | Get a clean, ATS-friendly PDF tailored to each application |
  | One-click apply | 📋 Planned | Auto-fill and submit job application forms with a single command |
  | Application tracking | 📋 Planned | Log every application and track its status over time |

### What's Ready Now
- **Parse any resume** — PDF or Word, extracts contact info, experience, education, and skills. Optional PII masking before sending to LLM.
- **Scrape any job posting** — works on static and JavaScript-rendered sites. Site-specific parsers for LinkedIn, Indeed, and Welcome to the Jungle.
- **Score your fit** — instant match score (0–100), list of matched and missing skills, strengths and gaps. Uses local Ollama LLM; falls back to embeddings or keyword overlap if offline.

### What's Coming Next
- **Tailored resume content** — Ollama rewrites your summary and top experience bullets to mirror the JD's language and requirements (factually grounded, no hallucinations)
- **One-click PDF** — polished, ATS-friendly PDF generated from the tailored resume, ready to attach
- **Auto-apply** — Playwright fills the application form and uploads your PDF. Dry-run by default (screenshots without submitting) until you explicitly go live

### Risks & Blockers
- Auto-apply bot (S2-03) depends on site-specific selectors — LinkedIn UI changes could require updates
- Ollama must be installed locally for tailoring and matching features; keyword fallback is available but lower quality
- No blockers on current sprint

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Development Details

  Sprint     2 — Tailoring & Output
  Role       scrum → next: developer
  Next cmd   `bmad continue`

### Current Sprint

  ✅ Done     Sprint 1 — parser (S1-01), JD analyzer (S1-02), semantic matcher (S1-03). 37/37 tests pass.
  🔨 Doing    S2-01 — Resume Tailor (src/tailor.py, Ollama rewrites summary + experience bullets)
  💡 Next     S2-02 — PDF Generator (src/pdf_generator.py, reportlab), then S2-03 — Auto-Apply Bot
  ⚠️ Blockers None

### Stories

  | ID | Title | Status | Effort |
  |----|-------|--------|--------|
  | S1-01 | Resume Parser (PDF/Docx) with PII masking | ✅ done | S |
  | S1-02 | JD Analyzer — scrape job descriptions | ✅ done | S |
  | S1-03 | Semantic Matcher — Ollama LLM resume-vs-JD scoring | ✅ done | M |
  | S2-01 | Resume Tailor — Ollama rewrites resume sections to target JD | 🔨 in progress | M |
  | S2-02 | PDF Generator — render tailored resume to polished PDF | ⬚ todo | M |
  | S2-03 | Auto-Apply Bot — Playwright form filler for job applications | ⬚ todo | L |

  Progress: 3/6 stories complete

### Roadmap to Release

  #### Planning ✅
  - PRD: done (bmad/prd.md)
  - Architecture: done (bmad/architecture.md)

  #### Development 🔨
  - Sprint 1: 3/3 stories ✅
  - Sprint 2: 0/3 stories 🔨 (active)
  - Sprint 3 (planned): tracking + pipeline wiring + README

  #### Testing ⬚
  - Unit tests: 37 passing (sprint 1), sprint 2 pending
  - E2E tests: not started

  #### Release ⬚
  - Docs/README: pending
  - CHANGELOG: pending
  - Publish: pending

### Artifacts

  | Artifact | Status |
  |----------|--------|
  | bmad/prd.md | ✅ done |
  | bmad/architecture.md | ✅ done |
  | bmad/artifacts/sprint-2026-04-17.md | ✅ done |
  | bmad/artifacts/stories/S2-01.md | ✅ done |
  | bmad/artifacts/stories/S2-02.md | ✅ done |
  | bmad/artifacts/stories/S2-03.md | ✅ done |
  | bmad/artifacts/test-report-S1-01.md | ✅ done |
  | bmad/artifacts/test-report-S1-02.md | ✅ done |
  | bmad/artifacts/test-report-S1-03.md | ✅ done |
  | Tech spec | ⬚ pending |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  bmad continue   — execute next step
  bmad test       — run tests
  bmad audit      — code quality
  bmad doc        — generate docs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
