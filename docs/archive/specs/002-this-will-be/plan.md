# Implementation Plan: Local Analyst Configuration Mode

**Branch**: `002-this-will-be` | **Date**: 2025-10-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-this-will-be/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Convert the existing multi-user API-based SBIR transition detection system into a single-user local application with YAML-configurable classifier parameters. Primary requirement is offline execution with all detection parameters exposed in human-readable configuration files for analyst customization.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, SQLite, Pandas, XGBoost, scikit-learn, PyYAML  
**Storage**: SQLite (local file-based database)  
**Testing**: pytest  
**Target Platform**: Local workstation (macOS/Linux/Windows)
**Project Type**: Single project (CLI-focused with optional local API)  
**Performance Goals**: Process detection run in <30 minutes for typical dataset  
**Constraints**: Offline-capable, no network dependencies during execution, YAML validation required  
**Scale/Scope**: Single analyst workstation, local datasets up to 10GB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Status**: PASS - Constitution file is template-only, no specific constraints to evaluate.

**Post-Design Status**: PASS - Design maintains architectural simplicity:
- Single project structure preserved
- No new external dependencies beyond PyYAML
- CLI interface follows existing patterns
- Local execution reduces complexity vs. distributed systems
- YAML configuration is standard practice

No constitutional violations identified in the design phase.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/sbir_transition_classifier/
├── api/                 # FastAPI application (existing)
├── core/               # Configuration and data models (existing)
├── data/               # Data schemas and validation (existing)
├── detection/          # Detection algorithms and scoring (existing)
├── db/                 # Database connection and management (existing)
├── config/             # NEW: YAML configuration management
└── cli/                # NEW: Local execution commands

scripts/                # Data loading and export utilities (existing)
tests/
├── unit/               # Unit tests (existing)
├── integration/        # Integration tests (existing)
└── config/             # NEW: Configuration validation tests

config/                 # NEW: Default YAML configuration files
├── default.yaml        # Default classifier parameters
└── examples/           # Example configurations
```

**Structure Decision**: Single project structure maintained. Adding new `config/` module for YAML management and `cli/` module for local execution commands. Existing FastAPI structure preserved for potential local API usage.

## Complexity Tracking

*No constitutional violations identified - section not applicable.*
