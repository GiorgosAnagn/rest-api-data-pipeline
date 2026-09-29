from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rest_api_pipeline.export.exporters import export_csv, export_json
from rest_api_pipeline.models.records import IssueRecord
from rest_api_pipeline.pipeline.transform import deduplicate_issues, normalize_issue
from rest_api_pipeline.pipeline.validation import validate_issue_payload
from rest_api_pipeline.storage.database import Database


class Pipeline:
    """Process raw issue payloads into normalized records, persisted storage, and exports."""

    def __init__(self, database_path: str = "data/pipeline.db", output_dir: str = "outputs") -> None:
        self.database = Database(database_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_stats: dict[str, Any] = {}
        self.database.initialize()

    def sync_records(self, raw_records: list[dict[str, Any]], *, repository: str | None = None) -> int:
        start = time.perf_counter()
        valid_records = validate_issue_payload(raw_records)
        normalized = [normalize_issue(item, repository=repository) for item in valid_records]
        deduped = deduplicate_issues(normalized)

        inserted = 0
        updated = 0
        duplicates = 0
        for issue in deduped:
            status = self.database.upsert_issue(issue)
            if status == "inserted":
                inserted += 1
            elif status == "updated":
                updated += 1
            elif status == "duplicate":
                duplicates += 1

        persisted = self.database.fetch_all()
        export_csv(persisted, self.output_dir / "issues.csv")
        export_json(persisted, self.output_dir / "issues.json")

        duration = time.perf_counter() - start
        self.last_stats = {
            "records_fetched": len(raw_records),
            "valid_records": len(valid_records),
            "invalid_records": max(0, len(raw_records) - len(valid_records)),
            "duplicates_handled": duplicates,
            "records_inserted": inserted,
            "records_updated": updated,
            "requests_made": 1,
            "duration_seconds": round(duration, 3),
            "warnings": [],
            "errors": [],
        }
        return inserted
