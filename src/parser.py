#!/usr/bin/env python3
"""
Jobber — Resume Parser

Extract structured data from PDF/Docx resume files.

Features:
- PDF extraction (PyPDF2, pdfminer)
- Docx extraction (python-docx)
- Structure preservation (headers, sections)
- PII masking (optional, before LLM)

Usage:
    python src/parser.py resume.pdf
    python src/parser.py resume.docx --mask-pii
"""

import sys
import os
import json
import re
from typing import Dict, List, Optional

# PDF parsing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
except ImportError:
    pdfminer_extract = None

# Docx parsing
try:
    from docx import Document
except ImportError:
    Document = None


class ResumeParser:
    """Parse resume files (PDF/Docx) into structured JSON."""
    
    def __init__(self):
        self.sections = {
            'personal': ['name', 'email', 'phone', 'address', 'linkedin', 'github'],
            'experience': ['experience', 'work', 'employment', 'professional'],
            'education': ['education', 'degree', 'university', 'school'],
            'skills': ['skills', 'technologies', 'languages', 'certifications'],
            'summary': ['summary', 'objective', 'profile', 'about']
        }
    
    def parse(self, file_path: str, mask_pii: bool = False) -> Dict:
        """
        Parse resume file.
        
        Args:
            file_path: Path to PDF or Docx file
            mask_pii: If True, mask personally identifiable information
            
        Returns:
            dict: Structured resume data
        """
        # Extract raw text
        text = self._extract_text(file_path)
        
        # Parse sections
        resume = {
            'personal': self._extract_personal(text),
            'summary': self._extract_section(text, self.sections['summary']),
            'experience': self._extract_experience(text),
            'education': self._extract_education(text),
            'skills': self._extract_skills(text)
        }
        
        # Mask PII if requested
        if mask_pii:
            resume['personal'] = self._mask_pii(resume['personal'])
        
        return resume
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from file."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._extract_pdf(file_path)
        elif ext == '.docx':
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Try pdfminer first (better structure preservation)
        if pdfminer_extract:
            try:
                return pdfminer_extract(file_path)
            except Exception:
                pass
        
        # Fallback to PyPDF2
        if PdfReader:
            try:
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
            except Exception as e:
                raise RuntimeError(f"PDF extraction failed: {e}")
        
        raise RuntimeError("No PDF library available (install PyPDF2 or pdfminer.six)")
    
    def _extract_docx(self, file_path: str) -> str:
        """Extract text from Docx."""
        if not Document:
            raise RuntimeError("python-docx not installed")
        
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    
    def _extract_personal(self, text: str) -> Dict:
        """Extract personal information."""
        personal = {}
        
        # Email
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        email_match = re.search(email_pattern, text)
        personal['email'] = email_match.group(0) if email_match else None
        
        # Phone
        phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{6,12}'
        phone_match = re.search(phone_pattern, text)
        personal['phone'] = phone_match.group(0) if phone_match else None
        
        # LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        personal['linkedin'] = linkedin_match.group(0) if linkedin_match else None
        
        # GitHub
        github_pattern = r'github\.com/[\w-]+'
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        personal['github'] = github_match.group(0) if github_match else None
        
        # Name (usually at top, capitalized words)
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 50 and not '@' in line:
                # Likely a name
                personal['name'] = line
                break
        
        return personal
    
    def _extract_section(self, text: str, keywords: List[str]) -> str:
        """Extract a section by keywords."""
        pattern = '|'.join(keywords)
        match = re.search(rf'({pattern}).*?(?=\n[A-Z]|\Z)', text, re.IGNORECASE | re.DOTALL)
        return match.group(0).strip() if match else ""
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience."""
        experiences = []
        
        # Simple pattern: company, role, dates, description
        # This is a basic implementation - can be enhanced with LLM
        lines = text.split('\n')
        current_exp = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for date pattern (e.g., "2020-2023" or "Jan 2020 - Present")
            date_pattern = r'\d{4}[-/]\d{4}|\w+ \d{4}[-/]\w+ \d{4}|Present'
            if re.search(date_pattern, line):
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {'period': line}
            elif current_exp and 'company' not in current_exp:
                current_exp['company'] = line
            elif current_exp and 'role' not in current_exp:
                current_exp['role'] = line
            elif current_exp:
                current_exp['description'] = current_exp.get('description', '') + line + ' '
        
        if current_exp:
            experiences.append(current_exp)
        
        return experiences
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education."""
        education = []
        
        # Look for degree patterns
        degree_keywords = ['Bachelor', 'Master', 'PhD', 'B.S.', 'M.S.', 'B.A.', 'M.A.']
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            for keyword in degree_keywords:
                if keyword in line:
                    edu = {
                        'degree': line.strip(),
                        'school': lines[i+1].strip() if i+1 < len(lines) else '',
                        'year': self._extract_year(line)
                    }
                    education.append(edu)
                    break
        
        return education
    
    def _extract_year(self, text: str) -> Optional[str]:
        """Extract year from text."""
        year_pattern = r'\b(19|20)\d{2}\b'
        match = re.search(year_pattern, text)
        return match.group(0) if match else None
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills list."""
        skills = []
        
        # Look for comma-separated lists or bullet points
        # Simple implementation - can be enhanced
        lines = text.split('\n')
        for line in lines:
            if ',' in line:
                items = [item.strip() for item in line.split(',') if len(item.strip()) < 50]
                skills.extend(items)
        
        # Remove duplicates and clean
        skills = list(set([s for s in skills if len(s) > 2 and len(s) < 50]))
        
        return skills[:50]  # Limit to 50 skills
    
    def _mask_pii(self, personal: Dict) -> Dict:
        """Mask personally identifiable information."""
        masked = personal.copy()
        
        if masked.get('name'):
            masked['name'] = '[NAME]'
        if masked.get('email'):
            masked['email'] = '[EMAIL]'
        if masked.get('phone'):
            masked['phone'] = '[PHONE]'
        if masked.get('address'):
            masked['address'] = '[ADDRESS]'
        if masked.get('linkedin'):
            masked['linkedin'] = '[LINKEDIN]'
        
        return masked
    
    def save_json(self, data: Dict, output_path: str):
        """Save parsed data to JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {output_path}")


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parser.py <resume.pdf|resume.docx> [--mask-pii]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    mask_pii = '--mask-pii' in sys.argv
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    parser = ResumeParser()
    
    print(f"📄 Parsing {file_path}...")
    resume = parser.parse(file_path, mask_pii=mask_pii)
    
    # Save to JSON
    output_path = os.path.splitext(file_path)[0] + '_parsed.json'
    parser.save_json(resume, output_path)
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"   Name: {resume['personal'].get('name', 'N/A')}")
    print(f"   Email: {resume['personal'].get('email', 'N/A')}")
    print(f"   Experience: {len(resume['experience'])} positions")
    print(f"   Education: {len(resume['education'])} degrees")
    print(f"   Skills: {len(resume['skills'])} items")
