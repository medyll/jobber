# Jobber

> Local-first Python tool that automatically tailors your resume to any job posting and applies for you — no cloud APIs, no subscriptions.

## Pipeline

```
resume.pdf + job URL
     ↓
[1] Parse resume     → structured JSON
[2] Scrape JD        → title, company, skills
[3] Match            → fit score 0-100, skill gaps
[4] Tailor           → Ollama rewrites summary + bullets
[5] Generate PDF     → ATS-friendly PDF
[6] Apply            → Playwright fills the form (dry-run safe)
[7] Track            → logged to jobber.db
```

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) (local LLM — optional, keyword fallback available)
- Playwright Chromium: `playwright install chromium`

## Installation

### Quick Start (Windows)

For the easiest setup on Windows, use our installation script:

```powershell
# Clone the repository
git clone https://github.com/you/jobber
cd jobber

# Run the installation script (creates venv, installs deps, sets up config)
.\install.ps1

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### Manual Installation

```bash
git clone https://github.com/you/jobber
cd jobber
pip install -r requirements.txt
playwright install chromium
```

### Without Ollama (Keyword-only mode)

```powershell
.\install.ps1 -NoOllama
```

## Configuration

Jobber uses a centralized configuration file (`config.yaml`) for all settings:

```yaml
# Example configuration
ollama:
  enabled: true
  base_url: http://localhost:11434
  model: mistral
  timeout: 30

playwright:
  browser: chromium
  headless: true
  timeout: 60000

mcp_server:
  host: 0.0.0.0
  port: 9000
  max_workers: 4
```

Edit `config.yaml` to customize Jobber's behavior. The installation script creates a default configuration.

## Service Management (Windows)

Jobber can be run as a Windows service for the MCP server:

```powershell
# Install the service (requires admin)
.\jobber-service.ps1 install

# Start the service
.\jobber-service.ps1 start

# Check status
.\jobber-service.ps1 status

# Stop the service
.\jobber-service.ps1 stop

# Uninstall the service
.\jobber-service.ps1 uninstall
```

## Quickstart

```bash
# Full pipeline — dry run (default, does not submit)
python src/main.py my_resume.pdf "https://linkedin.com/jobs/view/123456"

# Live mode — actually submits the application
python src/main.py my_resume.pdf "https://example.com/jobs/123" --live

# Skip apply, just score + tailor + PDF
python src/main.py my_resume.pdf "https://example.com/jobs/123" --skip-apply

# Check your application log
python src/tracker.py list
```

## Modules

| Module | File | Description |
|--------|------|-------------|
| Resume Parser | `src/parser.py` | Extract structured data from PDF/Docx |
| JD Analyzer | `src/jd_analyzer.py` | Scrape job postings (requests + Playwright) |
| Semantic Matcher | `src/matcher.py` | Score resume vs JD (Ollama → embeddings → keywords) |
| Resume Tailor | `src/tailor.py` | Rewrite resume for target JD via Ollama |
| PDF Generator | `src/pdf_generator.py` | ATS-friendly PDF via reportlab |
| Apply Bot | `src/apply_bot.py` | Playwright form filler (dry-run by default) |
| Tracker | `src/tracker.py` | SQLite application log |
| Pipeline | `src/main.py` | Orchestrates all modules end-to-end |

## CLI Reference

```bash
# Parser
python src/parser.py resume.pdf [--mask-pii]

# JD Analyzer
python src/jd_analyzer.py https://example.com/jobs/123 [--playwright]

# Matcher
python src/matcher.py resume.json jd.json [--ollama-model mistral]

# Tailor
python src/tailor.py resume.json jd.json match.json

# PDF Generator
python src/pdf_generator.py resume.json output.pdf

# Apply Bot
python src/apply_bot.py <url> resume.json resume.pdf [--live]

# Tracker
python src/tracker.py list
python src/tracker.py update <url> <applied|interview|rejected|offer>

# Full pipeline
python src/main.py resume.pdf <url> [--live] [--skip-tailor] [--skip-pdf] [--skip-apply]
```

## Tests

```bash
pytest tests/ -v        # 92 tests
```

## Supported Job Boards

Site-specific parsers for: **LinkedIn**, **Indeed**, **Welcome to the Jungle**.
Generic parser works on any static or JS-rendered page.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JOBBER_DB` | `jobber.db` | SQLite database path |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
