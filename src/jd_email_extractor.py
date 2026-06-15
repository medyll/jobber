#!/usr/bin/env python3
"""
Jobber — Job Extractor from Alert Emails

Refactor of the old `jd_analyzer.py`: instead of fetching a job page over HTTP,
the input is the **HTML body of a job-alert email** (LinkedIn / Indeed / Welcome
to the Jungle / Glassdoor digests, recruiter mails). A single digest commonly
bundles 5-20 postings, so the output is a **list** of structured job dicts.

Pure / no I/O / no persistence (UNIFY: jobber computes, idae-machine stores). Output is
aligned 1-for-1 with the idae `job` collection so the agent can `idae.create`
each row directly:

    { title, company, location, link, description, source, remote, skills_detected }

Usage:
    python src/jd_email_extractor.py alert.html [--source linkedin]
"""

import sys
import re
import json
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# Reused from the legacy analyzer — keyword catalog for cheap skill detection.
SKILL_KEYWORDS = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby',
    'React', 'Vue', 'Angular', 'Svelte', 'Node.js', 'Next.js', 'NestJS', 'Express',
    'Django', 'FastAPI', 'Flask', 'Spring', 'Symfony', 'Laravel', 'PHP',
    'SQL', 'PostgreSQL', 'MySQL', 'MariaDB', 'MongoDB', 'Redis', 'Elasticsearch',
    'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'CI/CD', 'Ansible',
    'Git', 'Linux', 'REST', 'GraphQL', 'Kafka', 'RabbitMQ', 'Socket.io', 'Nginx',
    'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP', 'LangChain',
    'Agile', 'Scrum', 'Kanban', 'DevOps', 'MLOps', 'DDD',
]

# Domain → idae `job_source.code` (mirrors the seeded referential).
SOURCE_BY_DOMAIN = {
    'linkedin.com': 'linkedin',
    'indeed.com': 'indeed',
    'welcometothejungle.com': 'wttj',
    'glassdoor.com': 'glassdoor',
}

# A href is treated as a job posting when it matches one of these shapes.
JOB_LINK_PATTERNS = [
    re.compile(r'/jobs?/view', re.I),
    re.compile(r'/viewjob', re.I),
    re.compile(r'[?&]jk=', re.I),                 # indeed job key
    re.compile(r'welcometothejungle\.com/.+/jobs/', re.I),
    re.compile(r'glassdoor\.[a-z.]+/(job|Job)', re.I),
    re.compile(r'/jobs?/\d+', re.I),
]

_REMOTE_RE = re.compile(r'\b(remote|télétravail|teletravail|full[- ]?remote|hybrid|hybride)\b', re.I)


class JobEmailExtractor:
    """Extract 1..N job postings from the HTML body of an alert email."""

    def extract(self, html: str, source_hint: str = "") -> List[Dict]:
        """
        Parse an alert email's HTML into a list of structured job postings.

        Args:
            html: Raw HTML body of the email.
            source_hint: Optional board code ('linkedin'|'indeed'|'wttj'|
                'glassdoor'|'recruiter'); inferred from links when empty.

        Returns:
            list[dict]: One dict per posting, aligned to the idae `job` collection.
        """
        if not BeautifulSoup:
            raise RuntimeError("beautifulsoup4 not installed — run: pip install beautifulsoup4")
        if not html or not html.strip():
            return []

        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['style', 'script']):
            tag.decompose()

        jobs: List[Dict] = []
        seen_links = set()

        for anchor in soup.find_all('a', href=True):
            href = self._clean_url(anchor['href'])
            if not href or not self._is_job_link(href):
                continue
            if href in seen_links:
                continue
            seen_links.add(href)

            title = anchor.get_text(separator=' ', strip=True)
            if not title or len(title) < 3:
                continue

            context = self._anchor_context(anchor)
            domain = self._domain(href)
            source = source_hint or SOURCE_BY_DOMAIN.get(domain, 'other')

            job = {
                'title': self._clean_title(title),
                'company': self._guess_company(context, title),
                'location': self._guess_location(context),
                'link': href,
                'description': context[:1000],
                'source': source,
                'remote': bool(_REMOTE_RE.search(context)),
                'skills_detected': self._detect_skills(f"{title} {context}"),
            }
            jobs.append(job)

        return jobs

    # ── Heuristics ────────────────────────────────────────────────────────────

    def _is_job_link(self, url: str) -> bool:
        return any(p.search(url) for p in JOB_LINK_PATTERNS)

    def _anchor_context(self, anchor) -> str:
        """Text surrounding the anchor — its enclosing card/row, for company/location."""
        node = anchor
        for _ in range(3):  # climb a few levels toward the posting "card"
            if node.parent is None:
                break
            node = node.parent
            text = node.get_text(separator=' ', strip=True)
            if len(text) > len(anchor.get_text(strip=True)) + 20:
                return text
        return anchor.get_text(separator=' ', strip=True)

    def _guess_company(self, context: str, title: str) -> str:
        """Best-effort: company often follows the title or sits before the location."""
        tail = context.replace(title, ' ', 1).strip()
        # "Company · Location" / "Company - Location" patterns
        m = re.split(r'\s*[·•|–-]\s*', tail, maxsplit=1)
        if m and m[0] and len(m[0]) < 80:
            return m[0].strip()
        return ''

    def _guess_location(self, context: str) -> str:
        m = re.search(r'([A-ZÀ-Ÿ][\wÀ-ÿ’\'-]+(?:[ ,]+[A-ZÀ-Ÿ][\wÀ-ÿ’\'-]+){0,2})\s*\(?(?:remote|hybrid|hybride|télétravail|on[- ]?site|sur site)?\)?', context, re.I)
        # Prefer an explicit "City, Country" near a remote marker; fall back to empty.
        loc = re.search(r'\b([A-ZÀ-Ÿ][\wÀ-ÿ’\'-]+(?:,\s*[A-ZÀ-Ÿ][\wÀ-ÿ’\'-]+)+)\b', context)
        return loc.group(1).strip() if loc else ''

    def _detect_skills(self, text: str) -> List[str]:
        low = text.lower()
        return [s for s in SKILL_KEYWORDS if s.lower() in low]

    def _clean_title(self, title: str) -> str:
        return re.sub(r'\s+', ' ', title).strip()[:200]

    def _clean_url(self, href: str) -> str:
        """Drop tracking query/fragment noise while keeping the canonical path."""
        href = href.strip()
        if href.startswith('mailto:') or href.startswith('#'):
            return ''
        try:
            p = urlparse(href)
        except ValueError:
            return ''
        if not p.scheme.startswith('http'):
            return ''
        # Keep the indeed job-key param (jk) but strip the rest of the query.
        query = ''
        if 'jk=' in (p.query or ''):
            m = re.search(r'jk=[^&]+', p.query)
            query = m.group(0) if m else ''
        # Normalize host (lowercase, drop www) so the link dedupes reliably.
        netloc = p.netloc.lower().removeprefix('www.')
        return urlunparse((p.scheme, netloc, p.path, '', query, ''))

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc.lower().removeprefix('www.')


# Module-level convenience (UNIFY §6: `jobber.extract_jobs_from_email`).
def extract(html: str, source_hint: str = "") -> List[Dict]:
    """Extract 1..N job postings from alert-email HTML. See JobEmailExtractor.extract."""
    return JobEmailExtractor().extract(html, source_hint)


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python jd_email_extractor.py <alert.html> [--source <code>]")
        sys.exit(1)

    path = sys.argv[1]
    source = ''
    if '--source' in sys.argv:
        source = sys.argv[sys.argv.index('--source') + 1]

    with open(path, encoding='utf-8') as f:
        html_body = f.read()

    postings = extract(html_body, source)
    print(json.dumps(postings, indent=2, ensure_ascii=False))
    print(f"\n# {len(postings)} posting(s) extracted", file=sys.stderr)
