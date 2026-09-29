from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rest_api_pipeline.adapters.github import GitHubIssueAdapter
from rest_api_pipeline.config import RuntimeConfig
from rest_api_pipeline.export.exporters import export_csv, export_json
from rest_api_pipeline.http.client import APIClient
from rest_api_pipeline.logging_config import configure_logging
from rest_api_pipeline.pipeline.sync import Pipeline
from rest_api_pipeline.pipeline.transform import normalize_issue
from rest_api_pipeline.reporting.report import build_report


def run_sync(
    *,
    owner: str,
    repo: str,
    db_path: str | None = None,
    output_dir: str | None = None,
    per_page: int = 30,
    max_pages: int = 10,
    timeout: int = 15,
    retries: int = 3,
    backoff: float = 1.0,
    verbose: bool = False,
    state: str = "all",
) -> dict:
    config = RuntimeConfig(
        owner=owner,
        repo=repo,
        db_path=db_path or "data/pipeline.db",
        output_dir=output_dir or "outputs",
        per_page=per_page,
        max_pages=max_pages,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff,
    )
    config.ensure_paths()
    logger = configure_logging("DEBUG" if verbose else "INFO")
    logger.info("Starting sync for %s/%s", owner, repo)
    start = time.perf_counter()

    client = APIClient(retries=retries, backoff=backoff, timeout=timeout, logger=logger)
    adapter = GitHubIssueAdapter(owner=owner, repo=repo, client=client, per_page=per_page, max_pages=max_pages)
    raw_issues = adapter.fetch_issues_raw(state=state)
    pipeline = Pipeline(database_path=config.db_path, output_dir=config.output_dir)
    repository_name = f"{owner}/{repo}"
    inserted = pipeline.sync_records(raw_issues, repository=repository_name)

    persisted = pipeline.database.fetch_all()
    export_csv(persisted, Path(config.output_dir) / "issues.csv")
    export_json(persisted, Path(config.output_dir) / "issues.json")

    stats = dict(pipeline.last_stats)
    stats["requests_made"] = max(1, len(raw_issues) // max(1, per_page)) + 1
    stats["duration_seconds"] = round(time.perf_counter() - start, 3)
    stats["valid_records"] = len(raw_issues)
    stats["records_fetched"] = len(raw_issues)
    stats["records_inserted"] = inserted
    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="REST API Data Sync & Reporting Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="Fetch GitHub issues and persist them")
    sync_parser.add_argument("--owner", default="microsoft", help="GitHub repository owner")
    sync_parser.add_argument("--repo", default="python-sdk", help="GitHub repository name")
    sync_parser.add_argument("--db-path", default="data/pipeline.db", help="SQLite database path")
    sync_parser.add_argument("--output-dir", default="outputs", help="Directory for exported CSV/JSON documents")
    sync_parser.add_argument("--per-page", type=int, default=30, help="Page size for GitHub issue queries")
    sync_parser.add_argument("--max-pages", type=int, default=10, help="Maximum number of pages to fetch")
    sync_parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    sync_parser.add_argument("--retries", type=int, default=3, help="Retry count for transient request failures")
    sync_parser.add_argument("--backoff", type=float, default=1.0, help="Base backoff duration in seconds")
    sync_parser.add_argument("--state", default="all", choices=["all", "open", "closed"], help="GitHub issue state filter")
    sync_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(flag in arguments for flag in ("-h", "--help")):
        parser.print_help()
        return 0

    parsed = parser.parse_args(arguments)
    if parsed.command is None:
        parser.print_help()
        return 0

    if parsed.command == "sync":
        if not parsed.owner or not parsed.repo:
            parser.error("--owner and --repo must be provided")
        try:
            stats = run_sync(
                owner=parsed.owner,
                repo=parsed.repo,
                db_path=parsed.db_path,
                output_dir=parsed.output_dir,
                per_page=parsed.per_page,
                max_pages=parsed.max_pages,
                timeout=parsed.timeout,
                retries=parsed.retries,
                backoff=parsed.backoff,
                verbose=parsed.verbose,
                state=parsed.state,
            )
        except Exception as exc:  # pragma: no cover - CLI failure path guard
            raise SystemExit(str(exc)) from exc
        print(build_report(stats))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
