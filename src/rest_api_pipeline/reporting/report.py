from __future__ import annotations

from typing import Any


def build_report(stats: dict[str, Any]) -> str:
    lines = [
        "REST API Data Sync Report",
        "========================",
        f"records_fetched: {stats.get('records_fetched', 0)}",
        f"valid_records: {stats.get('valid_records', 0)}",
        f"invalid_records: {stats.get('invalid_records', 0)}",
        f"duplicates_handled: {stats.get('duplicates_handled', 0)}",
        f"records_inserted: {stats.get('records_inserted', 0)}",
        f"records_updated: {stats.get('records_updated', 0)}",
        f"api_requests_made: {stats.get('requests_made', 0)}",
        f"execution_duration_seconds: {stats.get('duration_seconds', 0.0)}",
    ]

    warnings = stats.get("warnings") or []
    errors = stats.get("errors") or []
    if warnings:
        lines.append("warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    if errors:
        lines.append("errors:")
        for error in errors:
            lines.append(f"  - {error}")
    return "\n".join(lines)
