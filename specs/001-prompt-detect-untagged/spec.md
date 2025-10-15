# Feature Specification: Detect Untagged SBIR Phase III Transitions

**Feature Branch**: `001-prompt-detect-untagged`
**Created**: 2025-10-15
**Status**: Draft
**Input**: User description: "Prompt: Detect Untagged SBIR Phase III Transitions..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect High-Confidence Transitions (Priority: P1)

As a data-savvy policy analyst, I want the system to automatically detect likely SBIR transitions using structural data links, so I can identify commercialization that isn't captured by unreliable Phase III tags.

**Why this priority**: This is the core value proposition. It directly addresses the primary problem of unreliable Phase III tags by providing an alternative, data-driven method for identifying transitions.

**Independent Test**: Can be tested by running the detection algorithm on a sample of SBIR Phase II awards and verifying that it correctly identifies known transitions and proposes new, plausible ones based on structural evidence (e.g., a sole-source IDV from the same agency shortly after Phase II completion).

**Acceptance Scenarios**:

1.  **Given** a vendor has a Phase II award that completed within the last 24 months, **When** the system processes new contract data, **Then** it must detect a subsequent sole-source IDV awarded to the same vendor by the same agency and flag it as a "High Confidence" transition.
2.  **Given** a detected IDV anchor, **When** new orders are issued against that IDV, **Then** the system must correctly chain those orders to the original SBIR-linked vehicle and update total revenue metrics.
3.  **Given** a detected transition, **When** an analyst requests proof, **Then** the system must provide an evidence bundle containing the source fields, PIIDs, dates, and reason string for the detection.

---

### User Story 2 - Broaden Search to Include Competed and Cross-Service Transitions (Priority: P2)

As a policy analyst, I want the system to consider transitions that were competed or awarded by a different service branch, so that I can get a more complete picture of all transition pathways.

**Why this priority**: This expands the detection coverage beyond the most obvious cases, capturing a significant but harder-to-track segment of transitions and reflecting the complex reality of government procurement.

**Independent Test**: Can be tested by providing a known competed Phase III award or a cross-service award and verifying that the system correctly identifies it as a "Likely Transition" by using signals like department-level continuity and text-based links (e.g., SBIR topic codes in the description).

**Acceptance Scenarios**:

1.  **Given** a Phase II award from the Air Force, **When** the system finds a competed contract from a Department of the Navy office awarded to the same vendor, **Then** the system should evaluate it for transition potential based on other signals like NAICS code and description text.
2.  **Given** a contract that was competed, **When** its solicitation procedure is "Authorized by Statute" and it references an SBIR topic, **Then** the system must boost its transition likelihood score.

---

### User Story 3 - Access and Export Detection Data (Priority: P3)

As a policy analyst, I want to access the raw detection data via an API and export summary reports, so I can perform my own analysis and integrate the findings into other reports.

**Why this priority**: This enables the analyst to use the system's output flexibly and disseminate the findings, increasing the overall impact of the work.

**Independent Test**: Can be tested by hitting the API endpoints. A `POST` to `/detect` should trigger analysis, and a `GET` to `/evidence/{id}` should return a valid evidence bundle. The system should also generate consumable CSV and JSONL files.

**Acceptance Scenarios**:

1.  **Given** the system has completed a detection run, **When** I request the output, **Then** it must provide a JSONL file where each line is a detected transition with its full evidence bundle.
2.  **Given** the system has completed a detection run, **When** I request a summary, **Then** it must provide a CSV summary file aggregated by vendor, agency, and fiscal year.
3.  **Given** a detection ID, **When** I make a GET request to `/evidence/{id}`, **Then** the system must return the complete, auditable evidence bundle for that specific detection.

---

### Edge Cases

-   What happens when a company is acquired or changes its name/CAGE/UEI? The system should use crosswalk tables to maintain identity.
-   How does the system handle contract modifications? It must track modifications to see the full history and value of a contract vehicle.
-   How does the system avoid false positives from vendors who simply mention "SBIR" in their company description on a contract? It must require a structural link (e.g., temporal proximity, agency link) and not rely on text mentions alone.
-   What if a Phase II award has no subsequent contracts within the 24-month window? It is simply not flagged as a transition.

## Requirements *(mandatory)*

### Functional Requirements

-   **FR-001**: System MUST ingest and process contract data from USAspending and FPDS.
-   **FR-002**: System MUST ingest SBIR award metadata from SBIR.gov.
-   **FR-003**: System MUST identify Indefinite Delivery Vehicles (IDVs) like BOAs, BPAs, and IDIQs awarded to a vendor within a 1-24 month window after the vendor's Phase II award completion date.
-   **FR-004**: System MUST link all child orders to their parent IDV to track total revenue and duration.
-   **FR-005**: System MUST use vendor identifiers (UEI, DUNS, CAGE) to track entities and maintain alias tables for novations.
-   **FR-006**: System MUST analyze contract fields including PIID, Referenced-IDV PIID, agency/office codes, NAICS, PSC, and competition fields.
-   **FR-007**: System MUST calculate a `Transition Likelihood Score` (0-1) for potential transitions, blending rule-based heuristics and a simple gradient boosting model.
-   **FR-008**: System MUST classify transitions with a score ≥ 0.65 as "Likely Transition" and ≥ 0.80 as "High Confidence."
-   **FR-009**: System MUST generate a detailed, auditable evidence bundle for each detection, including source fields, values, and dates.
-   **FR-010**: System MUST provide a `POST /detect` API endpoint to initiate analysis for a firm or award.
-   **FR-011**: System MUST provide a `GET /evidence/{id}` API endpoint to retrieve a specific evidence bundle.
-   **FR-012**: System MUST output detections in a JSONL format.
-   **FR-013**: System MUST output summary reports in a CSV format, aggregated by vendor, agency, and Fiscal Year.

### Key Entities *(include if feature involves data)*

-   **SBIR Award**: Represents a Phase I or Phase II award. Key attributes: Vendor ID, Award Date, Completion Date, Agency, Topic.
-   **Contract Vehicle**: Represents a federal contract, primarily an IDV (BOA, BPA, IDIQ) but can be a standalone contract. Key attributes: PIID, Vendor ID, Agency/Office, Start Date, Referenced-IDV PIID, Competition details.
-   **Vendor**: A commercial entity receiving awards/contracts. Key attributes: UEI, DUNS, CAGE, and aliases.
-   **Detection**: The output of the system, representing a potential SBIR transition. Key attributes: Linked SBIR Award, Linked Contract Vehicle, Likelihood Score, Confidence Level, Evidence Bundle.
-   **Evidence Bundle**: An auditable collection of data supporting a detection. Key attributes: Reason String, Source Fields, Hashes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

-   **SC-001**: The system must achieve a precision of ≥85% for the top-K highest-scored detections during backtesting on FY20-FY24 data.
-   **SC-002**: The system must achieve a recall of ≥70% against a known set of tagged Phase III awards.
-   **SC-003**: A full backtest run for a single fiscal year's data must complete in under 8 hours.
-   **SC-004**: For 95% of API requests to `GET /evidence/{id}`, the response time must be under 500ms.