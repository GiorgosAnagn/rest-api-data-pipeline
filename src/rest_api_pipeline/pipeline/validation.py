from __future__ import annotations

from typing import Any


def validate_issue_payload(payload: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Issue payload must be a list of JSON objects")

    valid: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Issue entry {index} is not a JSON object")
        if "id" not in item:
            raise ValueError(f"Issue entry {index} is missing the required 'id' field")
        if "title" not in item:
            raise ValueError(f"Issue entry {index} is missing the required 'title' field")
        if "state" not in item:
            raise ValueError(f"Issue entry {index} is missing the required 'state' field")
        user = item.get("user")
        if not isinstance(user, dict) or not user.get("login"):
            raise ValueError(f"Issue entry {index} is missing a valid user login")
        valid.append(item)
    return valid
