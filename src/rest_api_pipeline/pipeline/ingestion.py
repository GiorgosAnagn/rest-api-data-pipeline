from __future__ import annotations

from rest_api_pipeline.adapters.github import GitHubIssueAdapter
from rest_api_pipeline.http.client import APIClient
from rest_api_pipeline.pipeline.sync import Pipeline


def fetch_and_store_issues(
    *,
    owner: str,
    repo: str,
    database_path: str = "data/pipeline.db",
    output_dir: str = "outputs",
    per_page: int = 30,
    max_pages: int = 10,
    timeout: int = 15,
    retries: int = 3,
    backoff: float = 1.0,
    state: str = "all",
) -> tuple[int, dict]:
    client = APIClient(retries=retries, backoff=backoff, timeout=timeout)
    adapter = GitHubIssueAdapter(
        owner=owner,
        repo=repo,
        client=client,
        per_page=per_page,
        max_pages=max_pages,
    )
    raw_issues = adapter.fetch_issues_raw(state=state)
    pipeline = Pipeline(database_path=database_path, output_dir=output_dir)
    inserted = pipeline.sync_records(raw_issues, repository=f"{owner}/{repo}")
    return inserted, pipeline.last_stats
