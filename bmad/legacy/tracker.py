#!/usr/bin/env python3
"""
Jobber — Application Tracker

SQLite-based log of every job application: URL, company, title, score, status.

Usage:
    python src/tracker.py list
    python src/tracker.py update <url> <status>
"""

import sys
import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

DB_PATH = os.environ.get('JOBBER_DB', 'jobber.db')

VALID_STATUSES = {'pending', 'applied', 'interview', 'rejected', 'offer'}

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    url       TEXT    NOT NULL UNIQUE,
    company   TEXT,
    title     TEXT,
    score     INTEGER,
    dry_run   INTEGER DEFAULT 1,
    status    TEXT    DEFAULT 'pending',
    applied_at TEXT,
    updated_at TEXT
);
"""


class ApplicationTracker:
    """Log and track job applications in a local SQLite database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    # ── Public API ────────────────────────────────────────────────────────────

    def log(self, url: str, jd: Dict, match_result: Dict, dry_run: bool = True) -> int:
        """
        Insert or update an application record.

        Args:
            url: Job posting URL (primary key)
            jd: Parsed JD dict (company, title)
            match_result: Match result dict (score)
            dry_run: Whether the application was a dry run

        Returns:
            int: Row ID of the inserted/updated record
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO applications (url, company, title, score, dry_run, status, applied_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    company    = excluded.company,
                    title      = excluded.title,
                    score      = excluded.score,
                    dry_run    = excluded.dry_run,
                    updated_at = excluded.updated_at
                """,
                (
                    url,
                    jd.get('company', ''),
                    jd.get('title', ''),
                    match_result.get('score', 0),
                    1 if dry_run else 0,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT last_insert_rowid()").fetchone()
            return row[0]

    def update_status(self, url: str, status: str) -> bool:
        """
        Update the status of an application.

        Args:
            url: Job posting URL
            status: One of pending / applied / interview / rejected / offer

        Returns:
            bool: True if a record was updated
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE applications SET status = ?, updated_at = ? WHERE url = ?",
                (status, now, url),
            )
            return cur.rowcount > 0

    def list_applications(self) -> List[Dict]:
        """Return all application records as a list of dicts."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, url, company, title, score, dry_run, status, applied_at, updated_at "
                "FROM applications ORDER BY applied_at DESC"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, url: str) -> Optional[Dict]:
        """Return a single application record by URL, or None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, url, company, title, score, dry_run, status, applied_at, updated_at "
                "FROM applications WHERE url = ?",
                (url,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    # ── Internals ─────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _row_to_dict(self, row) -> Dict:
        return {
            'id': row[0],
            'url': row[1],
            'company': row[2],
            'title': row[3],
            'score': row[4],
            'dry_run': bool(row[5]),
            'status': row[6],
            'applied_at': row[7],
            'updated_at': row[8],
        }


# CLI
if __name__ == "__main__":
    tracker = ApplicationTracker()

    if len(sys.argv) < 2:
        print("Usage: python tracker.py list | update <url> <status>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'list':
        apps = tracker.list_applications()
        if not apps:
            print("No applications logged yet.")
        else:
            print(f"{'ID':<4} {'Score':<6} {'Status':<12} {'Company':<20} {'Title'}")
            print('-' * 70)
            for a in apps:
                print(f"{a['id']:<4} {a['score']:<6} {a['status']:<12} {a['company']:<20} {a['title']}")

    elif cmd == 'update' and len(sys.argv) >= 4:
        url, status = sys.argv[2], sys.argv[3]
        ok = tracker.update_status(url, status)
        print(f"✅ Updated" if ok else f"❌ URL not found: {url}")

    else:
        print("Usage: python tracker.py list | update <url> <status>")
        sys.exit(1)
