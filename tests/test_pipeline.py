from __future__ import annotations

import json
from pathlib import Path

import pytest

from rest_api_pipeline.adapters.github import GitHubIssueAdapter
from rest_api_pipeline.export.exporters import export_csv, export_json
from rest_api_pipeline.http.client import APIClient
from rest_api_pipeline.models.records import IssueRecord
from rest_api_pipeline.pipeline.sync import Pipeline
from rest_api_pipeline.pipeline.transform import normalize_issue
from rest_api_pipeline.pipeline.validation import validate_issue_payload
from rest_api_pipeline.reporting.report import build_report
from rest_api_pipeline.storage.database import Database


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


def test_http_request_success(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def get(self, url, params=None, timeout=None):
            calls.append((url, params, timeout))
            return FakeResponse(payload={"ok": True})

    client = APIClient(session_factory=lambda: FakeSession())
    payload = client.get_json("https://example.com/test", params={"page": 1}, timeout=5)

    assert payload == {"ok": True}
    assert calls[0][0] == "https://example.com/test"
    assert calls[0][1] == {"page": 1}
    assert calls[0][2] == 5


def test_http_retry_on_transient_failure(monkeypatch):
    attempts = {"count": 0}

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {}
            self.text = "server error"

        def raise_for_status(self):
            if self.status_code >= 500:
                raise RuntimeError("server error")

    class FakeSession:
        def get(self, url, params=None, timeout=None):
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise RuntimeError("temporary")
            return FakeResponse(200)

    client = APIClient(session_factory=lambda: FakeSession(), retries=3, backoff=0)
    payload = client.get_json("https://example.com/test")

    assert payload == {}
    assert attempts["count"] == 2


def test_http_request_timeout_raises(monkeypatch):
    class FakeSession:
        def get(self, url, params=None, timeout=None):
            raise TimeoutError("timed out")

    client = APIClient(session_factory=lambda: FakeSession())

    with pytest.raises(TimeoutError):
        client.get_json("https://example.com/test")


def test_pagination_handles_pages():
    page_data = [
        {"items": [1, 2], "next": "p2"},
        {"items": [3], "next": None},
    ]

    class FakeClient:
        def __init__(self):
            self.calls = 0

        def get_json(self, url, params=None, timeout=None):
            self.calls += 1
            return page_data[self.calls - 1]

    client = FakeClient()
    pages = []
    seen_urls = []

    def callback(payload, page_no, url):
        seen_urls.append((page_no, url))
        pages.append(payload)

    results = APIClient.fetch_paginated(
        client,
        "https://example.com/items",
        page_param="page",
        page_size=2,
        callback=callback,
        max_pages=5,
    )

    assert results == [
        {"items": [1, 2], "next": "p2"},
        {"items": [3], "next": None},
    ]
    assert len(seen_urls) == 2


def test_validation_rejects_malformed_payload():
    bad_payload = [{"id": "123", "title": "ok"}, {"title": "missing id"}]

    with pytest.raises(ValueError):
        validate_issue_payload(bad_payload)


def test_transform_normalizes_issue():
    raw_record = {
        "id": 42,
        "title": "Fix API bug",
        "state": "open",
        "body": "Need better errors",
        "user": {"login": "octocat"},
        "html_url": "https://example.com/issues/42",
        "created_at": "2024-01-01T00:00:00Z",
    }

    issue = normalize_issue(raw_record)

    assert isinstance(issue, IssueRecord)
    assert issue.issue_id == 42
    assert issue.title == "Fix API bug"
    assert issue.author == "octocat"
    assert issue.url == "https://example.com/issues/42"
    assert issue.state == "open"


def test_duplicate_handling_in_database(tmp_path):
    db_path = tmp_path / "test.db"
    database = Database(str(db_path))
    database.initialize()

    issue = IssueRecord(
        issue_id=1,
        repository="octo/repo",
        title="Duplicate issue",
        state="open",
        body="Hello",
        author="octocat",
        url="https://example.com/1",
        created_at="2024-01-01T00:00:00Z",
        labels="bug",
    )

    database.upsert_issue(issue)
    database.upsert_issue(issue)

    rows = database.fetch_all()
    assert len(rows) == 1


def test_sync_insert_and_repeat_no_duplicates(tmp_path):
    db_path = tmp_path / "sync.db"
    payload = [
        {
            "id": 1,
            "title": "Issue alpha",
            "state": "open",
            "body": "Need work",
            "user": {"login": "alice"},
            "html_url": "https://example.com/1",
            "created_at": "2024-01-01T00:00:00Z",
            "labels": [{"name": "bug"}],
        }
    ]

    pipeline = Pipeline(database_path=str(db_path), output_dir=str(tmp_path / "out"))
    kicked = pipeline.sync_records(payload)
    assert kicked == 1

    kicked_again = pipeline.sync_records(payload)
    assert kicked_again == 0


def test_csv_and_json_exports(tmp_path):
    records = [
        IssueRecord(
            issue_id=101,
            repository="example/repo",
            title="Export me",
            state="closed",
            body="Body",
            author="alice",
            url="https://example.com/issues/101",
            created_at="2024-01-01T00:00:00Z",
            labels="bug",
        )
    ]
    output_dir = tmp_path / "exports"
    output_dir.mkdir()

    csv_path = export_csv(records, output_dir / "issues.csv")
    json_path = export_json(records, output_dir / "issues.json")

    assert csv_path.exists()
    assert json_path.exists()
    assert "Export me" in csv_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["title"] == "Export me"


def test_report_generation():
    report = build_report({
        "records_fetched": 10,
        "valid_records": 8,
        "invalid_records": 1,
        "duplicates_handled": 2,
        "inserted": 6,
        "updated": 2,
        "requests_made": 5,
        "duration_seconds": 1.25,
        "warnings": ["Rate limit close"],
        "errors": [],
    })

    assert "records_fetched" in report
    assert "warnings" in report
    assert "Rate limit close" in report


def test_cli_help_and_success(monkeypatch, tmp_path):
    from rest_api_pipeline import cli

    # success path: ensure CLI handles stand-alone invocation with default options
    result = cli.main(["--help"])
    assert result == 0

    records = [{
        "id": 7,
        "title": "A small issue",
        "state": "open",
        "body": "Body",
        "user": {"login": "alice"},
        "html_url": "https://example.com/7",
        "created_at": "2024-01-01T00:00:00Z",
        "labels": [{"name": "task"}],
    }]

    monkeypatch.setattr(cli, "run_sync", lambda **kwargs: {
        "records_inserted": 1,
        "records_updated": 0,
        "records_fetched": 1,
        "valid_records": 1,
        "invalid_records": 0,
        "duplicates_handled": 0,
        "requests_made": 1,
        "duration_seconds": 0.1,
        "warnings": [],
        "errors": [],
    })

    result = cli.main(["sync", "--owner", "octocat", "--repo", "hello-world", "--db-path", str(tmp_path / "cli.db"), "--output-dir", str(tmp_path / "output")])
    assert result == 0


def test_cli_failure_exits_nonzero(monkeypatch):
    from rest_api_pipeline import cli

    def boom(**kwargs):
        raise ValueError("bad config")

    monkeypatch.setattr(cli, "run_sync", boom)

    with pytest.raises(SystemExit):
        cli.main(["sync", "--owner", "", "--repo", "repo"])
