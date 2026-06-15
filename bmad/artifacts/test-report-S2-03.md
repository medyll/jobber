# Test Report — S2-03: Auto-Apply Bot

**Date:** 2026-04-18
**Story:** S2-03 — Auto-Apply Bot (Playwright form filler)
**Result:** ✅ All tests passed

## Output

```
platform win32 -- Python 3.13.1, pytest-9.0.3
collected 10 items

tests/test_apply_bot.py::TestApplyBot::test_init PASSED
tests/test_apply_bot.py::TestApplyBot::test_fill_fields_email PASSED
tests/test_apply_bot.py::TestApplyBot::test_fill_fields_full_name PASSED
tests/test_apply_bot.py::TestApplyBot::test_fill_fields_skips_empty_values PASSED
tests/test_apply_bot.py::TestApplyBot::test_fill_fields_skips_invisible PASSED
tests/test_apply_bot.py::TestApplyBot::test_upload_pdf_success PASSED
tests/test_apply_bot.py::TestApplyBot::test_upload_pdf_no_input PASSED
tests/test_apply_bot.py::TestApplyBot::test_result_shape PASSED
tests/test_apply_bot.py::TestApplyBot::test_dry_run_default PASSED
tests/test_apply_bot.py::TestApplyBot::test_no_playwright_raises PASSED

10 passed in 0.03s
```

## Full suite: 69/69 passing
