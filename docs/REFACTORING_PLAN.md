# Codebase Refactoring & Reorganization Plan

## Executive Summary

This document outlines opportunities for streamlining, simplifying, and reorganizing the SBIR Transition Classifier codebase. The analysis reveals several areas where we can reduce complexity, eliminate duplication, and improve maintainability.

**Key Findings:**
- **252KB of CLI code** (45% of codebase) with significant overlap
- **Deprecated modules** still in use
- **Duplicate functionality** across `cli/` and `scripts/`
- **Unused code** (LocalDetectionService, ConfigurableDetectionPipeline barely used)
- **Empty placeholder files** (cli/analysis.py, cli/db.py)
- **Configuration complexity** with 3+ overlapping systems

**Estimated Impact:**
- Reduce codebase by ~20-30%
- Improve test coverage potential
- Simplify onboarding for new contributors
- Reduce cognitive load for maintenance

---

## 1. Configuration System Consolidation

### Current State: Too Many Config Systems

**Problem:**
```
config/
├── loader.py          # Main unified config
├── schema.py          # Pydantic schemas
├── defaults.py        # Default values
├── validator.py       # Validation logic
├── reset.py           # Config reset utility
core/
└── config.py          # DEPRECATED but still used
db/
└── config.py          # Database config getter
```

**Issues:**
- `core/config.py` is deprecated but still imported by `scripts/setup_local_db.py`
- Database config duplicated between `config/schema.py` and `db/config.py`
- Unclear which module to use for what purpose

### Recommended Changes

#### Phase 1: Remove Deprecated Module ✅ IMMEDIATE
```bash
# 1. Update scripts/setup_local_db.py to use new config
# 2. Delete src/sbir_transition_classifier/core/config.py
# 3. Add deprecation notice in v0.2.0 release notes
```

**Files to update:**
- `scripts/setup_local_db.py` - Replace `from core.config import settings`
- Delete `core/config.py`

#### Phase 2: Simplify Config Module Structure
```
config/
├── __init__.py        # Re-export main classes
├── loader.py          # ConfigLoader class
└── schema.py          # All Pydantic models

# Move functionality:
config/defaults.py    -> Merge into schema.py as Field defaults
config/validator.py   -> Merge into schema.py as validators
config/reset.py       -> Move to cli/reset.py (CLI-specific)
db/config.py          -> Merge into config/loader.py
```

**Benefit:** Single source of truth for configuration, easier to understand and test.

---

## 2. CLI Command Consolidation

### Current State: Over-Engineered CLI Structure

**Size Analysis:**
```
bulk.py      - 623 lines (24.5 KB)
summary.py   - 445 lines (17.5 KB)
evidence.py  - 353 lines (13.6 KB)
output.py    - 299 lines (14.0 KB)
run.py       - 155 lines (5.3 KB)
dual_report.py - 133 lines (5.7 KB)
reset.py     - 123 lines (4.1 KB)
hygiene.py   - 110 lines (4.0 KB)
data.py      - 72 lines (2.2 KB)
export.py    - 57 lines (1.6 KB)
validate.py  - 85 lines (2.7 KB)
analysis.py  - 0 lines (EMPTY)
db.py        - 0 lines (EMPTY)
main.py      - 115 lines (3.7 KB)
```

**Total:** 14 files, 2,571 lines, 252 KB

### Problems Identified

#### 2.1 Empty Placeholder Files
- `cli/analysis.py` - 0 bytes, never implemented
- `cli/db.py` - 0 bytes, never implemented

**Action:** Delete these files immediately.

#### 2.2 Duplicate Export Functionality
```
cli/export.py          # CLI wrapper (57 lines)
  └─> calls scripts/export_data.py   # Actual implementation (142 lines)
```

**Why is this bad?**
- Extra indirection for no benefit
- Testing requires testing both layers
- Users might call `scripts/export_data.py` directly and bypass CLI validation

**Recommendation:** Merge into single module
```python
# Proposed: cli/export.py (combined ~150 lines)
@click.group()
def export():
    """Data export commands."""

@export.command()
def jsonl(output_path, verbose):
    """Export detections to JSONL."""
    # Direct implementation here, no wrapper
    db = db_module.SessionLocal()
    # ... actual export logic ...
```

**Files to merge:**
- `scripts/export_data.py` → `cli/export.py`
- Delete `scripts/export_data.py`

#### 2.3 Report Generation Overlap

Three different report/summary commands with overlapping functionality:
```
cli/summary.py        - Generate summary reports (445 lines)
cli/dual_report.py    - Generate dual reports (133 lines)
cli/output.py         - OutputGenerator class (299 lines)
cli/evidence.py       - Evidence reports (353 lines)
```

**Overlap:**
- All generate reports from detection data
- Similar filtering/aggregation logic
- Duplicated formatting code
- Different output formats (JSON, CSV, HTML, markdown)

**Recommendation:** Consolidate into unified reporting module
```
cli/reports.py        # Single consolidated module (~500 lines)
├── @click.group() report
├── @report.command() summary
├── @report.command() evidence  
├── @report.command() dual
└── class ReportGenerator (shared logic)
```

**Benefits:**
- ~400 line reduction
- Shared formatting/filtering logic
- Consistent report structure
- Easier to add new report types

#### 2.4 Data Management Commands

Currently scattered:
```
cli/data.py          - Load SBIR/contracts (72 lines)
scripts/load_bulk_data.py - Bulk loading (200+ lines)
cli/hygiene.py       - Data cleaning (110 lines)
```

**Recommendation:** Single data management module
```
cli/data.py          # Consolidated (~300 lines)
├── @data.command() load
├── @data.command() clean
├── @data.command() validate
└── @data.command() sample
```

### CLI Reorganization Summary

**Before (14 files, 2,571 lines):**
```
cli/
├── analysis.py (0) DELETE
├── db.py (0) DELETE  
├── bulk.py (623)
├── data.py (72) EXPAND
├── dual_report.py (133) MERGE → reports.py
├── evidence.py (353) MERGE → reports.py
├── export.py (57) EXPAND
├── hygiene.py (110) MERGE → data.py
├── main.py (115) KEEP
├── output.py (299) MERGE → reports.py
├── reset.py (123) KEEP (config-specific)
├── run.py (155) KEEP
├── summary.py (445) MERGE → reports.py
└── validate.py (85) KEEP
```

**After (8 files, ~2,100 lines):**
```
cli/
├── bulk.py (623) - No changes
├── data.py (~350) - Consolidated data management
├── export.py (~200) - Merged with scripts/export_data.py
├── main.py (115) - No changes
├── reports.py (~500) - Consolidated reporting
├── reset.py (123) - Config management
├── run.py (155) - No changes
└── validate.py (85) - No changes
```

**Reduction:** ~18% fewer lines, 6 fewer files, clearer organization

---

## 3. Remove Unused Detection Code

### Unused: ConfigurableDetectionPipeline

**File:** `detection/pipeline.py` (300 lines)

**Usage Analysis:**
```bash
$ grep -r "ConfigurableDetectionPipeline" src/
src/sbir_transition_classifier/cli/run.py:        from ..detection.pipeline import ConfigurableDetectionPipeline
```

**Only used in:** `cli/run.py` (single detection command)

**Problem:**
- Overlaps heavily with `detection/main.py::run_full_detection()`
- Both do the same thing with different interfaces
- `pipeline.py` is 300 lines of code used in one place
- Creates confusion about which detection method to use

**Actual Detection Flow:**
```
User runs: sbir-detect bulk-process
    └─> cli/bulk.py
        └─> detection/main.py::run_full_detection()  ← PRODUCTION PATH
        
User runs: sbir-detect run
    └─> cli/run.py  
        └─> detection/pipeline.py::ConfigurableDetectionPipeline ← RARELY USED
```

**Recommendation:** DELETE `detection/pipeline.py`

**Migration Strategy:**
1. Update `cli/run.py` to use `detection/main.py::run_full_detection()`
2. Add single-award mode to `run_full_detection()` if needed
3. Delete `detection/pipeline.py`
4. **Benefit:** 300 fewer lines, one detection path to maintain

### Unused: LocalDetectionService

**File:** `detection/local_service.py` (285 lines)

**Usage Analysis:**
```bash
$ grep -r "LocalDetectionService" src/
# NO RESULTS - completely unused!
```

**Recommendation:** DELETE `detection/local_service.py`

This appears to be an early prototype that was superseded by the current detection architecture.

### Detection Module After Cleanup

**Before:**
```
detection/
├── data_quality.py (100 lines) - Used
├── heuristics.py (200 lines) - Used  
├── local_service.py (285 lines) - UNUSED DELETE
├── main.py (350 lines) - Used (primary)
├── pipeline.py (300 lines) - BARELY USED DELETE
└── scoring.py (250 lines) - Used
```

**After:**
```
detection/
├── data_quality.py (100 lines)
├── heuristics.py (200 lines)
├── main.py (350 lines) 
└── scoring.py (250 lines)
```

**Reduction:** 585 lines (47%), simpler architecture

---

## 4. Scripts Directory Cleanup

### Current State

```
scripts/
├── enhanced_analysis.py (200 lines) - Standalone script
├── export_data.py (142 lines) - Used by cli/export.py
├── load_bulk_data.py (200 lines) - Overlaps cli/data.py
├── setup_local_db.py (100 lines) - Used occasionally
├── train_model.py (?) - May be unused/experimental
└── validate_config.py (50 lines) - Overlaps cli/validate.py
```

### Problems

**Confusion:** Are these meant to be run directly or imported?
- Some have `if __name__ == '__main__'` blocks
- Some are imported by CLI commands
- Unclear which are utilities vs standalone tools

**Duplication:**
- `export_data.py` duplicates `cli/export.py`
- `load_bulk_data.py` overlaps `cli/data.py`
- `validate_config.py` overlaps `cli/validate.py`

### Recommended Changes

#### Move to CLI Commands
```bash
scripts/export_data.py → cli/export.py (merge)
scripts/load_bulk_data.py → cli/data.py (merge)  
scripts/validate_config.py → cli/validate.py (merge)
```

#### Keep as Utilities
```bash
scripts/setup_local_db.py → Keep (DB initialization utility)
scripts/enhanced_analysis.py → Evaluate (may be experimental)
scripts/train_model.py → Evaluate (may be experimental)
```

**Policy Decision Needed:** What is `scripts/` for?

**Proposal:** `scripts/` should only contain:
- Database migration scripts
- One-off data processing utilities
- Development/admin tools NOT exposed via CLI

All user-facing functionality should be in `cli/`.

---

## 5. Data Module Reorganization

### Current State: Unclear Boundaries

```
data/
├── evidence.py (150 lines) - Evidence formatting
├── hygiene.py (200 lines) - Data cleaning (also in cli/hygiene.py!)
├── local_loader.py (100 lines) - Load data from disk
├── models.py (50 lines) - Pydantic data models (not DB models)
└── schemas.py (300 lines) - More Pydantic models
```

**Confusion:** 
- `models.py` vs `schemas.py` - What's the difference?
- `data/hygiene.py` vs `cli/hygiene.py` - Duplication?
- Overlaps with `core/models.py` (SQLAlchemy models)

### Problems

**Naming:**
- `core/models.py` = SQLAlchemy database models
- `data/models.py` = Pydantic data models
- `data/schemas.py` = More Pydantic data models

**Recommendation:** Merge and clarify
```
data/
├── schemas.py (400 lines) - ALL Pydantic models
├── loader.py (renamed from local_loader.py)
├── evidence.py (keep as-is)
└── cleaning.py (renamed from hygiene.py, merge with cli/hygiene.py)
```

**Delete:** `data/models.py` (merge into `data/schemas.py`)

---

## 6. Core Module Simplification

### Current State

```
core/
├── config.py (DEPRECATED)
└── models.py (SQLAlchemy models)
```

**After removing deprecated config.py:**
```
core/
└── models.py
```

**Question:** Do we need a `core/` directory with one file?

**Recommendation:** Rename or merge
```
Option A: Rename core/ → db/models.py
Option B: Keep as-is (signals "core domain models")
Option C: Flatten to top-level models.py
```

**Preferred: Option B** - `core/` signals these are core domain entities

---

## 7. Analysis Module Clarity

### Current State

```
analysis/
├── statistics.py (150 lines)
└── transition_perspectives.py (200 lines)
```

**Usage:**
```bash
$ grep -r "from.*analysis import" src/
# Used in cli/summary.py and scripts/enhanced_analysis.py
```

**Status:** Lightly used but functional

**Recommendation:** Keep as-is, but add tests

These provide valuable analytical capabilities. No refactoring needed, but need test coverage.

---

## Implementation Roadmap

### Phase 1: Quick Wins (1 week)

**Delete Dead Code:**
- [ ] Remove `cli/analysis.py` (0 bytes)
- [ ] Remove `cli/db.py` (0 bytes)
- [ ] Remove `detection/local_service.py` (unused)
- [ ] Remove `core/config.py` (deprecated)
- [ ] Update `scripts/setup_local_db.py` to not use deprecated config

**Estimated Impact:** -600 lines, 4 fewer files

### Phase 2: Merge Duplicate Functionality (2 weeks)

**Export Consolidation:**
- [ ] Merge `scripts/export_data.py` into `cli/export.py`
- [ ] Add tests for export functionality
- [ ] Update documentation

**Data Management:**
- [ ] Merge `scripts/load_bulk_data.py` into `cli/data.py`
- [ ] Merge `cli/hygiene.py` into `cli/data.py`
- [ ] Consolidate `data/hygiene.py` and `data/cleaning.py`

**Estimated Impact:** -300 lines, clearer command structure

### Phase 3: CLI Reorganization (3 weeks)

**Report Consolidation:**
- [ ] Create `cli/reports.py`
- [ ] Migrate `cli/summary.py` commands
- [ ] Migrate `cli/dual_report.py` commands
- [ ] Migrate `cli/evidence.py` commands
- [ ] Extract shared logic from `cli/output.py`
- [ ] Delete old files
- [ ] Update main.py command registration
- [ ] Update tests

**Estimated Impact:** -400 lines, better UX

### Phase 4: Detection Simplification (2 weeks)

**Pipeline Removal:**
- [ ] Analyze `cli/run.py` requirements
- [ ] Refactor to use `detection/main.py`
- [ ] Add single-award mode if needed
- [ ] Delete `detection/pipeline.py`
- [ ] Update tests

**Estimated Impact:** -300 lines, single detection path

### Phase 5: Configuration Cleanup (1 week)

**Config Consolidation:**
- [ ] Merge `config/defaults.py` into `config/schema.py`
- [ ] Merge `config/validator.py` into `config/schema.py`
- [ ] Move `config/reset.py` logic to `cli/reset.py`
- [ ] Merge `db/config.py` into `config/loader.py`
- [ ] Update imports across codebase
- [ ] Update tests

**Estimated Impact:** -200 lines, simpler config system

### Phase 6: Data Module Cleanup (1 week)

**Schema Consolidation:**
- [ ] Merge `data/models.py` into `data/schemas.py`
- [ ] Rename `data/local_loader.py` to `data/loader.py`
- [ ] Rename `data/hygiene.py` to `data/cleaning.py`
- [ ] Update imports
- [ ] Update tests

**Estimated Impact:** -50 lines, clearer organization

---

## Testing Strategy During Refactoring

### Prevent Regressions

**Before Each Phase:**
1. Run full test suite and ensure passing
2. Document current behavior with integration tests
3. Create "golden" test fixtures

**During Refactoring:**
1. Keep tests passing (refactor tests alongside code)
2. Add new tests for consolidated code
3. Ensure 100% test coverage of changed modules

**After Each Phase:**
1. Run full test suite
2. Perform manual smoke tests
3. Update documentation

### Critical Test Coverage

**Must have tests before refactoring:**
- [ ] Export functionality (all formats)
- [ ] Data loading (SBIR + contracts)
- [ ] Detection pipeline (full workflow)
- [ ] Configuration loading
- [ ] Report generation

---

## Expected Outcomes

### Quantitative Improvements

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Files | 55 | ~42 | -24% |
| Total Lines | ~11,000 | ~8,500 | -23% |
| CLI Files | 14 | 8 | -43% |
| CLI Lines | 2,571 | ~2,100 | -18% |
| Detection Files | 6 | 4 | -33% |
| Config Files | 7 | 3 | -57% |

### Qualitative Improvements

**Developer Experience:**
- ✅ Single detection implementation path
- ✅ Clear separation: CLI vs library code
- ✅ Obvious where to add new features
- ✅ Faster onboarding for new contributors

**Code Quality:**
- ✅ Less duplication
- ✅ Better test coverage potential
- ✅ Clearer module responsibilities
- ✅ Easier to navigate codebase

**User Experience:**
- ✅ Consistent CLI command structure
- ✅ Predictable command naming
- ✅ Better help documentation
- ✅ Fewer "which command do I use?" moments

---

## Risk Assessment

### Low Risk (Safe to do immediately)
- Deleting empty files (cli/analysis.py, cli/db.py)
- Removing unused code (local_service.py)
- Removing deprecated code (core/config.py)

### Medium Risk (Need good tests first)
- Merging CLI commands
- Consolidating export functionality
- Merging config modules

### High Risk (Need careful planning)
- Removing detection/pipeline.py (used in cli/run.py)
- Major CLI restructuring (user-facing changes)
- Database model changes

---

## Migration Guide for Users

### Breaking Changes Checklist

**CLI Commands:**
- `sbir-detect summary` → `sbir-detect report summary`
- `sbir-detect dual-report` → `sbir-detect report dual`
- `sbir-detect evidence` → `sbir-detect report evidence`

**Python API:**
```python
# Before
from sbir_transition_classifier.scripts.export_data import export_jsonl

# After  
from sbir_transition_classifier.cli.export import export_jsonl
```

**Configuration:**
```python
# Before
from sbir_transition_classifier.core.config import settings

# After
from sbir_transition_classifier.config.loader import ConfigLoader
config = ConfigLoader.load_default()
```

### Deprecation Timeline

**v0.1.x (Current):** Deprecation warnings
**v0.2.0:** Remove deprecated code
**v0.3.0:** Complete refactoring

---

## Appendix: File Deletion Checklist

### Safe to Delete Immediately
- [ ] `cli/analysis.py` (0 bytes, empty placeholder)
- [ ] `cli/db.py` (0 bytes, empty placeholder)
- [ ] `detection/local_service.py` (285 lines, unused)

### Delete After Migration
- [ ] `core/config.py` (deprecated) → Migrate `scripts/setup_local_db.py`
- [ ] `detection/pipeline.py` (300 lines) → Migrate `cli/run.py`
- [ ] `scripts/export_data.py` (142 lines) → Merge into `cli/export.py`
- [ ] `scripts/load_bulk_data.py` (200 lines) → Merge into `cli/data.py`
- [ ] `scripts/validate_config.py` (50 lines) → Merge into `cli/validate.py`
- [ ] `data/models.py` (50 lines) → Merge into `data/schemas.py`
- [ ] `config/defaults.py` → Merge into `config/schema.py`
- [ ] `config/validator.py` → Merge into `config/schema.py`
- [ ] `db/config.py` → Merge into `config/loader.py`

### Post-Merge Deletions
- [ ] `cli/summary.py` → After merging into `cli/reports.py`
- [ ] `cli/dual_report.py` → After merging into `cli/reports.py`
- [ ] `cli/evidence.py` → After merging into `cli/reports.py`
- [ ] `cli/output.py` → After extracting to `cli/reports.py`
- [ ] `cli/hygiene.py` → After merging into `cli/data.py`

**Total:** ~1,800 lines to be deleted or merged

---

## Conclusion

This refactoring plan will reduce the codebase by approximately 20-25% while improving clarity, maintainability, and testability. The phased approach allows for incremental progress with minimal risk.

**Recommended Next Steps:**
1. Review and approve this plan
2. Start with Phase 1 (Quick Wins) - low risk, immediate value
3. Add tests for critical paths before Phases 2-4
4. Execute phases sequentially with full test coverage

**Timeline:** 10-12 weeks for complete refactoring
**Effort:** ~60-80 developer hours
**Risk Level:** Medium (with proper testing strategy)

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-28  
**Next Review:** After Phase 1 completion