# Implementation Plan: Detect Untagged SBIR Phase III Transitions

**Branch**: `001-prompt-detect-untagged` | **Date**: 2025-10-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-prompt-detect-untagged/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This plan outlines the implementation of a system to detect untagged SBIR Phase III transitions. The system will ingest bulk federal spending data, use a combination of heuristics and a simple machine learning model to identify potential transitions, and expose the results via a REST API. The primary goal is to create a reliable, auditable process for identifying SBIR commercialization that is not officially flagged.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, Pandas, Dask, scikit-learn, XGBoost, SQLAlchemy
**Storage**: PostgreSQL
**Testing**: pytest
**Target Platform**: Dockerized Linux server
**Project Type**: Single project (data processing backend with an API)
**Performance Goals**: Backtest a full fiscal year of data in < 8 hours. API p95 response time < 500ms.
**Constraints**: Must be able to process large (~10-100GB) yearly data files.
**Scale/Scope**: Initial scope is backtesting 5 fiscal years of data.
**Data Sources**: Local `award_data.csv` for SBIR awards; Bulk downloads from USAspending.gov for contract data.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file is a template and does not contain specific principles to check against. Assuming standard principles of testability, clarity, and maintainability, this plan is compliant. No violations are noted.

## Project Structure

### Documentation (this feature)

```
specs/001-prompt-detect-untagged/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── api.yaml         # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Option 1: Single project (DEFAULT)
src/
├── sbir_transition_classifier/
│   ├── api/
│   │   └── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── models.py
│   ├── data/
│   │   ├── ingestion.py
│   │   └── schemas.py
│   ├── detection/
│   │   ├── heuristics.py
│   │   └── scoring.py
│   └── db/
│       └── database.py
├── scripts/
│   └── load_bulk_data.py
└── main.py

tests/
├── integration/
└── unit/
```

**Structure Decision**: A single project structure is chosen. The application is a self-contained data processing service with a simple API, so a monolithic structure within `src/` is appropriate and avoids premature complexity. The directory is named `sbir_transition_classifier` to be explicit.

## Complexity Tracking

*No violations noted.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       | N/A        | N/A                                 |