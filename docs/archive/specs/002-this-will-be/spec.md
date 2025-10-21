# Feature Specification: Local Analyst Configuration Mode

**Feature Branch**: `002-this-will-be`  
**Created**: 2025-10-15  
**Status**: Draft  
**Input**: User description: "This will be run locally, it's not a multi-user application, and folks won't be pulling API data from this app. All classifier parameters should be exposed in YAML for easy user tweaking."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Detection Locally (Priority: P1)

As a policy analyst working on a single workstation, I want to install and execute the detection workflow locally so I can produce SBIR transition findings without standing up shared services.

**Why this priority**: Local execution ensures analysts can operate independently of enterprise infrastructure, which is essential for adoption in secure or resource-limited settings.

**Independent Test**: Can be fully tested by following the local setup guide on a clean machine and verifying that a detection run completes using only local data files.

**Acceptance Scenarios**:

1. **Given** a workstation with the documented prerequisites, **When** the analyst follows the local setup steps, **Then** the detection workflow installs and initializes without requiring remote services.
2. **Given** local SBIR and contract datasets, **When** the analyst triggers a detection run, **Then** the system processes the data offline and produces JSONL and CSV outputs.

---

### User Story 2 - Tune Classifier via YAML (Priority: P2)

As the same analyst, I want every classifier threshold, weight, and feature flag exposed in a YAML file so I can adjust detection sensitivity without editing source code.

**Why this priority**: Editable configuration removes the need for engineering support when analysts experiment with scoring logic, accelerating iteration.

**Independent Test**: Can be tested by updating YAML parameters, rerunning detection, and confirming the new settings change scores as expected.

**Acceptance Scenarios**:

1. **Given** the default YAML configuration, **When** the analyst edits a threshold value, **Then** the next detection run reflects the new threshold in its scoring output.
2. **Given** an invalid YAML value, **When** the analyst launches a run, **Then** the system stops with an error message naming the problematic key and accepted range.

---

### User Story 3 - Review Outputs Without API Calls (Priority: P3)

As the analyst, I want to review detection evidence directly from local files and reports so I never need to query a live API.

**Why this priority**: Removing network dependencies aligns with the single-user deployment goal and simplifies auditing.

**Independent Test**: Can be tested by running the reporting workflow with network access disabled and verifying that evidence bundles are accessible through generated files.

**Acceptance Scenarios**:

1. **Given** a completed detection run, **When** the analyst opens the generated evidence bundle, **Then** all supporting details are available in locally stored artifacts.
2. **Given** a machine without outbound network access, **When** the analyst repeats the detection process, **Then** all steps succeed because no API calls are required.

---

### Edge Cases

- What happens when the YAML configuration file is missing or renamed? The system should regenerate or prompt the user to select a configuration before proceeding.
- How does the system handle malformed YAML syntax? It should halt gracefully with guidance on the nearest line and key.
- What if required local data files are absent or outdated? The workflow should flag the missing inputs and point to the documentation for sourcing them.
- How does the system protect default settings from accidental overwrite? Provide a command to restore defaults without reinstalling.

## Assumptions

- Analysts have local copies of SBIR award and contract datasets before running detection.
- Users have permission to install required runtimes and write to the project directories on their machines.
- Quarterly model retraining still happens, but updated model files are distributed separately from this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a documented single-machine setup process that installs dependencies, initializes the database, and prepares sample data without requiring remote services.
- **FR-002**: System MUST execute detection runs entirely offline once local datasets and configuration files are present.
- **FR-003**: System MUST expose all classifier parameters (weights, thresholds, feature toggles, retraining intervals) in a human-readable YAML file stored within the project.
- **FR-004**: System MUST load the YAML configuration at the start of each run and apply every parameter to the detection logic before processing data.
- **FR-005**: System MUST validate YAML keys and value ranges, halting execution with descriptive errors that reference the offending key and acceptable values.
- **FR-006**: System MUST offer a documented command that triggers detection using a specified YAML file so analysts can maintain multiple configuration presets.
- **FR-007**: System MUST generate detection results, evidence bundles, and summaries as local artifacts that analysts can open without invoking API endpoints.
- **FR-008**: System MUST provide a recovery option that reverts the YAML configuration to the shipped defaults without reinstalling the application.

### Key Entities *(include if feature involves data)*

- **Local Configuration Profile**: Represents the YAML file containing classifier parameters, including metadata about version and last modified timestamp.
- **Detection Session**: Represents a single offline run, capturing the configuration used, input datasets, execution time, and generated outputs.
- **Evidence Bundle Artifact**: Represents the locally stored evidence files analysts review, including score explanations and linked contract identifiers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of first-time analysts can complete the documented local setup and run a detection session in under 30 minutes on a clean workstation.
- **SC-002**: 100% of classifier parameters referenced in the detection logic are adjustable via the YAML file and take effect on the very next run without code changes.
- **SC-003**: Detection and reporting workflows complete successfully in a network-restricted test environment with zero external API calls.
- **SC-004**: In validation tests with intentionally invalid YAML values, the system provides specific error guidance for every failure case without generating stack traces.
