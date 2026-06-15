#!/usr/bin/env python3
"""
Jobber — MCP server (compute only)

UNIFY.md §6. Exposes jobber's pure compute over MCP (stdio) for an orchestrating
agent. NO persistence, NO mailbox, NO state: the agent reads mail via the
`protonesk` MCP and persists results via the `idae` MCP of idae-machine (MongoDB store). This
server only:

    profile_parse(resume_path, mask_pii)        -> profile JSON   (parser.py)
    extract_jobs_from_email(html, source_hint)  -> [job]          (jd_email_extractor.py)
    score_job(profile, job)                     -> match result   (matcher.py)

Tool outputs are shaped to drop straight into the idae `profile` / `job` /
`match_result` / `job_skill` collections (see jobberScheme.ts).

Run:
    python src/mcp_server.py          # stdio
    python -m src.mcp_server          # (cwd = jobber/)
Register in the agent's .mcp.json as the "jobber" server.
"""

import os
import re
import sys
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

from parser import ResumeParser
from jd_email_extractor import extract as extract_email_jobs
from matcher import SemanticMatcher

mcp = FastMCP("jobber")

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def profile_parse(resume_path: str, mask_pii: bool = True) -> Dict[str, Any]:
    """
    Parse a resume (PDF/Docx) into a structured profile. Does NOT persist — the
    agent writes the result into the idae `profile` collection.

    Args:
        resume_path: Absolute path to the resume file.
        mask_pii: Mask PII (email/phone/address) before returning. Default True.

    Returns:
        Profile dict: { personal, summary, experience, education, skills }.
    """
    return ResumeParser().parse(resume_path, mask_pii=mask_pii)


@mcp.tool()
def extract_jobs_from_email(html: str, source_hint: str = "") -> List[Dict[str, Any]]:
    """
    Extract 1..N job postings from the HTML body of a job-alert email. Digests
    bundle many postings; recruiter mails usually one. Output is aligned with the
    idae `job` collection — the agent dedups on `link` then `idae.create` each.

    Args:
        html: Raw HTML body of the email (from protonesk.get_message).
        source_hint: Optional board code (linkedin|indeed|wttj|glassdoor|recruiter);
                     inferred from links when empty.

    Returns:
        list[job]: { title, company, location, link, description, source,
                     remote, skills_detected }.
    """
    return extract_email_jobs(html, source_hint)


@mcp.tool()
def score_job(profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a job posting against the candidate profile (Ollama local, embeddings
    fallback). Does NOT persist — the agent writes a `match_result` row and
    `job_skill` rows into idae-machine.

    Args:
        profile: Profile dict. Accepts either the parser shape ({personal, skills,
                 ...}) or the idae `profile` row ({full_name, summary, skills, ...}).
        job: Job dict from extract_jobs_from_email (or any {title, company,
             description, skills_detected}).

    Returns:
        {
          score:      float 0..1   (idae match_result.score / job.score),
          summary:    str,
          strengths:  str,         (newline-joined bullets)
          gaps:       str,         (newline-joined bullets)
          model:      str,
          method:     "ollama" | "embeddings",
          skills:     [ { code, kind } ]   kind: matched | missing
        }
    """
    resume = _normalize_profile(profile)
    jd = _normalize_job(job)

    raw = SemanticMatcher(ollama_model=DEFAULT_MODEL).match(resume, jd)

    skills: List[Dict[str, str]] = []
    for name in raw.get("matched_skills", []) or []:
        skills.append({"code": _slug(name), "kind": "matched"})
    for name in raw.get("missing_skills", []) or []:
        skills.append({"code": _slug(name), "kind": "missing"})

    return {
        "score": _normalize_score(raw.get("score", 0)),
        "summary": raw.get("summary", ""),
        "strengths": _join(raw.get("strengths", [])),
        "gaps": _join(raw.get("gaps", [])),
        "model": raw.get("model", DEFAULT_MODEL),
        "method": raw.get("method", "ollama"),
        "skills": skills,
    }


# ── Normalizers ────────────────────────────────────────────────────────────────

def _normalize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Accept parser shape as-is; adapt an idae `profile` row to what matcher reads."""
    if not isinstance(profile, dict):
        return {"personal": {}, "skills": []}
    if "personal" in profile:
        return profile
    summary = " ".join(filter(None, [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("raw_text", ""),
    ]))
    return {
        "personal": {"name": profile.get("full_name") or profile.get("name", "")},
        "summary": summary,
        "experience": profile.get("experience", []),
        "education": profile.get("education", []),
        "skills": profile.get("skills", []) or [],
    }


def _normalize_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Map an idae `job` row onto the keys matcher's _jd_to_text expects."""
    if not isinstance(job, dict):
        return {}
    jd = dict(job)
    jd.setdefault("skills_detected", job.get("skills_detected", []))
    jd.setdefault("requirements", job.get("requirements", ""))
    return jd


def _normalize_score(score: Any) -> float:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0
    if s > 1.0:           # matcher returns 0-100 from Ollama
        s = s / 100.0
    return round(max(0.0, min(1.0, s)), 4)


def _join(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v) for v in value if v)
    return str(value or "")


def _slug(name: str) -> str:
    """Skill name -> canonical-ish code (best effort; the skill refines mapping)."""
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s


if __name__ == "__main__":
    mcp.run()  # stdio transport
