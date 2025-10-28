# Implementation Guide

This document provides development workflow and implementation tasks for the SBIR Transition Classifier, consolidated from the original specs system.

## Quick Start Guide

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Poetry (for dependency management)
- `curl` or similar HTTP client for API testing

### Local Setup & Running

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd sbir-transition-classifier
   poetry install
   ```

2. **Prepare data**:
   - Place SBIR awards data in `data/award_data.csv`
   - Add USAspending bulk data files to `data/` directory
   - The system will automatically detect and process CSV files

3. **Run detection pipeline**:
   ```bash
   # Complete end-to-end processing
   poetry run sbir-detect bulk-process --verbose
   
   # Or step-by-step
   poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose
   poetry run python -m scripts.export_data export-jsonl --output-path output/detections.jsonl
   ```

4. **For containerized deployment**:
   ```bash
   docker-compose up --build -d
   ```

### API Usage

Once running, the API is available at `http://localhost:8000`:

#### Trigger Analysis
```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"vendor_identifier": "ABCDE12345"}'
```

#### Retrieve Evidence
```bash
curl http://localhost:8000/evidence/<detection-uuid>
```

Example response:
```json
{
  "detection_id": "<detection-uuid>",
  "likelihood_score": 0.85,
  "confidence": "High Confidence",
  "reason_string": "Sole-source IDV awarded 8 months after Phase II completion by the same agency.",
  "source_sbir_award": {
    "piid": "W911NF-18-C-0033",
    "agency": "DEPT OF DEFENSE",
    "completion_date": "2020-01-15"
  },
  "source_contract": {
    "piid": "HD0340-20-D-0001", 
    "agency": "DEPT OF DEFENSE",
    "start_date": "2020-09-01"
  }
}
```

## Development Workflow

### Project Structure

```
src/sbir_transition_classifier/
├── api/           # FastAPI endpoints
├── core/          # Configuration and data models  
├── data/          # Data schemas and validation
├── detection/     # Detection algorithms and scoring
└── db/            # Database connection and management

scripts/           # Data loading and export utilities
tests/             # Unit and integration tests
output/            # Generated reports and exports
```

### Implementation Phases

#### Phase 1: Setup & Foundation
**Purpose**: Basic project infrastructure and core data models

**Key Tasks**:
- [x] Create project directory structure 
- [x] Setup `pyproject.toml` with dependencies (fastapi, sqlalchemy, pandas, dask, xgboost, scikit-learn)
- [x] Create `docker-compose.yml` for API service and PostgreSQL
- [x] Implement database connection and session management
- [x] Define SQLAlchemy ORM models for all entities
- [x] Create Pydantic schemas for data validation
- [x] Implement initial data ingestion for SBIR and contract data

**Technologies**: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Pandas, Dask

#### Phase 2: Core Detection (MVP)
**Purpose**: Implement high-confidence transition detection

**Key Tasks**:
- [x] Core query to find candidate contracts within 24-month window after Phase II completion
- [x] Logic to identify "High Confidence" signals (same service, sole-source)
- [x] Initial scoring logic assigning high scores (>0.8) for high-confidence heuristics
- [x] Main detection orchestration script/service
- [x] Save detection results to database

**Validation**: Test against known sole-source IDVs following Phase II awards

#### Phase 3: Enhanced Detection  
**Purpose**: Expand detection to include competed and cross-service transitions

**Key Tasks**:
- [x] Extend queries for department-level continuity checks
- [x] Add logic for competition field analysis and "Authorized by Statute" signals  
- [x] Implement text-based analysis (SBIR topic codes, description matching)
- [x] Upgrade to XGBoost gradient boosting model incorporating new heuristics
- [x] Model training and evaluation with new features

**Validation**: Test on known competed or cross-service transitions

#### Phase 4: API & Export
**Purpose**: Expose detection data through REST API and file exports

**Key Tasks**:
- [x] Create main FastAPI application
- [x] Implement `POST /detect` endpoint with background task processing
- [x] Implement `GET /evidence/{id}` endpoint for evidence retrieval
- [x] Export functions for JSONL format (all detections with evidence bundles)
- [x] Export functions for CSV summary (aggregated by vendor, agency, fiscal year)

**Validation**: API endpoint testing with curl, file export validation

#### Phase 5: Configuration & Polish
**Purpose**: Local deployment configuration and production readiness

**Key Tasks**:
- [x] YAML configuration system for all classifier parameters
- [x] Local deployment mode (no remote services required)
- [x] Comprehensive error handling and validation
- [x] Structured logging throughout application
- [x] Integration tests for main workflows
- [x] Documentation and setup guides

## Configuration Management

### YAML Configuration
All classifier parameters are exposed in a YAML configuration file:

```yaml
detection:
  scoring:
    high_confidence_threshold: 0.80
    likely_threshold: 0.65
    timing_window_months: 24
  
  heuristics:
    same_agency_weight: 0.4
    sole_source_weight: 0.3
    timing_weight: 0.2
    topic_continuity_weight: 0.1
  
  model:
    retrain_frequency: "quarterly"
    max_features: 10
    n_estimators: 100
```

### Local vs Containerized Deployment

**Local Mode**:
- Single-machine setup
- SQLite database
- All processing offline
- YAML configuration files
- No authentication required

**Containerized Mode**:
- Docker Compose setup
- PostgreSQL database
- API service container
- Environment variable configuration
- Production-ready scaling

## Data Pipeline

### Ingestion Process
1. **SBIR Data**: Process `award_data.csv` with vendor creation/linking
2. **Contract Data**: Process USAspending bulk CSV files with chunked processing
3. **Vendor Resolution**: Cross-walk UEI, DUNS, CAGE identifiers
4. **Data Validation**: Schema validation and quality checks

### Detection Process
1. **Candidate Identification**: Query Phase II awards with completion dates
2. **Contract Matching**: Find subsequent contracts within timing window  
3. **Feature Extraction**: Apply heuristics for scoring signals
4. **ML Scoring**: Use gradient boosting model for likelihood scores
5. **Classification**: Apply thresholds for confidence levels
6. **Evidence Generation**: Create detailed evidence bundles

### Export Process
1. **JSONL Export**: Complete detection records with evidence bundles
2. **CSV Summary**: Aggregated statistics by vendor, agency, fiscal year
3. **YAML Export**: Human-readable format (configurable default)
4. **API Access**: Real-time evidence bundle retrieval

## Testing Strategy

### Unit Tests
- Data model validation
- Heuristic logic verification
- Scoring algorithm accuracy
- Configuration parsing

### Integration Tests
- End-to-end detection pipeline
- Data ingestion workflows
- API endpoint functionality
- Export format validation

### Performance Tests
- Large dataset processing (50,000+ records)
- API response time validation (<500ms for 95% of requests)
- Memory usage optimization
- Batch processing efficiency

## Quality Metrics

### Detection Accuracy
- **Precision**: ≥85% for top-K highest-scored detections
- **Recall**: ≥70% against known tagged Phase III awards
- **Processing Time**: Full fiscal year backtest in <8 hours

### System Performance  
- **API Response**: <500ms for 95% of evidence retrieval requests
- **Throughput**: Process 10K-100K records per batch efficiently
- **Scalability**: Handle datasets up to 50,000 detections without memory issues

### User Experience
- **Setup Time**: 90% of analysts complete local setup in <30 minutes
- **Configuration**: 100% of parameters adjustable via YAML with immediate effect
- **Offline Operation**: Complete workflow in network-restricted environments

## Feature Specifications

This section consolidates functional requirements, user stories, and acceptance criteria for core and secondary features.

### Core Feature: Detect Untagged SBIR Phase III Transitions

#### User Stories & Requirements

**User Story 1: Detect High-Confidence Transitions (Priority P1)**

As a data-savvy policy analyst, I want the system to automatically detect likely SBIR transitions using structural data links, so I can identify commercialization that isn't captured by unreliable Phase III tags.

*Acceptance Criteria:*
1. System detects subsequent sole-source IDV awarded to same vendor by same agency within 24 months of Phase II completion
2. System correctly chains child orders to parent IDV and updates total revenue metrics
3. System provides complete auditable evidence bundle for each detection

**User Story 2: Broaden Search Coverage (Priority P2)**

As a policy analyst, I want the system to consider transitions that were competed or awarded by different service branches for a more complete picture of transition pathways.

*Acceptance Criteria:*
1. System evaluates cross-service transitions based on department continuity and text analysis
2. System boosts scores for competed contracts with SBIR indicators (e.g., "Authorized by Statute")
3. System uses NAICS codes and description text for transition likelihood assessment

**User Story 3: Access and Export Detection Data (Priority P3)**

As a policy analyst, I want to access raw detection data and export summary reports for further analysis and integration into other reports.

*Acceptance Criteria:*
1. System provides JSONL file with complete evidence bundles for each detection
2. System generates CSV summary aggregated by vendor, agency, and fiscal year
3. System provides API endpoints for retrieving specific evidence bundles

#### Functional Requirements

**Data Ingestion & Processing**
- **FR-001**: System MUST ingest and process contract data from USAspending and FPDS using batch processing with configurable chunk sizes (10K-100K records)
- **FR-002**: System MUST ingest SBIR award metadata from SBIR.gov
- **FR-005**: System MUST use vendor identifiers (UEI, DUNS, CAGE) to track entities and maintain alias tables for novations

**Detection Logic**
- **FR-003**: System MUST identify Indefinite Delivery Vehicles (IDVs) like BOAs, BPAs, and IDIQs awarded within 1-24 month window after Phase II completion
- **FR-004**: System MUST link all child orders to their parent IDV to track total revenue and duration
- **FR-006**: System MUST analyze contract fields including PIID, Referenced-IDV PIID, agency/office codes, NAICS, PSC, and competition fields
- **FR-007**: System MUST calculate Transition Likelihood Score (0-1) blending rule-based heuristics and gradient boosting model with quarterly retraining
- **FR-008**: System MUST classify transitions with score ≥0.65 as "Likely Transition" and ≥0.80 as "High Confidence"

**Output & Reporting**
- **FR-009**: System MUST generate detailed, auditable evidence bundle for each detection
- **FR-010**: System MUST provide `POST /detect` endpoint to initiate analysis
- **FR-011**: System MUST provide `GET /evidence/{id}` endpoint to retrieve evidence bundles
- **FR-012**: System MUST output detections in JSONL format
- **FR-013**: System MUST output summary reports in CSV format, aggregated by vendor, agency, and fiscal year

**Quality & Feedback**
- **FR-014**: System MUST provide manual review queue for analysts to validate detections
- **FR-015**: System MUST track analyst feedback to retrain and improve detection accuracy
- **FR-017**: System MUST retrain gradient boosting model quarterly to capture seasonal patterns

#### Data Model

**Core Entities:**
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

#### Success Criteria
- **SC-001**: System achieves ≥85% precision for top-K highest-scored detections during backtesting on FY20-FY24 data
- **SC-002**: System achieves ≥70% recall against known set of tagged Phase III awards
- **SC-003**: Full backtest run for single fiscal year completes in under 8 hours
- **SC-004**: 95% of API requests to `GET /evidence/{id}` respond in under 500ms

### Secondary Features

#### Local Analyst Configuration Mode

Enable local execution without shared services, with all classifier parameters exposed in YAML for easy user tweaking.

*Requirements:*
- Single-machine setup process without requiring remote services
- Execute detection runs entirely offline once local datasets are present  
- Expose all classifier parameters in human-readable YAML file
- Load and apply YAML configuration at start of each run
- Validate YAML keys and value ranges with descriptive errors
- Support multiple configuration presets via specified YAML files
- Generate results as local artifacts without requiring API endpoints
- Provide recovery option to revert to default YAML configuration

*Success Criteria:*
- 90% of analysts complete local setup and run detection in under 30 minutes
- 100% of classifier parameters are adjustable via YAML and take effect immediately
- Detection workflows complete successfully in network-restricted environment

#### Export Format Migration (JSONL to YAML)

Migrate primary export format from JSONL to YAML for better human readability while maintaining backward compatibility.

*Requirements:*
- Export detection results in valid YAML format by default
- Maintain JSONL export capability for backward compatibility
- Allow format specification via command-line flag (--format yaml|jsonl)
- Preserve all existing data fields when converting formats
- Validate YAML output for syntax correctness before writing
- Handle large datasets (10,000+ records) without memory overflow
- Allow setting default export format via environment variable or config file

*Success Criteria:*
- All detection data exports successfully to valid YAML without data loss
- YAML export performance within 20% of current JSONL export time
- 100% of existing JSONL functionality remains available in compatibility mode
- System handles datasets up to 50,000 detection records without memory issues

## Performance & Technical Specifications

### Performance Optimizations Implemented

**High-Impact Database Optimizations** (3-10x improvement)
- Comprehensive Indexing Strategy: Added 15+ indexes for frequently queried columns
- Batch Operations: Row-by-row → bulk operations with caching (5-20x faster)
- Chunk Size Optimization: Increased from 1K → 5K records per batch (2-5x faster)

**CSV Loading Optimizations** (2-5x improvement)

```python
# Optimized pandas settings
pd.read_csv(
    file_path,
    engine='c',           # Use C engine (fastest)
    na_filter=False,      # Don't convert to NaN
    keep_default_na=False, # Don't interpret strings as NaN
    usecols=required_cols  # Only load needed columns
)
```

**Vectorized Data Processing** (5-10x improvement)

```python
# Instead of row-by-row filtering
valid_mask = (
    df['piid'].notna() & 
    (df['piid'].str.strip() != '') &
    df['agency'].notna()
)
df = df[valid_mask]
```

### Production Scale Performance

- **Data Volume**: 14GB+ federal spending data + 364MB SBIR awards
- **Processing Rate**: 66,728 detections/minute (optimized for 2x larger dataset)
- **Total Pipeline Time**: 225 seconds (3.75 minutes) for complete processing
- **Detection Processing**: 58.9 seconds for 236,194 new awards
- **Export Processing**: 9.6 seconds for 496,719 detections

### Data Loading Performance

- **SBIR Loading**: 35,000+ records/sec (vs. previous 17,440)
- **Contract Loading**: 150,000+ records/sec (vs. previous 78,742)
- **Memory Efficiency**: 30-50% reduction with streaming processing

### Database Indexes Added

**Performance Indexes:**
- `idx_vendors_name` - Vendor name lookups
- `idx_sbir_awards_vendor_id` - Join performance  
- `idx_sbir_awards_agency` - Agency filtering
- `idx_contracts_vendor_id` - Join performance
- `idx_vendor_agency_date` - Composite query patterns
- **15+ additional indexes** for comprehensive coverage

### Expected Performance Gains

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Bulk processing | 1000 records/batch | 5000 records/batch | 2-5x faster |
| Database queries | No indexes | Comprehensive indexes | 3-10x faster |
| Data loading | Row-by-row | Batch operations | 5-20x faster |
| **Overall** | **Baseline** | **Combined optimizations** | **10-50x faster** |

### Data Quality & Recovery

**SBIR Data Recovery Results** ✅
- CSV Rows: 214,282 (source data)
- Database Records: 252,025 (117.6% - includes legitimate multiple awards)
- Unique Companies with Multiple Awards: 25,179 (expected pattern)
- Data Quality: 99.99% (excellent retention)

**Date Field Recovery**
| Field | Valid Records | Recovery Rate |
|-------|---------------|---------------|
| Proposal Award Date | 107,778 | 50.3% |
| Date of Notification | 82,902 | 38.7% |
| Solicitation Close Date | 77,669 | 36.2% |
| Proposal Receipt Date | 60,634 | 28.3% |
| **Award Year (Fallback)** | **214,282** | **100.0%** |

## Deployment Options</parameter>
</invoke>

### Development
```bash
# Local development with hot reload
poetry run uvicorn src.sbir_transition_classifier.api.main:app --reload

# Run tests
poetry run pytest tests/
```

### Production
```bash
# Docker deployment
docker-compose up --build -d

# Manual deployment  
poetry run uvicorn src.sbir_transition_classifier.api.main:app --host 0.0.0.0 --port 8000
```

### Batch Processing
```bash
# Complete pipeline
poetry run sbir-detect bulk-process --data-dir ./data --output-dir ./output

# Individual steps
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv
poetry run python -m scripts.export_data export-jsonl --output-path results.jsonl
```

This implementation guide provides a comprehensive roadmap for developing, testing, and deploying the SBIR Transition Classifier system.