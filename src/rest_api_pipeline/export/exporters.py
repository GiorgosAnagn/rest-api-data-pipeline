from __future__ import annotations

import csv
import json
from pathlib import Path

from rest_api_pipeline.models.records import IssueRecord


def export_csv(records: list[IssueRecord], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "issue_id",
        "repository",
        "title",
        "state",
        "body",
        "author",
        "url",
        "created_at",
        "labels",
    ]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())
    return target


def export_json(records: list[IssueRecord], output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.to_dict() for record in records]
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
