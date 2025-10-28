# SBIR Transition Classifier — Product & Engineering Roadmap

This roadmap consolidates our improvement plan, immediate next steps, and prioritized refactoring opportunities. It is a living document; we review and update it at the start of each sprint.

Last updated: 2025-10-28 (post Pydantic v2 and SQLAlchemy v2 deprecation cleanup)

---

## Vision

Provide a fast, auditable, and developer-friendly pipeline to detect untagged SBIR Phase III transitions from public data sources, with:
- Clear, reproducible CLI workflows
- Robust evidence bundles and exports
- A testing strategy that enables safe, incremental change
- Config-driven detection logic and tunable thresholds
- Performance headroom for year-scale ingest and analysis

---

## Guiding Principles

- Prefer configuration over code when tuning behavior.
- Maintain two detection paths (file-based and DB-based) unless usage shows one is obsolete.
- Keep CLI ergonomics simple and consistent; expose power via flags and config.
- Optimize for testability (no import-time side effects, easy to swap DB, deterministic I/O).
- Consolidate docs; reduce duplication to minimize drift.

---

## Roadmap Themes

1) Reliability & Testability
2) Performance & Scale
3) Developer Experience (DX) & Docs
4) Detection Quality (signals, scoring, evidence)
5) Data Hygiene & Provenance
6) Operationalization (observability, reproducibility, releases)

---

## Near-Term (1–2 Sprints)

### A. Documentation Streamline (in-flight)
- Create docs/README.md as the canonical docs index (done).
- Consolidate historical refactoring/phase docs into CHANGELOG.md (seeded).
- Create docs/ROADMAP.md (this file).
- Retire or merge duplicative docs:
  - Merge E2E_TEST_ASSESSMENT into TESTING_STRATEGY.
  - Move commit message template under docs/templates or .github.

Acceptance criteria:
- One-click path from repo README to canonical docs index.
- CHANGELOG.md captures the historical phase/refactor narrative.
- No “undiscoverable” Markdown files in root/docs (index covers all).

### B. Testing & CI Quality Gates
- Add smoke tests for common CLI flows under constrained datasets (done for bulk/export; expand for hygiene).
- Make run CLI robust to absence of config (done) and ensure JSON/JSONL modes validated in tests (done).
- Gate on warnings: ensure zero Pydantic and SQLAlchemy deprecation warnings (done).

Acceptance criteria:
- CI runs all integration tests with zero deprecation warnings.
- Minimal flake rate; re-runs behave identically.

### C. SQLAlchemy v2 idioms (follow-up)
- Confirm ORM usage is v2 style throughout (session lifecycle, queries).
- Add a short “DB patterns” section in IMPLEMENTATION_GUIDE.

Acceptance criteria:
- No v1 API usage; style guide documents preferred patterns.

---

## Mid-Term (1–2 Months)

### D. Performance & Scale
- Introduce batch ingestion metrics (row counts, durations, chunk sizes) in logs.
- Add optional multi-processing toggles for ingestion (with clear caveats for SQLite).
- Evaluate Parquet/Feather intermediates for large workflows (optional path).

Acceptance criteria:
- For a representative FY dataset, document ingest/detect/export timings and memory footprint.
- Config flag enables/disables multi-processing; defaults safe for CI and laptops.

### E. Detection Quality and Signals
- Add a pluggable signal registry (detection/features/) so new heuristics can be toggled from config.
- Expand competition signal vocabulary (normalize extent_competed and synonyms).
- Improve timing decay function (already penalized >365d; make decay curve configurable).
- Optional: light-weight text similarity with curated keyword lists, behind a feature flag.

Acceptance criteria:
- Feature toggles in YAML selectively enable signals.
- Documented impact of each signal on score with unit tests.

### F. Evidence & Explainability
- Standardize evidence bundle schema versioning (e.g., evidence.version).
- Add compact “why” summary to evidence (top 3 signals with weights).
- Provide a small “evidence viewer” CLI subcommand that pretty-prints a bundle.

Acceptance criteria:
- Evidence has a version and short explanation.
- CLI: sbir-detect reports evidence --detection-id <id> renders summary.

---

## Long-Term (Quarter+)

### G. Source Provenance & Lineage
- Track source file/URL, selection filters, and import config in DB rows (awards, contracts).
- Embed minimal provenance in evidence bundles.

Acceptance criteria:
- Given a detection, you can trace its inputs back to data files and ingester settings.

### H. Pluggable Storage & Cloud Optionality
- Abstract DB settings to support Postgres when needed (pool sizing, timeouts).
- Optional object storage for large evidence bundles and exports.

Acceptance criteria:
- Switching between SQLite and Postgres requires only YAML changes.
- Evidence can be directed to filesystem or S3-like stores (flagged; not required by default).

### I. Operationalization & Releases
- Versioned releases with pinned dependencies (Poetry lock committed).
- Release notes auto-generated from CHANGELOG.
- Optional: publish a small container image for standardized runs.

Acceptance criteria:
- Reproducible run instructions pinned to version tags.
- CHANGELOG drives release notes.

---

## Refactoring Opportunities (Prioritized)

1) Detection Path Convergence (Deferred; revisit with data)
- Today: file-based pipeline (ConfigurableDetectionPipeline) and DB-based pipeline (run_full_detection).
- Decision: keep both unless telemetry shows one is obsolete.
- If converged in the future: define a unified service layer orchestrating loaders, filters, and scoring regardless of source.

2) Ingestion Normalization
- Normalize USAspending columns (extent_competed, pricing type, NAICS/PSC) through a single transform module.
- Provide a schema contract for ingesters; ensure unit tests cover malformed CSV patterns.

3) Config Simplification
- Reduce top-level config complexity by nesting feature toggles under detection.features.* with consistent naming.
- Provide preset “profiles” (high-precision, broad-discovery) as YAML examples.

4) Evidence Schema Cleanup
- Separate “raw_data” from “normalized_data” in evidence, and cap sizes (truncate or summarize) for portability.
- Introduce optional “attachments” to point at stored artifacts without bundling large blobs inline.

5) CLI Subcommand Layout Polish
- Ensure each group has a consistent --help layout and examples.
- Add “dry-run” mode where applicable.

---

## Data Hygiene & Quality

- Continue strengthening DataCleaner: column trimming, type coercion, date parsing with clear fallbacks.
- Provide data validation reports (missing critical fields, null rates).
- Validate CSV headers against expected sets (warn on unknowns).

Acceptance criteria:
- Running hygiene produces a summary with row counts, dropped rows, null-columns, and recommendations.

---

## Observability & Telemetry (Optional)

- Structured logs for ingestion/detection with step timings.
- Optional metrics export (Prometheus/OpenTelemetry) when run in long-lived environments.
- Add “–trace” mode to capture more detailed timings and sampling of intermediate results.

Acceptance criteria:
- A single run’s performance can be compared across commits/configs by inspecting logs/metrics.

---

## Security & Compliance

- Enforce config-driven secrets (no hardcoding). Already covered in AGENTS.md.
- Document SBIR/USAspending data handling expectations (scrub before commit).
- Provide a section in IMPLEMENTATION_GUIDE on secure local usage.

Acceptance criteria:
- No secrets in repo; docs specify environment-variable usage and safe patterns.

---

## Documentation Improvements

- Keep README succinct; link into docs/ for deep-dives.
- Ensure every CLI group has examples in README and IMPLEMENTATION_GUIDE.
- Provide a “Troubleshooting” appendix (common CSV pitfalls, SQLite locking, memory issues).

Acceptance criteria:
- Contributors can complete common flows using only README + docs/README.

---

## Milestones & KPIs

- CI health: 100% integration tests passing; zero deprecation warnings.
- Performance baseline: document ingest/detection/export for one FY; track ±10% drift.
- Detection quality: define a small labeled set to sanity-check thresholds (internal; optional).
- Release cadence: lightweight, tagged releases each milestone with CHANGELOG entries.

---

## Decision Log (Short)

- Keep two detection paths for now; revisit if usage shows one is not needed.
- Favor SQLite for local and CI; Postgres remains a future option via config.
- Pydantic v2 and SQLAlchemy v2 migrations complete; commit to v2 patterns.

---

## Review Cadence

- Update ROADMAP.md every sprint planning.
- Update CHANGELOG.md when merging meaningful changes.
- Archive superseded docs and link replacements from docs/README.md.

---

## Quick Next Steps Checklist

- [ ] Move commit message template to docs/templates or .github (and cross-link in AGENTS.md).
- [ ] Merge E2E_TEST_ASSESSMENT into TESTING_STRATEGY.
- [x] Add DB patterns section to IMPLEMENTATION_GUIDE (session lifecycle, eager loading, chunked bulk inserts).
- [x] Add Ingestion Normalization section to IMPLEMENTATION_GUIDE (transforms and validation flags).
- [x] Create CLI utilities module (cli/utils.py) with CliContext, progress tracking, and shared helpers.
- [x] Create database queries module (db/queries.py) with common patterns (vendors, awards, contracts, detections).
- [x] Remove unused detection/data_quality.py (data quality checks now in ingestion validation).
- [x] Consolidate SPECIFICATIONS.md and PERFORMANCE.md into IMPLEMENTATION_GUIDE.md (reduce docs/ from 9 to 7 files).
- [ ] Add evidence "why" summary and version field.
- [ ] Add ingestion metrics logging and summarize per run.
- [ ] Define signal registry and YAML toggles; add unit tests for each signal.
- [ ] Write baseline performance doc section with reproducible commands.

---

If you’re planning new work, propose an update here and in the next sprint planning. This roadmap is our single source of truth for where the system is headed.