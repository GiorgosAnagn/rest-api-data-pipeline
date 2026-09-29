# REST API Data Sync & Reporting Pipeline

A lightweight Python data pipeline for collecting public GitHub issue data, validating it, persisting it to SQLite, exporting it to CSV/JSON, and summarizing what was processed.

## Why this project exists

This project demonstrates a practical, reusable data-engineering workflow for integrating with a real REST API without depending on a custom backend or vendor-specific tooling. It is designed to be easy to read, easy to test, and easy to extend to other APIs beyond GitHub.

## Features

- HTTP client with timeout handling, retry logic, and exponential backoff
- Paginated GitHub issue collection from the public REST API
- Defensive JSON validation and normalization
- Typed internal record model for application logic
- SQLite persistence with repeatable sync behavior
- CSV and JSON export for downstream reporting or analysis
- CLI-driven execution and a readable pipeline summary
- Clear error handling and deterministic output

## Architecture

```text
API
  ↓
HTTP client
  ↓
pagination + retry handling
  ↓
validation
  ↓
transformation
  ↓
SQLite storage
  ↓
CSV / JSON export
  ↓
summary report
```

## Project structure

```text
rest-api-data-pipeline/
├── src/
│   └── rest_api_pipeline/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── logging_config.py
│       ├── http/
│       │   ├── __init__.py
│       │   └── client.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   └── github.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── records.py
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── ingestion.py
│       │   ├── transform.py
│       │   ├── validation.py
│       │   └── sync.py
│       ├── storage/
│       │   ├── __init__.py
│       │   └── database.py
│       ├── export/
│       │   ├── __init__.py
│       │   └── exporters.py
│       └── reporting/
│           ├── __init__.py
│           └── report.py
├── tests/
├── examples/
├── data/
├── outputs/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
└── LICENSE
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Usage

Run a sync against a public GitHub repository:

```bash
python -m rest_api_pipeline.cli sync --owner microsoft --repo python-sdk --output-dir outputs --db-path data/pipeline.db
```

The command will:

1. fetch issues from the public GitHub API,
2. validate and normalize each issue,
3. persist records to SQLite,
4. export a CSV and a JSON document,
5. print a readable summary report.

## GitHub API example

This project uses the public GitHub REST API for repository issues. A basic unauthenticated request is sufficient for demonstration purposes:

```bash
python -m rest_api_pipeline.cli sync --owner octocat --repo Hello-World --per-page 30 --max-pages 3
```

GitHub applies rate limits for unauthenticated requests. If the limit is reached, the client will retry transient errors and surface clear reporting when further requests are not possible.

## Configuration

The application supports environment variables for the public demo and a friendly CLI override mechanism.

Example values:

```env
GITHUB_OWNER=microsoft
GITHUB_REPO=python-sdk
GITHUB_PER_PAGE=30
DB_PATH=./data/pipeline.db
OUTPUT_DIR=./outputs
LOG_LEVEL=INFO
```

You can also pass values directly to the CLI if you need to override environment configuration.

## Example commands

```bash
python -m rest_api_pipeline.cli --help
python -m rest_api_pipeline.cli sync --owner microsoft --repo python-sdk --verbose
python -m rest_api_pipeline.cli sync --owner octocat --repo Hello-World --state open
```

## Example output / report

```text
REST API Data Sync Report
========================
records_fetched: 18
valid_records: 18
invalid_records: 0
duplicates_handled: 2
records_inserted: 16
records_updated: 0
api_requests_made: 2
execution_duration_seconds: 1.861
warnings:
  - GitHub rate limit is nearing the threshold
```

## Testing

```bash
python -m pytest -q
```

## Error handling and retry behavior

The HTTP client is intentionally conservative:

- timeouts fail fast with a clear exception,
- transient 429/5xx responses are retried,
- backoff grows exponentially,
- GitHub Retry-After headers are respected when they are present,
- malformed payloads are rejected before they reach downstream storage.

## Design decisions

- The HTTP layer is separate from the domain logic, which keeps the adapter reusable.
- The internal issue model is explicit and typed rather than passing arbitrary dictionaries through the entire stack.
- SQLite is the persistence choice because it keeps the demo portable and dependency-light.
- The pipeline is intentionally small and readable, rather than using framework-heavy abstractions.

## Limitations

- The public GitHub API is rate-limited for unauthenticated requests.
- This demo focuses on GitHub issues, not every repository dataset.
- The CLI is intentionally simple and is not a full SaaS control plane.

## Future extensions

- Add additional adapters for Jira, Azure DevOps, or GitLab.
- Add a scheduling layer for periodic syncs.
- Add a richer metrics dashboard or Slack/email notification option.
- Build a small ETL workflow for transforming issue data into operational metrics.

## License

This project is provided under the MIT License.
