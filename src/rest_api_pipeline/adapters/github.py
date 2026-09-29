from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_api_pipeline.http.client import APIClient
from rest_api_pipeline.models.records import IssueRecord


class GitHubIssueAdapter:
    """Fetch public repository issues from the GitHub REST API."""

    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        client: APIClient | None = None,
        api_base_url: str = "https://api.github.com",
        per_page: int = 30,
        max_pages: int = 10,
    ) -> None:
        if not owner or not repo:
            raise ValueError("Repository owner and repo name are required")
        self.owner = owner
        self.repo = repo
        self.base_url = api_base_url.rstrip("/")
        self.per_page = per_page
        self.max_pages = max_pages
        self.client = client or APIClient(timeout=15)

    @property
    def repository_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    def fetch_issues(self, *, state: str = "all") -> list[IssueRecord]:
        endpoint = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        page_number = 1
        records: list[IssueRecord] = []

        while page_number <= self.max_pages:
            payload = self.client.get_json(
                endpoint,
                params={"state": state, "per_page": self.per_page, "page": page_number},
            )
            if not isinstance(payload, list):
                raise ValueError(f"GitHub issues endpoint returned a non-list payload for {self.repository_name!r}")
            if not payload:
                break
            for item in payload:
                if not isinstance(item, dict):
                    continue
                if "pull_request" in item:
                    continue
                records.append(IssueRecord.from_raw(item, repository=self.repository_name))
            page_number += 1

        return records

    def fetch_issues_raw(self, *, state: str = "all") -> list[dict[str, Any]]:
        endpoint = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues"
        page_number = 1
        collected: list[dict[str, Any]] = []

        while page_number <= self.max_pages:
            payload = self.client.get_json(
                endpoint,
                params={"state": state, "per_page": self.per_page, "page": page_number},
            )
            if not isinstance(payload, list):
                raise ValueError(f"GitHub issues endpoint returned a non-list payload for {self.repository_name!r}")
            if not payload:
                break
            collected.extend(item for item in payload if isinstance(item, dict) and "pull_request" not in item)
            page_number += 1

        return collected
