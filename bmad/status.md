# Jobber — Project Status
**Generated:** 2026-04-17 | **Phase:** Development | **Progress:** 75%

---

## Product Overview

**Jobber** is a local-first Python tool that automates the job application workflow. It parses your resume, scrapes job descriptions, uses an LLM (Ollama) to semantically match and tailor your CV, generates a polished PDF, and optionally auto-applies. No cloud APIs required.

---

## Strategic Dimensions

### Marketing
- Automates the job application workflow end-to-end
- Tailors your resume to each job description automatically
- Saves hours per application with intelligent PDF generation
- Fully local — Ollama LLM, no cloud API keys required

### Product
- Resume parser implemented — extracts personal info, experience, education, skills (PDF + Docx)
- JD scraper is the next critical module (Playwright-based web scraping)
- Semantic matching via Ollama LLM will score resume fit against JD
- Auto-apply bot and tracking modules deferred to Sprint 2+

### Far Vision
- Full pipeline: parse resume → scrape JD → match/tailor → generate PDF → auto-apply
- Tracking dashboard for application status
- Multi-platform JD sources (LinkedIn, Indeed, custom URLs)

---

## Development Details

### Current Sprint: Sprint 1 — Core Pipeline
**Goal:** Resume parser + JD scraper + semantic matcher

| ID | Story | Status | Tests |
|----|-------|--------|-------|
| S1-01 | Resume Parser (PDF/Docx) with PII masking | ✅ complete | 11/11 pass |
| S1-02 | JD Analyzer — scrape job descriptions | ✅ complete | 12/12 pass |
| S1-03 | Semantic Matcher — Ollama LLM resume-vs-JD scoring | ✅ complete | 14/14 pass |

**Full suite: 37/37 tests passing.**

### Files
| File | Status | Notes |
|------|--------|-------|
| `src/parser.py` | ✅ complete | ResumeParser — PDF/Docx, PII masking, CLI |
| `tests/test_parser.py` | ✅ 11/11 pass | — |
| `src/jd_analyzer.py` | ✅ complete | JDAnalyzer — requests+BS4, Playwright fallback, LinkedIn/Indeed/WTTJ |
| `tests/test_jd_analyzer.py` | ✅ 12/12 pass | — |
| `src/matcher.py` | ✅ complete | SemanticMatcher — Ollama primary, embeddings + keyword fallbacks |
| `tests/test_matcher.py` | ✅ 14/14 pass | — |

### Artifacts
- PRD: `bmad/prd.md`
- Architecture: `bmad/architecture.md`
- Tech spec: missing

---

## Chain Protocol
- **Active role:** Tester (sprint sign-off)
- **Next action:** Sprint 1 complete — plan sprint 2 (PDF generator + auto-apply bot)
- **Next command:** `bmad continue`
- **Next role:** Scrum Master

---

## Blockers
None.
