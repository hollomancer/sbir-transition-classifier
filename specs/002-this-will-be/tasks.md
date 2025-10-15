# Implementation Tasks: Local Analyst Configuration Mode

**Feature**: Local Analyst Configuration Mode  
**Branch**: `002-this-will-be`  
**Total Tasks**: 24  
**Estimated Effort**: 3-5 days

## Task Summary by User Story

- **Setup & Foundation**: 8 tasks
- **User Story 1 (P1)**: 8 tasks - Run Detection Locally
- **User Story 2 (P2)**: 5 tasks - Tune Classifier via YAML  
- **User Story 3 (P3)**: 3 tasks - Review Outputs Without API Calls

## Phase 1: Setup & Project Structure

**Goal**: Initialize project structure and dependencies for local execution mode

- [x] T001 Create config module directory structure in src/sbir_transition_classifier/config/
- [x] T002 Create CLI module directory structure in src/sbir_transition_classifier/cli/
- [x] T003 Create default YAML configuration files in config/default.yaml
- [x] T004 Create example configurations directory in config/examples/
- [x] T005 Add PyYAML and Click dependencies to pyproject.toml
- [x] T006 Create configuration validation test directory in tests/config/
- [x] T007 Update .gitignore to exclude local configuration overrides
- [x] T008 Create CLI entry point script in scripts/sbir-detect

## Phase 2: Foundation - Configuration Management (User Story 2 Prerequisites)

**Goal**: Core configuration loading and validation infrastructure

- [x] T009 [US2] Implement ConfigSchema Pydantic model in src/sbir_transition_classifier/config/schema.py
- [x] T010 [US2] Implement YAML configuration loader in src/sbir_transition_classifier/config/loader.py
- [x] T011 [US2] Implement configuration validator with error reporting in src/sbir_transition_classifier/config/validator.py
- [x] T012 [US2] Create default configuration template in src/sbir_transition_classifier/config/defaults.py
- [x] T013 [US2] Implement configuration reset functionality in src/sbir_transition_classifier/config/reset.py

## Phase 3: User Story 1 - Run Detection Locally (Priority P1)

**Goal**: Enable offline detection execution with local data processing

**Independent Test**: Follow quickstart guide on clean machine, verify detection completes with local data files

- [x] T014 [US1] Create DetectionSession model in src/sbir_transition_classifier/data/models.py
- [x] T015 [US1] Create EvidenceBundleArtifact model in src/sbir_transition_classifier/data/models.py
- [x] T016 [US1] Implement local database setup script in scripts/setup_local_db.py
- [x] T017 [US1] Create CLI run command in src/sbir_transition_classifier/cli/run.py
- [x] T018 [US1] Implement offline detection service in src/sbir_transition_classifier/detection/local_service.py
- [x] T019 [US1] Create local data loader in src/sbir_transition_classifier/data/local_loader.py
- [x] T020 [US1] Implement output file generation in src/sbir_transition_classifier/cli/output.py
- [x] T021 [US1] Create main CLI application in src/sbir_transition_classifier/cli/main.py

## Phase 4: User Story 2 - Tune Classifier via YAML (Priority P2)

**Goal**: Enable parameter customization through YAML configuration

**Independent Test**: Edit YAML parameters, rerun detection, verify new settings affect scores

- [x] T022 [US2] Create CLI validate-config command in src/sbir_transition_classifier/cli/validate.py
- [x] T023 [US2] Create CLI reset-config command in src/sbir_transition_classifier/cli/reset.py
- [x] T024 [US2] Integrate configuration parameters into detection scoring in src/sbir_transition_classifier/detection/scoring.py
- [x] T025 [US2] Implement configuration-aware detection pipeline in src/sbir_transition_classifier/detection/pipeline.py
- [x] T026 [US2] Add configuration validation to run command in src/sbir_transition_classifier/cli/run.py

## Phase 5: User Story 3 - Review Outputs Without API Calls (Priority P3)

**Goal**: Generate comprehensive local evidence files for offline review

**Independent Test**: Run detection with network disabled, verify all evidence accessible in local files

- [x] T027 [US3] Implement evidence bundle generator in src/sbir_transition_classifier/data/evidence.py
- [x] T028 [US3] Create local file-based evidence viewer in src/sbir_transition_classifier/cli/evidence.py
- [x] T029 [US3] Generate human-readable summary reports in src/sbir_transition_classifier/cli/summary.py

## Dependencies & Execution Order

### Story Dependencies
- **User Story 1**: Independent (can start after Foundation)
- **User Story 2**: Partially dependent on US1 (needs detection pipeline)
- **User Story 3**: Dependent on US1 (needs detection results)

### Recommended Execution Order
1. **Phase 1**: Setup (all tasks can run in parallel)
2. **Phase 2**: Foundation (T009-T013 can run in parallel)
3. **Phase 3**: User Story 1 (T014-T016 parallel, then T017-T021 sequential)
4. **Phase 4**: User Story 2 (T022-T023 parallel, T024-T026 sequential)
5. **Phase 5**: User Story 3 (T027-T029 can run in parallel)

### Parallel Execution Opportunities

**Phase 1 (All Parallel)**:
- T001-T008: Directory structure and dependency setup

**Phase 2 (All Parallel)**:
- T009-T013: Configuration management components

**Phase 3 (Mixed)**:
- Parallel: T014-T016 (data models and setup)
- Sequential: T017→T018→T019→T020→T021 (CLI and services)

**Phase 4 (Mixed)**:
- Parallel: T022-T023 (CLI commands)
- Sequential: T024→T025→T026 (integration with detection)

**Phase 5 (All Parallel)**:
- T027-T029: Evidence and reporting components

## Implementation Strategy

### MVP Scope (Recommended First Iteration)
- **Phase 1**: Complete setup
- **Phase 2**: Basic configuration loading
- **Phase 3**: User Story 1 only (local detection execution)

This provides a working local detection system that can be validated before adding configuration customization and enhanced reporting.

### Incremental Delivery Plan
1. **Week 1**: MVP (Phases 1-3) - Basic local execution
2. **Week 2**: User Story 2 - YAML configuration tuning
3. **Week 3**: User Story 3 - Enhanced offline reporting

### Validation Checkpoints
- **After Phase 3**: Verify local detection runs complete successfully
- **After Phase 4**: Verify configuration changes affect detection results
- **After Phase 5**: Verify all evidence accessible without network access

## Success Metrics
- **SC-001**: 90% of analysts complete setup in <30 minutes
- **SC-002**: 100% of classifier parameters configurable via YAML
- **SC-003**: Detection works in network-restricted environment
- **SC-004**: Clear error messages for all YAML validation failures
