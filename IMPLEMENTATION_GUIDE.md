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

## Deployment Options

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