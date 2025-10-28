# SBIR Transition Detection System

A command-line tool to detect untagged SBIR Phase III transitions by analyzing federal spending data and identifying potential commercialization patterns.

## Overview

This system is intended to process bulk federal spending data using a combination of heuristics and machine learning to identify potential SBIR Phase III transitions. The primary goal is to create a reliable, auditable process for identifying SBIR commercialization that is not officially flagged through comprehensive data analysis and export capabilities.

But it's not done yet. See `docs/IMPLEMENTATION_GUIDE.md` for a development playbook, including safe, repeatable steps to purge large files from git history (history-purge procedure) and guidance for collaborators after a history rewrite.

## Features

- **High-Confidence Detection**: Identifies likely transitions using strong structural signals like sole-source contracts
- **Broad Search Capabilities**: Detects competed and cross-service transitions
- **Command-Line Interface**: Easy-to-use CLI tools for data loading, processing, and export
- **Auditable Evidence**: Each detection includes a comprehensive evidence bundle
- **Bulk Data Processing**: Efficiently processes large federal spending datasets with progress tracking
- **Multiple Export Formats**: Export results as JSONL, CSV, or both formats
- **Rich Progress Indicators**: Visual progress bars and detailed status updates for long-running operations

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

2. **Run the setup script**:
   ```bash
   poetry install
   ```
   
   Or manually:
   ```bash
   poetry install
   ```

3. **Prepare data**:
   - Place SBIR awards data in `data/award_data.csv`
   - Add USAspending bulk data files to `data/` directory
   - The system will automatically detect and process CSV files
   - See [Data Setup](#data-setup) section below for detailed requirements

### Usage

#### 1. Quick Bulk Processing (Recommended)
```bash
# Run complete detection pipeline with automatic data loading and export
poetry run sbir-detect bulk-process --verbose

# Or using the module directly (package-invocation)
poetry run python -m sbir_transition_classifier.cli.main bulk-process --verbose
```

#### 2. Step-by-Step Processing

**Load SBIR Awards Data:**
```bash
poetry run sbir-detect data load-sbir --file-path data/award_data.csv --verbose
```

**Load Contract Data:**
```bash
poetry run sbir-detect data load-contracts --file-path data/contracts.csv --verbose
```

**Export Detection Results:**
```bash
# Export as JSONL
poetry run sbir-detect export jsonl --output-path output/detections.jsonl --verbose

# Export as CSV summary
poetry run sbir-detect export csv --output-path output/summary.csv
```

#### 3. CLI Commands

**View System Information:**
```bash
poetry run sbir-detect info
```

**Quick Database Statistics:**
```bash
poetry run sbir-detect quick-stats
```

**View All Commands:**
```bash
poetry run sbir-detect --help

# View data commands
poetry run sbir-detect data --help

# View export commands
poetry run sbir-detect export --help
```

## Architecture

### Tech Stack
- **Language**: Python 3.11
- **CLI Framework**: Click
- **Progress Indicators**: Rich, tqdm
- **Database**: SQLite
- **Data Processing**: Pandas
- **Machine Learning**: Optional — model training tools are not required for core CLI processing (see `docs/IMPLEMENTATION_GUIDE.md` for model workflows).
- **Logging**: Loguru
- **Dependency Management**: Poetry

### Project Structure
```
src/sbir_transition_classifier/
├── cli/           # Command-line interface commands
├── core/          # Configuration and data models
├── data/          # Data schemas and validation
├── detection/     # Detection algorithms and scoring
└── db/            # Database connection and management

scripts/           # Data loading and export utilities
tests/             # Unit and integration tests
output/            # Generated reports and exports
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

## Command-Line Reference

### Main Commands

**`bulk-process`** - Complete end-to-end processing pipeline
```bash
poetry run sbir-detect bulk-process [OPTIONS]

Options:
  --data-dir PATH          Directory containing input data files [default: ./data]
  --output-dir PATH        Output directory for results [default: ./output]  
  --chunk-size INTEGER     Batch size for processing [default: 1000]
  --export-format [jsonl|csv|both]  Export format [default: both]
  --verbose, -v            Enable detailed progress logging
```

**`info`** - Display system and configuration information
```bash
poetry run sbir-detect info
```

**`quick-stats`** - Show database statistics and summary metrics
```bash
poetry run sbir-detect quick-stats
```

### Data Scripts

**Load SBIR Data:**
```bash
# Use the package-installed script entry for data loading (package namespace)
poetry run python -m sbir_transition_classifier.scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose
```

**Export Results:**
```bash
poetry run python -m scripts.export_data export-jsonl --output-path results.jsonl
poetry run python -m scripts.export_data export-csv-summary --output-path summary.csv
```

## Development

### Local Development Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run CLI commands directly
sbir-detect --help
```

### Running Tests
```bash
# Unit tests
poetry run pytest tests/unit/

# Integration tests
poetry run pytest tests/integration/

# Full test suite
poetry run pytest
```

### Development Workflow
```bash
# Load sample data
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/sample_awards.csv

# Run detection on small dataset
poetry run sbir-detect bulk-process --data-dir data/samples --verbose

# Export and review results
poetry run python -m scripts.export_data export-jsonl --output-path dev_results.jsonl
```

## Performance

- **Target**: Backtest a full fiscal year in < 8 hours
- **Processing Rate**: 1000+ records/minute on modern hardware  
- **Scale**: Processes 10-100GB yearly data files
- **Memory Efficiency**: Streaming processing with configurable chunk sizes

## Progress Indicators

The CLI provides rich visual feedback during processing:

- **File Discovery**: Shows detected CSV files and their sizes
- **Database Operations**: Progress bars for initialization and data loading
- **Detection Pipeline**: Real-time progress with time estimates
- **Export Operations**: Status updates for result generation
- **Summary Tables**: Formatted results with processing metrics

## Example Workflows

### Complete Processing Pipeline
```bash
# 1. Setup environment
poetry install

# 2. Run complete pipeline with rich progress indicators
poetry run sbir-detect bulk-process \
  --data-dir ./data \
  --output-dir ./output \
  --export-format both \
  --verbose

# 3. Check results
ls -la ./output/
```

### Manual Step-by-Step Processing
```bash
# Load data with progress tracking
poetry run python -m scripts.load_bulk_data load-sbir-data \
  --file-path data/awards.csv \
  --chunk-size 5000 \
  --verbose

# Check system status
poetry run sbir-detect quick-stats

# Export results in multiple formats
poetry run python -m scripts.export_data export-jsonl --output-path detections.jsonl --verbose
poetry run python -m scripts.export_data export-csv-summary --output-path summary.csv
```

## Data Setup

### Data Directory Structure

The project uses three data directories for different purposes:

- **`data/`** - Production data files (excluded from git due to size)
- **`data_subset/`** - Development-friendly smaller samples  
- **`test_data/`** - Test fixtures and mock data for unit/integration tests

### Required Production Files (`data/`)

#### SBIR Awards Data
- **File:** `award_data.csv` (364MB)
- **Source:** SBIR.gov database export
- **Contains:** Complete SBIR Phase I and II awards

#### USAspending Contract Data
- **File:** `FY2026_All_Contracts_Full_20251008_1.csv` (18.6MB)
- **Source:** https://www.usaspending.gov/download_center/award_data_archive
- **Contains:** FY2026 federal contract data

#### Recommended Additional Files:
- `Contracts_PrimeAwardSummary_2020_1.csv`
- `Contracts_PrimeAwardSummary_2021_1.csv`
- `Contracts_PrimeAwardSummary_2022_1.csv`
- `Contracts_PrimeAwardSummary_2023_1.csv`
- `Contracts_PrimeAwardSummary_2024_1.csv`

### Download Instructions

#### For SBIR Data:
Contact project maintainer for `award_data.csv` file

#### For USAspending Data:
1. Visit https://www.usaspending.gov/download_center/award_data_archive
2. Download contract data for desired fiscal years
3. Place files in `data/` directory

### Development Usage

#### For Development (`data_subset/`)
Place smaller versions of the main data files here for development work:
- Subset of `award_data.csv` 
- Contract data samples
- Development-friendly data sizes

#### For Testing (`test_data/`)
- Sample datasets for unit and integration testing
- Test fixtures and mock data
- Generate using scripts in `scripts/` directory

### Data Processing Commands

```bash
# Load SBIR data
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose

# Run complete pipeline
poetry run sbir-detect bulk-process --data-dir ./data --verbose

# Development with smaller datasets
poetry run sbir-detect bulk-process --data-dir ./data_subset --verbose
```

**Note**: Start with smaller samples in `data_subset/` for testing before processing full datasets from `data/`.

## Contributing

1. Follow existing CLI patterns and command structure
2. Use rich progress indicators for long-running operations
3. Include comprehensive logging and error handling
4. Add tests for new functionality
5. Update documentation and help text
6. Ensure Poetry builds succeed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Quick Reference Card

**Most Common Commands:**
```bash
# Install dependencies
poetry install

# Quick start (recommended)
poetry run sbir-detect bulk-process --verbose

# Manual data loading
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose

# Export results
poetry run python -m scripts.export_data export-jsonl --output-path results.jsonl --verbose

# System status
poetry run sbir-detect quick-stats
```

**File Organization:**
- `data/` - Input CSV files (awards, contracts)
- `output/` - Generated reports and exports  
- `scripts/` - Data loading and export utilities
- `src/` - Core application code

**Log Files:**
- Bulk processing creates timestamped logs in output directory
- Use `--verbose` flag for detailed progress tracking
- Rich progress bars show real-time status updates
