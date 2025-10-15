# SBIR Transition Detection System

A system to detect untagged SBIR Phase III transitions by analyzing federal spending data and identifying potential commercialization patterns.

## Overview

This system ingests bulk federal spending data, uses a combination of heuristics and machine learning to identify potential SBIR Phase III transitions, and exposes the results via a REST API. The primary goal is to create a reliable, auditable process for identifying SBIR commercialization that is not officially flagged.

## Features

- **High-Confidence Detection**: Identifies likely transitions using strong structural signals like sole-source contracts
- **Broad Search Capabilities**: Detects competed and cross-service transitions
- **REST API**: Access and export detection data programmatically
- **Auditable Evidence**: Each detection includes a comprehensive evidence bundle
- **Bulk Data Processing**: Efficiently processes large federal spending datasets

## Quick Start

### Prerequisites

- Docker
- Docker Compose
- `curl` or similar HTTP client

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd sbir-transition-classifier
   ```

2. **Prepare data**:
   - Ensure `data/award_data.csv` is present (SBIR awards data)
   - Download USAspending bulk data files to `data/` directory

3. **Start the services**:
   ```bash
   docker-compose up --build -d
   ```

### Usage

#### 1. Load Data
```bash
# Load SBIR awards and contract data
docker-compose exec api python -m scripts.load_bulk_data
```

#### 2. Trigger Detection
```bash
curl -X POST http://localhost:8000/detect \
  -H "Content-Type: application/json" \
  -d '{"vendor_identifier": "ABCDE12345"}'
```

#### 3. Retrieve Evidence
```bash
curl http://localhost:8000/evidence/<detection-uuid>
```

## Architecture

### Tech Stack
- **Language**: Python 3.11
- **API Framework**: FastAPI
- **Database**: SQLite
- **Data Processing**: Pandas, Dask
- **Machine Learning**: XGBoost, scikit-learn
- **Containerization**: Docker

### Project Structure
```
src/sbir_transition_classifier/
├── api/           # FastAPI application
├── core/          # Configuration and data models
├── data/          # Data schemas and validation
├── detection/     # Detection algorithms and scoring
└── db/            # Database connection and management

scripts/           # Data loading and export utilities
tests/             # Unit and integration tests
```

## Data Model

The system uses five main entities:
- **vendors**: Commercial entities receiving awards
- **vendor_identifiers**: Cross-walking between ID systems (UEI, CAGE, DUNS)
- **sbir_awards**: SBIR Phase I and II awards
- **contracts**: Federal contract vehicles from FPDS/USAspending
- **detections**: Identified potential transitions with evidence

## Detection Logic

### High-Confidence Signals
- Same service branch and agency
- Sole-source contract awards
- Timing within 24 months of Phase II completion
- Service/topic continuity

### Likely Transition Signals
- Cross-service transitions
- Competed contracts with SBIR indicators
- Department-level continuity
- Text-based analysis of descriptions

## API Reference

### POST /detect
Initiates detection analysis for a vendor or specific SBIR award.

**Request Body:**
```json
{
  "vendor_identifier": "ABCDE12345",  // UEI, CAGE, or DUNS
  "sbir_award_piid": "W911NF-18-C-0033"  // Optional: specific award
}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "status": "Analysis has been accepted and is in progress."
}
```

### GET /evidence/{detection_id}
Retrieves the evidence bundle for a specific detection.

**Response:**
```json
{
  "detection_id": "<uuid>",
  "likelihood_score": 0.85,
  "confidence": "High Confidence",
  "reason_string": "Sole-source IDV awarded 8 months after Phase II completion by the same agency.",
  "source_sbir_award": {...},
  "source_contract": {...}
}
```

## Development

### Running Tests
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/
```

### Data Export
```bash
# Export all detections to JSONL
python -m scripts.export_data --format jsonl

# Generate CSV summary report
python -m scripts.export_data --format csv
```

## Performance

- **Target**: Backtest a full fiscal year in < 8 hours
- **API Response**: p95 < 500ms
- **Scale**: Processes 10-100GB yearly data files

## Contributing

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure Docker builds succeed

## License

[Add appropriate license information]

---

For detailed setup instructions and validation steps, see [quickstart.md](specs/001-prompt-detect-untagged/quickstart.md).
