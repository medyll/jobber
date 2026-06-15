#!/usr/bin/env python3
"""
Tests unitaires — Resume Tailor

Run: pytest tests/test_tailor.py -v
"""

import pytest
import sys
import os
import json
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tailor import ResumeTailor

RESUME = {
    'personal': {'name': 'Jane Dev', 'email': 'jane@example.com'},
    'summary': 'Backend engineer with 7 years Python experience building APIs.',
    'experience': [
        {
            'role': 'Senior Engineer',
            'company': 'Acme',
            'period': '2020-2024',
            'description': 'Built REST APIs with Django. Deployed on AWS EC2.',
        },
        {
            'role': 'Engineer',
            'company': 'Beta Corp',
            'period': '2017-2020',
            'description': 'Maintained PostgreSQL databases and wrote Python scripts.',
        },
    ],
    'education': [{'degree': "Bachelor's CS", 'year': '2017'}],
    'skills': ['Python', 'Django', 'AWS', 'PostgreSQL'],
}

JD = {
    'title': 'Staff Python Engineer',
    'company': 'TechCorp',
    'description': 'We need a Python engineer with FastAPI and Kubernetes experience.',
    'requirements': '7+ years Python, Kubernetes, CI/CD, PostgreSQL.',
    'skills_detected': ['Python', 'FastAPI', 'Kubernetes', 'PostgreSQL', 'CI/CD'],
}

MATCH = {
    'score': 72,
    'matched_skills': ['Python', 'PostgreSQL'],
    'missing_skills': ['FastAPI', 'Kubernetes', 'CI/CD'],
}


class TestResumeTailor:

    @pytest.fixture
    def tailor(self):
        return ResumeTailor()

    def test_init(self, tailor):
        assert tailor.ollama_model == 'mistral'

    def test_tailor_no_ollama_returns_original(self, tailor, monkeypatch):
        """When Ollama unavailable, original resume returned with note."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: False)
        result = tailor.tailor(RESUME, JD, MATCH)
        assert result['summary'] == RESUME['summary']
        assert result['experience'][0]['description'] == RESUME['experience'][0]['description']
        assert 'Ollama unavailable' in result['_tailor_note']

    def test_tailor_does_not_mutate_original(self, tailor, monkeypatch):
        """Original resume dict is never modified."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: False)
        original_summary = RESUME['summary']
        tailor.tailor(RESUME, JD, MATCH)
        assert RESUME['summary'] == original_summary

    def test_tailor_with_ollama_rewrites_summary(self, tailor, monkeypatch):
        """When Ollama available, summary is rewritten."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'Rewritten summary targeting Staff Python Engineer.')
        result = tailor.tailor(RESUME, JD, MATCH)
        assert result['summary'] == 'Rewritten summary targeting Staff Python Engineer.'
        assert result['summary'] != RESUME['summary']

    def test_tailor_with_ollama_rewrites_experience(self, tailor, monkeypatch):
        """Top 2 experience descriptions are rewritten."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'Rewritten experience.')
        result = tailor.tailor(RESUME, JD, MATCH)
        assert result['experience'][0]['description'] == 'Rewritten experience.'
        assert result['experience'][1]['description'] == 'Rewritten experience.'

    def test_tailor_preserves_beyond_top2_experience(self, tailor, monkeypatch):
        """Only top 2 experiences are rewritten; rest unchanged."""
        resume3 = copy.deepcopy(RESUME)
        resume3['experience'].append({
            'role': 'Junior', 'company': 'Old Co', 'period': '2015-2017',
            'description': 'Old description untouched.'
        })
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'Rewritten.')
        result = tailor.tailor(resume3, JD, MATCH)
        assert result['experience'][2]['description'] == 'Old description untouched.'

    def test_tailor_fallback_on_empty_generate(self, tailor, monkeypatch):
        """Empty LLM response keeps original text."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: '')
        result = tailor.tailor(RESUME, JD, MATCH)
        assert result['summary'] == RESUME['summary']

    def test_tailor_note_set_on_success(self, tailor, monkeypatch):
        """_tailor_note records target job when Ollama succeeds."""
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'ok')
        result = tailor.tailor(RESUME, JD, MATCH)
        assert 'Staff Python Engineer' in result['_tailor_note']
        assert 'TechCorp' in result['_tailor_note']

    def test_tailor_no_summary_skips_rewrite(self, tailor, monkeypatch):
        """Resume without summary field does not crash."""
        resume_no_summary = copy.deepcopy(RESUME)
        resume_no_summary.pop('summary', None)
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'rewritten')
        result = tailor.tailor(resume_no_summary, JD, MATCH)
        assert 'summary' not in result or result.get('summary') == ''

    def test_tailor_no_experience_skips_rewrite(self, tailor, monkeypatch):
        """Resume without experience does not crash."""
        resume_no_exp = copy.deepcopy(RESUME)
        resume_no_exp['experience'] = []
        monkeypatch.setattr(tailor, '_ollama_available', lambda: True)
        monkeypatch.setattr(tailor, '_generate', lambda prompt: 'rewritten')
        result = tailor.tailor(resume_no_exp, JD, MATCH)
        assert result['experience'] == []

    def test_save_json(self, tailor, tmp_path):
        data = {'summary': 'Tailored resume', '_tailor_note': 'test'}
        output = str(tmp_path / 'tailored.json')
        tailor.save_json(data, output)
        with open(output) as f:
            loaded = json.load(f)
        assert loaded['summary'] == 'Tailored resume'
