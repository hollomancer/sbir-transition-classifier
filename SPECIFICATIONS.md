# SBIR Transition Classifier - Feature Specifications

This document consolidates all feature specifications previously defined in the specs system.

## Core Feature: Detect Untagged SBIR Phase III Transitions

### Overview
The primary feature is to detect untagged SBIR Phase III transitions by analyzing federal spending data and identifying potential commercialization patterns using a combination of heuristics and machine learning.

### User Stories & Requirements

#### **User Story 1: Detect High-Confidence Transitions (Priority P1)**
As a data-savvy policy analyst, I want the system to automatically detect likely SBIR transitions using structural data links, so I can identify commercialization that isn't captured by unreliable Phase III tags.

**Acceptance Criteria:**
1. System detects subsequent sole-source IDV awarded to same vendor by same agency within 24 months of Phase II completion
2. System correctly chains child orders to parent IDV and updates total revenue metrics
3. System provides complete auditable evidence bundle for each detection

#### **User Story 2: Broaden Search Coverage (Priority P2)**
As a policy analyst, I want the system to consider transitions that were competed or awarded by different service branches for a more complete picture of transition pathways.

**Acceptance Criteria:**
1. System evaluates cross-service transitions based on department continuity and text analysis
2. System boosts scores for competed contracts with SBIR indicators (e.g., "Authorized by Statute")
3. System uses NAICS codes and description text for transition likelihood assessment

#### **User Story 3: Access and Export Detection Data (Priority P3)**
As a policy analyst, I want to access raw detection data and export summary reports for further analysis and integration into other reports.

**Acceptance Criteria:**
1. System provides JSONL file with complete evidence bundles for each detection
2. System generates CSV summary aggregated by vendor, agency, and fiscal year
3. System provides API endpoints for retrieving specific evidence bundles

### Functional Requirements

#### Data Ingestion & Processing
- **FR-001**: System MUST ingest and process contract data from USAspending and FPDS using batch processing with configurable chunk sizes (10K-100K records)
- **FR-002**: System MUST ingest SBIR award metadata from SBIR.gov
- **FR-005**: System MUST use vendor identifiers (UEI, DUNS, CAGE) to track entities and maintain alias tables for novations

#### Detection Logic
- **FR-003**: System MUST identify Indefinite Delivery Vehicles (IDVs) like BOAs, BPAs, and IDIQs awarded within 1-24 month window after Phase II completion
- **FR-004**: System MUST link all child orders to their parent IDV to track total revenue and duration
- **FR-006**: System MUST analyze contract fields including PIID, Referenced-IDV PIID, agency/office codes, NAICS, PSC, and competition fields
- **FR-007**: System MUST calculate Transition Likelihood Score (0-1) blending rule-based heuristics and gradient boosting model with quarterly retraining
- **FR-008**: System MUST classify transitions with score ≥0.65 as "Likely Transition" and ≥0.80 as "High Confidence"

#### Output & Reporting
- **FR-009**: System MUST generate detailed, auditable evidence bundle for each detection
- **FR-010**: System MUST provide `POST /detect` API endpoint to initiate analysis
- **FR-011**: System MUST provide `GET /evidence/{id}` API endpoint to retrieve evidence bundles
- **FR-012**: System MUST output detections in JSONL format
- **FR-013**: System MUST output summary reports in CSV format, aggregated by vendor, agency, and fiscal year

#### Quality & Feedback
- **FR-014**: System MUST provide manual review queue for analysts to validate detections
- **FR-015**: System MUST track analyst feedback to retrain and improve detection accuracy
- **FR-017**: System MUST retrain gradient boosting model quarterly to capture seasonal patterns

### Data Model

#### Core Entities
- **vendors**: Commercial entities receiving awards/contracts
  - `id` (UUID), `name` (TEXT), `created_at` (TIMESTAMP), `updated_at` (TIMESTAMP)

- **vendor_identifiers**: Cross-walking between ID systems (UEI, CAGE, DUNS)
  - `id` (UUID), `vendor_id` (FK), `identifier_type` (TEXT), `identifier_value` (TEXT), `created_at` (TIMESTAMP)

- **sbir_awards**: SBIR Phase I and II awards
  - `id` (UUID), `vendor_id` (FK), `award_piid` (TEXT), `phase` (TEXT), `agency` (TEXT), `award_date` (DATE), `completion_date` (DATE), `topic` (TEXT), `raw_data` (JSONB)

- **contracts**: Federal contract vehicles from FPDS/USAspending  
  - `id` (UUID), `vendor_id` (FK), `piid` (TEXT), `parent_piid` (TEXT), `agency` (TEXT), `start_date` (DATE), `naics_code` (TEXT), `psc_code` (TEXT), `competition_details` (JSONB), `raw_data` (JSONB)

- **detections**: Identified potential transitions with evidence
  - `id` (UUID), `sbir_award_id` (FK), `contract_id` (FK), `likelihood_score` (FLOAT), `confidence` (TEXT), `evidence_bundle` (JSONB), `detection_date` (TIMESTAMP)

### Success Criteria
- **SC-001**: System achieves ≥85% precision for top-K highest-scored detections during backtesting on FY20-FY24 data
- **SC-002**: System achieves ≥70% recall against known set of tagged Phase III awards
- **SC-003**: Full backtest run for single fiscal year completes in under 8 hours
- **SC-004**: 95% of API requests to `GET /evidence/{id}` respond in under 500ms

## Secondary Features

### Feature 2: Local Analyst Configuration Mode

#### Overview
Enable local execution without shared services, with all classifier parameters exposed in YAML for easy user tweaking.

#### Key Requirements
- **FR-001**: Single-machine setup process without requiring remote services
- **FR-002**: Execute detection runs entirely offline once local datasets are present  
- **FR-003**: Expose all classifier parameters in human-readable YAML file
- **FR-004**: Load and apply YAML configuration at start of each run
- **FR-005**: Validate YAML keys and value ranges with descriptive errors
- **FR-006**: Support multiple configuration presets via specified YAML files
- **FR-007**: Generate results as local artifacts without requiring API endpoints
- **FR-008**: Provide recovery option to revert to default YAML configuration

#### Success Criteria
- 90% of analysts complete local setup and run detection in under 30 minutes
- 100% of classifier parameters are adjustable via YAML and take effect immediately
- Detection workflows complete successfully in network-restricted environment
- System provides specific error guidance for invalid YAML values

### Feature 3: Export Format Migration (JSONL to YAML)

#### Overview
Migrate primary export format from JSONL to YAML for better human readability while maintaining backward compatibility.

#### Key Requirements
- **FR-001**: Export detection results in valid YAML format by default
- **FR-002**: Maintain JSONL export capability for backward compatibility
- **FR-003**: Allow format specification via command-line flag (--format yaml|jsonl)
- **FR-004**: Preserve all existing data fields when converting formats
- **FR-005**: Validate YAML output for syntax correctness before writing
- **FR-006**: Handle large datasets (10,000+ records) without memory overflow
- **FR-010**: Allow setting default export format via environment variable or config file

#### Success Criteria
- All detection data exports successfully to valid YAML without data loss
- YAML export performance within 20% of current JSONL export time
- 100% of existing JSONL functionality remains available in compatibility mode
- System handles datasets up to 50,000 detection records without memory issues

## Implementation Notes

### Detection Algorithms
1. **High-Confidence Signals**: Same agency, sole-source, 24-month timing, topic continuity
2. **Likely Transition Signals**: Cross-service transitions, competed contracts with SBIR indicators, department-level continuity
3. **Text Analysis**: Description similarity, topic matching, keyword analysis
4. **Machine Learning**: Gradient boosting model with quarterly retraining cycles

### Edge Cases & Considerations
- Company acquisitions and name/identifier changes (use crosswalk tables)
- Contract modifications tracking for complete history
- False positive prevention (require structural links, not just text mentions)
- Missing subsequent contracts within 24-month window (no transition flagged)
- YAML serialization failures with complex nested structures
- Large dataset handling without memory overflow
- Network-restricted environments for local deployment

### API Design
- `POST /detect` - Initiate analysis (returns task ID)
- `GET /evidence/{id}` - Retrieve evidence bundle for specific detection
- No authentication required for local deployment
- All endpoints must respond within 500ms for 95% of requests

This specification defines a comprehensive SBIR transition detection system with flexible configuration, multiple export formats, and both local and API-based operation modes.