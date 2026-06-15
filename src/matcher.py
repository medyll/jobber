#!/usr/bin/env python3
"""
Jobber — Semantic Matcher

Score a parsed resume against a parsed job description using:
1. Ollama LLM (local) — structured reasoning + fit score
2. Sentence-transformers — cosine similarity fallback

Usage:
    python src/matcher.py resume.json jd.json
    python src/matcher.py resume.json jd.json --ollama-model mistral
"""

import sys
import os
import json
import re
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None


OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
DEFAULT_MODEL = 'mistral'

SCORE_PROMPT = """You are a resume screening expert. Compare the following resume and job description.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Respond in JSON with this exact structure:
{{
  "score": <integer 0-100>,
  "matched_skills": [<list of skills present in both>],
  "missing_skills": [<list of required skills absent from resume>],
  "strengths": [<2-3 bullet points>],
  "gaps": [<2-3 bullet points>],
  "summary": "<one sentence overall assessment>"
}}
Only output valid JSON. No explanation outside the JSON block."""


class SemanticMatcher:
    """Score resume fit against a job description."""

    def __init__(self, ollama_model: str = DEFAULT_MODEL, embedding_model: str = 'all-MiniLM-L6-v2'):
        self.ollama_model = ollama_model
        self.embedding_model_name = embedding_model
        self._embedder = None  # lazy-loaded

    def match(self, resume: Dict, jd: Dict) -> Dict:
        """
        Score resume against JD.

        Args:
            resume: Parsed resume dict (from ResumeParser)
            jd: Parsed JD dict (from JDAnalyzer)

        Returns:
            dict: Match result with score, skills gap, strengths, summary
        """
        resume_text = self._resume_to_text(resume)
        jd_text = self._jd_to_text(jd)

        # Try Ollama first
        if self._ollama_available():
            result = self._score_with_ollama(resume_text, jd_text)
            result['method'] = 'ollama'
            result['model'] = self.ollama_model
        else:
            result = self._score_with_embeddings(resume, jd, resume_text, jd_text)
            result['method'] = 'embeddings'
            result['model'] = self.embedding_model_name

        result['resume_skills'] = resume.get('skills', [])
        result['jd_skills'] = jd.get('skills_detected', [])
        return result

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _ollama_available(self) -> bool:
        """Check if Ollama is reachable."""
        if not requests:
            return False
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def _score_with_ollama(self, resume_text: str, jd_text: str) -> Dict:
        """Call Ollama generate API and parse JSON response."""
        prompt = SCORE_PROMPT.format(
            resume_text=resume_text[:3000],
            jd_text=jd_text[:2000],
        )
        payload = {
            'model': self.ollama_model,
            'prompt': prompt,
            'stream': False,
            'format': 'json',
        }
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json().get('response', '{}')
        return self._parse_llm_json(raw)

    def _parse_llm_json(self, raw: str) -> Dict:
        """Extract JSON from LLM response, tolerating markdown fences."""
        # Strip ```json ... ``` if present
        match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', raw)
        if match:
            raw = match.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                'score': 0,
                'matched_skills': [],
                'missing_skills': [],
                'strengths': [],
                'gaps': ['Could not parse LLM response'],
                'summary': 'Parse error',
            }

    # ── Embeddings fallback ───────────────────────────────────────────────────

    def _score_with_embeddings(
        self, resume: Dict, jd: Dict, resume_text: str, jd_text: str
    ) -> Dict:
        """Cosine similarity between resume and JD embeddings."""
        if not SentenceTransformer:
            return self._score_keyword_overlap(resume, jd)

        if self._embedder is None:
            self._embedder = SentenceTransformer(self.embedding_model_name)

        embeddings = self._embedder.encode([resume_text[:3000], jd_text[:2000]])
        similarity = float(util.cos_sim(embeddings[0], embeddings[1]))
        score = int(similarity * 100)

        matched, missing = self._skills_gap(
            resume.get('skills', []),
            jd.get('skills_detected', []),
        )
        return {
            'score': score,
            'matched_skills': matched,
            'missing_skills': missing,
            'strengths': [f"Semantic similarity: {similarity:.2f}"],
            'gaps': [f"{len(missing)} required skills not found in resume"] if missing else [],
            'summary': f"Embedding similarity score: {score}/100",
        }

    def _score_keyword_overlap(self, resume: Dict, jd: Dict) -> Dict:
        """Pure keyword overlap — last resort when no ML libs available."""
        resume_skills = {s.lower() for s in resume.get('skills', [])}
        jd_skills = jd.get('skills_detected', [])

        matched = [s for s in jd_skills if s.lower() in resume_skills]
        missing = [s for s in jd_skills if s.lower() not in resume_skills]

        score = int(len(matched) / max(len(jd_skills), 1) * 100)
        return {
            'score': score,
            'matched_skills': matched,
            'missing_skills': missing,
            'strengths': [f"Matched {len(matched)}/{len(jd_skills)} required skills"],
            'gaps': missing[:5],
            'summary': f"Keyword overlap score: {score}/100",
            'method': 'keyword',
            'model': 'none',
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _skills_gap(
        self, resume_skills: List[str], jd_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        resume_lower = {s.lower() for s in resume_skills}
        matched = [s for s in jd_skills if s.lower() in resume_lower]
        missing = [s for s in jd_skills if s.lower() not in resume_lower]
        return matched, missing

    def _resume_to_text(self, resume: Dict) -> str:
        parts = []
        p = resume.get('personal', {})
        if p.get('name'):
            parts.append(p['name'])
        if resume.get('summary'):
            parts.append(resume['summary'])
        for exp in resume.get('experience', []):
            parts.append(f"{exp.get('role', '')} at {exp.get('company', '')} {exp.get('period', '')}")
            if exp.get('description'):
                parts.append(exp['description'])
        for edu in resume.get('education', []):
            parts.append(edu.get('degree', ''))
        skills = resume.get('skills', [])
        if skills:
            parts.append('Skills: ' + ', '.join(skills))
        return '\n'.join(filter(None, parts))

    def _jd_to_text(self, jd: Dict) -> str:
        parts = [
            jd.get('title', ''),
            jd.get('company', ''),
            jd.get('description', ''),
            jd.get('requirements', ''),
        ]
        skills = jd.get('skills_detected', [])
        if skills:
            parts.append('Required skills: ' + ', '.join(skills))
        return '\n'.join(filter(None, parts))

    def save_json(self, data: Dict, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {output_path}")


# ── UNIFY adapter ─────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    """Normalize a skill label to an idae `skill.code`-style slug."""
    s = name.strip().lower()
    s = s.replace('node.js', 'nodejs').replace('next.js', 'nextjs').replace('socket.io', 'socketio')
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s


def score(profile: Dict, job: Dict, ollama_model: str = DEFAULT_MODEL) -> Dict:
    """
    Score a job against the candidate profile (UNIFY `jobber.score_job`).

    Thin adapter over SemanticMatcher.match that reshapes the result to the
    contract consumed by the idae store:

        { score: float 0..1, summary, strengths[], gaps[],
          skills: [{code, kind}],   # kind in matched|missing
          method, model }

    Args:
        profile: Parsed candidate profile (parser output shape; needs `skills`).
        job: One posting (jd_email_extractor output shape; `skills_detected`).
        ollama_model: Ollama model name.

    Returns:
        dict: Scoring aligned to idae `match_result` + `job_skill`.
    """
    m = SemanticMatcher(ollama_model=ollama_model).match(profile, job)

    skills = [{'code': _slug(s), 'kind': 'matched'} for s in m.get('matched_skills', [])]
    skills += [{'code': _slug(s), 'kind': 'missing'} for s in m.get('missing_skills', [])]

    raw = m.get('score', 0) or 0
    fit = round(raw / 100.0, 3) if raw > 1 else round(float(raw), 3)  # accept 0-100 or 0..1

    return {
        'score': fit,
        'summary': m.get('summary', ''),
        'strengths': m.get('strengths', []),
        'gaps': m.get('gaps', []),
        'skills': skills,
        'method': m.get('method'),
        'model': m.get('model'),
    }


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python matcher.py <resume.json> <jd.json> [--ollama-model <model>]")
        sys.exit(1)

    resume_path, jd_path = sys.argv[1], sys.argv[2]
    model = DEFAULT_MODEL
    if '--ollama-model' in sys.argv:
        idx = sys.argv.index('--ollama-model')
        model = sys.argv[idx + 1]

    with open(resume_path) as f:
        resume = json.load(f)
    with open(jd_path) as f:
        jd = json.load(f)

    matcher = SemanticMatcher(ollama_model=model)
    print(f"🤖 Matching resume against JD (model: {model})...")
    result = matcher.match(resume, jd)

    print(f"\n📊 Match Result:")
    print(f"   Score:    {result['score']}/100")
    print(f"   Method:   {result.get('method', 'unknown')}")
    print(f"   Matched:  {', '.join(result.get('matched_skills', [])) or 'none'}")
    print(f"   Missing:  {', '.join(result.get('missing_skills', [])) or 'none'}")
    print(f"   Summary:  {result.get('summary', '')}")

    output_path = 'match_result.json'
    matcher.save_json(result, output_path)
