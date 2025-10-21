# Tasks: Detect Untagged SBIR Phase III Transitions

**Input**: Design documents from `/specs/001-prompt-detect-untagged/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No tests were explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Paths shown below assume single project structure from `plan.md`.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure.

- [x] T001 Create the project directory structure outlined in `plan.md` inside the `src/` directory.
- [x] T002 Create a `pyproject.toml` file and add main dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `pandas`, `dask`, `xgboost`, `scikit-learn`.
- [x] T003 [P] Create a `docker-compose.yml` file to define the `api` service (running the FastAPI app) and a `postgres` service.
- [x] T004 [P] Create a `.gitignore` file with standard Python and environment ignores.
- [x] T005 [P] Implement basic application settings management in `src/sbir_transition_classifier/core/config.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [x] T006 Implement the SQLAlchemy database connection and session management in `src/sbir_transition_classifier/db/database.py`.
- [x] T007 [P] Define the SQLAlchemy ORM models for `vendors`, `vendor_identifiers`, `sbir_awards`, `contracts`, and `detections` in `src/sbir_transition_classifier/core/models.py` based on `data-model.md`.
- [x] T008 [P] Define Pydantic schemas for data validation and serialization in `src/sbir_transition_classifier/data/schemas.py`.
- [x] T009 Implement the initial data ingestion logic in `scripts/load_bulk_data.py` to parse `award_data.csv` and USAspending CSVs and populate the PostgreSQL database using the ORM models. This script should handle large files efficiently, possibly using Dask.

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Detect High-Confidence Transitions (Priority: P1) 🎯 MVP

**Goal**: Implement the core logic to detect likely, untagged SBIR transitions using strong structural signals like sole-source contracts.

**Independent Test**: Run the detection script against the ingested data. Verify that it creates `detections` in the database for known sole-source IDVs that follow a Phase II award within the 24-month window.

### Implementation for User Story 1

- [x] T010 [US1] Implement the core query to find candidate contract vehicles that were awarded to a vendor within 24 months of a Phase II completion in `src/sbir_transition_classifier/detection/heuristics.py`.
- [x] T011 [US1] Implement the logic to identify "High Confidence" signals (e.g., "same service" and "sole-source") in `src/sbir_transition_classifier/detection/heuristics.py`.
- [x] T012 [US1] Implement the initial scoring logic in `src/sbir_transition_classifier/detection/scoring.py` that assigns a high score (e.g., >0.8) based on the high-confidence heuristics.
- [x] T013 [US1] Create a main detection script or service that orchestrates the process: query candidates, apply heuristics, score, and save results to the `detections` table.

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Broaden Search to Include Competed and Cross-Service Transitions (Priority: P2)

**Goal**: Enhance the detection logic to find transitions that are competed or occur across different service branches.

**Independent Test**: Run the detection script on data containing known competed or cross-service transitions. Verify the system correctly flags them as "Likely Transition" and that the evidence bundle cites the correct reasoning.

### Implementation for User Story 2

- [x] T014 [US2] Extend the query in `src/sbir_transition_classifier/detection/heuristics.py` to include department-level continuity checks.
- [x] T015 [US2] Add logic to `src/sbir_transition_classifier/detection/heuristics.py` to analyze competition fields and boost scores for signals like "Authorized by Statute".
- [x] T016 [US2] [P] Add text-based analysis features (e.g., checking for "SBIR" or topic codes in descriptions) to the heuristics module.
- [x] T017 [US2] Update the model in `src/sbir_transition_classifier/detection/scoring.py` to a simple gradient boosting model (XGBoost) that incorporates the new heuristics from this user story.
- [x] T018 [US2] Re-train and evaluate the scoring model with the new features.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work.

---

## Phase 5: User Story 3 - Access and Export Detection Data (Priority: P3)

**Goal**: Expose the detection findings through a REST API and file exports.

**Independent Test**: Start the API server. Use `curl` to hit the `POST /detect` endpoint and receive a task ID. Use `curl` with a known detection ID on `GET /evidence/{id}` and verify the correct evidence bundle is returned.

### Implementation for User Story 3

- [x] T019 [US3] Create the main FastAPI application in `src/sbir_transition_classifier/api/main.py`.
- [x] T020 [US3] Implement the `POST /detect` endpoint in `src/sbir_transition_classifier/api/main.py`. This should trigger the detection process as a background task.
- [x] T021 [US3] Implement the `GET /evidence/{id}` endpoint in `src/sbir_transition_classifier/api/main.py` to query the database and return a detection's evidence bundle.
- [x] T022 [US3] [P] Implement a function to export all detections to a JSONL file as described in the spec.
- [x] T023 [US3] [P] Implement a function to generate and export the CSV summary report as described in the spec.

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [x] T024 [P] Add structured logging (e.g., using `loguru`) throughout the application.
- [x] T025 [P] Add comprehensive error handling and validation to the API endpoints.
- [x] T026 [P] Create a `README.md` at the project root with setup and usage instructions, referencing `quickstart.md`.
- [x] T027 [P] Add integration tests in `tests/integration/` to cover the main data ingestion and detection flow.
- [x] T028 Run all validation steps in `quickstart.md` to ensure the project is runnable.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. BLOCKS all user stories.
- **User Stories (Phase 3-5)**: Depend on Foundational completion.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2).
- **User Story 2 (P2)**: Depends on User Story 1, as it extends the same logic.
- **User Story 3 (P3)**: Can start after User Story 1, as it needs detections to expose.

### Parallel Opportunities

- **Setup**: T003, T004, T005 can run in parallel.
- **Foundational**: T007, T008 can run in parallel after T006.
- **User Stories**: Once the foundational data model and ingestion are done, work on the API (US3) and the core detection logic (US1) could begin in parallel, but the API would have no data to serve until US1 is at least partially complete.
- **Polish**: All polish tasks can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test that the core detection logic correctly identifies high-confidence transitions.

### Incremental Delivery

1. Complete Setup + Foundational.
2. Add User Story 1 → MVP is ready.
3. Add User Story 2 → Detection capabilities are enhanced.
4. Add User Story 3 → Data is now accessible via API.
5. Complete Polish phase.
