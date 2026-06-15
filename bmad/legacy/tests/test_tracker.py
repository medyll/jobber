#!/usr/bin/env python3
"""
Tests unitaires — Application Tracker

Run: pytest tests/test_tracker.py -v
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tracker import ApplicationTracker

JD = {'company': 'TechCorp', 'title': 'Staff Engineer'}
MATCH = {'score': 85}
URL = 'https://example.com/jobs/123'
URL2 = 'https://example.com/jobs/456'


@pytest.fixture
def tracker(tmp_path):
    return ApplicationTracker(db_path=str(tmp_path / 'test.db'))


class TestApplicationTracker:

    def test_init_creates_db(self, tmp_path):
        db = str(tmp_path / 'new.db')
        ApplicationTracker(db_path=db)
        assert os.path.exists(db)

    def test_log_inserts_record(self, tracker):
        row_id = tracker.log(URL, JD, MATCH)
        assert row_id > 0

    def test_log_returns_id(self, tracker):
        id1 = tracker.log(URL, JD, MATCH)
        id2 = tracker.log(URL2, JD, MATCH)
        assert id1 != id2

    def test_log_upsert_on_duplicate_url(self, tracker):
        tracker.log(URL, JD, MATCH)
        updated_match = {'score': 90}
        tracker.log(URL, JD, updated_match)
        record = tracker.get(URL)
        assert record['score'] == 90

    def test_log_sets_pending_status(self, tracker):
        tracker.log(URL, JD, MATCH)
        record = tracker.get(URL)
        assert record['status'] == 'pending'

    def test_log_dry_run_flag(self, tracker):
        tracker.log(URL, JD, MATCH, dry_run=True)
        assert tracker.get(URL)['dry_run'] is True
        tracker.log(URL2, JD, MATCH, dry_run=False)
        assert tracker.get(URL2)['dry_run'] is False

    def test_update_status_valid(self, tracker):
        tracker.log(URL, JD, MATCH)
        result = tracker.update_status(URL, 'applied')
        assert result is True
        assert tracker.get(URL)['status'] == 'applied'

    def test_update_status_all_valid_values(self, tracker):
        for status in ('pending', 'applied', 'interview', 'rejected', 'offer'):
            tracker.log(f'https://example.com/{status}', JD, MATCH)
            assert tracker.update_status(f'https://example.com/{status}', status) is True

    def test_update_status_invalid_raises(self, tracker):
        tracker.log(URL, JD, MATCH)
        with pytest.raises(ValueError, match="Invalid status"):
            tracker.update_status(URL, 'ghosted')

    def test_update_status_unknown_url_returns_false(self, tracker):
        result = tracker.update_status('https://unknown.com', 'applied')
        assert result is False

    def test_list_applications_empty(self, tracker):
        assert tracker.list_applications() == []

    def test_list_applications_returns_all(self, tracker):
        tracker.log(URL, JD, MATCH)
        tracker.log(URL2, {'company': 'Acme', 'title': 'Dev'}, {'score': 60})
        apps = tracker.list_applications()
        assert len(apps) == 2

    def test_list_applications_shape(self, tracker):
        tracker.log(URL, JD, MATCH)
        app = tracker.list_applications()[0]
        for key in ('id', 'url', 'company', 'title', 'score', 'dry_run', 'status', 'applied_at'):
            assert key in app

    def test_get_existing(self, tracker):
        tracker.log(URL, JD, MATCH)
        record = tracker.get(URL)
        assert record['url'] == URL
        assert record['company'] == 'TechCorp'
        assert record['score'] == 85

    def test_get_nonexistent_returns_none(self, tracker):
        assert tracker.get('https://missing.com') is None
