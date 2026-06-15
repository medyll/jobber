#!/usr/bin/env python3
"""
Tests unitaires — Resume Parser

Run: pytest tests/test_parser.py -v
"""

import pytest
import os
import sys
import json
import tempfile

# Import module à tester
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from parser import ResumeParser


class TestResumeParser:
    """Tests pour ResumeParser."""
    
    @pytest.fixture
    def parser(self):
        """Fixture: Parser instance."""
        return ResumeParser()
    
    @pytest.fixture
    def sample_resume_pdf(self):
        """Fixture: Create a sample PDF resume for testing."""
        # Skip if PyPDF2 not available
        try:
            from PyPDF2 import PdfWriter
        except ImportError:
            pytest.skip("PyPDF2 not installed")
        
        # Create a minimal PDF for testing
        # Note: This is a placeholder - in real tests, use actual PDF files
        return None
    
    def test_init(self, parser):
        """Test: Parser initializes correctly."""
        assert parser.sections is not None
        assert 'personal' in parser.sections
        assert 'experience' in parser.sections
    
    def test_extract_email(self, parser):
        """Test: Extract email from text."""
        text = "John Doe\njohn.doe@example.com\n+1234567890"
        personal = parser._extract_personal(text)
        
        assert personal['email'] == 'john.doe@example.com'
    
    def test_extract_phone(self, parser):
        """Test: Extract phone from text."""
        text = "John Doe\njohn@example.com\n+1 (555) 123-4567"
        personal = parser._extract_personal(text)
        
        assert personal['phone'] is not None
        assert '123' in personal['phone']
    
    def test_extract_linkedin(self, parser):
        """Test: Extract LinkedIn URL from text."""
        text = "linkedin.com/in/johndoe"
        personal = parser._extract_personal(text)
        
        assert personal['linkedin'] == 'linkedin.com/in/johndoe'
    
    def test_extract_github(self, parser):
        """Test: Extract GitHub URL from text."""
        text = "github.com/johndoe"
        personal = parser._extract_personal(text)
        
        assert personal['github'] == 'github.com/johndoe'
    
    def test_extract_year(self, parser):
        """Test: Extract year from text."""
        text = "Bachelor's Degree, 2020"
        year = parser._extract_year(text)
        
        assert year == '2020'
    
    def test_mask_pii(self, parser):
        """Test: PII masking."""
        personal = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
            'linkedin': 'linkedin.com/in/johndoe'
        }
        
        masked = parser._mask_pii(personal)
        
        assert masked['name'] == '[NAME]'
        assert masked['email'] == '[EMAIL]'
        assert masked['phone'] == '[PHONE]'
        assert masked['linkedin'] == '[LINKEDIN]'
    
    def test_extract_skills(self, parser):
        """Test: Extract skills from text."""
        text = "Skills: Python, JavaScript, AWS, Docker, Kubernetes"
        skills = parser._extract_skills(text)
        
        assert len(skills) > 0
        assert any('Python' in s for s in skills)
    
    def test_parse_unsupported_file(self, parser):
        """Test: Unsupported file type raises error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse("resume.txt")
    
    def test_parse_nonexistent_file(self, parser):
        """Test: Nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            parser.parse("nonexistent.pdf")
    
    def test_save_json(self, parser, tmp_path):
        """Test: Save parsed data to JSON."""
        data = {
            'personal': {'name': 'Test User'},
            'skills': ['Python', 'JavaScript']
        }
        output_path = tmp_path / "test.json"
        
        parser.save_json(data, str(output_path))
        
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['personal']['name'] == 'Test User'
        assert 'Python' in loaded['skills']


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
