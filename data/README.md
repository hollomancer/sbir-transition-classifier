# Data Directory

This directory contains all bulk data files for the SBIR Transition Detection System.

## Current Files

- `award_data.csv` - SBIR Phase I and II awards data (381MB)

## USAspending Data

Download contract data from https://www.usaspending.gov/download_center/award_data_archive

### Recommended Files:
- `Contracts_PrimeAwardSummary_2020_1.csv`
- `Contracts_PrimeAwardSummary_2021_1.csv`
- `Contracts_PrimeAwardSummary_2022_1.csv`
- `Contracts_PrimeAwardSummary_2023_1.csv`
- `Contracts_PrimeAwardSummary_2024_1.csv`

### Processing:
```bash
# Load SBIR data
python -m scripts.load_bulk_data load-sbir-data

# Load contract data (when available)
python -m scripts.load_bulk_data load-contract-data --file-path data/Contracts_PrimeAwardSummary_2024_1.csv
```

**Note**: Contract files are large (2-10GB each). Start with one fiscal year for testing.
