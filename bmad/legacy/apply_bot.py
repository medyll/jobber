#!/usr/bin/env python3
"""
Jobber — Auto-Apply Bot

Fill and optionally submit job application forms using Playwright.
Dry-run mode by default — fills fields and screenshots without submitting.

Usage:
    python src/apply_bot.py <url> <resume.json> <resume.pdf>
    python src/apply_bot.py <url> <resume.json> <resume.pdf> --live
"""

import sys
import os
import json
import time
from typing import Dict, Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser
except ImportError:
    sync_playwright = None

SCREENSHOTS_DIR = os.path.join('bmad', 'artifacts', 'screenshots')

# Generic CSS selectors tried in order for each field
FIELD_SELECTORS = {
    'first_name': [
        'input[name*="first"][type="text"]',
        'input[id*="first"]',
        'input[placeholder*="First"]',
    ],
    'last_name': [
        'input[name*="last"][type="text"]',
        'input[id*="last"]',
        'input[placeholder*="Last"]',
    ],
    'full_name': [
        'input[name="name"]',
        'input[name*="full"]',
        'input[id*="name"]',
        'input[placeholder*="Full name"]',
        'input[placeholder*="Your name"]',
    ],
    'email': [
        'input[type="email"]',
        'input[name*="email"]',
        'input[id*="email"]',
        'input[placeholder*="email"]',
    ],
    'phone': [
        'input[type="tel"]',
        'input[name*="phone"]',
        'input[id*="phone"]',
        'input[placeholder*="phone"]',
    ],
    'linkedin': [
        'input[name*="linkedin"]',
        'input[id*="linkedin"]',
        'input[placeholder*="LinkedIn"]',
    ],
}


class ApplyBot:
    """Fill job application forms via Playwright. Dry-run safe by default."""

    def __init__(self, headless: bool = True, timeout: int = 15000):
        self.headless = headless
        self.timeout = timeout
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    def apply(self, url: str, resume: Dict, pdf_path: Optional[str] = None,
               dry_run: bool = True) -> Dict:
        """
        Navigate to a job application URL and fill the form.

        Args:
            url: Application form URL
            resume: Parsed resume dict
            pdf_path: Path to resume PDF for file upload fields
            dry_run: If True (default), fill but do NOT submit

        Returns:
            dict: {success, url, fields_filled, screenshot_path, dry_run}
        """
        if not sync_playwright:
            raise RuntimeError(
                "playwright not installed — run: pip install playwright && playwright install chromium"
            )

        result = {
            'success': False,
            'url': url,
            'fields_filled': [],
            'screenshot_path': None,
            'dry_run': dry_run,
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()

            try:
                page.goto(url, wait_until='networkidle', timeout=self.timeout * 2)
                personal = resume.get('personal', {})

                # Fill text fields
                filled = self._fill_fields(page, personal)
                result['fields_filled'] = filled

                # Upload PDF if provided and an upload input exists
                if pdf_path and os.path.exists(pdf_path):
                    uploaded = self._upload_pdf(page, pdf_path)
                    if uploaded:
                        result['fields_filled'].append('resume_file')

                # Screenshot (always — proof of fill)
                screenshot_path = self._screenshot(page, url)
                result['screenshot_path'] = screenshot_path

                # Submit only in live mode
                if not dry_run:
                    submitted = self._submit(page)
                    result['success'] = submitted
                else:
                    result['success'] = True  # dry-run always succeeds if no crash

            except Exception as e:
                result['error'] = str(e)
            finally:
                browser.close()

        return result

    # ── Field filling ─────────────────────────────────────────────────────────

    def _fill_fields(self, page: 'Page', personal: Dict) -> list:
        """Try to fill contact fields. Returns list of filled field names."""
        filled = []
        name = personal.get('name', '')
        first, *rest = name.split(' ', 1) if name else ('', [])
        last = rest[0] if rest else ''

        field_values = {
            'first_name': first,
            'last_name': last,
            'full_name': name,
            'email': personal.get('email', ''),
            'phone': personal.get('phone', ''),
            'linkedin': personal.get('linkedin', ''),
        }

        for field_name, value in field_values.items():
            if not value:
                continue
            for selector in FIELD_SELECTORS[field_name]:
                try:
                    locator = page.locator(selector).first
                    if locator.count() > 0 and locator.is_visible(timeout=500):
                        locator.fill(value)
                        filled.append(field_name)
                        break
                except Exception:
                    continue

        return filled

    def _upload_pdf(self, page: 'Page', pdf_path: str) -> bool:
        """Attempt to set a file input to the resume PDF."""
        upload_selectors = [
            'input[type="file"][accept*="pdf"]',
            'input[type="file"][name*="resume"]',
            'input[type="file"][name*="cv"]',
            'input[type="file"]',
        ]
        for selector in upload_selectors:
            try:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    locator.set_input_files(pdf_path)
                    return True
            except Exception:
                continue
        return False

    def _submit(self, page: 'Page') -> bool:
        """Click the submit button."""
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
        ]
        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if btn.count() > 0 and btn.is_visible(timeout=500):
                    btn.click()
                    page.wait_for_load_state('networkidle', timeout=self.timeout)
                    return True
            except Exception:
                continue
        return False

    def _screenshot(self, page: 'Page', url: str) -> str:
        """Save a screenshot and return the path."""
        ts = int(time.time())
        filename = f"apply-{ts}.png"
        path = os.path.join(SCREENSHOTS_DIR, filename)
        page.screenshot(path=path, full_page=True)
        return os.path.abspath(path)


# CLI
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python apply_bot.py <url> <resume.json> <resume.pdf> [--live]")
        sys.exit(1)

    url = sys.argv[1]
    resume_path = sys.argv[2]
    pdf_path = sys.argv[3]
    dry_run = '--live' not in sys.argv

    with open(resume_path) as f:
        resume = json.load(f)

    bot = ApplyBot()
    mode = "DRY RUN" if dry_run else "🚀 LIVE"
    print(f"🤖 Apply Bot [{mode}] → {url}")

    result = bot.apply(url, resume, pdf_path=pdf_path, dry_run=dry_run)

    print(f"\n📊 Result:")
    print(f"   Success:       {result['success']}")
    print(f"   Fields filled: {', '.join(result['fields_filled']) or 'none'}")
    print(f"   Screenshot:    {result['screenshot_path']}")
    if result.get('error'):
        print(f"   Error:         {result['error']}")
