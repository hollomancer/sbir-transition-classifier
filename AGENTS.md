# Repository Guidelines

## Project Structure & Module Organization
Core code resides in `src/sbir_transition_classifier/`: `detection/` hosts scoring logic, `core/` holds shared settings and models, `data/` defines schemas, and `db/` manages persistence. CLI entry points mirror this layout under `src/sbir_transition_classifier/cli/`. All commands are accessed through the `sbir-detect` CLI. Tests are split between `tests/unit/` for isolated components and `tests/integration/` for pipeline coverage. Place large inputs in `data/` and write generated artifacts to `output/`.

## Build, Test, and Development Commands

### Installation & Setup
- `poetry install` – install dependencies for Python 3.11.
- `poetry shell` – enter the virtualenv for ad-hoc commands.

### Core CLI Commands
- `sbir-detect run --config config/custom.yaml --output output/` – execute detection with explicit configuration.
- `sbir-detect bulk-process --verbose` – execute the full detection pipeline with progress reporting.
- `sbir-detect validate-config --config config/default.yaml` – validate a configuration file before use.
- `sbir-detect reset-config --output config/default.yaml --template default` – generate a configuration file from a template.
- `sbir-detect list-templates` – list available configuration templates (default, high-precision, broad-discovery).
- `sbir-detect show-template --template default` – display a template's content.

### Data Management
- `sbir-detect data load-sbir --file-path data/awards.csv --verbose` – stage SBIR award extracts from `data/`.
- `sbir-detect data load-contracts --file-path data/contracts.csv --verbose` – load contract data.
- `sbir-detect hygiene check-dates --data-dir data/` – validate data quality and detect anomalies.

### Export & Reporting
- `sbir-detect export jsonl --output-path output/results.jsonl` – export detection results in JSONL format.
- `sbir-detect export csv --output-path output/results.csv` – export detection results as CSV.
- `sbir-detect export excel --output-path output/results.xlsx` – export detection results as Excel.
- `sbir-detect reports stats` – display summary statistics of current detections.
- `sbir-detect reports summary --output-path output/summary.md` – generate markdown summary report.

### System Information
- `sbir-detect info` – show system information and quick start tips.
- `sbir-detect version` – display version information.
- `sbir-detect --help` – show all available commands.

### Testing
- `poetry run pytest tests/unit/ -v` – run unit tests with verbose output during development.
- `poetry run pytest tests/unit/ -v --tb=short --cov=sbir_transition_classifier --cov-report=term-missing` – run unit tests with coverage reporting.
- `poetry run pytest` – run full test suite (unit + integration) before submitting.
- `poetry run pytest tests/integration/` – run integration tests only.
- `poetry run pytest -k test_name` – run a specific test by name.

## Coding Style & Naming Conventions
Follow PEP 8 spacing (4 spaces, soft 120-character limit) and prefer descriptive snake_case for modules and functions. Use PascalCase for classes, return structured `loguru` messages instead of `print`, and annotate function signatures with types. Match existing directory names when adding modules (e.g., `detection/features/signal_name.py`) and lean on Rich for interactive console output.

## Testing Guidelines
Pytest drives all suites; keep files as `tests/unit/test_*.py` or `tests/integration/test_*.py` with functions named `test_<behavior>`. Write unit tests alongside new logic and add integration coverage when workflows or schemas change. Run `poetry run pytest tests/unit/ -v` during active development to iterate quickly, then run `poetry run pytest` with coverage before submitting pull requests. Update golden fixtures under `tests/` if schema updates are intentional. Ensure all tests pass locally before pushing to CI.

## Commit & Pull Request Guidelines
Write commits with concise, imperative subjects (e.g., `Add detection signal for competed awards`) and optional explanatory bodies. Pull requests should outline motivation, summarize data or schema impacts, list test commands run (e.g., `poetry run pytest tests/unit/`), and link issues via `Fixes #123`. Coordinate heavy data migrations or bulk reloads with maintainers before merging.

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