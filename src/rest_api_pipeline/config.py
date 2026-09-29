from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuntimeConfig:
    owner: str = "microsoft"
    repo: str = "python-sdk"
    api_base_url: str = "https://api.github.com"
    db_path: str = "data/pipeline.db"
    output_dir: str = "outputs"
    timeout: int = 15
    retries: int = 3
    backoff_seconds: float = 1.0
    per_page: int = 30
    max_pages: int = 10
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        values = {
            "owner": os.getenv("GITHUB_OWNER", "microsoft"),
            "repo": os.getenv("GITHUB_REPO", "python-sdk"),
            "api_base_url": os.getenv("GITHUB_API_BASE_URL", "https://api.github.com"),
            "db_path": os.getenv("DB_PATH", "data/pipeline.db"),
            "output_dir": os.getenv("OUTPUT_DIR", "outputs"),
            "timeout": int(os.getenv("REQUEST_TIMEOUT", "15")),
            "retries": int(os.getenv("REQUEST_RETRIES", "3")),
            "backoff_seconds": float(os.getenv("REQUEST_BACKOFF", "1.0")),
            "per_page": int(os.getenv("GITHUB_PER_PAGE", "30")),
            "max_pages": int(os.getenv("GITHUB_MAX_PAGES", "10")),
            "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
        }
        return cls(**values)

    def ensure_paths(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)


def load_config() -> RuntimeConfig:
    return RuntimeConfig.from_env()
