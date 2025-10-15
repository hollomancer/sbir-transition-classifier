# Repository Guidelines

## Project Structure & Module Organization
Core services live under `src/sbir_transition_classifier/`: `api/` exposes the FastAPI service, `detection/` contains scoring logic, `core/` houses settings and shared models, `data/` defines request and evidence schemas, and `db/` manages persistence. Supporting data utilities live in `scripts/` and should be invoked via `python -m scripts.<task>`. Test suites are split into `tests/unit/` for isolated logic and `tests/integration/` for end-to-end flows. Project-level assets and bulk inputs belong in `data/`; avoid committing sensitive or oversized raw downloads.

## Build, Test, and Development Commands
- `poetry install` – set up the Python environment (requires Poetry ≥1.5).
- `docker-compose up --build -d` – start the API, worker, and database stack exactly as production uses it.
- `poetry run uvicorn src.sbir_transition_classifier.api.main:app --reload` – run the API locally without Docker when iterating on backend code.
- `docker-compose exec api python -m scripts.load_bulk_data` – ingest award and contract files placed in `data/`.
- `poetry run python -m scripts.export_data --format jsonl` – generate detection exports for manual review.

## Coding Style & Naming Conventions
Write Python 3.11 code with PEP 8 spacing (4 spaces, 120-character soft limit) and prefer descriptive, snake_case module and function names. Classes should use PascalCase and return detailed `Loguru` messages rather than bare `print`. Annotate function signatures with types, keep FastAPI routers in `api/` modularized by domain, and mirror existing folder names when adding new modules (e.g., `detection/features`).

## Testing Guidelines
Tests use `pytest`; name files `test_*.py` and functions `test_<behavior>` so they auto-discover. Add unit coverage alongside new logic and place scenario or API tests under `tests/integration/`. Run `poetry run pytest tests/unit` before opening a PR, and finish with `poetry run pytest` to confirm both suites. Provide fixtures for external services instead of hitting live endpoints, and update golden evidence samples if schema changes are intentional.

## Commit & Pull Request Guidelines
Follow the existing Git history: concise, imperative subject lines (e.g., “Add detection signal for competed awards”) with optional detail in the body. Reference related issues in the description (`Fixes #123`) and summarize data migrations or schema shifts explicitly. Pull requests should include: brief motivation, testing notes (command output or relevant screenshots), API or schema changes, and any follow-up tasks. Coordinate large data updates or migration scripts with the maintainers before merging.

## Data & Security Notes
The repository assumes SBIR award and USAspending extracts are staged under `data/`; scrub PII before sharing local fixtures. Credentials for external services belong in environment variables consumed by `core.settings`. When developing new loaders or exporters, ensure they respect the existing SQLite migrations and avoid writing outside writable volumes defined in `docker-compose.yml`.
