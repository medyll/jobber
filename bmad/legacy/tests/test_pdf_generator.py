#!/usr/bin/env python3
"""
Tests unitaires — PDF Generator

Run: pytest tests/test_pdf_generator.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pdf_generator import PDFGenerator

RESUME = {
    'personal': {
        'name': 'Jane Dev',
        'email': 'jane@example.com',
        'phone': '+33600000000',
        'linkedin': 'linkedin.com/in/janedev',
        'github': 'github.com/janedev',
    },
    'summary': 'Senior backend engineer with 7 years of Python experience.',
    'experience': [
        {
            'role': 'Senior Engineer',
            'company': 'Acme Corp',
            'period': '2020-2024',
            'description': 'Built REST APIs with Django and FastAPI. Deployed on AWS.',
        },
    ],
    'education': [
        {'degree': "Bachelor's in Computer Science", 'school': 'Université Paris 6', 'year': '2017'},
    ],
    'skills': ['Python', 'Django', 'FastAPI', 'AWS', 'PostgreSQL', 'Docker'],
}

RESUME_MINIMAL = {
    'personal': {},
    'summary': '',
    'experience': [],
    'education': [],
    'skills': [],
}


class TestPDFGenerator:

    @pytest.fixture
    def gen(self):
        return PDFGenerator()

    def test_init(self, gen):
        assert gen.margin is not None
        assert gen.page_size is not None

    def test_generate_creates_file(self, gen, tmp_path):
        output = str(tmp_path / 'resume.pdf')
        result = gen.generate(RESUME, output)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_generate_returns_absolute_path(self, gen, tmp_path):
        output = str(tmp_path / 'resume.pdf')
        result = gen.generate(RESUME, output)
        assert os.path.isabs(result)

    def test_generate_minimal_resume(self, gen, tmp_path):
        """Minimal resume with empty fields should not crash."""
        output = str(tmp_path / 'minimal.pdf')
        result = gen.generate(RESUME_MINIMAL, output)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_generate_no_summary(self, gen, tmp_path):
        resume = {**RESUME, 'summary': ''}
        output = str(tmp_path / 'no_summary.pdf')
        result = gen.generate(resume, output)
        assert os.path.exists(result)

    def test_generate_no_experience(self, gen, tmp_path):
        resume = {**RESUME, 'experience': []}
        output = str(tmp_path / 'no_exp.pdf')
        result = gen.generate(resume, output)
        assert os.path.exists(result)

    def test_generate_no_skills(self, gen, tmp_path):
        resume = {**RESUME, 'skills': []}
        output = str(tmp_path / 'no_skills.pdf')
        result = gen.generate(resume, output)
        assert os.path.exists(result)

    def test_render_skills_joined(self, gen):
        styles = gen._build_styles()
        elements = gen._render_skills(['Python', 'Django', 'AWS'], styles)
        # Should be heading + one paragraph
        assert len(elements) == 2

    def test_render_header_no_name(self, gen):
        styles = gen._build_styles()
        elements = gen._render_header({}, styles)
        # HRFlowable only (no name, no contacts)
        assert len(elements) == 1

    def test_render_header_full(self, gen):
        styles = gen._build_styles()
        elements = gen._render_header(RESUME['personal'], styles)
        # name + contact line + HR = 3
        assert len(elements) == 3

    def test_no_reportlab_raises(self, gen, monkeypatch):
        import pdf_generator as pg
        monkeypatch.setattr(pg, 'REPORTLAB_AVAILABLE', False)
        with pytest.raises(RuntimeError, match="reportlab not installed"):
            gen.generate(RESUME, 'out.pdf')
