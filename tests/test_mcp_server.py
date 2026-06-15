#!/usr/bin/env python3
"""
Tests unitaires — Jobber MCP server (compute only)

Ollama is NOT contacted: SemanticMatcher.match is monkeypatched. These tests
cover the UNIFY shaping (idae match_result / job_skill) and the normalizers.

Run: pytest tests/test_mcp_server.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import mcp_server as m


# ── Normalizers ────────────────────────────────────────────────────────────────

def test_normalize_score_from_0_100():
    assert m._normalize_score(86) == 0.86
    assert m._normalize_score(100) == 1.0
    assert m._normalize_score(0) == 0.0


def test_normalize_score_from_unit_interval():
    assert m._normalize_score(0.72) == 0.72


def test_normalize_score_clamps_and_handles_garbage():
    assert m._normalize_score(150) == 1.0
    assert m._normalize_score(-5) == 0.0
    assert m._normalize_score("nan-ish") == 0.0


def test_slug():
    assert m._slug('Node.js') == 'node-js'
    assert m._slug('CI/CD') == 'ci-cd'
    assert m._slug('TypeScript') == 'typescript'


def test_join_list_and_scalar():
    assert m._join(['a', 'b']) == 'a\nb'
    assert m._join('solo') == 'solo'
    assert m._join(None) == ''


def test_normalize_profile_parser_shape_passthrough():
    p = {'personal': {'name': 'X'}, 'skills': ['python']}
    assert m._normalize_profile(p) is p


def test_normalize_profile_idae_machine_shape_adapts():
    idae_profile = {
        'full_name': 'Meddy Lebrun',
        'headline': 'Lead Dev',
        'summary': 'senior fullstack',
        'skills': ['react', 'svelte'],
    }
    out = m._normalize_profile(idae_profile)
    assert out['personal']['name'] == 'Meddy Lebrun'
    assert 'Lead Dev' in out['summary'] and 'senior fullstack' in out['summary']
    assert out['skills'] == ['react', 'svelte']


# ── score_job shaping ──────────────────────────────────────────────────────────

def test_score_job_maps_matcher_output(monkeypatch):
    fake = {
        'score': 86,
        'matched_skills': ['React', 'Node.js'],
        'missing_skills': ['GraphQL'],
        'strengths': ['Strong React', 'Lead experience'],
        'gaps': ['Light GraphQL'],
        'summary': 'Strong fit.',
        'method': 'ollama',
        'model': 'mistral',
    }
    monkeypatch.setattr(m.SemanticMatcher, 'match', lambda self, resume, jd: fake)

    out = m.score_job(
        {'full_name': 'Meddy', 'skills': ['react']},
        {'title': 'Lead React', 'description': 'react', 'skills_detected': ['React']},
    )

    assert out['score'] == 0.86
    assert out['summary'] == 'Strong fit.'
    assert out['strengths'] == 'Strong React\nLead experience'
    assert out['gaps'] == 'Light GraphQL'
    assert out['method'] == 'ollama'
    assert {'code': 'react', 'kind': 'matched'} in out['skills']
    assert {'code': 'node-js', 'kind': 'matched'} in out['skills']
    assert {'code': 'graphql', 'kind': 'missing'} in out['skills']


def test_score_job_handles_missing_keys(monkeypatch):
    monkeypatch.setattr(m.SemanticMatcher, 'match', lambda self, resume, jd: {'score': 50})
    out = m.score_job({'skills': []}, {'title': 'x'})
    assert out['score'] == 0.5
    assert out['skills'] == []
    assert out['strengths'] == '' and out['gaps'] == ''


# ── extract_jobs_from_email passthrough ────────────────────────────────────────

def test_extract_tool_returns_list():
    html = '<a href="https://www.linkedin.com/jobs/view/999">Dev</a>'
    jobs = m.extract_jobs_from_email(html, 'linkedin')
    assert isinstance(jobs, list) and jobs[0]['title'] == 'Dev'
