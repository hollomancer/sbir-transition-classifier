# SBIR Transition Detection System

A command-line tool to detect untagged SBIR Phase III transitions by analyzing federal spending data and identifying potential commercialization patterns.

## Overview

This system processes bulk federal spending data using a combination of heuristics and machine learning to identify potential SBIR Phase III transitions. The primary goal is to create a reliable, auditable process for identifying SBIR commercialization that is not officially flagged through comprehensive data analysis and export capabilities.

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
   python setup.py
   ```
   
   Or manually:
   ```bash
   poetry install
   ```

3. **Prepare data**:
   - Place SBIR awards data in `data/award_data.csv`
   - Add USAspending bulk data files to `data/` directory
   - The system will automatically detect and process CSV files

### Usage

#### 1. Quick Bulk Processing (Recommended)
```bash
# Run complete detection pipeline with automatic data loading and export
poetry run sbir-detect bulk-process --verbose

# Or using the module directly
poetry run python -m src.sbir_transition_classifier.cli.main bulk-process --verbose
```

#### 2. Step-by-Step Processing

**Load SBIR Awards Data:**
```bash
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/award_data.csv --verbose
```

**Export Detection Results:**
```bash
# Export as JSONL
poetry run python -m scripts.export_data export-jsonl --output-path output/detections.jsonl --verbose

# Export as CSV summary
poetry run python -m scripts.export_data export-csv-summary --output-path output/summary.csv
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

**Show all available commands:**
```bash
poetry run sbir-detect --help
```

## Architecture

### Tech Stack
- **Language**: Python 3.11
- **CLI Framework**: Click
- **Progress Indicators**: Rich, tqdm
- **Database**: SQLite
- **Data Processing**: Pandas, Dask
- **Machine Learning**: XGBoost, scikit-learn
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
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose
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
# Quick setup
python setup.py

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
