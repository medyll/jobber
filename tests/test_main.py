#!/usr/bin/env python3
"""
Tests — Compute CLI (main.py, post-pivot)

main.py is now a stateless compute harness (parse / extract / score). The old
end-to-end pipeline (tailor/pdf/apply/tracker) was archived under bmad/legacy/.

Run: pytest tests/test_main.py -v
"""

import os
import sys
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

PROFILE_DATA = {
    'personal': {'name': 'Jane Dev', 'email': 'jane@example.com'},
    'summary': 'Backend engineer.',
    'experience': [{'role': 'Engineer', 'company': 'Acme', 'period': '2020-2024', 'description': 'Python APIs.'}],
    'education': [{'degree': "Bachelor's CS", 'year': '2017'}],
    'skills': ['Python', 'Django', 'AWS'],
}
JOB_DATA = {
    'title': 'Staff Engineer', 'company': 'TechCorp', 'location': 'Remote',
    'link': 'https://example.com/jobs/view/1', 'description': 'Python, FastAPI.',
    'source': 'linkedin', 'remote': True, 'skills_detected': ['Python', 'FastAPI'],
}
SCORE_DATA = {
    'score': 0.72, 'summary': 'Solid fit.', 'strengths': ['Python'], 'gaps': ['FastAPI'],
    'skills': [{'code': 'python', 'kind': 'matched'}, {'code': 'fastapi', 'kind': 'missing'}],
    'method': 'keyword', 'model': 'none',
}


class TestParse:
    def test_parse_returns_profile(self, monkeypatch):
        import main as m
        monkeypatch.setattr(m.resume_parser.ResumeParser, 'parse',
                            lambda self, path, **kw: PROFILE_DATA)
        out = m.cmd_parse('cv.pdf')
        assert out['personal']['name'] == 'Jane Dev'
        assert out['skills'] == ['Python', 'Django', 'AWS']

    def test_parse_mask_pii_forwarded(self, monkeypatch):
        import main as m
        seen = {}
        monkeypatch.setattr(m.resume_parser.ResumeParser, 'parse',
                            lambda self, path, mask_pii=True: seen.update(mask=mask_pii) or PROFILE_DATA)
        m.cmd_parse('cv.pdf', mask_pii=False)
        assert seen['mask'] is False


class TestExtract:
    def test_extract_reads_file_and_delegates(self, monkeypatch, tmp_path):
        import main as m
        html = tmp_path / 'alert.html'
        html.write_text('<html><a href="x">job</a></html>', encoding='utf-8')
        monkeypatch.setattr(m.jd_email_extractor, 'extract',
                            lambda content, hint='': [JOB_DATA])
        out = m.cmd_extract(str(html), 'linkedin')
        assert isinstance(out, list) and out[0]['link'].endswith('/jobs/view/1')

    def test_extract_passes_source_hint(self, monkeypatch, tmp_path):
        import main as m
        html = tmp_path / 'alert.html'
        html.write_text('<html></html>', encoding='utf-8')
        captured = {}
        monkeypatch.setattr(m.jd_email_extractor, 'extract',
                            lambda content, hint='': captured.update(hint=hint) or [])
        m.cmd_extract(str(html), 'wttj')
        assert captured['hint'] == 'wttj'


class TestScore:
    def test_score_loads_inputs_and_delegates(self, monkeypatch, tmp_path):
        import main as m
        pf = tmp_path / 'profile.json'; pf.write_text(json.dumps(PROFILE_DATA), encoding='utf-8')
        jb = tmp_path / 'job.json';     jb.write_text(json.dumps(JOB_DATA), encoding='utf-8')
        monkeypatch.setattr(m.matcher, 'score',
                            lambda profile, job, ollama_model='mistral': SCORE_DATA)
        out = m.cmd_score(str(pf), str(jb))
        assert 0.0 <= out['score'] <= 1.0
        assert {s['kind'] for s in out['skills']} == {'matched', 'missing'}


class TestExtractorReal:
    """Light end-to-end on the real extractor (skipped if bs4 absent)."""

    def test_extract_finds_job_link(self):
        pytest.importorskip('bs4')
        from jd_email_extractor import extract
        html = """
        <html><body>
          <table><tr><td>
            <a href="https://www.linkedin.com/jobs/view/123456/?trk=x">Senior Python Engineer</a>
            <span>Acme Corp · Paris, France · Remote</span>
            <p>We use Python, Docker and React.</p>
          </td></tr></table>
        </body></html>
        """
        jobs = extract(html)
        assert len(jobs) == 1
        j = jobs[0]
        assert j['title'].startswith('Senior Python Engineer')
        assert j['link'] == 'https://linkedin.com/jobs/view/123456/'
        assert j['source'] == 'linkedin'
        assert j['remote'] is True
        assert 'Python' in j['skills_detected'] and 'Docker' in j['skills_detected']

    def test_extract_empty_html(self):
        pytest.importorskip('bs4')
        from jd_email_extractor import extract
        assert extract('') == []
