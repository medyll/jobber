# Changelog

## [Unreleased] — Sprint 3

### Added
- `src/tracker.py` — SQLite application tracker (log, update status, list)
- `src/main.py` — end-to-end pipeline entrypoint with skip flags
- `README.md` — full documentation with quickstart, module reference, CLI examples
- `CHANGELOG.md`

## [0.2.0] — Sprint 2

### Added
- `src/tailor.py` — Ollama-powered resume tailoring (summary + experience rewrite, graceful fallback)
- `src/pdf_generator.py` — ATS-friendly PDF generation via reportlab Platypus
- `src/apply_bot.py` — Playwright auto-apply bot (dry-run by default, screenshot proof)

## [0.1.0] — Sprint 1

### Added
- `src/parser.py` — Resume parser for PDF (PyPDF2/pdfminer) and Docx (python-docx), PII masking
- `src/jd_analyzer.py` — Job description scraper with site-specific parsers (LinkedIn, Indeed, WTTJ) and Playwright fallback
- `src/matcher.py` — Semantic resume-vs-JD scorer (Ollama LLM → sentence-transformers → keyword overlap)
