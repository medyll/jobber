#!/usr/bin/env python3
"""
Tests unitaires — JD Analyzer

Run: pytest tests/test_jd_analyzer.py -v
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from jd_analyzer import JDAnalyzer


HTML_GENERIC = """
<html>
<head><title>Senior Python Developer — Acme Corp</title></head>
<body>
  <h1>Senior Python Developer</h1>
  <div class="company">Acme Corp</div>
  <div id="job-desc">
    We are looking for a Senior Python Developer with experience in Django,
    FastAPI, PostgreSQL, and Docker. You will work with AWS and Kubernetes.
    Requirements: 5+ years Python, strong SQL skills, CI/CD experience.
    Salary: $120,000 - $150,000/yr
  </div>
</body>
</html>
"""

HTML_LINKEDIN_LIKE = """
<html><body>
  <h1 class="top-card-layout__title">Staff Engineer</h1>
  <a class="topcard__org-name-link">TechCorp</a>
  <span class="topcard__flavor--bullet">Paris, France</span>
  <div class="description__text">
    Build scalable systems using Python, Go, Kafka, and Kubernetes.
    Strong experience with AWS and PostgreSQL required.
  </div>
</body></html>
"""


class TestJDAnalyzer:

    @pytest.fixture
    def analyzer(self):
        return JDAnalyzer()

    def test_init(self, analyzer):
        assert analyzer.timeout == 15
        assert 'linkedin.com' in analyzer._site_parsers

    def test_domain_extraction(self, analyzer):
        assert analyzer._domain('https://www.linkedin.com/jobs/view/123') == 'linkedin.com'
        assert analyzer._domain('https://indeed.com/viewjob?jk=abc') == 'indeed.com'
        assert analyzer._domain('https://example.com/jobs/456') == 'example.com'

    def test_detect_skills(self, analyzer):
        text = "Experience with Python, Django, AWS and Docker required."
        skills = analyzer._detect_skills(text)
        assert 'Python' in skills
        assert 'Django' in skills
        assert 'AWS' in skills
        assert 'Docker' in skills

    def test_detect_skills_empty(self, analyzer):
        skills = analyzer._detect_skills("We are a great team!")
        assert skills == []

    def test_extract_salary(self, analyzer):
        assert analyzer._extract_salary("Salary: $120,000 - $150,000/yr") == "$120,000 - $150,000/yr"
        assert analyzer._extract_salary("No salary info here") is None

    def test_parse_generic_from_html(self, analyzer):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(HTML_GENERIC, 'html.parser')
        jd = analyzer._parse_generic(soup, 'https://example.com/jobs/1')
        assert 'Python Developer' in jd['title'] or 'Senior' in jd['title']
        assert len(jd['description']) > 0

    def test_parse_linkedin_selectors(self, analyzer):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(HTML_LINKEDIN_LIKE, 'html.parser')
        jd = analyzer._parse_linkedin(soup, 'https://linkedin.com/jobs/view/1')
        assert jd['title'] == 'Staff Engineer'
        assert jd['company'] == 'TechCorp'
        assert jd['location'] == 'Paris, France'

    def test_skills_detected_in_full_analyze(self, analyzer, monkeypatch):
        """analyze() with monkeypatched HTTP returns skills from content."""
        monkeypatch.setattr(analyzer, '_fetch_requests', lambda url: HTML_GENERIC)
        jd = analyzer.analyze('https://example.com/jobs/1')
        assert 'Python' in jd['skills_detected']
        assert 'Django' in jd['skills_detected']
        assert 'Docker' in jd['skills_detected']
        assert jd['url'] == 'https://example.com/jobs/1'
        assert jd['domain'] == 'example.com'

    def test_needs_playwright(self, analyzer):
        assert analyzer._needs_playwright('linkedin.com') is True
        assert analyzer._needs_playwright('indeed.com') is True
        assert analyzer._needs_playwright('example.com') is False

    def test_text_selector_fallback(self, analyzer):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html><body><h2>Fallback Title</h2></body></html>', 'html.parser')
        result = analyzer._text(soup, ['h1.missing', 'h2'])
        assert result == 'Fallback Title'

    def test_text_selector_no_match(self, analyzer):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html><body><p>Nothing</p></body></html>', 'html.parser')
        result = analyzer._text(soup, ['h1', 'h2'])
        assert result == ''

    def test_save_json(self, analyzer, tmp_path):
        data = {'title': 'Dev', 'company': 'Acme', 'skills_detected': ['Python']}
        output = str(tmp_path / 'jd.json')
        analyzer.save_json(data, output)
        with open(output) as f:
            loaded = json.load(f)
        assert loaded['title'] == 'Dev'
        assert loaded['skills_detected'] == ['Python']
