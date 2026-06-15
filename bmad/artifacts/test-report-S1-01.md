# Test Report — S1-01: Resume Parser

**Date:** 2026-04-17
**Story:** S1-01 — Resume Parser (PDF/Docx) with PII masking
**Result:** ✅ All tests passed

## Output

```
platform win32 -- Python 3.13.1, pytest-9.0.3
collected 11 items

tests/test_parser.py::TestResumeParser::test_init PASSED
tests/test_parser.py::TestResumeParser::test_extract_email PASSED
tests/test_parser.py::TestResumeParser::test_extract_phone PASSED
tests/test_parser.py::TestResumeParser::test_extract_linkedin PASSED
tests/test_parser.py::TestResumeParser::test_extract_github PASSED
tests/test_parser.py::TestResumeParser::test_extract_year PASSED
tests/test_parser.py::TestResumeParser::test_mask_pii PASSED
tests/test_parser.py::TestResumeParser::test_extract_skills PASSED
tests/test_parser.py::TestResumeParser::test_parse_unsupported_file PASSED
tests/test_parser.py::TestResumeParser::test_parse_nonexistent_file PASSED
tests/test_parser.py::TestResumeParser::test_save_json PASSED

11 passed, 1 warning in 0.50s
```

## Warning
- PyPDF2 deprecated — `pypdf` is the successor. Non-blocking for now.
