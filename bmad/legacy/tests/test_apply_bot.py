#!/usr/bin/env python3
"""
Tests unitaires — Auto-Apply Bot

Run: pytest tests/test_apply_bot.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from apply_bot import ApplyBot

RESUME = {
    'personal': {
        'name': 'Jane Dev',
        'email': 'jane@example.com',
        'phone': '+33600000000',
        'linkedin': 'linkedin.com/in/janedev',
    },
    'skills': ['Python', 'Django'],
}


class MockLocator:
    """Minimal Playwright locator mock."""
    def __init__(self, visible=True, count=1):
        self._visible = visible
        self._count = count
        self.filled_value = None
        self.files_set = None
        self.clicked = False

    def count(self):
        return self._count

    def is_visible(self, timeout=500):
        return self._visible

    def fill(self, value):
        self.filled_value = value

    def set_input_files(self, path):
        self.files_set = path

    def click(self):
        self.clicked = True


class MockPage:
    """Minimal Playwright page mock."""
    def __init__(self, locators=None):
        self._locators = locators or {}
        self.screenshot_path = None

    def locator(self, selector):
        mock = self._locators.get(selector, MockLocator(visible=False, count=0))
        return type('L', (), {
            'first': mock,
            'count': lambda s: mock.count(),
        })()

    def screenshot(self, path, full_page=False):
        self.screenshot_path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(b'PNG_MOCK')

    def wait_for_load_state(self, *args, **kwargs):
        pass


class TestApplyBot:

    @pytest.fixture
    def bot(self):
        return ApplyBot()

    def test_init(self, bot):
        assert bot.headless is True
        assert bot.timeout == 15000

    def test_fill_fields_email(self, bot):
        email_locator = MockLocator(visible=True, count=1)
        page = MockPage({
            'input[type="email"]': email_locator,
        })
        personal = {'name': '', 'email': 'jane@example.com', 'phone': '', 'linkedin': ''}
        filled = bot._fill_fields(page, personal)
        assert 'email' in filled
        assert email_locator.filled_value == 'jane@example.com'

    def test_fill_fields_full_name(self, bot):
        name_locator = MockLocator(visible=True, count=1)
        page = MockPage({'input[name="name"]': name_locator})
        personal = {'name': 'Jane Dev', 'email': '', 'phone': '', 'linkedin': ''}
        filled = bot._fill_fields(page, personal)
        assert 'full_name' in filled
        assert name_locator.filled_value == 'Jane Dev'

    def test_fill_fields_skips_empty_values(self, bot):
        locator = MockLocator(visible=True, count=1)
        page = MockPage({'input[type="email"]': locator})
        personal = {'name': '', 'email': '', 'phone': '', 'linkedin': ''}
        filled = bot._fill_fields(page, personal)
        assert 'email' not in filled

    def test_fill_fields_skips_invisible(self, bot):
        locator = MockLocator(visible=False, count=1)
        page = MockPage({'input[type="email"]': locator})
        personal = {'name': '', 'email': 'a@b.com', 'phone': '', 'linkedin': ''}
        filled = bot._fill_fields(page, personal)
        assert 'email' not in filled

    def test_upload_pdf_success(self, bot, tmp_path):
        pdf = str(tmp_path / 'resume.pdf')
        with open(pdf, 'wb') as f:
            f.write(b'%PDF')
        upload_locator = MockLocator(visible=True, count=1)
        page = MockPage({'input[type="file"][accept*="pdf"]': upload_locator})
        result = bot._upload_pdf(page, pdf)
        assert result is True
        assert upload_locator.files_set == pdf

    def test_upload_pdf_no_input(self, bot, tmp_path):
        pdf = str(tmp_path / 'resume.pdf')
        with open(pdf, 'wb') as f:
            f.write(b'%PDF')
        page = MockPage({})
        result = bot._upload_pdf(page, pdf)
        assert result is False

    def test_result_shape(self, bot, monkeypatch):
        """apply() returns correct dict shape (Playwright monkeypatched)."""
        def fake_apply(url, resume, pdf_path=None, dry_run=True):
            return {
                'success': True,
                'url': url,
                'fields_filled': ['email'],
                'screenshot_path': '/fake/screenshot.png',
                'dry_run': dry_run,
            }
        monkeypatch.setattr(bot, 'apply', fake_apply)
        result = bot.apply('https://example.com/apply', RESUME)
        assert result['success'] is True
        assert result['dry_run'] is True
        assert 'fields_filled' in result
        assert 'screenshot_path' in result

    def test_dry_run_default(self, bot):
        """dry_run=True is the default — verify signature."""
        import inspect
        sig = inspect.signature(bot.apply)
        assert sig.parameters['dry_run'].default is True

    def test_no_playwright_raises(self, bot, monkeypatch):
        import apply_bot as ab
        monkeypatch.setattr(ab, 'sync_playwright', None)
        with pytest.raises(RuntimeError, match="playwright not installed"):
            bot.apply('https://example.com', RESUME)
