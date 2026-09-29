from __future__ import annotations

from rest_api_pipeline.cli import run_sync


if __name__ == "__main__":
    result = run_sync(
        owner="microsoft",
        repo="python-sdk",
        db_path="data/pipeline.db",
        output_dir="outputs",
        per_page=30,
        max_pages=3,
        verbose=True,
    )
    print(result)
