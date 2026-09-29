from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests


class APIClient:
    """Small, retry-aware adapter for paginated REST API consumption."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Any] | None = None,
        retries: int = 3,
        backoff: float = 1.0,
        timeout: int = 15,
        logger: logging.Logger | None = None,
    ) -> None:
        self.session_factory = session_factory or requests.Session
        self.retries = max(0, retries)
        self.backoff = max(0.0, backoff)
        self.timeout = timeout
        self.logger = logger or logging.getLogger("rest_api_pipeline.http")

    def request(self, url: str, *, params: dict[str, Any] | None = None, timeout: int | None = None) -> requests.Response:
        params = dict(params or {})
        last_error: Exception | None = None
        final_timeout = timeout if timeout is not None else self.timeout

        for attempt in range(self.retries + 1):
            response = None
            try:
                session = self.session_factory()
                response = session.get(url, params=params, timeout=final_timeout)
                if getattr(response, "status_code", 200) in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"Transient HTTP status: {getattr(response, 'status_code', 'unknown')}")
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                return response
            except Exception as exc:  # includes fake-session generated RuntimeError and real requests failures
                last_error = exc
                if attempt >= self.retries:
                    break
                retry_after = self._retry_after_delay(response=response)
                delay = self.backoff * (2**attempt)
                sleep_for = max(delay, retry_after)
                self.logger.warning("Request failed for %s (attempt %s/%s); retrying in %.2f seconds", url, attempt + 1, self.retries + 1, sleep_for)
                time.sleep(sleep_for)

        if isinstance(last_error, TimeoutError):
            raise last_error
        if last_error is not None:
            raise last_error
        raise requests.RequestException(f"Request failed for {url}")

    @staticmethod
    def _retry_after_delay(*, response: requests.Response | None) -> float:
        if response is None or not hasattr(response, "headers"):
            return 0.0
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return 0.0
        try:
            return float(retry_after)
        except ValueError:
            return 0.0

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, timeout: int | None = None) -> Any:
        response = self.request(url, params=params, timeout=timeout)
        try:
            return response.json()
        except (AttributeError, ValueError):
            return {}

    @staticmethod
    def fetch_paginated(
        client: Any,
        url: str,
        *,
        page_param: str = "page",
        page_size: int = 30,
        callback: Callable[[Any, int, str], None] | None = None,
        max_pages: int = 10,
    ) -> list[Any]:
        results: list[Any] = []
        page_number = 1
        current_url = url
        last_payload: Any = None

        while page_number <= max_pages:
            params = {page_param: page_number, "per_page": page_size}
            payload = client.get_json(current_url, params=params)
            if payload is None:
                break
            if callback is not None:
                callback(payload, page_number, current_url)
            results.append(payload)
            last_payload = payload
            if not isinstance(payload, dict):
                break
            next_value = payload.get("next") or payload.get("next_page")
            if not next_value:
                break
            page_number += 1
            current_url = url
            if next_value is not None and next_value != url:
                current_url = next_value
            if page_number > max_pages:
                break
        return results
