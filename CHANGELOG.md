# Changelog

All notable changes to this project will be documented in this file.

This changelog follows Keep a Changelog conventions.

## [Unreleased]

### Added
- Centralized docs index at `docs/README.md` to serve as the canonical entry point for documentation.
- New `CHANGELOG.md` seeded with summaries from refactor/phase documents.

### Changed
- CLI `run` command:
  - `--config` is now optional; uses default config if present or built-in defaults.
  - `--output` can be a directory or a file (`.json`, `.jsonl`). If a file is provided, results are written directly to it.

- Scoring:
  - Strong penalty added for very-late contracts (> 365 days after Phase II completion) to ensure they fall below the “Likely Transition” threshold.

- Packaging/Imports:
  - Explicit Poetry `packages` include for `src/` layout to ensure all modules (e.g., `data/cleaning.py`) are packaged.
  - Lazy-imports in CLI modules (`bulk`, `hygiene`) to avoid import-time failures and reduce optional dependency coupling.

### Migrated
- Pydantic v2:
  - Replaced class-based `Config` and `orm_mode` with `ConfigDict` and `from_attributes`.
  - Replaced `@validator` with `@model_validator` as appropriate.
  - Replaced `min_items` with `min_length` and `dict()` with `model_dump()` where needed.

- SQLAlchemy v2:
  - Switched `declarative_base` import to `sqlalchemy.orm.declarative_base`.

### Fixed
- CI collection failures due to `ModuleNotFoundError` on `sbir_transition_classifier.data.cleaning`.
- Integration test failures triggered by mandatory `--config` and rigid output expectations in `run` CLI.
- Import-time DB binding and serialization issues discovered earlier in the refactor (see Phase entries below).

### Quality
- Tests: 96 tests passing locally with no Pydantic or SQLAlchemy deprecation warnings.

---

## [0.1.0] - 2024-10-28
Initial refactor initiative baselined here. The following summarizes the Phase 0–6 refactoring effort (as documented in PHASE and REFACTORING summary files).

### Refactoring Initiative Summary (Phases 0–6)

#### Phase 0: Test Safety Net (Foundation)
- Added comprehensive integration tests and shared fixtures to safely refactor the codebase.
- Ensured tests could replace the DB engine/session for isolation.

#### Phase 1: Quick Wins (Dead Code Removal)
- Removed or isolated clearly unused/legacy code paths to shrink the surface area for later phases.
- Reduced incidental complexity to make CI more reliable.

#### Phase 2: Export & Data Consolidation
- Consolidated legacy scripts into the CLI:
  - Deleted `src/sbir_transition_classifier/scripts/export_data.py` and `src/sbir_transition_classifier/scripts/load_bulk_data.py`.
  - Implemented `src/sbir_transition_classifier/cli/export.py` with reusable helpers:
    - `export_detections_to_jsonl`
    - `export_detections_to_csv`
- Fixed DB usage in exports to use dynamic session access (`db_module.SessionLocal()`).
- Updated `AGENTS.md` and `README.md` to recommend unified CLI:
  - `poetry run sbir-detect data load-sbir --file-path data/awards.csv`
  - `poetry run sbir-detect export jsonl --output-path output/results.jsonl`
- Result: Substantial code deletion while keeping functionality intact and testable.

#### Phase 3: CLI Reorganization
- Consolidated reporting commands into `src/sbir_transition_classifier/cli/reports.py`:
  - Unified `summary`, `dual_report`, and `evidence`-style outputs behind a single group.
- Updated `src/sbir_transition_classifier/cli/main.py` to register the new command group.
- Preserved backward compatibility for common workflows.

#### Phase 4: Detection Simplification (Deferred)
- After analysis, merging the file-based path and the DB-based path was intentionally deferred:
  - The two detection flows serve different use cases (local file pipeline vs. database-backed bulk detection).
  - Unification would be high-risk for limited gain; the project keeps both paths supported.

#### Phase 5: Configuration Cleanup
- Consolidated configuration code:
  - Unified schema, defaults, and validation within `src/sbir_transition_classifier/config/schema.py`.
  - Introduced `ConfigLoader` usage consistently and deprecated legacy imports.
- Ensured a single YAML-driven configuration surface with sensible defaults.

#### Phase 6: Data Module Cleanup
- Renamed for clarity and consistency:
  - `data/local_loader.py` → `data/loader.py`
  - `data/hygiene.py` → `data/cleaning.py`
- Improved CSV hygiene functions and introduced robust sampling capability with progress feedback.

### Key Technical Fixes Achieved During the Initiative
- Database session and engine references no longer captured at import-time, enabling test isolation.
- UUID and timestamp serialization correctness:
  - Converted `uuid.UUID` to strings where required by DB/JSON fields.
  - Normalized pandas `Timestamp`/NaT to JSON-safe representations.
- Ensured DB schema initialization order before queries in CLI.
- Improved error handling and progress reporting across ingestion and exports.

### CLI UX Improvements
- Introduced cohesive command groups:
  - `sbir-detect data` for loading
  - `sbir-detect export` for exporting
  - `sbir-detect reports` for summaries/evidence

### Documentation
- Updated `README.md` and `AGENTS.md` to reflect consolidated commands and best practices.
- Created and/or updated several docs describing refactor motivations, outcomes, and recommended usage.

### Compatibility
- Backward compatibility preserved for common commands and workflows.
- No breaking changes to core user flows; where changed, wrappers were provided or docs updated.

---

## Migration Notes (Selected)
- Prefer the unified CLI for all data operations:
  - Data loading: `sbir-detect data load-sbir --file-path <file>`
  - Export: `sbir-detect export jsonl --output-path <file>`
  - Reports: `sbir-detect reports ...`
- Configuration:
  - Use the unified YAML config via `ConfigLoader`; legacy `core.config.settings` was deprecated.
- Imports (developer-facing):
  - Config: `from sbir_transition_classifier.config import ConfigLoader, ConfigSchema, ConfigValidator`
  - Data: `from sbir_transition_classifier.data.cleaning import DataCleaner`
  - Ingestion: `from sbir_transition_classifier.ingestion import SbirIngester, ContractIngester`

---

## Historical Sources and Consolidation Status
This changelog entry consolidates content from and supersedes the following documents:

- PHASE2_SUMMARY.md
- PHASE3_SUMMARY.md
- PHASE5_6_SUMMARY.md
- REFACTORING_COMPLETE.md
- REFACTORING_STATUS.md
- docs/PHASE_0_SUMMARY.md
- docs/PHASE1_COMPLETION.md
- docs/PHASE_1_COMPLETE.md
- docs/PHASE2_COMPLETION.md
- docs/PROGRESS_SUMMARY.md
- docs/REFACTORING_PLAN.md
- docs/REFACTORING_SUMMARY.md
- docs/REFACTORING_QUICK_REF.md
- docs/REFACTORING_GUIDE.md

Files marked for deletion (superseded by CHANGELOG.md and ROADMAP.md):
- PHASE2_SUMMARY.md
- PHASE3_SUMMARY.md
- PHASE5_6_SUMMARY.md
- REFACTORING_COMPLETE.md
- REFACTORING_STATUS.md
- docs/PHASE_0_SUMMARY.md
- docs/PHASE1_COMPLETION.md
- docs/PHASE_1_COMPLETE.md
- docs/PHASE2_COMPLETION.md
- docs/PROGRESS_SUMMARY.md
- docs/REFACTORING_PLAN.md
- docs/REFACTORING_SUMMARY.md
- docs/REFACTORING_QUICK_REF.md
- docs/REFACTORING_GUIDE.md

### Consolidated Phase Summaries

#### Phase 2 — Export & Data Consolidation (Complete)
- Consolidated export and data loading from legacy scripts into CLI modules.
- Deleted scripts/export_data.py and scripts/load_bulk_data.py (1,300+ lines removed).
- Implemented reusable helpers in cli/export.py:
  - export_detections_to_jsonl, export_detections_to_csv
- Fixed DB session usage for test isolation (db_module.SessionLocal()).
- Updated README and AGENTS to recommend unified CLI commands.
- Test outcomes: Export & data tests fully passing; no breaking changes.

#### Phase 3 — CLI Reorganization (Complete)
- Unified reporting under cli/reports.py with a single reports command group.
- Removed cli/summary.py, cli/dual_report.py, cli/evidence.py.
- Updated cli/main.py to register reports group; tests migrated accordingly.
- Improved discoverability and consistency of reporting commands.
- Backward compatibility preserved via equivalent subcommands.

#### Phases 5 & 6 — Configuration and Data Cleanup (Complete)
- Unified config schema, defaults, and validation in config/schema.py.
- Deprecated legacy config imports; adopted ConfigLoader consistently.
- Renamed data modules for clarity (local_loader.py → loader.py; hygiene.py → cleaning.py).
- Hardened CSV cleaning and sampling with progress feedback.

> Note: Detailed per‑phase metrics, command migration examples, and test matrices have been consolidated here. CHANGELOG.md is now the authoritative historical record. Forward‑looking plans and work items are tracked in docs/ROADMAP.md.
