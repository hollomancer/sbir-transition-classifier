# Data Directory

This directory contains all bulk data files for the SBIR Transition Detection System.

**Note: Data files are excluded from git due to size (400MB+). Download separately.**

## Required Files

### SBIR Awards Data
- **File:** `award_data.csv` (364MB)
- **Source:** SBIR.gov database export
- **Contains:** Complete SBIR Phase I and II awards

### USAspending Contract Data
- **File:** `FY2026_All_Contracts_Full_20251008_1.csv` (18.6MB)
- **Source:** https://www.usaspending.gov/download_center/award_data_archive
- **Contains:** FY2026 federal contract data

## Download Instructions

### For SBIR Data:
Contact project maintainer for `award_data.csv` file

### For USAspending Data:
1. Visit https://www.usaspending.gov/download_center/award_data_archive
2. Download contract data for desired fiscal years
3. Place files in this directory

### Recommended Additional Files:
- `Contracts_PrimeAwardSummary_2020_1.csv`
- `Contracts_PrimeAwardSummary_2021_1.csv`
- `Contracts_PrimeAwardSummary_2022_1.csv`
- `Contracts_PrimeAwardSummary_2023_1.csv`
- `Contracts_PrimeAwardSummary_2024_1.csv`

## Processing

```bash
# Load SBIR data
PYTHONPATH=. python scripts/load_bulk_data.py load-sbir-data

# Run enhanced analysis
PYTHONPATH=. python scripts/enhanced_analysis.py --sbir-sample 10000 --contract-sample 2000
```

**Note**: Start with smaller samples for testing before processing full datasets.
