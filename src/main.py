#!/usr/bin/env python3
"""
Jobber — Compute CLI (post-pivot)

After the UNIFY pivot, jobber is a **stateless coprocessor**: it parses a CV,
extracts postings from alert-email HTML, and scores fit vs the profile. It does
**not** persist, tailor, generate PDFs, or auto-apply — persistence/dedup/triage
live in the idae-machine MongoDB store (via its MCP), and orchestration is done
by the agent. The legacy end-to-end pipeline (tailor/pdf/apply/tracker) is
archived under `bmad/legacy/`.

This CLI is a thin local harness over the three compute primitives; the agent
normally reaches them through `src/mcp_server.py` (stdio MCP).

Usage:
    python src/main.py parse   <resume.(pdf|docx)> [--no-mask]
    python src/main.py extract <alert.html> [--source linkedin|indeed|wttj|glassdoor|recruiter]
    python src/main.py score   <profile.json> <job.json> [--ollama-model mistral]

Each subcommand prints JSON to stdout (pipe-friendly). The shapes match the
idae `profile` / `job` / `match_result` collections so the agent can persist
the output verbatim via `idae.create` / `idae.update_by_id`.
"""

import sys
import os
import json
import argparse
from typing import Dict, List

# Allow `python src/main.py` (flat imports) and `python -m src.main`.
sys.path.insert(0, os.path.dirname(__file__))

import parser as resume_parser            # noqa: E402
import jd_email_extractor                  # noqa: E402
import matcher                             # noqa: E402


def cmd_parse(resume_path: str, mask_pii: bool = True) -> Dict:
    """Parse a CV into a structured profile dict (idae `profile` shape)."""
    return resume_parser.ResumeParser().parse(resume_path, mask_pii=mask_pii)


def cmd_extract(html_path: str, source_hint: str = "") -> List[Dict]:
    """Extract 1..N postings from an alert-email HTML file (idae `job` shape)."""
    with open(html_path, encoding='utf-8') as f:
        html = f.read()
    return jd_email_extractor.extract(html, source_hint)


def cmd_score(profile_path: str, job_path: str, ollama_model: str = 'mistral') -> Dict:
    """Score one posting vs a profile (idae `match_result` shape)."""
    with open(profile_path, encoding='utf-8') as f:
        profile = json.load(f)
    with open(job_path, encoding='utf-8') as f:
        job = json.load(f)
    return matcher.score(profile, job, ollama_model=ollama_model)


def _emit(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def main():
    ap = argparse.ArgumentParser(
        prog='jobber',
        description='Jobber compute CLI — parse CV / extract email postings / score fit (stateless).',
    )
    sub = ap.add_subparsers(dest='command', required=True)

    p_parse = sub.add_parser('parse', help='Parse a CV into a profile JSON')
    p_parse.add_argument('resume', help='Path to resume PDF or Docx')
    p_parse.add_argument('--no-mask', action='store_true', help='Do not mask PII (default: masked)')

    p_extract = sub.add_parser('extract', help='Extract postings from an alert-email HTML file')
    p_extract.add_argument('html', help='Path to the email HTML body')
    p_extract.add_argument('--source', default='', help='Board code hint (linkedin|indeed|wttj|glassdoor|recruiter)')

    p_score = sub.add_parser('score', help='Score a posting against a profile')
    p_score.add_argument('profile', help='Path to profile JSON (from `parse`)')
    p_score.add_argument('job', help='Path to job JSON (one item from `extract`)')
    p_score.add_argument('--ollama-model', default='mistral', help='Ollama model (default: mistral)')

    args = ap.parse_args()

    if args.command == 'parse':
        _emit(cmd_parse(args.resume, mask_pii=not args.no_mask))
    elif args.command == 'extract':
        postings = cmd_extract(args.html, args.source)
        _emit(postings)
        print(f"# {len(postings)} posting(s) extracted", file=sys.stderr)
    elif args.command == 'score':
        _emit(cmd_score(args.profile, args.job, ollama_model=args.ollama_model))


if __name__ == "__main__":
    main()
