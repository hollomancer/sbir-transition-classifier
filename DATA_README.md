# Data Directory Guide

## Overview

The project uses three data directories for different purposes:

- **`data/`** - Production data files (excluded from git due to size)
- **`data_subset/`** - Development-friendly smaller samples  
- **`test_data/`** - Test fixtures and mock data for unit/integration tests

## Required Production Files (`data/`)

### SBIR Awards Data
- **File:** `award_data.csv` (364MB)
- **Source:** SBIR.gov database export
- **Contains:** Complete SBIR Phase I and II awards

### USAspending Contract Data
- **File:** `FY2026_All_Contracts_Full_20251008_1.csv` (18.6MB)
- **Source:** https://www.usaspending.gov/download_center/award_data_archive
- **Contains:** FY2026 federal contract data

### Recommended Additional Files:
- `Contracts_PrimeAwardSummary_2020_1.csv`
- `Contracts_PrimeAwardSummary_2021_1.csv`
- `Contracts_PrimeAwardSummary_2022_1.csv`
- `Contracts_PrimeAwardSummary_2023_1.csv`
- `Contracts_PrimeAwardSummary_2024_1.csv`

## Download Instructions

### For SBIR Data:
Contact project maintainer for `award_data.csv` file

### For USAspending Data:
1. Visit https://www.usaspending.gov/download_center/award_data_archive
2. Download contract data for desired fiscal years
3. Place files in `data/` directory

## Development Usage

### For Development (`data_subset/`)
Place smaller versions of the main data files here for development work:
- Subset of `award_data.csv` 
- Contract data samples
- Development-friendly data sizes

### For Testing (`test_data/`)
- Sample datasets for unit and integration testing
- Test fixtures and mock data
- Generate using scripts in `scripts/` directory

## Processing Commands

```bash
# Load SBIR data
poetry run python -m scripts.load_bulk_data load-sbir-data --file-path data/awards.csv --verbose

# Run complete pipeline
poetry run sbir-detect bulk-process --data-dir ./data --verbose

# Development with smaller datasets
poetry run sbir-detect bulk-process --data-dir ./data_subset --verbose
```

**Note**: Start with smaller samples in `data_subset/` for testing before processing full datasets from `data/`.