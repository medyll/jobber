#!/usr/bin/env python3
"""
Tests unitaires — Job Email Extractor (UNIFY pivot)

Run: pytest tests/test_jd_email_extractor.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from jd_email_extractor import extract, JobEmailExtractor


LINKEDIN_DIGEST = """
<html><body>
  <table>
    <tr><td>
      <a href="https://www.linkedin.com/jobs/view/3811111111?trk=eml&utm_source=x">Lead Frontend React</a>
      <div>Acme Corp · Nice, France · Remote</div>
      <p>We need React, TypeScript and Node.js. Senior role.</p>
    </td></tr>
    <tr><td>
      <a href="https://www.linkedin.com/jobs/view/3822222222?trk=eml">Backend Engineer Python</a>
      <div>Globex · Paris, France</div>
      <p>Python, PostgreSQL, Docker, AWS.</p>
    </td></tr>
  </table>
  <a href="https://www.linkedin.com/comm/settings">Unsubscribe</a>
  <a href="mailto:noreply@linkedin.com">Contact</a>
</body></html>
"""


def test_extracts_multiple_postings_from_digest():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    assert len(jobs) == 2
    titles = {j['title'] for j in jobs}
    assert 'Lead Frontend React' in titles
    assert 'Backend Engineer Python' in titles


def test_strips_tracking_params_from_link():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    links = {j['link'] for j in jobs}
    # tracking query dropped; host canonicalized (www stripped) for stable dedup
    assert 'https://linkedin.com/jobs/view/3811111111' in links
    assert all('trk=' not in l and 'utm_' not in l for l in links)


def test_ignores_non_job_links():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    links = [j['link'] for j in jobs]
    assert not any('settings' in l for l in links)
    assert not any(l.startswith('mailto:') for l in links)


def test_detects_skills():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    react = next(j for j in jobs if j['title'] == 'Lead Frontend React')
    assert 'React' in react['skills_detected']
    assert 'TypeScript' in react['skills_detected']


def test_remote_flag_and_source():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    react = next(j for j in jobs if j['title'] == 'Lead Frontend React')
    assert react['remote'] is True
    assert react['source'] == 'linkedin'


def test_dedupes_same_link():
    html = LINKEDIN_DIGEST + LINKEDIN_DIGEST  # same postings twice
    jobs = extract(html, 'linkedin')
    links = [j['link'] for j in jobs]
    assert len(links) == len(set(links))  # no duplicate links


def test_source_inferred_when_hint_empty():
    jobs = extract(LINKEDIN_DIGEST, '')
    assert all(j['source'] == 'linkedin' for j in jobs)


def test_empty_html_returns_empty_list():
    assert extract('', 'linkedin') == []
    assert extract('   ', '') == []


def test_indeed_jk_param_kept():
    html = '<a href="https://fr.indeed.com/viewjob?jk=abc123&from=alert">Dev Indeed</a>'
    jobs = extract(html, 'indeed')
    assert len(jobs) == 1
    assert 'jk=abc123' in jobs[0]['link']
    assert 'from=alert' not in jobs[0]['link']


def test_output_shape_matches_idae_job():
    jobs = extract(LINKEDIN_DIGEST, 'linkedin')
    expected = {'title', 'company', 'location', 'link', 'description',
                'source', 'remote', 'skills_detected'}
    assert expected.issubset(set(jobs[0].keys()))
