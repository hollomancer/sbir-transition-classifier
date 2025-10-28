# End-to-End Test Coverage Assessment

## Executive Summary

**Answer: NO, we do NOT have comprehensive E2E tests.**

**Current State:**
- 3 integration tests total
- ~15% E2E workflow coverage
- Happy path only, no edge cases
- Single test data scenario per workflow

**Risk Level for Aggressive Refactoring: HIGH**

**Recommendation: Option B (Balanced Approach)** - Add critical tests before major refactoring.

---

## Current E2E Test Inventory

### Test 1: `test_end_to_end_detection`
**File:** `tests/integration/test_end_to_end.py`  
**Coverage:** Basic detection flow with manual DB setup

**What it tests:**
- ✅ Create vendor, award, contract directly in DB
- ✅ Run `run_detection_for_award()` (synchronous, single award)
- ✅ Verify detection is created
- ✅ Basic evidence bundle structure

**What it DOESN'T test:**
- ❌ CSV ingestion (bypassed)
- ❌ Bulk detection (`run_full_detection()`)
- ❌ Multiprocessing/parallel execution
- ❌ Multiple awards/contracts
- ❌ Edge cases (duplicates, missing data, etc.)
- ❌ Export functionality
- ❌ CLI commands

**Coverage:** ~10% (narrow happy path)

---

### Test 2: `test_run_full_detection_in_process`
**File:** `tests/integration/test_run_full_detection_in_process.py`  
**Coverage:** Full ingestion → detection pipeline

**What it tests:**
- ✅ CSV file creation (1 SBIR award, 1 contract)
- ✅ SBIR ingestion via `SbirIngester`
- ✅ Contract ingestion via `ContractIngester`
- ✅ `run_full_detection(in_process=True)` - serial mode
- ✅ Detection creation from ingested data
- ✅ Evidence bundle validation

**What it DOESN'T test:**
- ❌ Multiprocessing mode (`in_process=False`)
- ❌ Large datasets (only 1 record each)
- ❌ Multiple detections per award
- ❌ Duplicate handling
- ❌ Invalid/malformed CSV data
- ❌ Export functionality
- ❌ CLI command invocation

**Coverage:** ~30% (core pipeline, happy path)

---

### Test 3: `test_cli_bulk_process_end_to_end_smoke`
**File:** `tests/integration/test_cli_bulk_process.py`  
**Coverage:** CLI bulk-process command

**What it tests:**
- ✅ CLI command invocation via Click runner
- ✅ Isolated filesystem setup
- ✅ CSV file creation (1 SBIR, 1 contract)
- ✅ `bulk-process` command execution
- ✅ Exit code 0 (success)
- ✅ Output file creation (or DB exists)

**What it DOESN'T test:**
- ❌ Other CLI commands (run, export, analysis, etc.)
- ❌ CLI error handling
- ❌ Large datasets
- ❌ Export format validation (just checks file exists)
- ❌ Detection quality/correctness
- ❌ Command-line argument variations

**Coverage:** ~5% (single CLI command, minimal validation)

---

## Coverage Gaps Analysis

### Critical Workflows NOT Tested

#### 1. Export Functionality (0% coverage)
```bash
sbir-detect export jsonl
sbir-detect export csv
```
- No tests for JSONL export format
- No tests for CSV export format
- No tests for export filtering
- No tests for empty database export
- **Risk:** Export refactoring could break silently

#### 2. Single Detection Command (0% coverage)
```bash
sbir-detect run --award-id XYZ
```
- Uses different code path (`detection/pipeline.py`)
- No integration tests at all
- **Risk:** Could delete `pipeline.py` and not know it breaks

#### 3. Analysis/Reporting (0% coverage)
```bash
sbir-detect summary
sbir-detect dual-report
sbir-detect evidence
```
- No tests for report generation
- No tests for statistics calculation
- **Risk:** Report consolidation could break everything

#### 4. Data Management (0% coverage)
```bash
sbir-detect data load-sbir
sbir-detect data load-contracts
```
- No tests for CLI data loading
- Only tested via bulk-process
- **Risk:** Refactoring could break standalone commands

#### 5. Configuration Management (0% coverage)
```bash
sbir-detect validate-config
sbir-detect reset
```
- No CLI tests for config validation
- No tests for config reset
- **Risk:** Config consolidation could break CLI

### Edge Cases NOT Tested

#### Data Quality Issues
- ❌ Malformed CSV files
- ❌ Missing required columns
- ❌ Invalid date formats
- ❌ Duplicate awards/contracts
- ❌ Empty files
- ❌ UTF-8 encoding issues
- ❌ Very large files (>1M rows)

#### Detection Edge Cases
- ❌ Zero detections found
- ❌ Hundreds of detections for single award
- ❌ Multiple awards with same PIID
- ❌ Contracts before award completion
- ❌ Missing vendor information
- ❌ Different vendor name spellings

#### System Edge Cases
- ❌ Disk space errors
- ❌ Database connection failures
- ❌ Permission errors (read/write)
- ❌ Concurrent execution conflicts
- ❌ Out of memory scenarios

---

## Test Data Limitations

### Current Test Scenarios

**Scenario 1: "Happy Path"**
```
1 Vendor: "Acme Widgets" / "Integration Test Co"
1 SBIR Award: Phase II, Air Force, FA0001
1 Contract: Sole source, starts +60 days after SBIR
Expected: 1 detection with high score
```

**That's it. That's the only scenario.**

### Missing Test Scenarios

#### Detection Scenarios We Should Test
- [ ] Phase I award → Should NOT detect (if config excludes Phase I)
- [ ] Contract starts 1 day after SBIR → Should detect (high score)
- [ ] Contract starts 365 days after SBIR → Should detect (low score)
- [ ] Contract starts BEFORE SBIR ends → Should NOT detect
- [ ] Different vendor names → Should NOT detect
- [ ] Same PIID, different agencies → Should detect (lower score)
- [ ] Multiple contracts for same award → Should detect all
- [ ] Competed contract vs sole-source → Different scores
- [ ] Missing competition details → Should handle gracefully

#### Ingestion Scenarios We Should Test
- [ ] Duplicate SBIR awards → Skip second
- [ ] Same vendor, different spellings → Merge or separate?
- [ ] Award with missing dates → Reject or use defaults?
- [ ] Contract with missing PIID → Reject
- [ ] CSV with extra columns → Ignore
- [ ] CSV with missing columns → Error

#### System Scenarios We Should Test
- [ ] 10k SBIR awards + 100k contracts → Performance
- [ ] Empty database → Graceful handling
- [ ] Database already has data → Incremental load
- [ ] Parallel execution with 4 workers → Correctness
- [ ] Serial execution → Same results as parallel

---

## Coverage by Module

| Module | E2E Coverage | Notes |
|--------|--------------|-------|
| **Ingestion** | | |
| SBIR Ingester | 30% | Happy path only |
| Contract Ingester | 30% | Happy path only |
| Vendor Matching | 10% | Minimal testing |
| **Detection** | | |
| Heuristics | 30% | Single scenario |
| Scoring | 30% | Via integration only |
| Main Pipeline | 30% | In-process mode only |
| Pipeline (single) | 0% | NOT TESTED |
| **CLI Commands** | | |
| bulk-process | 10% | Smoke test only |
| run | 0% | NOT TESTED |
| export | 0% | NOT TESTED |
| summary | 0% | NOT TESTED |
| analysis | 0% | NOT TESTED |
| data | 0% | NOT TESTED |
| Others | 0% | NOT TESTED |
| **Export** | | |
| JSONL export | 0% | NOT TESTED |
| CSV export | 0% | NOT TESTED |
| **Reporting** | | |
| Summary reports | 0% | NOT TESTED |
| Evidence viewing | 0% | NOT TESTED |
| Dual reports | 0% | NOT TESTED |

**Overall E2E Coverage: ~15%**

---

## What "Comprehensive E2E Tests" Would Look Like

### Minimum Comprehensive Coverage

#### 1. Core Detection Workflows (3 tests)
- [ ] **Full Pipeline Test:** CSV → Ingest → Detect → Export → Verify
- [ ] **Bulk Processing Test:** Large dataset (1k awards, 10k contracts)
- [ ] **Single Detection Test:** CLI run command with specific award ID

#### 2. CLI Command Tests (8 tests)
- [ ] bulk-process (variations: with/without verbose, different formats)
- [ ] run (single detection)
- [ ] export jsonl
- [ ] export csv
- [ ] summary report
- [ ] evidence view
- [ ] data load-sbir
- [ ] data load-contracts

#### 3. Data Quality Tests (5 tests)
- [ ] Malformed CSV handling
- [ ] Duplicate data handling
- [ ] Missing required fields
- [ ] Invalid date formats
- [ ] Empty database scenarios

#### 4. Detection Scenarios (10 tests)
- [ ] Perfect match (high score)
- [ ] Late contract (low score)
- [ ] Very late contract (no detection)
- [ ] Different agency (penalty)
- [ ] Sole source (bonus)
- [ ] Multiple contracts per award
- [ ] Zero detections found
- [ ] Phase I vs Phase II
- [ ] Contract before SBIR ends
- [ ] Vendor name variations

#### 5. Performance Tests (2 tests)
- [ ] Large dataset processing (10k+ records)
- [ ] Parallel vs serial correctness

#### 6. Error Handling Tests (3 tests)
- [ ] Database connection failure
- [ ] File permission errors
- [ ] Disk space errors

**Total Comprehensive Coverage: 31 E2E tests minimum**  
**Current: 3 tests**  
**Gap: 28 tests (93%)**

---

## Risk Assessment for Refactoring

### If We Refactor Now (Without More Tests)

#### HIGH RISK Areas
- **CLI Reorganization** (Phase 3)
  - Risk: 13/14 commands untested, could break silently
  - Impact: User workflows broken
  - Mitigation: Don't do this without tests

- **Detection Pipeline Removal** (Phase 4)
  - Risk: Only used by `run` command which has 0% coverage
  - Impact: Single detection completely broken
  - Mitigation: Add tests first or keep both implementations

- **Export Consolidation** (Phase 2)
  - Risk: 0% E2E coverage of export functionality
  - Impact: Data export broken, users can't get results
  - Mitigation: Add export tests before merging

#### MEDIUM RISK Areas
- **Config Consolidation** (Phase 5)
  - Risk: Config loading tested, but not CLI usage
  - Impact: Commands might fail to load config
  - Mitigation: Unit tests exist, add integration tests

#### LOW RISK Areas
- **Dead Code Removal** (Phase 1)
  - Risk: Low (unused code by definition)
  - Impact: Minimal (if truly unused)
  - Mitigation: Grep for usage, remove cautiously

---

## Recommendations

### Immediate Actions (Before ANY Refactoring)

#### 1. Add Critical E2E Tests (1 week)
```python
# Must-have before refactoring:
tests/integration/test_cli_export.py
tests/integration/test_cli_run.py
tests/integration/test_detection_scenarios.py
tests/integration/test_data_quality.py
```

**Why:** These test the areas we plan to refactor heavily.

#### 2. Create Test Data Fixtures (2 days)
```python
tests/fixtures/datasets.py
- small_dataset() → 10 awards, 50 contracts
- medium_dataset() → 100 awards, 500 contracts
- edge_cases_dataset() → All edge case scenarios
```

**Why:** Reusable test data across all E2E tests.

#### 3. Add Golden Tests (1 day)
```python
tests/golden/
- baseline_detections.json → Known-good detection results
- Compare refactored output to baseline
```

**Why:** Catch regression in detection behavior.

### Updated Refactoring Strategy

**REVISED RECOMMENDATION: Option B+ (Balanced with Safety Net)**

#### Phase 0: Test Safety Net (2 weeks) - NEW
- [ ] Add 10 critical E2E tests (export, run, scenarios)
- [ ] Create reusable test fixtures
- [ ] Set up golden test baselines
- [ ] Achieve 50% E2E coverage minimum

**ONLY THEN proceed with:**

#### Phase 1: Quick Wins (1 week)
- Delete dead code (low risk, tests not required)

#### Phase 2: Export Consolidation (2 weeks)
- Now safe because export tests exist

#### Phase 3: CLI Reorganization (3 weeks)
- Now safe because CLI tests exist

#### Phase 4+: Continue as planned
- Detection, config, data module refactoring

---

## Coverage Roadmap

### Short-Term (Before Refactoring)
**Target: 50% E2E coverage**

- [ ] 5 CLI command tests (bulk, run, export x2, data)
- [ ] 5 detection scenario tests
- [ ] 3 data quality tests
- [ ] 2 error handling tests

**Total: 15 E2E tests (vs current 3)**

### Medium-Term (During Refactoring)
**Target: 75% E2E coverage**

- [ ] All CLI commands tested (13 tests)
- [ ] 10 detection scenarios
- [ ] 5 data quality tests
- [ ] 3 performance tests

**Total: 31 E2E tests**

### Long-Term (Post-Refactoring)
**Target: 90%+ E2E coverage**

- [ ] Comprehensive CLI test suite
- [ ] All edge cases covered
- [ ] Load/stress tests
- [ ] Multi-platform tests (Windows, Linux, macOS)

---

## Conclusion

**We do NOT have comprehensive E2E tests.**

**Current Coverage:** 15% (3 tests, happy path only)  
**Required for Safe Refactoring:** 50% minimum (15+ tests)  
**Gap:** 12 critical tests needed

**Aggressive refactoring (Option C) is NOT recommended** without first building a test safety net.

**Recommended Path:**
1. **Phase 0 (NEW):** Add critical E2E tests (2 weeks)
2. **Phase 1:** Quick wins - delete dead code (1 week)
3. **Phase 2+:** Proceed with balanced refactoring approach

**Timeline Impact:** Add 2 weeks to roadmap for test foundation  
**Risk Reduction:** High → Medium  
**Long-term Value:** Tests prevent future regressions, speed up development

---

**Document Version:** 1.0  
**Assessment Date:** 2025-01-28  
**Confidence Level:** HIGH (based on thorough code review)  
**Next Review:** After Phase 0 test additions