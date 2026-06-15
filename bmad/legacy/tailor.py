#!/usr/bin/env python3
"""
Jobber — Resume Tailor

Rewrite resume sections to better target a specific job description.
Uses Ollama LLM (local). Falls back to original resume if unavailable.

Usage:
    python src/tailor.py resume.json jd.json match.json
    python src/tailor.py resume.json jd.json match.json --ollama-model mistral
"""

import sys
import os
import json
import copy
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
DEFAULT_MODEL = 'mistral'

SUMMARY_PROMPT = """You are a professional resume writer. Rewrite the resume summary below to better target the job description.

ORIGINAL SUMMARY:
{summary}

JOB TITLE: {job_title}
JOB DESCRIPTION (excerpt):
{jd_excerpt}

MATCHED SKILLS: {matched_skills}

Rules:
- Keep it to 2-3 sentences max
- Mirror keywords from the job description naturally
- Do NOT invent experience, companies, or credentials
- Do NOT use buzzwords like "passionate" or "ninja"
- Output only the rewritten summary text, nothing else"""

EXPERIENCE_PROMPT = """You are a professional resume writer. Rewrite this job experience description to better highlight relevance to the target role.

ORIGINAL DESCRIPTION:
{description}

TARGET ROLE: {job_title}
MISSING SKILLS TO EMPHASIZE (if genuinely present): {missing_skills}
MATCHED SKILLS: {matched_skills}

Rules:
- Keep the same number of bullet points or sentences
- Use strong action verbs
- Quantify impact where the original already has numbers
- Do NOT invent metrics, tools, or responsibilities not in the original
- Output only the rewritten description text, nothing else"""


class ResumeTailor:
    """Rewrite resume sections to target a specific job description."""

    def __init__(self, ollama_model: str = DEFAULT_MODEL):
        self.ollama_model = ollama_model

    def tailor(self, resume: Dict, jd: Dict, match_result: Dict) -> Dict:
        """
        Return a tailored copy of the resume.

        Args:
            resume: Parsed resume dict (from ResumeParser)
            jd: Parsed JD dict (from JDAnalyzer)
            match_result: Match result dict (from SemanticMatcher)

        Returns:
            dict: Tailored resume (deep copy — original is never mutated)
        """
        tailored = copy.deepcopy(resume)

        if not self._ollama_available():
            tailored['_tailor_note'] = 'Ollama unavailable — original resume returned unchanged'
            return tailored

        job_title = jd.get('title', '')
        jd_excerpt = (jd.get('description', '') + ' ' + jd.get('requirements', ''))[:1500]
        matched = match_result.get('matched_skills', [])
        missing = match_result.get('missing_skills', [])

        # Rewrite summary
        original_summary = resume.get('summary', '')
        if original_summary:
            tailored['summary'] = self._rewrite_summary(
                original_summary, job_title, jd_excerpt, matched
            )

        # Rewrite top 2 experience descriptions
        for i, exp in enumerate(tailored.get('experience', [])[:2]):
            desc = exp.get('description', '')
            if desc:
                tailored['experience'][i]['description'] = self._rewrite_experience(
                    desc, job_title, matched, missing
                )

        tailored['_tailor_note'] = f'Tailored for: {job_title} @ {jd.get("company", "unknown")}'
        tailored['_ollama_model'] = self.ollama_model
        return tailored

    # ── Ollama calls ──────────────────────────────────────────────────────────

    def _ollama_available(self) -> bool:
        if not requests:
            return False
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _generate(self, prompt: str) -> str:
        """Call Ollama and return the text response."""
        payload = {
            'model': self.ollama_model,
            'prompt': prompt,
            'stream': False,
        }
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get('response', '').strip()

    def _rewrite_summary(
        self, summary: str, job_title: str, jd_excerpt: str, matched: List[str]
    ) -> str:
        prompt = SUMMARY_PROMPT.format(
            summary=summary,
            job_title=job_title,
            jd_excerpt=jd_excerpt[:800],
            matched_skills=', '.join(matched[:10]) or 'none',
        )
        result = self._generate(prompt)
        return result if result else summary

    def _rewrite_experience(
        self, description: str, job_title: str, matched: List[str], missing: List[str]
    ) -> str:
        prompt = EXPERIENCE_PROMPT.format(
            description=description[:800],
            job_title=job_title,
            matched_skills=', '.join(matched[:8]) or 'none',
            missing_skills=', '.join(missing[:5]) or 'none',
        )
        result = self._generate(prompt)
        return result if result else description

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_json(self, data: Dict, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {output_path}")


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python tailor.py <resume.json> <jd.json> <match.json> [--ollama-model <model>]")
        sys.exit(1)

    resume_path, jd_path, match_path = sys.argv[1], sys.argv[2], sys.argv[3]
    model = DEFAULT_MODEL
    if '--ollama-model' in sys.argv:
        idx = sys.argv.index('--ollama-model')
        model = sys.argv[idx + 1]

    with open(resume_path) as f:
        resume = json.load(f)
    with open(jd_path) as f:
        jd = json.load(f)
    with open(match_path) as f:
        match_result = json.load(f)

    tailor = ResumeTailor(ollama_model=model)
    print(f"✍️  Tailoring resume for: {jd.get('title')} @ {jd.get('company')}...")
    tailored = tailor.tailor(resume, jd, match_result)

    print(f"\n📝 Note: {tailored.get('_tailor_note', '')}")
    if tailored.get('summary'):
        print(f"\nSummary preview:\n{tailored['summary'][:200]}")

    output_path = 'resume_tailored.json'
    tailor.save_json(tailored, output_path)
