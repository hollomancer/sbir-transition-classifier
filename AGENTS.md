# Repository Guidelines

## Project Structure & Module Organization
Core code resides in `src/sbir_transition_classifier/`: `detection/` hosts scoring logic, `core/` holds shared settings and models, `data/` defines schemas, and `db/` manages persistence. CLI entry points mirror this layout under `src/sbir_transition_classifier/cli/`. Data utilities live in `scripts/` and should be executed with `python -m scripts.<task>`. Tests are split between `tests/unit/` for isolated components and `tests/integration/` for pipeline coverage. Place large inputs in `data/` and write generated artifacts to `output/`.

## Build, Test, and Development Commands
- `poetry install` – install dependencies for Python 3.11.
- `poetry shell` – enter the virtualenv for ad-hoc commands.
- `poetry run sbir-detect bulk-process --verbose` – execute the full detection pipeline with progress reporting.
- `poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose` – stage SBIR award extracts from `data/`.
- `poetry run python -m scripts.export_data export-jsonl --output-path output/results.jsonl` – export detection results for manual review.

## Coding Style & Naming Conventions
Follow PEP 8 spacing (4 spaces, soft 120-character limit) and prefer descriptive snake_case for modules and functions. Use PascalCase for classes, return structured `loguru` messages instead of `print`, and annotate function signatures with types. Match existing directory names when adding modules (e.g., `detection/features/signal_name.py`) and lean on Rich for interactive console output.

## Testing Guidelines
Pytest drives all suites; keep files as `tests/*/test_*.py` with functions named `test_<behavior>`. Write unit tests alongside new logic and add integration coverage when workflows or schemas change. Run `poetry run pytest tests/unit` during development and finish with `poetry run pytest` before submitting. Update golden fixtures under `tests/` if schema updates are intentional.

## Commit & Pull Request Guidelines
Write commits with concise, imperative subjects (e.g., `Add detection signal for competed awards`) and optional explanatory bodies. Pull requests should outline motivation, summarize data or schema impacts, list test commands run, and link issues via `Fixes #123`. Coordinate heavy data migrations or bulk reloads with maintainers before merging.

## Configuration Management
Use the unified YAML-based configuration system for all settings:

```python
from sbir_transition_classifier.config import ConfigLoader
from sbir_transition_classifier.db.config import get_database_config

# Load full config
config = ConfigLoader.load_from_file("config/custom.yaml")

# Load just database config
db_config = get_database_config()
```

DO NOT use `core.config.settings` - it is deprecated and will be removed in v0.2.0.

## Security & Configuration Tips
Load secrets through environment variables or the unified YAML config system. Database settings can be overridden via `SBIR_DB_URL` environment variable. Ensure SBIR and USAspending feeds are scrubbed before copying into `data/`, and avoid committing raw exports. New loaders or exporters must respect existing SQLite migrations and write timestamped outputs under `output/`.
