#!/usr/bin/env python3
"""
Jobber — PDF Generator

Render a parsed (and optionally tailored) resume to an ATS-friendly PDF.
Uses reportlab Platypus for structured layout.

Usage:
    python src/pdf_generator.py resume.json output.pdf
"""

import sys
import os
import json
from typing import Dict, List, Optional

try:
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class PDFGenerator:
    """Render resume dict to an ATS-friendly PDF."""

    def __init__(self):
        # Constants resolved at runtime to avoid NameError when reportlab absent
        self.page_size = A4 if REPORTLAB_AVAILABLE else (595, 842)
        self.margin = (2 * cm) if REPORTLAB_AVAILABLE else 56

    def generate(self, resume: Dict, output_path: str) -> str:
        """
        Generate a PDF from a resume dict.

        Args:
            resume: Parsed (or tailored) resume dict
            output_path: Destination .pdf path

        Returns:
            str: Absolute path to the created PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed — run: pip install reportlab")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        styles = self._build_styles()
        story = []

        # Header
        story += self._render_header(resume.get('personal', {}), styles)

        # Summary
        summary = resume.get('summary', '')
        if summary:
            story += self._render_section('Summary', [summary], styles)

        # Experience
        experience = resume.get('experience', [])
        if experience:
            story += self._render_experience(experience, styles)

        # Education
        education = resume.get('education', [])
        if education:
            story += self._render_education(education, styles)

        # Skills
        skills = resume.get('skills', [])
        if skills:
            story += self._render_skills(skills, styles)

        doc.build(story)
        return os.path.abspath(output_path)

    # ── Styles ────────────────────────────────────────────────────────────────

    def _build_styles(self) -> Dict:
        base = getSampleStyleSheet()
        return {
            'name': ParagraphStyle(
                'Name',
                parent=base['Title'],
                fontSize=18,
                spaceAfter=4,
                textColor=colors.HexColor('#1a1a1a'),
            ),
            'contact': ParagraphStyle(
                'Contact',
                parent=base['Normal'],
                fontSize=9,
                spaceAfter=8,
                textColor=colors.HexColor('#444444'),
            ),
            'section_heading': ParagraphStyle(
                'SectionHeading',
                parent=base['Heading2'],
                fontSize=11,
                spaceBefore=10,
                spaceAfter=3,
                textColor=colors.HexColor('#1a1a1a'),
                borderPad=0,
            ),
            'body': ParagraphStyle(
                'Body',
                parent=base['Normal'],
                fontSize=9,
                spaceAfter=4,
                leading=13,
            ),
            'job_title': ParagraphStyle(
                'JobTitle',
                parent=base['Normal'],
                fontSize=10,
                spaceBefore=6,
                spaceAfter=1,
                textColor=colors.HexColor('#1a1a1a'),
                fontName='Helvetica-Bold',
            ),
            'job_meta': ParagraphStyle(
                'JobMeta',
                parent=base['Normal'],
                fontSize=8,
                spaceAfter=2,
                textColor=colors.HexColor('#666666'),
            ),
        }

    # ── Section renderers ─────────────────────────────────────────────────────

    def _render_header(self, personal: Dict, styles: Dict) -> list:
        elements = []
        name = personal.get('name', '')
        if name:
            elements.append(Paragraph(name, styles['name']))

        contacts = []
        for field in ('email', 'phone', 'linkedin', 'github'):
            val = personal.get(field)
            if val:
                contacts.append(val)
        if contacts:
            elements.append(Paragraph(' · '.join(contacts), styles['contact']))

        elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#cccccc')))
        return elements

    def _render_section(self, title: str, paragraphs: List[str], styles: Dict) -> list:
        elements = [Paragraph(title.upper(), styles['section_heading'])]
        for text in paragraphs:
            if text.strip():
                elements.append(Paragraph(text, styles['body']))
        return elements

    def _render_experience(self, experience: List[Dict], styles: Dict) -> list:
        elements = [Paragraph('EXPERIENCE', styles['section_heading'])]
        for exp in experience:
            role = exp.get('role', '')
            company = exp.get('company', '')
            period = exp.get('period', '')
            desc = exp.get('description', '')

            if role or company:
                title_text = f"{role}" + (f" — {company}" if company else '')
                elements.append(Paragraph(title_text, styles['job_title']))
            if period:
                elements.append(Paragraph(period, styles['job_meta']))
            if desc:
                elements.append(Paragraph(desc.strip(), styles['body']))
            elements.append(Spacer(1, 3))
        return elements

    def _render_education(self, education: List[Dict], styles: Dict) -> list:
        elements = [Paragraph('EDUCATION', styles['section_heading'])]
        for edu in education:
            degree = edu.get('degree', '')
            school = edu.get('school', '')
            year = edu.get('year', '')
            line = degree
            if school:
                line += f" — {school}"
            if year:
                line += f" ({year})"
            if line.strip():
                elements.append(Paragraph(line, styles['body']))
        return elements

    def _render_skills(self, skills: List[str], styles: Dict) -> list:
        elements = [Paragraph('SKILLS', styles['section_heading'])]
        elements.append(Paragraph(', '.join(skills), styles['body']))
        return elements


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python pdf_generator.py <resume.json> <output.pdf>")
        sys.exit(1)

    resume_path, output_path = sys.argv[1], sys.argv[2]

    with open(resume_path) as f:
        resume = json.load(f)

    gen = PDFGenerator()
    print(f"📄 Generating PDF...")
    path = gen.generate(resume, output_path)
    print(f"✅ PDF saved to {path}")
