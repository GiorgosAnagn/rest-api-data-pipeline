from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class IssueRecord:
    issue_id: int
    repository: str
    title: str
    state: str
    body: str | None
    author: str | None
    url: str | None
    created_at: str | None
    labels: str | None = None

    @classmethod
    def from_raw(cls, payload: dict[str, Any], repository: str | None = None) -> "IssueRecord":
        user = payload.get("user") or {}
        labels = payload.get("labels") or []
        label_names = [
            label.get("name") for label in labels if isinstance(label, dict) and label.get("name")
        ]
        return cls(
            issue_id=int(payload.get("id")),
            repository=repository or "unknown/unknown",
            title=str(payload.get("title") or "Untitled"),
            state=str(payload.get("state") or "unknown"),
            body=payload.get("body"),
            author=user.get("login") if isinstance(user, dict) else None,
            url=payload.get("html_url") or payload.get("url"),
            created_at=payload.get("created_at"),
            labels=", ".join(label_names) if label_names else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "repository": self.repository,
            "title": self.title,
            "state": self.state,
            "body": self.body,
            "author": self.author,
            "url": self.url,
            "created_at": self.created_at,
            "labels": self.labels,
        }

    def to_row(self) -> tuple[Any, ...]:
        return (
            self.issue_id,
            self.repository,
            self.title,
            self.state,
            self.body,
            self.author,
            self.url,
            self.created_at,
            self.labels,
        )

    @classmethod
    def from_row(cls, row: tuple[Any, ...]) -> "IssueRecord":
        if len(row) != 9:
            raise ValueError(f"Unexpected row length {len(row)} while reading IssueRecord")
        return cls(
            issue_id=int(row[0]),
            repository=str(row[1]),
            title=str(row[2]),
            state=str(row[3]),
            body=row[4],
            author=row[5],
            url=row[6],
            created_at=row[7],
            labels=row[8],
        )
