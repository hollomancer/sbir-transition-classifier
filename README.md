# SBIR Transition Detection System

A command-line tool to detect untagged SBIR Phase III transitions by analyzing federal spending data and identifying potential commercialization patterns.

## Overview

This system processes bulk federal spending data using a combination of heuristics and configuration-driven detection to identify potential SBIR Phase III transitions. The primary goal is to create a reliable, auditable process for identifying SBIR commercialization that is not officially flagged through comprehensive data analysis and export capabilities.

## Features

- **High-Confidence Detection**: Identifies likely transitions using strong structural signals like sole-source contracts
- **Broad Search Capabilities**: Detects competed and cross-service transitions
- **Command-Line Interface**: Easy-to-use CLI tools for data loading, processing, and export
- **Auditable Evidence**: Each detection includes a comprehensive evidence bundle
- **Bulk Data Processing**: Efficiently processes large federal spending datasets with progress tracking
- **Multiple Export Formats**: Export results as JSONL, CSV, or Excel formats
- **Rich Progress Indicators**: Visual progress bars and detailed status updates for long-running operations
- **Configuration-Driven**: Customizable detection thresholds and scoring parameters via YAML config

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd sbir-transition-classifier
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Prepare data**:
   - Place SBIR awards data in `data/awards.csv`
   - Add federal contract data files to `data/` directory
   - The system will automatically discover CSV files
   - See [Data Setup](#data-setup) section below for detailed requirements

### Quick Commands

```bash
# Run complete detection pipeline
poetry run sbir-detect bulk-process --verbose

# Or step-by-step:

# Load SBIR awards
poetry run sbir-detect data load-sbir --file-path data/awards.csv --verbose

# Load contract data
poetry run sbir-detect data load-contracts --file-path data/contracts.csv --verbose

# Export results
poetry run sbir-detect export jsonl --output-path output/detections.jsonl --verbose
poetry run sbir-detect export csv --output-path output/summary.csv --verbose

# View system info
poetry run sbir-detect info
```

## Architecture

### Tech Stack
- **Language**: Python 3.11
- **CLI Framework**: Click
- **Progress Indicators**: Rich, tqdm
- **Database**: SQLite
- **Data Processing**: Pandas
- **Logging**: Loguru
- **Configuration**: YAML-based schema with Pydantic
- **Dependency Management**: Poetry

### Project Structure
```
src/sbir_transition_classifier/
├── cli/              # Command-line interface
│   ├── main.py       # CLI entry point
│   ├── bulk.py       # Bulk processing command
│   ├── run.py        # Single-run command
│   ├── data.py       # Data loading commands
│   ├── export.py     # Export commands
│   ├── reports.py    # Reporting commands
│   ├── validate.py   # Configuration validation
│   ├── reset.py      # Configuration reset/templates
│   ├── hygiene.py    # Data quality commands
│   └── output.py     # Output generation utilities
├── core/             # Shared configuration and models
│   ├── models.py     # Data models (Vendor, Contract, Award)
│   └── vendor_matching.py  # Vendor name normalization
├── config/           # Configuration management
│   ├── loader.py     # Config file loading
│   ├── schema.py     # Config schema and validation
│   └── reset.py      # Config templates and reset
├── data/             # Data schemas and validation
│   ├── models.py     # Pydantic schemas
│   ├── evidence.py   # Evidence bundle definitions
│   └── schemas.py    # Data transfer schemas
├── detection/        # Detection algorithms
│   ├── main.py       # Main detection logic
│   ├── pipeline.py   # Detection pipeline
│   ├── scoring.py    # Scoring algorithms
│   └── heuristics.py # Heuristic rules
├── db/               # Database access layer
│   ├── database.py   # SQLAlchemy setup
│   ├── config.py     # DB configuration
│   └── queries.py    # SQL queries
├── ingestion/        # Data loading
│   ├── sbir.py       # SBIR data ingestion
│   ├── contracts.py  # Contract data ingestion
│   ├── base.py       # Base ingester
│   └── factory.py    # Ingester factory
└── utils/            # Utility functions
    ├── dates.py      # Date calculations
    └── __init__.py

tests/
├── unit/             # Unit tests
└── integration/      # Integration tests

output/               # Generated reports and exports
data/                 # Input data files (not in git)
```

## Data Model

The system uses five main database entities:

- **vendors**: Commercial entities receiving awards
- **vendor_identifiers**: Cross-walking between ID systems (UEI, CAGE, DUNS)
- **sbir_awards**: SBIR Phase I and II awards
- **contracts**: Federal contract vehicles from FPDS/USAspending
- **detections**: Identified potential transitions with evidence bundles

## Detection Logic

### High-Confidence Signals
- Same agency (service branch match)
- Sole-source contract awards
- Timing within configured window (default: 1-24 months) after Phase II completion
- Service/topic continuity

### Likely Transition Signals
- Cross-service transitions (same department, different branch)
- Competed contracts with SBIR indicators
- Department-level continuity
- Text-based description analysis

### Configuration
Detection thresholds and parameters are configured via YAML:

```yaml
detection:
  eligible_phases: ["Phase II"]
  thresholds:
    high_confidence: 0.85
    likely_transition: 0.65
  timing:
    min_months_after_phase2: 1
    max_months_after_phase2: 24
  scoring:
    sole_source_weight: 0.30
    timing_weight: 0.25
    agency_match_weight: 0.20
    vendor_match_weight: 0.25
```

## Command-Line Reference

### Core Commands

**`bulk-process`** - Complete end-to-end detection pipeline
```bash
poetry run sbir-detect bulk-process [OPTIONS]

Options:
  --data-dir PATH         Directory containing input CSV files [default: ./data]
  --output-dir PATH       Output directory for results [default: ./output]
  --chunk-size INTEGER    Batch size for processing [default: 5000]
  --export-format TEXT    Format: jsonl|csv|both [default: both]
  --verbose, -v           Enable detailed progress logging
  --quiet, -q             Minimal output
```

**`run`** - Execute detection with explicit configuration
```bash
poetry run sbir-detect run [OPTIONS]

Options:
  --config PATH           Path to YAML configuration file
  --output PATH           Output directory or file for results (required)
  --data-dir PATH         Directory with input data [default: ./data]
  --verbose, -v           Enable verbose logging
```

**`validate-config`** - Validate configuration file
```bash
poetry run sbir-detect validate-config [OPTIONS]

Options:
  --config PATH           Configuration file to validate (required)
  --verbose, -v           Show detailed validation results
```

**`reset-config`** - Generate configuration from template
```bash
poetry run sbir-detect reset-config [OPTIONS]

Options:
  --output PATH           Output path for config file (required)
  --template TEXT         Template: default|high-precision|broad-discovery
```

**`list-templates`** - Show available configuration templates
```bash
poetry run sbir-detect list-templates
```

**`show-template`** - Display template content
```bash
poetry run sbir-detect show-template --template default
```

### Data Commands

**`data load-sbir`** - Load SBIR award data
```bash
poetry run sbir-detect data load-sbir [OPTIONS]

Options:
  --file-path PATH        Path to SBIR CSV file (required)
  --chunk-size INTEGER    Records per batch [default: 5000]
  --verbose, -v           Enable verbose logging
```

**`data load-contracts`** - Load federal contract data
```bash
poetry run sbir-detect data load-contracts [OPTIONS]

Options:
  --file-path PATH        Path to contracts CSV file (required)
  --chunk-size INTEGER    Records per batch [default: 50000]
  --verbose, -v           Enable verbose logging
```

### Export Commands

**`export jsonl`** - Export detections as JSONL
```bash
poetry run sbir-detect export jsonl [OPTIONS]

Options:
  --output-path PATH      Output file path (required)
  --verbose, -v           Enable verbose logging
```

**`export csv`** - Export detection summary as CSV
```bash
poetry run sbir-detect export csv [OPTIONS]

Options:
  --output-path PATH      Output file path (required)
  --verbose, -v           Enable verbose logging
```

**`export excel`** - Export as Excel with multiple sheets
```bash
poetry run sbir-detect export excel [OPTIONS]

Options:
  --output-path PATH      Output file path (required)
  --verbose, -v           Enable verbose logging
```

### Reporting Commands

**`reports summary`** - Generate summary report
```bash
poetry run sbir-detect reports summary [OPTIONS]

Options:
  --results-dir PATH      Results directory (required)
  --output PATH           Output file (prints to stdout if omitted)
  --format TEXT           Format: text|markdown|json [default: text]
  --include-details       Include detailed analysis
```

**`reports stats`** - Show detection statistics
```bash
poetry run sbir-detect reports stats [OPTIONS]

Options:
  --json, -j              Output as JSON
```

**`reports perspectives`** - Analyze transitions from multiple perspectives
```bash
poetry run sbir-detect reports perspectives [OPTIONS]

Options:
  --output PATH           Output file path
  --format TEXT           Format: text|markdown|json [default: text]
```

### System Commands

**`info`** - Display system and configuration information
```bash
poetry run sbir-detect info
```

**`hygiene check-dates`** - Validate data quality and detect anomalies
```bash
poetry run sbir-detect hygiene check-dates [OPTIONS]

Options:
  --data-dir PATH         Data directory to check
  --output PATH           Output report path
```

**`version`** - Show version information
```bash
poetry run sbir-detect version
```

**`--help`** - Show all available commands
```bash
poetry run sbir-detect --help
poetry run sbir-detect data --help
poetry run sbir-detect export --help
poetry run sbir-detect reports --help
```

## Development

### Local Development Setup
```bash
# Install dependencies
poetry install

# Enter virtual environment
poetry shell

# Run CLI commands
sbir-detect --help
```

### Running Tests
```bash
# Unit tests only
poetry run pytest tests/unit/ -v

# Unit tests with coverage
poetry run pytest tests/unit/ -v --tb=short --cov=sbir_transition_classifier --cov-report=term-missing

# Integration tests
poetry run pytest tests/integration/ -v

# Full test suite
poetry run pytest

# Run specific test
poetry run pytest -k test_name -v
```

### Development Workflow
```bash
# 1. Create sample config
poetry run sbir-detect reset-config --output config/dev.yaml --template default

# 2. Validate config
poetry run sbir-detect validate-config --config config/dev.yaml --verbose

# 3. Load sample data
poetry run sbir-detect data load-sbir --file-path data/sample_awards.csv --verbose
poetry run sbir-detect data load-contracts --file-path data/sample_contracts.csv --verbose

# 4. Run detection
poetry run sbir-detect run --config config/dev.yaml --output output/dev_results/ --verbose

# 5. Export and review results
poetry run sbir-detect export jsonl --output-path output/dev_results.jsonl --verbose
poetry run sbir-detect reports summary --results-dir output/ --format markdown --include-details
```

## Performance

- **Target**: Backtest a full fiscal year in < 8 hours
- **Processing Rate**: 1000+ records/minute on modern hardware
- **Scale**: Processes 10-100GB yearly data files
- **Memory Efficiency**: Streaming processing with configurable chunk sizes
- **Database**: SQLite with indexed queries for fast lookups

## Data Setup

### Data Directory Structure

The project uses three data directories for different purposes:

- **`data/`** - Production data files (excluded from git due to size)
- **`output/`** - Generated reports, exports, and logs
- **`test_data/`** - Test fixtures and mock data for unit/integration tests

### Required Data Files

#### SBIR Awards Data
- **File:** `data/awards.csv`
- **Source:** SBIR.gov database export
- **Columns:** award_piid, phase, agency, award_date, completion_date, topic, vendor_name, etc.

#### Federal Contract Data
- **File:** `data/contracts.csv`
- **Source:** https://www.usaspending.gov/download_center/award_data_archive
- **Columns:** piid, agency, start_date, vendor_name, naics_code, psc_code, etc.

### Data Format Requirements

Both CSV files must contain headers and use UTF-8 encoding. The system is tolerant of minor format variations but requires:

- **SBIR Data**: PIID, phase, agency, completion date
- **Contract Data**: PIID, agency, start date, vendor name

### Download Instructions

#### SBIR Awards Data
Contact project maintainer for access to `awards.csv`

#### USAspending Contract Data
1. Visit https://www.usaspending.gov/download_center/award_data_archive
2. Select desired fiscal year(s)
3. Download contract data (CSV format)
4. Place in `data/` directory

### Example Data Loading

```bash
# Load SBIR data
poetry run sbir-detect data load-sbir \
  --file-path data/awards.csv \
  --chunk-size 5000 \
  --verbose

# Load contract data (may be large)
poetry run sbir-detect data load-contracts \
  --file-path data/contracts.csv \
  --chunk-size 50000 \
  --verbose
```

## Configuration

### Default Configuration
If no configuration is specified, the system uses built-in defaults. To customize:

```bash
# Generate default config
poetry run sbir-detect reset-config --output config/custom.yaml

# Edit config/custom.yaml with your parameters

# Run with custom config
poetry run sbir-detect run --config config/custom.yaml --output output/results/
```

### Available Templates
- **default**: Balanced detection approach
- **high-precision**: Higher thresholds, fewer false positives
- **broad-discovery**: Lower thresholds, more detections

```bash
# Show template
poetry run sbir-detect show-template --template high-precision

# Create config from template
poetry run sbir-detect reset-config --output config/strict.yaml --template high-precision
```

## Contributing

1. Follow existing CLI patterns and command structure
2. Use Rich progress indicators for long-running operations
3. Include comprehensive logging and error handling
4. Add tests for new functionality (see AGENTS.md for testing guidelines)
5. Update documentation and help text
6. Ensure Poetry builds succeed and all tests pass
7. See AGENTS.md for detailed contribution guidelines

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Documentation

- **[AGENTS.md](AGENTS.md)** - Complete development and contribution guidelines
- **Configuration**: See `config/` directory for example YAML files
- **Testing**: See `tests/` directory for unit and integration tests

---

## Quick Reference Card

### Most Common Tasks

```bash
# Initial setup
poetry install

# Full pipeline (recommended)
poetry run sbir-detect bulk-process --verbose

# Manual steps
poetry run sbir-detect data load-sbir --file-path data/awards.csv --verbose
poetry run sbir-detect data load-contracts --file-path data/contracts.csv --verbose
poetry run sbir-detect run --output output/results/ --verbose

# Export results
poetry run sbir-detect export jsonl --output-path output/detections.jsonl --verbose
poetry run sbir-detect export csv --output-path output/summary.csv

# View results
poetry run sbir-detect reports summary --results-dir output/ --format markdown
```

### File Organization
- `data/` - Input CSV files
- `output/` - Generated reports and exports
- `src/sbir_transition_classifier/cli/` - Command implementations
- `src/sbir_transition_classifier/detection/` - Detection logic
- `tests/` - Unit and integration tests

### Getting Help
```bash
# All commands
poetry run sbir-detect --help

# Command group help
poetry run sbir-detect data --help
poetry run sbir-detect export --help
poetry run sbir-detect reports --help

# System info
poetry run sbir-detect info
```
