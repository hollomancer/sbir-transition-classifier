# SBIR Transition Classifier: Improvement Roadmap

**Executive Summary**  
This document provides a strategic roadmap for improving the SBIR Transition Classifier codebase through systematic testing improvements and code refactoring.

---

## Current State Assessment

### Codebase Metrics
- **Total Source Files:** 55 Python modules
- **Total Lines of Code:** ~11,000
- **Test Coverage:** Estimated 20-25%
- **CLI Commands:** 14 files (252 KB, 45% of codebase)
- **Test Files:** 10 (7 unit + 3 integration)

### Key Issues Identified
1. **Low test coverage** - Critical paths inadequately tested
2. **Code duplication** - CLI and scripts overlap significantly
3. **Unused code** - ~600 lines of unused/deprecated modules
4. **Configuration complexity** - 3+ overlapping config systems
5. **Unclear organization** - Confusing module boundaries

---

## Strategic Priorities

### Phase 1: Foundation & Quick Wins (Weeks 1-2)

**Goal:** Stabilize codebase and remove obvious problems

#### Testing Improvements
- [ ] Add `test_contract_ingester.py` (HIGH PRIORITY - we just fixed UUID bugs here)
- [ ] Add `test_heuristics.py` (core detection logic)
- [ ] Add `test_data_quality.py` (PIID/date validation)
- [ ] Document test patterns in `TESTING_STRATEGY.md` ✅ DONE

**Impact:** Protect critical code paths from regressions

#### Code Cleanup
- [ ] Delete `cli/analysis.py` (0 bytes, empty)
- [ ] Delete `cli/db.py` (0 bytes, empty)
- [ ] Delete `detection/local_service.py` (285 lines, unused)
- [ ] Remove `core/config.py` (deprecated) after updating `scripts/setup_local_db.py`

**Impact:** -600 lines, 4 fewer files, immediate clarity gain

**Effort:** 1 week  
**Risk:** Low  
**Dependencies:** None

---

### Phase 2: Export & Data Management (Weeks 3-4)

**Goal:** Consolidate duplicate functionality

#### Refactoring Tasks
- [ ] Merge `scripts/export_data.py` → `cli/export.py`
- [ ] Merge `scripts/load_bulk_data.py` → `cli/data.py`
- [ ] Merge `cli/hygiene.py` → `cli/data.py`
- [ ] Consolidate `data/hygiene.py` and `data/cleaning.py`

**Impact:** -300 lines, clearer command structure

#### Testing Tasks
- [ ] Add `test_cli_export.py` (JSONL, CSV formats)
- [ ] Add `test_cli_data.py` (load, clean, validate commands)
- [ ] Test edge cases (empty DB, large datasets, malformed data)

**Effort:** 2 weeks  
**Risk:** Medium (need good tests first)  
**Dependencies:** Phase 1 testing complete

---

### Phase 3: CLI Reorganization (Weeks 5-7)

**Goal:** Streamline user-facing commands

#### Refactoring Tasks
- [ ] Create unified `cli/reports.py` module
- [ ] Migrate `cli/summary.py` (445 lines)
- [ ] Migrate `cli/dual_report.py` (133 lines)
- [ ] Migrate `cli/evidence.py` (353 lines)
- [ ] Extract shared logic from `cli/output.py` (299 lines)
- [ ] Delete old report files

**Before:** 14 CLI files, 2,571 lines  
**After:** 8 CLI files, ~2,100 lines  
**Reduction:** 18% fewer lines, 43% fewer files

#### Testing Tasks
- [ ] Add `test_cli_reports.py` (comprehensive report testing)
- [ ] Add `test_cli_run.py` (single detection command)
- [ ] Integration tests for full workflows

**Breaking Changes:** CLI command restructure
```bash
# Before
sbir-detect summary
sbir-detect dual-report
sbir-detect evidence

# After
sbir-detect report summary
sbir-detect report dual
sbir-detect report evidence
```

**Effort:** 3 weeks  
**Risk:** Medium-High (user-facing changes)  
**Dependencies:** Phase 2 complete

---

### Phase 4: Detection Simplification (Weeks 8-9)

**Goal:** Single detection implementation path

#### Refactoring Tasks
- [ ] Analyze `cli/run.py` requirements
- [ ] Refactor to use `detection/main.py` instead of `pipeline.py`
- [ ] Add single-award mode to `run_full_detection()` if needed
- [ ] Delete `detection/pipeline.py` (300 lines)

**Before:**
- Two detection implementations (main.py + pipeline.py)
- Confusion about which to use
- 585 lines of detection code

**After:**
- Single detection path
- Clear architecture
- 285 lines of detection code

#### Testing Tasks
- [ ] Add `test_detection_pipeline.py` (orchestration tests)
- [ ] Test single-award vs bulk modes
- [ ] Performance benchmarks

**Effort:** 2 weeks  
**Risk:** Medium  
**Dependencies:** Good integration test coverage

---

### Phase 5: Configuration Consolidation (Week 10)

**Goal:** Single source of truth for configuration

#### Refactoring Tasks
- [ ] Merge `config/defaults.py` → `config/schema.py`
- [ ] Merge `config/validator.py` → `config/schema.py`
- [ ] Merge `db/config.py` → `config/loader.py`
- [ ] Move `config/reset.py` logic to `cli/reset.py`

**Before:** 7 config files across 2 directories  
**After:** 3 config files in single directory

#### Testing Tasks
- [ ] Add `test_config_validator.py`
- [ ] Test invalid configs, missing fields, type errors
- [ ] Test environment variable overrides

**Breaking Changes:** Import path updates
```python
# Before
from sbir_transition_classifier.db.config import get_database_config

# After
from sbir_transition_classifier.config import get_database_config
```

**Effort:** 1 week  
**Risk:** Low-Medium  
**Dependencies:** None (can be done in parallel)

---

### Phase 6: Data Module Cleanup (Week 11)

**Goal:** Clear module boundaries and naming

#### Refactoring Tasks
- [ ] Merge `data/models.py` → `data/schemas.py`
- [ ] Rename `data/local_loader.py` → `data/loader.py`
- [ ] Rename `data/hygiene.py` → `data/cleaning.py`

#### Testing Tasks
- [ ] Add `test_data_evidence.py` (evidence formatting)
- [ ] Add `test_data_schemas.py` (Pydantic validation)

**Effort:** 1 week  
**Risk:** Low  
**Dependencies:** Phase 2 complete

---

### Phase 7: Test Coverage Expansion (Weeks 12+)

**Goal:** Achieve 70%+ test coverage

#### Priority Areas
- [ ] Analysis modules (currently 0% coverage)
- [ ] All CLI commands (currently ~7% coverage)
- [ ] Edge cases and error handling
- [ ] Performance tests

#### Infrastructure
- [ ] Set up coverage reporting in CI
- [ ] Add property-based tests (hypothesis)
- [ ] Create test data factory utilities
- [ ] Add performance benchmarks

**Target Metrics:**
- Unit test coverage: 70%+
- Integration coverage: 50%+
- Critical path coverage: 95%+

**Effort:** Ongoing  
**Risk:** Low  
**Dependencies:** All refactoring phases complete

---

## Impact Summary

### Quantitative Improvements

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Test Coverage** | 20-25% | 70%+ | +50% |
| **Total Files** | 55 | ~42 | -24% |
| **Total Lines** | ~11,000 | ~8,500 | -23% |
| **CLI Files** | 14 | 8 | -43% |
| **Deprecated Code** | 600 lines | 0 | -100% |
| **Duplicate Code** | ~800 lines | ~200 | -75% |

### Qualitative Improvements

**Developer Experience:**
- ✅ Single detection implementation path
- ✅ Clear separation: CLI vs library code
- ✅ Obvious where to add new features
- ✅ Faster onboarding for new contributors
- ✅ Better IDE navigation and autocomplete

**Code Quality:**
- ✅ Less duplication (DRY principle)
- ✅ Better test coverage
- ✅ Clearer module responsibilities (SRP)
- ✅ Easier to navigate codebase
- ✅ Consistent patterns

**User Experience:**
- ✅ Consistent CLI command structure
- ✅ Predictable command naming
- ✅ Better help documentation
- ✅ Fewer breaking changes going forward

---

## Resource Requirements

### Time Investment
- **Total Duration:** 12+ weeks
- **Developer Hours:** 80-100 hours
- **Testing Hours:** 40-60 hours
- **Documentation:** 10-20 hours

### Team Allocation
- **Ideal:** 1 developer full-time for 3 months
- **Minimum:** 2 developers part-time (50% each) for 6 months

### Risk Mitigation
- Phased approach allows rollback
- Test coverage prevents regressions
- Gradual deprecation (not immediate breaking changes)
- Documentation updates alongside code changes

---

## Success Criteria

### Phase Completion Metrics

**Phase 1 Complete When:**
- [ ] Critical path tests passing
- [ ] Dead code removed
- [ ] No deprecated imports remain

**Phase 2 Complete When:**
- [ ] Single export implementation
- [ ] Single data management CLI
- [ ] Export tests at 80%+ coverage

**Phase 3 Complete When:**
- [ ] CLI commands consolidated
- [ ] All report functionality tested
- [ ] Migration guide published

**Phase 4 Complete When:**
- [ ] Single detection path
- [ ] All detection tests passing
- [ ] Performance benchmarks established

**Phase 5 Complete When:**
- [ ] Config imports simplified
- [ ] Config tests at 90%+ coverage
- [ ] Migration guide for API users

**Phase 6 Complete When:**
- [ ] Data module naming clear
- [ ] Schema tests comprehensive
- [ ] No import confusion

**Phase 7 Complete When:**
- [ ] 70%+ overall coverage
- [ ] CI coverage reporting active
- [ ] All critical paths tested

### Overall Success Indicators
- ✅ CI pipeline consistently green
- ✅ No increase in bug reports during refactoring
- ✅ Positive developer feedback
- ✅ Reduced time-to-fix for bugs
- ✅ Faster feature development velocity

---

## Risk Management

### High Risk Areas

**1. CLI Command Changes (Phase 3)**
- **Risk:** Breaking user workflows
- **Mitigation:** 
  - Deprecation warnings in v0.1.x
  - Maintain backwards compatibility for 1 release cycle
  - Clear migration guide
  - Announce in release notes

**2. Detection Logic Changes (Phase 4)**
- **Risk:** Altering detection behavior
- **Mitigation:**
  - Comprehensive integration tests before refactoring
  - Golden test fixtures (baseline results)
  - Verify identical output before/after refactor
  - Gradual rollout

**3. Configuration API Changes (Phase 5)**
- **Risk:** Breaking third-party integrations
- **Mitigation:**
  - Maintain compatibility layer for 1 version
  - Document all API changes
  - Provide codemod/migration script if needed

### Contingency Plans

**If tests reveal major issues:**
- Pause refactoring
- Fix underlying bugs first
- Re-evaluate scope

**If timeline slips:**
- Prioritize Phases 1-2 (highest value)
- Defer Phases 5-6 to future releases
- Keep Phase 7 ongoing

**If breaking changes cause user issues:**
- Hotfix release with compatibility shims
- Extend deprecation timeline
- Gather user feedback, adjust plan

---

## Communication Plan

### Internal Communication
- Weekly progress updates in team meetings
- Phase completion demos
- Documentation updates in PR descriptions
- Slack/email notifications for breaking changes

### External Communication
- **Pre-announcement:** "Upcoming improvements" blog post
- **During:** Deprecation warnings in code + docs
- **Release notes:** Detailed changelog for each phase
- **Migration guides:** Step-by-step upgrade instructions

### Documentation Updates
- [ ] Update CONTRIBUTING.md with new structure
- [ ] Update README.md with new CLI examples
- [ ] Create MIGRATION.md for v0.1 → v0.2
- [ ] Update API documentation (if exists)
- [ ] Record architecture decision records (ADRs)

---

## Monitoring & Measurement

### Metrics to Track

**Code Quality:**
- Lines of code (trending down)
- Cyclomatic complexity (trending down)
- Test coverage (trending up)
- Number of deprecated imports (→ 0)

**Developer Productivity:**
- Time to fix bugs (trending down)
- Time to add new features (trending down)
- PR review time (trending down)
- Onboarding time for new contributors (trending down)

**System Reliability:**
- CI build times (stable or improving)
- Test flakiness rate (trending down)
- Bug reports (stable or declining)
- User-reported issues (stable or declining)

### Review Cadence
- **Weekly:** Phase progress, blockers, adjustments
- **End of Phase:** Retrospective, lessons learned
- **Monthly:** Overall roadmap review, metric analysis
- **End of Project:** Final retrospective, documentation

---

## Appendix: Quick Reference

### Priority Order
1. **IMMEDIATE:** Delete empty/unused files (Phase 1)
2. **HIGH:** Add critical path tests (Phase 1)
3. **HIGH:** Consolidate exports and data commands (Phase 2)
4. **MEDIUM:** Reorganize CLI (Phase 3)
5. **MEDIUM:** Simplify detection (Phase 4)
6. **LOW:** Config consolidation (Phase 5)
7. **LOW:** Data module cleanup (Phase 6)
8. **ONGOING:** Expand test coverage (Phase 7)

### Key Documents
- `docs/TESTING_STRATEGY.md` - Detailed testing plan
- `docs/REFACTORING_PLAN.md` - Detailed refactoring specs
- `docs/IMPROVEMENT_ROADMAP.md` - This document
- `AGENTS.md` - Repository guidelines

### Stakeholder Contacts
- **Engineering Lead:** [Name]
- **Product Owner:** [Name]
- **DevOps/CI:** [Name]
- **Documentation:** [Name]

---

## Next Steps

### This Week
1. Review and approve this roadmap
2. Schedule kickoff meeting
3. Assign Phase 1 tasks
4. Create tracking board (GitHub Projects, Jira, etc.)

### This Month
- Complete Phase 1 (Foundation)
- Start Phase 2 (Export consolidation)
- Set up coverage reporting
- Begin documentation updates

### This Quarter
- Complete Phases 1-4
- Achieve 50%+ test coverage
- Release v0.2.0 with refactored code
- Gather user feedback

---

**Document Version:** 1.0  
**Created:** 2025-01-28  
**Authors:** Engineering Team  
**Status:** PROPOSED - Awaiting Approval  
**Next Review:** After stakeholder feedback