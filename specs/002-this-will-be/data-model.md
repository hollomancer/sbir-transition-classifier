# Data Model: Local Analyst Configuration Mode

**Date**: 2025-10-15  
**Feature**: Local execution with YAML configuration

## New Entities

### Local Configuration Profile

**Purpose**: Represents YAML configuration file with classifier parameters

**Fields**:
- `config_path`: str - Absolute path to YAML file
- `version`: str - Configuration schema version
- `created_at`: datetime - File creation timestamp
- `modified_at`: datetime - Last modification timestamp
- `checksum`: str - SHA256 hash for integrity verification

**Validation Rules**:
- config_path must exist and be readable
- version must match supported schema versions
- All threshold values must be between 0.0 and 1.0
- Weight values must be non-negative
- Feature flags must be boolean

**State Transitions**:
- Created → Validated → Active
- Active → Modified → Validated
- Any state → Invalid (on validation failure)

### Detection Session

**Purpose**: Represents single offline detection run with metadata

**Fields**:
- `session_id`: UUID - Unique identifier
- `config_used`: str - Path to configuration file used
- `config_checksum`: str - Hash of config at runtime
- `input_datasets`: List[str] - Paths to input data files
- `start_time`: datetime - Execution start
- `end_time`: datetime - Execution completion
- `status`: enum - RUNNING, COMPLETED, FAILED, CANCELLED
- `output_path`: str - Directory containing results
- `detection_count`: int - Number of detections found
- `error_message`: Optional[str] - Failure details if applicable

**Validation Rules**:
- session_id must be unique
- config_used must reference valid configuration
- input_datasets must all exist and be readable
- output_path must be writable
- status transitions must follow valid sequence

**Relationships**:
- References Local Configuration Profile via config_used
- Contains multiple Evidence Bundle Artifacts

### Evidence Bundle Artifact

**Purpose**: Locally stored evidence files for analyst review

**Fields**:
- `bundle_id`: UUID - Unique identifier
- `session_id`: UUID - Parent detection session
- `detection_id`: UUID - Links to detection record
- `file_path`: str - Path to evidence JSON file
- `summary_path`: str - Path to human-readable summary
- `created_at`: datetime - Bundle generation time
- `file_size`: int - Size in bytes
- `evidence_type`: enum - HIGH_CONFIDENCE, LIKELY_TRANSITION, CROSS_SERVICE

**Validation Rules**:
- bundle_id must be unique
- file_path and summary_path must exist
- session_id must reference valid Detection Session
- evidence_type must match detection classification

**Relationships**:
- Belongs to Detection Session
- References existing detection record
- Contains file artifacts on disk

## Modified Entities

### Detection (existing)

**New Fields Added**:
- `config_version`: str - Version of config used for this detection
- `local_session_id`: Optional[UUID] - Links to Detection Session if run locally

**Modified Validation**:
- Must validate against configuration schema used
- Score calculations must use configured weights and thresholds

## Configuration Schema

### DetectionConfig

**Structure**:
```yaml
schema_version: "1.0"
detection:
  thresholds:
    high_confidence: float (0.0-1.0)
    likely_transition: float (0.0-1.0)
  weights:
    sole_source_bonus: float (>=0.0)
    timing_weight: float (>=0.0)
    agency_continuity: float (>=0.0)
    text_similarity: float (>=0.0)
  features:
    enable_cross_service: boolean
    enable_text_analysis: boolean
    enable_competed_contracts: boolean
  timing:
    max_months_after_phase2: int (1-60)
    min_months_after_phase2: int (0-12)
output:
  formats: List[str] # ["jsonl", "csv", "excel"]
  include_evidence: boolean
  evidence_detail_level: str # "summary" | "full"
```

**Validation Rules**:
- schema_version must be supported
- All threshold values 0.0 ≤ value ≤ 1.0
- All weight values ≥ 0.0
- timing.min_months_after_phase2 < timing.max_months_after_phase2
- output.formats must contain valid format strings
- evidence_detail_level must be "summary" or "full"
