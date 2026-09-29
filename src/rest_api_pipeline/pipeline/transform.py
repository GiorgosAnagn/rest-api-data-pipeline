from __future__ import annotations

from typing import Any

from rest_api_pipeline.models.records import IssueRecord


def normalize_issue(raw: dict[str, Any], *, repository: str | None = None) -> IssueRecord:
    if not isinstance(raw, dict):
        raise ValueError("Issue record must be a dictionary")
    user = raw.get("user") or {}
    labels = raw.get("labels") or []
    label_names = [
        label.get("name") for label in labels if isinstance(label, dict) and label.get("name")
    ]
    return IssueRecord(
        issue_id=int(raw.get("id")),
        repository=repository or "unknown/unknown",
        title=str(raw.get("title") or "Untitled"),
        state=str(raw.get("state") or "unknown"),
        body=raw.get("body"),
        author=user.get("login") if isinstance(user, dict) else None,
        url=raw.get("html_url") or raw.get("url"),
        created_at=raw.get("created_at"),
        labels=", ".join(sorted(label_names)) if label_names else None,
    )


def deduplicate_issues(records: list[IssueRecord]) -> list[IssueRecord]:
    seen: set[tuple[int, str]] = set()
    unique: list[IssueRecord] = []
    for record in records:
        key = (record.issue_id, record.repository)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique
