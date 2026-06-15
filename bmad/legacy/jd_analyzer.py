#!/usr/bin/env python3
"""
Jobber — Job Description Analyzer

Scrape and extract structured data from job posting URLs.

Features:
- HTTP scraping (requests + BeautifulSoup) for static pages
- Playwright fallback for JS-heavy sites (LinkedIn, Indeed)
- Structured extraction: title, company, location, description, skills, salary
- Site-specific parsers for common job boards

Usage:
    python src/jd_analyzer.py https://example.com/jobs/123
    python src/jd_analyzer.py https://linkedin.com/jobs/view/123 --playwright
"""

import sys
import os
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


SKILL_KEYWORDS = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby',
    'React', 'Vue', 'Angular', 'Node.js', 'Django', 'FastAPI', 'Flask', 'Spring',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch',
    'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'CI/CD',
    'Git', 'Linux', 'REST', 'GraphQL', 'Kafka', 'RabbitMQ',
    'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP',
    'Agile', 'Scrum', 'DevOps', 'MLOps',
]


class JDAnalyzer:
    """Scrape job description URLs and extract structured data."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._site_parsers = {
            'linkedin.com': self._parse_linkedin,
            'indeed.com': self._parse_indeed,
            'welcometothejungle.com': self._parse_wttj,
        }

    def analyze(self, url: str, use_playwright: bool = False) -> Dict:
        """
        Fetch and parse a job posting URL.

        Args:
            url: Full URL of the job posting
            use_playwright: Force Playwright even for static-capable sites

        Returns:
            dict: Structured job description data
        """
        domain = self._domain(url)
        site_parser = self._site_parsers.get(domain)

        if use_playwright or (site_parser and self._needs_playwright(domain)):
            html = self._fetch_playwright(url)
        else:
            html = self._fetch_requests(url)

        soup = BeautifulSoup(html, 'html.parser')

        if site_parser:
            jd = site_parser(soup, url)
        else:
            jd = self._parse_generic(soup, url)

        jd['url'] = url
        jd['domain'] = domain
        jd['skills_detected'] = self._detect_skills(
            jd.get('description', '') + ' ' + jd.get('requirements', '')
        )

        return jd

    # ── Fetchers ──────────────────────────────────────────────────────────────

    def _fetch_requests(self, url: str) -> str:
        """Fetch HTML via requests."""
        if not requests:
            raise RuntimeError("requests not installed — run: pip install requests beautifulsoup4")

        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def _fetch_playwright(self, url: str) -> str:
        """Fetch HTML via headless Playwright (for JS-rendered pages)."""
        if not sync_playwright:
            raise RuntimeError("playwright not installed — run: pip install playwright && playwright install chromium")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
            html = page.content()
            browser.close()
        return html

    # ── Site-specific parsers ─────────────────────────────────────────────────

    def _parse_linkedin(self, soup: 'BeautifulSoup', url: str) -> Dict:
        jd = self._base_jd()
        jd['title'] = self._text(soup, [
            'h1.top-card-layout__title',
            'h1.job-details-jobs-unified-top-card__job-title',
            'h1',
        ])
        jd['company'] = self._text(soup, [
            'a.topcard__org-name-link',
            'span.top-card-layout__second-subline',
            '.job-details-jobs-unified-top-card__company-name',
        ])
        jd['location'] = self._text(soup, [
            'span.topcard__flavor--bullet',
            '.job-details-jobs-unified-top-card__bullet',
        ])
        jd['description'] = self._text(soup, [
            'div.description__text',
            'div.job-details-jobs-unified-top-card__job-insight',
            'section.description',
        ])
        return jd

    def _parse_indeed(self, soup: 'BeautifulSoup', url: str) -> Dict:
        jd = self._base_jd()
        jd['title'] = self._text(soup, ['h1.jobsearch-JobInfoHeader-title', 'h1'])
        jd['company'] = self._text(soup, [
            'div[data-company-name]',
            'span.css-92r8pb',
        ])
        jd['location'] = self._text(soup, ['div.icl-u-xs-mt--xs', 'div[data-testid="job-location"]'])
        jd['description'] = self._text(soup, ['div#jobDescriptionText', 'div.jobsearch-jobDescriptionText'])
        return jd

    def _parse_wttj(self, soup: 'BeautifulSoup', url: str) -> Dict:
        jd = self._base_jd()
        jd['title'] = self._text(soup, ['h1[data-testid="job-title"]', 'h1'])
        jd['company'] = self._text(soup, ['a[data-testid="company-title-link"]'])
        jd['location'] = self._text(soup, ['span[data-testid="job-location"]'])
        jd['description'] = self._text(soup, ['div[data-testid="job-section-description"]', 'section'])
        return jd

    def _parse_generic(self, soup: 'BeautifulSoup', url: str) -> Dict:
        """Best-effort extraction for unknown sites."""
        jd = self._base_jd()

        # Remove noise
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        jd['title'] = self._text(soup, ['h1', 'h2', 'title'])
        jd['description'] = self._largest_text_block(soup)

        # Try to guess company from meta or og tags
        og_site = soup.find('meta', property='og:site_name')
        if og_site:
            jd['company'] = og_site.get('content', '')

        return jd

    # ── Extractors ────────────────────────────────────────────────────────────

    def _detect_skills(self, text: str) -> List[str]:
        """Detect known skill keywords in text."""
        found = []
        text_lower = text.lower()
        for skill in SKILL_KEYWORDS:
            if skill.lower() in text_lower:
                found.append(skill)
        return found

    def _extract_salary(self, text: str) -> Optional[str]:
        """Extract salary range from text."""
        pattern = r'[\$€£][\d,]+(?:\s*[-–]\s*[\$€£]?[\d,]+)?(?:\s*[kK])?(?:\s*/\s*(?:yr|year|an|month|mo))?'
        match = re.search(pattern, text)
        return match.group(0) if match else None

    def _largest_text_block(self, soup: 'BeautifulSoup') -> str:
        """Find the div with the most text — likely the job description."""
        best, best_len = '', 0
        for tag in soup.find_all(['div', 'section', 'article']):
            text = tag.get_text(separator=' ', strip=True)
            if len(text) > best_len:
                best, best_len = text, len(text)
        return best[:5000]  # cap at 5k chars

    def _text(self, soup: 'BeautifulSoup', selectors: List[str]) -> str:
        """Try selectors in order, return first match text."""
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return el.get_text(separator=' ', strip=True)
        return ''

    def _base_jd(self) -> Dict:
        return {
            'title': '',
            'company': '',
            'location': '',
            'description': '',
            'requirements': '',
            'salary': None,
        }

    def _domain(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        # Strip www.
        return host.removeprefix('www.')

    def _needs_playwright(self, domain: str) -> bool:
        """Sites known to require JS rendering."""
        return domain in {'linkedin.com', 'indeed.com'}

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_json(self, data: Dict, output_path: str):
        """Save structured JD to JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {output_path}")


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python jd_analyzer.py <url> [--playwright]")
        sys.exit(1)

    url = sys.argv[1]
    use_playwright = '--playwright' in sys.argv

    analyzer = JDAnalyzer()

    print(f"🔍 Analyzing {url}...")
    jd = analyzer.analyze(url, use_playwright=use_playwright)

    output_path = 'jd_parsed.json'
    analyzer.save_json(jd, output_path)

    print(f"\n📊 Summary:")
    print(f"   Title:    {jd.get('title', 'N/A')}")
    print(f"   Company:  {jd.get('company', 'N/A')}")
    print(f"   Location: {jd.get('location', 'N/A')}")
    print(f"   Skills:   {', '.join(jd.get('skills_detected', [])) or 'N/A'}")
    print(f"   Salary:   {jd.get('salary', 'N/A')}")
