#!/usr/bin/env python3
"""
Tests unitaires — Semantic Matcher

Run: pytest tests/test_matcher.py -v
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from matcher import SemanticMatcher


RESUME = {
    'personal': {'name': 'Jane Dev', 'email': 'jane@example.com'},
    'summary': 'Senior backend engineer with 7 years Python experience.',
    'experience': [
        {'role': 'Senior Engineer', 'company': 'Acme', 'period': '2020-2024',
         'description': 'Built scalable APIs with Django and FastAPI. Deployed on AWS.'},
    ],
    'education': [{'degree': "Bachelor's Computer Science", 'year': '2017'}],
    'skills': ['Python', 'Django', 'FastAPI', 'AWS', 'PostgreSQL', 'Docker', 'Git'],
}

JD = {
    'title': 'Senior Python Developer',
    'company': 'TechCorp',
    'location': 'Remote',
    'description': 'We need a Python developer with Django and AWS experience.',
    'requirements': '5+ years Python, AWS, PostgreSQL, CI/CD.',
    'skills_detected': ['Python', 'Django', 'AWS', 'PostgreSQL', 'Kubernetes'],
}

JD_NO_MATCH = {
    'title': 'iOS Engineer',
    'description': 'Swift, Objective-C, Xcode, iOS SDK.',
    'skills_detected': ['Swift', 'Objective-C', 'iOS'],
}


class TestSemanticMatcher:

    @pytest.fixture
    def matcher(self):
        return SemanticMatcher()

    def test_init(self, matcher):
        assert matcher.ollama_model == 'mistral'
        assert matcher._embedder is None

    def test_resume_to_text(self, matcher):
        text = matcher._resume_to_text(RESUME)
        assert 'Jane Dev' in text
        assert 'Python' in text
        assert 'Django' in text

    def test_jd_to_text(self, matcher):
        text = matcher._jd_to_text(JD)
        assert 'Senior Python Developer' in text
        assert 'Python' in text

    def test_skills_gap_full_match(self, matcher):
        resume_skills = ['Python', 'Django', 'AWS']
        jd_skills = ['Python', 'Django']
        matched, missing = matcher._skills_gap(resume_skills, jd_skills)
        assert set(matched) == {'Python', 'Django'}
        assert missing == []

    def test_skills_gap_partial(self, matcher):
        resume_skills = ['Python', 'Django']
        jd_skills = ['Python', 'Django', 'Kubernetes']
        matched, missing = matcher._skills_gap(resume_skills, jd_skills)
        assert 'Python' in matched
        assert 'Kubernetes' in missing

    def test_skills_gap_case_insensitive(self, matcher):
        matched, missing = matcher._skills_gap(['python', 'aws'], ['Python', 'AWS'])
        assert len(matched) == 2
        assert missing == []

    def test_keyword_overlap_good_match(self, matcher):
        result = matcher._score_keyword_overlap(RESUME, JD)
        assert result['score'] > 50
        assert 'Python' in result['matched_skills']
        assert 'Kubernetes' in result['missing_skills']
        assert result['method'] == 'keyword'

    def test_keyword_overlap_no_match(self, matcher):
        result = matcher._score_keyword_overlap(RESUME, JD_NO_MATCH)
        assert result['score'] == 0
        assert result['matched_skills'] == []

    def test_keyword_overlap_empty_jd_skills(self, matcher):
        jd_empty = {**JD, 'skills_detected': []}
        result = matcher._score_keyword_overlap(RESUME, jd_empty)
        assert result['score'] == 0

    def test_parse_llm_json_valid(self, matcher):
        raw = '{"score": 80, "matched_skills": ["Python"], "missing_skills": [], "strengths": [], "gaps": [], "summary": "Good"}'
        result = matcher._parse_llm_json(raw)
        assert result['score'] == 80
        assert result['matched_skills'] == ['Python']

    def test_parse_llm_json_fenced(self, matcher):
        raw = '```json\n{"score": 75, "matched_skills": [], "missing_skills": [], "strengths": [], "gaps": [], "summary": "Ok"}\n```'
        result = matcher._parse_llm_json(raw)
        assert result['score'] == 75

    def test_parse_llm_json_invalid(self, matcher):
        result = matcher._parse_llm_json('not json at all')
        assert result['score'] == 0
        assert 'Parse error' in result['summary']

    def test_match_uses_keyword_fallback_no_ollama(self, matcher, monkeypatch):
        monkeypatch.setattr(matcher, '_ollama_available', lambda: False)
        monkeypatch.setattr(matcher, '_score_with_embeddings',
                            lambda r, j, rt, jt: matcher._score_keyword_overlap(r, j))
        result = matcher.match(RESUME, JD)
        assert 'score' in result
        assert 'matched_skills' in result
        assert result['resume_skills'] == RESUME['skills']
        assert result['jd_skills'] == JD['skills_detected']

    def test_save_json(self, matcher, tmp_path):
        data = {'score': 85, 'matched_skills': ['Python']}
        output = str(tmp_path / 'result.json')
        matcher.save_json(data, output)
        with open(output) as f:
            loaded = json.load(f)
        assert loaded['score'] == 85
