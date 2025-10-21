# Quick Start: Local Analyst Configuration Mode

**Target**: Single analyst workstation setup and execution  
**Time**: ~30 minutes for first-time setup  
**Prerequisites**: Python 3.11+, Git

## Installation

### 1. Clone and Setup Environment
```bash
git clone <repository-url>
cd sbir-transition-classifier
git checkout 002-this-will-be

# Install dependencies
poetry install
```

### 2. Prepare Local Data
```bash
# Create data directory structure
mkdir -p data/{awards,contracts,outputs}

# Place your data files (obtain separately):
# - data/awards/sbir_awards.csv (SBIR Phase I/II awards)
# - data/contracts/fpds_contracts.csv (Federal contract data)
```

### 3. Initialize Local Database
```bash
# Create and populate local SQLite database
poetry run python -m scripts.setup_local_db
poetry run python -m scripts.load_bulk_data --data-dir data/
```

## Basic Usage

### 1. Run Detection with Default Settings
```bash
# Execute detection using default configuration
poetry run sbir-detect run \
  --config config/default.yaml \
  --output results/

# Check results
ls results/
# Expected: detections.jsonl, summary.csv, evidence/
```

### 2. Customize Detection Parameters
```bash
# Generate custom configuration
poetry run sbir-detect reset-config --output config/my-config.yaml

# Edit configuration (example changes):
# - Lower high_confidence threshold to 0.75
# - Enable text analysis
# - Extend search window to 36 months

# Validate your changes
poetry run sbir-detect validate-config --config config/my-config.yaml

# Run with custom settings
poetry run sbir-detect run \
  --config config/my-config.yaml \
  --output results/custom/
```

### 3. Review Results
```bash
# View summary statistics
cat results/summary.csv

# Examine specific detection evidence
poetry run python -c "
import json
with open('results/detections.jsonl') as f:
    for line in f:
        detection = json.loads(line)
        if detection['confidence'] == 'High Confidence':
            print(f'Detection {detection['detection_id']}: {detection['reason_string']}')
            break
"

# Open evidence bundle for detailed review
ls results/evidence/<detection-uuid>/
# Contains: evidence.json, summary.txt, source_documents/
```

## Configuration Examples

### High-Precision Mode (Fewer False Positives)
```yaml
# config/high-precision.yaml
schema_version: "1.0"
detection:
  thresholds:
    high_confidence: 0.90  # Raised threshold
    likely_transition: 0.80
  weights:
    sole_source_bonus: 0.3  # Emphasize sole-source
    agency_continuity: 0.4  # Emphasize same agency
  features:
    enable_cross_service: false  # Disable cross-service
    enable_competed_contracts: false  # Sole-source only
```

### Broad Discovery Mode (More Comprehensive)
```yaml
# config/broad-discovery.yaml
schema_version: "1.0"
detection:
  thresholds:
    high_confidence: 0.70  # Lowered threshold
    likely_transition: 0.50
  features:
    enable_cross_service: true
    enable_text_analysis: true  # Enable text matching
    enable_competed_contracts: true
  timing:
    max_months_after_phase2: 36  # Extended window
```

## Troubleshooting

### Configuration Errors
```bash
# Common validation error:
ERROR: detection.thresholds.high_confidence: 1.2 is not <= 1.0

# Fix: Ensure all thresholds are between 0.0 and 1.0
```

### Missing Data Files
```bash
# Error: FileNotFoundError: data/awards/sbir_awards.csv
# Solution: Ensure data files are placed in correct directories
# Check: ls data/awards/ data/contracts/
```

### Performance Issues
```bash
# For large datasets (>5GB), increase memory:
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=4

# Monitor progress:
poetry run sbir-detect run --config config/default.yaml --verbose
```

### Output Validation
```bash
# Verify detection count is reasonable:
wc -l results/detections.jsonl
# Expected: 10-1000 detections for typical fiscal year

# Check for empty results:
if [ ! -s results/detections.jsonl ]; then
  echo "No detections found - check configuration thresholds"
fi
```

## Next Steps

1. **Iterate on Configuration**: Adjust thresholds based on initial results
2. **Validate Findings**: Manually review high-confidence detections
3. **Export for Analysis**: Use generated CSV files for further analysis
4. **Schedule Regular Runs**: Set up periodic detection with updated data

## Support

- Configuration schema: `specs/002-this-will-be/contracts/config-schema.yaml`
- CLI reference: `specs/002-this-will-be/contracts/cli.yaml`
- Data model: `specs/002-this-will-be/data-model.md`
