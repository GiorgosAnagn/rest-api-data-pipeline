from __future__ import annotations

import sqlite3
from pathlib import Path

from rest_api_pipeline.models.records import IssueRecord


class Database:
    """Thin SQLite layer for issue persistence."""

    def __init__(self, db_path: str = "data/pipeline.db") -> None:
        self.db_path = db_path
        self._ensure_parent_directory()

    def _ensure_parent_directory(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS issues (
                    issue_id INTEGER NOT NULL,
                    repository TEXT NOT NULL,
                    title TEXT NOT NULL,
                    state TEXT,
                    body TEXT,
                    author TEXT,
                    url TEXT,
                    created_at TEXT,
                    labels TEXT,
                    PRIMARY KEY (issue_id, repository)
                )
                """
            )
            conn.commit()

    def upsert_issue(self, issue: IssueRecord) -> str:
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT issue_id, repository, title, state, body, author, url, created_at, labels FROM issues WHERE issue_id = ? AND repository = ?",
                (issue.issue_id, issue.repository),
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO issues (issue_id, repository, title, state, body, author, url, created_at, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    issue.to_row(),
                )
                conn.commit()
                return "inserted"

            row = tuple(existing)
            if row == issue.to_row():
                return "duplicate"

            conn.execute(
                "UPDATE issues SET title = ?, state = ?, body = ?, author = ?, url = ?, created_at = ?, labels = ? WHERE issue_id = ? AND repository = ?",
                (issue.title, issue.state, issue.body, issue.author, issue.url, issue.created_at, issue.labels, issue.issue_id, issue.repository),
            )
            conn.commit()
            return "updated"

    def fetch_all(self) -> list[IssueRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT issue_id, repository, title, state, body, author, url, created_at, labels FROM issues ORDER BY issue_id ASC, repository ASC"
            ).fetchall()
        return [IssueRecord.from_row(row) for row in rows]

    def count_all(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM issues").fetchone()
        return int(row[0]) if row else 0
