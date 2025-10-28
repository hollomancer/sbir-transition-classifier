# Testing Strategy & Coverage Analysis

## Current Test Suite Overview

### Test Organization

```
tests/
├── unit/
│   ├── config/
│   │   └── test_loader.py           # Config loading tests
│   ├── detection/
│   │   └── test_scoring.py          # Scoring algorithm tests
│   ├── ingestion/
│   │   └── test_sbir_ingester.py    # SBIR data ingestion tests
│   └── test_config_and_detection.py # Legacy combined tests
├── integration/
│   ├── test_cli_bulk_process.py     # Full CLI bulk-process workflow
│   ├── test_end_to_end.py           # Detection pipeline end-to-end
│   └── test_run_full_detection_in_process.py  # In-process detection
└── conftest.py                       # Shared fixtures
```

**Total Source Modules**: 45 non-init Python files  
**Total Test Files**: 7 unit + 3 integration = 10 test files  
**Estimated Coverage**: ~20-25% of source modules have direct tests

---

## Coverage Analysis by Component

### ✅ Well-Covered Components

| Component | Coverage | Test Files |
|-----------|----------|------------|
| SBIR Ingestion | Good | `test_sbir_ingester.py` |
| Scoring Algorithm | Good | `test_scoring.py` |
| Config Loading | Good | `test_loader.py` |
| Detection Pipeline | Moderate | Integration tests |
| Bulk CLI Workflow | Moderate | `test_cli_bulk_process.py` |

### ⚠️ Partially Covered Components

| Component | Issues | Priority |
|-----------|--------|----------|
| Contract Ingestion | **No dedicated tests** - just fixed UUID bugs here! | **HIGH** |
| Detection Heuristics | Used in integration tests only, no unit tests | **HIGH** |
| Data Quality Checks | No tests for PIID/date validation logic | **MEDIUM** |
| Export Functionality | No tests for JSONL/CSV export | **MEDIUM** |

### ❌ Untested Components (Critical Gaps)

#### CLI Commands (13/14 untested)
- `cli/run.py` - Single detection command
- `cli/export.py` - Export command
- `cli/analysis.py` - Analysis commands
- `cli/dual_report.py` - Dual report generation
- `cli/evidence.py` - Evidence viewing
- `cli/summary.py` - Summary reports
- `cli/validate.py` - Config validation CLI
- `cli/db.py` - Database management
- `cli/data.py` - Data management
- `cli/reset.py` - Reset command
- `cli/hygiene.py` - Data hygiene
- `cli/output.py` - Output formatting

#### Analysis Modules (2/2 untested)
- `analysis/statistics.py` - Statistical analysis
- `analysis/transition_perspectives.py` - Transition analysis views

#### Detection Components (4/6 untested)
- `detection/data_quality.py` - Data quality filters
- `detection/heuristics.py` - Candidate matching logic
- `detection/pipeline.py` - Detection pipeline orchestration
- `detection/local_service.py` - Local detection service

#### Scripts (5/5 untested)
- `scripts/export_data.py` - Export utilities (used by CLI)
- `scripts/load_bulk_data.py` - Bulk data loading
- `scripts/setup_local_db.py` - Database setup
- `scripts/enhanced_analysis.py` - Enhanced analysis
- `scripts/train_model.py` - Model training (if used)

#### Data/Schema Modules (4/5 untested)
- `data/evidence.py` - Evidence formatting
- `data/hygiene.py` - Data cleaning utilities
- `data/local_loader.py` - Local data loading
- `data/models.py` - Data models

---

## Test Quality Issues Identified

### 1. **Import-Time Binding Problems** ✅ FIXED
- **Issue**: Tests couldn't swap database sessions due to module-level imports
- **Fix Applied**: Changed to dynamic `db_module.SessionLocal()` imports
- **Affected Files**: `detection/main.py`, `cli/bulk.py`, ingesters
- **Lesson**: Always use dynamic imports for testable components

### 2. **Database Initialization Order** ✅ FIXED
- **Issue**: CLI queried database before creating tables
- **Fix Applied**: Moved `create_all()` before first query
- **Lesson**: Ensure DB initialization happens early in execution flow

### 3. **Type Conversion for SQLite** ✅ FIXED
- **Issue**: UUID and Timestamp objects not compatible with SQLite
- **Fix Applied**: Convert to strings/datetime objects before insertion
- **Lesson**: Test with actual SQLite backend, not just in-memory mocks

### 4. **Test Isolation**
- **Current State**: Some tests share database state
- **Risk**: Flaky tests, order dependencies
- **Recommendation**: Use isolated DB per test via fixtures

### 5. **Test Data Quality**
- **Current State**: Minimal CSV fixtures with 1-2 rows
- **Risk**: Edge cases not covered (duplicates, malformed data, etc.)
- **Recommendation**: Add fixture sets for edge cases

---

## Recommended Testing Improvements

### Priority 1: Critical Functionality (1-2 weeks)

#### 1.1 Contract Ingestion Tests
**File**: `tests/unit/ingestion/test_contract_ingester.py`

```python
# Test cases needed:
- Valid contract ingestion with all fields
- PIID generation (base + mod + transaction)
- Vendor matching and creation
- Duplicate detection
- Missing required fields handling
- Bulk insert performance (chunked processing)
- Competition details JSON structure
- Edge case: contracts without vendor
```

**Why**: We just fixed UUID bugs here; need regression protection.

#### 1.2 Detection Heuristics Tests
**File**: `tests/unit/detection/test_heuristics.py`

```python
# Test cases needed:
- find_candidate_contracts() logic
  - PIID matching (exact, substring, parent)
  - Vendor matching
  - Time window filtering
  - Agency filtering
- get_confidence_signals() accuracy
- get_text_based_signals() parsing
- Edge case: no candidates found
- Edge case: multiple strong matches
```

**Why**: Core detection logic with complex matching rules.

#### 1.3 Data Quality Validation Tests
**File**: `tests/unit/detection/test_data_quality.py`

```python
# Test cases needed:
- _has_date_mismatch() for PIID/date validation
- Threshold detection (>2 year difference)
- Various PIID formats (FA2020, N00014-21-C-1234, etc.)
- Missing date handling
- Missing PIID handling
```

**Why**: Recently added logic that filters detections; needs verification.

### Priority 2: User-Facing Features (2-3 weeks)

#### 2.1 Export Command Tests
**File**: `tests/integration/test_cli_export.py`

```python
# Test cases needed:
- Export to JSONL format
- Export to CSV format
- Export filters (by confidence, agency, date range)
- Output file creation and structure
- Empty database handling
- Large result sets (pagination if applicable)
```

**Why**: Users rely on exports for downstream analysis.

#### 2.2 Run Command Tests
**File**: `tests/integration/test_cli_run.py`

```python
# Test cases needed:
- Single award detection
- Award not found
- Multiple detections for one award
- No detections found
- Verbose output formatting
```

**Why**: Primary user-facing detection command.

#### 2.3 Analysis Command Tests
**File**: `tests/integration/test_cli_analysis.py`

```python
# Test cases needed:
- Statistics generation
- Transition perspectives
- Agency breakdown
- Confidence distribution
- Empty database handling
```

**Why**: Key insights feature for users.

### Priority 3: Robustness & Edge Cases (Ongoing)

#### 3.1 Configuration Validation
**File**: `tests/unit/config/test_validator.py`

```python
# Test cases needed:
- Valid config acceptance
- Invalid URL detection
- Missing required fields
- Type validation (int, float, bool)
- Nested config validation
```

#### 3.2 Pipeline Orchestration
**File**: `tests/unit/detection/test_pipeline.py`

```python
# Test cases needed:
- Pipeline stages execute in order
- Error handling at each stage
- Progress reporting
- Chunk processing with multiprocessing
- In-process mode for testing
```

#### 3.3 Evidence Formatting
**File**: `tests/unit/data/test_evidence.py`

```python
# Test cases needed:
- Evidence bundle structure
- Signal aggregation
- Source data inclusion
- JSON serialization
- Display formatting
```

---

## Test Patterns & Best Practices

### Database Test Pattern (Current Working Approach)

```python
@pytest.fixture(scope="function")
def test_db(tmp_path):
    """Isolated database for each test."""
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"
    
    # Create isolated engine
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool
    )
    
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestSession = sessionmaker(bind=engine)
    
    # Swap module references
    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    
    db_module.engine = engine
    db_module.SessionLocal = TestSession
    
    yield TestSession
    
    # Cleanup
    db_module.engine = original_engine
    db_module.SessionLocal = original_session
```

### CLI Test Pattern (Current Working Approach)

```python
from click.testing import CliRunner

def test_cli_command():
    """Test CLI command in isolated environment."""
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # Setup test data/DB
        setup_test_database()
        
        # Run command
        result = runner.invoke(
            cli_command,
            ['--option', 'value'],
            catch_exceptions=False  # See full tracebacks
        )
        
        # Assert
        assert result.exit_code == 0
        assert "expected output" in result.output
```

### CSV Fixture Pattern

```python
def write_test_csv(path: Path, rows: list):
    """Write test CSV with proper escaping."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# Usage in tests
def test_ingestion(tmp_path):
    csv_file = tmp_path / "data.csv"
    write_test_csv(csv_file, [
        ["Company", "Phase", "Agency", ...],
        ["Acme Corp", "Phase II", "Air Force", ...],
    ])
```

---

## Coverage Metrics & Goals

### Current Estimated Coverage
- **Unit Test Coverage**: ~15-20% of source modules
- **Integration Coverage**: ~5-10% of user workflows
- **Critical Path Coverage**: ~40% (main detection flow)

### Short-Term Goals (3 months)
- **Unit Test Coverage**: 50% of source modules
- **Integration Coverage**: 25% of user workflows  
- **Critical Path Coverage**: 80%
- **Focus**: Ingestion, detection heuristics, core CLI commands

### Long-Term Goals (6 months)
- **Unit Test Coverage**: 70%+ of source modules
- **Integration Coverage**: 50%+ of user workflows
- **Critical Path Coverage**: 95%+
- **Add**: Performance tests, load tests, property-based tests

---

## Testing Infrastructure Improvements

### 1. Test Data Management
**Current**: Inline CSV generation in each test  
**Proposed**: Shared fixture library

```python
# tests/fixtures/data_factory.py
class SbirAwardFactory:
    @staticmethod
    def create_minimal(**overrides):
        """Create minimal valid SBIR award."""
        defaults = {
            "Company": "Test Corp",
            "Phase": "Phase II",
            "Agency": "Air Force",
            ...
        }
        return {**defaults, **overrides}
    
    @staticmethod
    def create_csv(path: Path, count: int = 1, **overrides):
        """Write CSV with N awards."""
        ...
```

### 2. Assertion Helpers
**Proposed**: Domain-specific assertions

```python
# tests/helpers/assertions.py
def assert_valid_detection(detection):
    """Assert detection has required structure."""
    assert detection.likelihood_score >= 0.0
    assert detection.likelihood_score <= 1.0
    assert detection.confidence in ["High", "Likely Transition", "Low"]
    assert "source_sbir_award" in detection.evidence_bundle
    assert "source_contract" in detection.evidence_bundle

def assert_csv_structure(path: Path, required_columns: list):
    """Assert CSV has required columns."""
    df = pd.read_csv(path, nrows=1)
    assert all(col in df.columns for col in required_columns)
```

### 3. Performance Test Suite
**Proposed**: `tests/performance/`

```python
# tests/performance/test_ingestion_performance.py
def test_sbir_ingestion_scales(benchmark):
    """Benchmark SBIR ingestion with 10k records."""
    result = benchmark(ingest_sbir_awards, count=10000)
    assert result.stats['mean'] < 5.0  # seconds
```

### 4. Property-Based Testing
**Proposed**: Use `hypothesis` for edge case discovery

```python
from hypothesis import given, strategies as st

@given(
    piid=st.text(min_size=1, max_size=50),
    date=st.dates()
)
def test_contract_ingestion_accepts_valid_data(piid, date):
    """Fuzz test contract ingestion."""
    # Property: any valid piid/date should ingest without error
    ...
```

---

## Continuous Integration Enhancements

### Current CI Pipeline
```yaml
# .github/workflows/test.yml
- Run unit tests
- Run integration tests
- Basic success/failure reporting
```

### Proposed Enhancements

1. **Coverage Reporting**
   ```yaml
   - name: Generate coverage
     run: poetry run pytest --cov --cov-report=xml
   - name: Upload to Codecov
     uses: codecov/codecov-action@v3
   ```

2. **Test Categorization**
   ```yaml
   - name: Fast tests (< 1s each)
     run: poetry run pytest -m "not slow"
   - name: Slow tests
     run: poetry run pytest -m "slow"
   ```

3. **Failure Artifacts**
   ```yaml
   - name: Upload failure logs
     if: failure()
     uses: actions/upload-artifact@v3
     with:
       name: test-logs
       path: output/*.log
   ```

---

## Test Maintenance Guidelines

### When to Write Tests
1. **Before fixing a bug**: Write failing test, then fix
2. **Before refactoring**: Ensure behavior is captured
3. **For new features**: TDD approach when possible
4. **For CLI commands**: Integration test for happy path

### Test Naming Convention
```python
# Pattern: test_<component>_<behavior>_<condition>

def test_sbir_ingester_skips_duplicates_when_award_exists():
    """Test that duplicate awards are skipped during ingestion."""
    ...

def test_scoring_penalizes_late_contracts_after_threshold():
    """Test that contracts starting >6 months after SBIR get penalty."""
    ...
```

### Test Documentation
- **Docstring**: Explain WHAT is being tested
- **Comments**: Explain WHY (business logic, edge case rationale)
- **Assert messages**: Provide context for failures

```python
def test_contract_ingestion_validates_piid():
    """Test that contracts without PIID are rejected."""
    # PIID is required for matching to SBIR awards
    stats = ingester.ingest(csv_with_missing_piid)
    
    assert stats.rejection_reasons["missing_piid"] > 0, \
        "Expected records with missing PIID to be rejected"
```

---

## Action Items Summary

### Immediate (This Sprint)
- [ ] Add `tests/unit/ingestion/test_contract_ingester.py`
- [ ] Add `tests/unit/detection/test_heuristics.py`
- [ ] Add `tests/unit/detection/test_data_quality.py`
- [ ] Document test database fixture pattern

### Short-Term (Next 2 Sprints)
- [ ] Add export command tests
- [ ] Add run command tests
- [ ] Add config validation tests
- [ ] Set up coverage reporting in CI
- [ ] Create test data factory utilities

### Medium-Term (Next Quarter)
- [ ] Achieve 50% unit test coverage
- [ ] Test all user-facing CLI commands
- [ ] Add performance benchmarks
- [ ] Add property-based tests for ingestion
- [ ] Document testing best practices in CONTRIBUTING.md

### Long-Term (6 months)
- [ ] Achieve 70%+ overall coverage
- [ ] Full integration test suite for workflows
- [ ] Automated regression test suite
- [ ] Load testing for production scenarios

---

## Appendix: Test Coverage by File

### Legend

## Integration and E2E Testing

This section consolidates our end-to-end (E2E) testing guidance, superseding the standalone E2E_TEST_ASSESSMENT.md document.

Scope:
- Full CLI paths: data → ingestion → detection → export
- Database isolation using a temporary SQLite database per test
- Minimal, realistic CSV fixtures with correct headers and types
- Deterministic assertions that avoid flakiness

Patterns and best practices:
- Use click.testing.CliRunner with isolated_filesystem for end-to-end CLI tests.
- Swap sbir_transition_classifier.db.database.engine and SessionLocal to a test engine/session per test; restore originals in a finally block to ensure isolation.
- Prefer validating outputs by structure and schema over byte-for-byte equality:
  - JSONL: ensure each line is valid JSON and expected keys are present
  - CSV: validate headers, row counts, and sample rows rather than entire contents
- Use “in-process” or single-process execution flags for tests that would otherwise use multiprocessing to improve determinism and speed.
- Avoid network calls; seed any inputs locally and keep tests hermetic.

Performance notes:
- Keep E2E tests small and focused; large workflows belong in performance or integration suites with explicit markers.
- If timing-sensitive, assert within ranges or use summarized metrics printed by the CLI instead of exact durations.

Migration note:
- Content previously in docs/E2E_TEST_ASSESSMENT.md is merged here for a single authoritative testing guide.
- For historical details and rationale, see CHANGELOG.md (E2E testing consolidation entry).
- ✅ Good coverage (dedicated unit/integration tests)
- ⚠️ Partial coverage (tested indirectly)
- ❌ No coverage

| Module | Status | Notes |
|--------|--------|-------|
| `ingestion/sbir.py` | ✅ | Unit tests exist |
| `ingestion/contracts.py` | ❌ | **HIGH PRIORITY** |
| `ingestion/base.py` | ⚠️ | Tested via subclasses |
| `ingestion/factory.py` | ❌ | Needs tests |
| `detection/scoring.py` | ✅ | Unit tests exist |
| `detection/heuristics.py` | ⚠️ | **HIGH PRIORITY** - indirect only |
| `detection/main.py` | ⚠️ | Integration tests only |
| `detection/pipeline.py` | ❌ | Needs tests |
| `detection/data_quality.py` | ❌ | **HIGH PRIORITY** |
| `detection/local_service.py` | ❌ | Needs tests |
| `config/loader.py` | ✅ | Unit tests exist |
| `config/validator.py` | ❌ | Needs tests |
| `config/schema.py` | ⚠️ | Tested via loader |
| `cli/bulk.py` | ⚠️ | Integration test exists |
| `cli/run.py` | ❌ | **MEDIUM PRIORITY** |
| `cli/export.py` | ❌ | **MEDIUM PRIORITY** |
| `cli/analysis.py` | ❌ | Needs tests |
| `cli/*` (others) | ❌ | Low priority |
| `analysis/*` | ❌ | Low priority |
| `scripts/*` | ❌ | Low priority |
| `data/evidence.py` | ❌ | Needs tests |
| `data/hygiene.py` | ❌ | Low priority |

---

**Last Updated**: 2025-01-28  
**Next Review**: After Priority 1 tests are implemented