# SBIR Transition Classifier - Refactoring Implementation Guide

**Version:** 1.0  
**Last Updated:** 2024  
**Estimated Total Time:** 22-30 hours (Phase 1)

---

## Purpose

This guide provides step-by-step instructions to implement the high-priority refactoring recommendations identified in `REFACTORING_OPPORTUNITIES.md`. Follow these steps in order to minimize breaking changes and maintain a working codebase throughout the process.

---

## Prerequisites

Before starting:

1. **Create a feature branch:**
   ```bash
   git checkout -b refactor/consolidation-phase-1
   ```

2. **Ensure tests pass:**
   ```bash
   poetry run pytest
   ```

3. **Create a backup branch:**
   ```bash
   git branch backup/pre-refactor-$(date +%Y%m%d)
   ```

4. **Set up proper IDE tooling:**
   - Enable type checking (mypy)
   - Enable auto-formatting (black, isort)
   - Enable linting (ruff or flake8)

---

## Phase 1: High-Priority Refactoring

### Task 1: Merge Configuration Systems (4-6 hours)

#### Step 1.1: Extend ConfigSchema with Database Settings

**File:** `src/sbir_transition_classifier/config/schema.py`

Add the following class before `ConfigSchema`:

```python
class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    
    url: str = Field(
        default="sqlite:///./sbir_transitions.db",
        description="SQLAlchemy database connection URL"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging"
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Database connection pool size (non-SQLite only)"
    )
    pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Connection pool timeout in seconds"
    )
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "SBIR_DB_"  # Allow SBIR_DB_URL env var override
```

Update `ConfigSchema` to include database config:

```python
class ConfigSchema(BaseModel):
    """Complete configuration schema for SBIR transition classifier."""

    schema_version: Literal["1.0"] = Field(
        default="1.0", description="Configuration schema version"
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database connection settings"
    )
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True
```

**Commit:** `git commit -m "feat(config): add database config to unified schema"`

#### Step 1.2: Create Database Configuration Loader

**File:** `src/sbir_transition_classifier/db/config.py` (new file)

```python
"""Database configuration management."""

from pathlib import Path
from typing import Optional

from loguru import logger

from ..config.loader import ConfigLoader, ConfigLoadError
from ..config.schema import DatabaseConfig


def get_database_config(config_path: Optional[Path] = None) -> DatabaseConfig:
    """
    Load database configuration from unified config file.
    
    Args:
        config_path: Optional path to config file. If None, uses default.
        
    Returns:
        DatabaseConfig instance
        
    Raises:
        ConfigLoadError: If config cannot be loaded
    """
    try:
        if config_path:
            full_config = ConfigLoader.load_from_file(config_path)
        else:
            # Try to load default, fall back to defaults if not found
            try:
                full_config = ConfigLoader.load_default()
            except ConfigLoadError:
                logger.warning(
                    "No config file found, using default database settings"
                )
                return DatabaseConfig()
        
        return full_config.database
    except Exception as e:
        logger.warning(f"Failed to load database config: {e}, using defaults")
        return DatabaseConfig()


# Singleton instance
_db_config: Optional[DatabaseConfig] = None


def get_db_config_singleton() -> DatabaseConfig:
    """Get singleton database configuration instance."""
    global _db_config
    if _db_config is None:
        _db_config = get_database_config()
    return _db_config
```

**Commit:** `git commit -m "feat(db): add database config loader"`

#### Step 1.3: Update Database Connection to Use Unified Config

**File:** `src/sbir_transition_classifier/db/database.py`

Replace entire file content:

```python
"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_db_config_singleton

# Load database configuration
db_config = get_db_config_singleton()

# Create engine based on configuration
if db_config.url.startswith("sqlite"):
    engine = create_engine(
        db_config.url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=db_config.echo,
    )
else:
    # PostgreSQL, MySQL, etc.
    engine = create_engine(
        db_config.url,
        pool_size=db_config.pool_size,
        pool_timeout=db_config.pool_timeout,
        echo=db_config.echo,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
```

**Commit:** `git commit -m "refactor(db): use unified config for database connection"`

#### Step 1.4: Update Default Configuration Template

**File:** `config/default.yaml`

Add database section at the top:

```yaml
schema_version: "1.0"

# Database configuration
database:
  url: "sqlite:///./sbir_transitions.db"
  echo: false
  pool_size: 5
  pool_timeout: 30

# Data ingestion settings
ingestion:
  data_formats:
    - csv
  encoding: utf-8
  chunk_size: 10000
  max_records: null

# ... rest of existing config
```

**Commit:** `git commit -m "feat(config): add database section to default config"`

#### Step 1.5: Deprecate core/config.py

**File:** `src/sbir_transition_classifier/core/config.py`

Replace with deprecation warning:

```python
"""
DEPRECATED: This module is deprecated.

Please use the unified configuration system:
    from sbir_transition_classifier.db.config import get_database_config
    
This file will be removed in version 0.2.0.
"""

import warnings
from pydantic_settings import BaseSettings

warnings.warn(
    "core.config is deprecated. Use db.config.get_database_config() instead.",
    DeprecationWarning,
    stacklevel=2
)


class Settings(BaseSettings):
    """DEPRECATED: Use unified config system."""
    DATABASE_URL: str = "sqlite:///./sbir_transitions.db"

    class Config:
        env_file = ".env"


settings = Settings()
```

**Commit:** `git commit -m "deprecate(core): mark core.config as deprecated"`

#### Step 1.6: Test Configuration Changes

Run tests to ensure nothing broke:

```bash
poetry run pytest tests/unit/test_config_and_detection.py -v
```

If tests pass, update AGENTS.md:

**File:** `AGENTS.md`

Update "Coding Style & Naming Conventions" section:

```markdown
## Configuration Management

Use the unified YAML-based configuration system for all settings:

```python
from sbir_transition_classifier.config import ConfigLoader
from sbir_transition_classifier.db.config import get_database_config

# Load full config
config = ConfigLoader.load_from_file("config/custom.yaml")

# Load just database config
db_config = get_database_config()
```

DO NOT use `core.config.settings` - it is deprecated.
```

**Commit:** `git commit -m "docs: update AGENTS.md with new config patterns"`

---

### Task 2: Consolidate CLI and Scripts (6-8 hours)

#### Step 2.1: Create New CLI Module Structure

Create these new files:

```bash
touch src/sbir_transition_classifier/cli/data.py
touch src/sbir_transition_classifier/cli/export.py
touch src/sbir_transition_classifier/cli/analysis.py
touch src/sbir_transition_classifier/cli/db.py
```

#### Step 2.2: Migrate load_bulk_data.py to cli/data.py

**File:** `src/sbir_transition_classifier/cli/data.py`

```python
"""Data loading CLI commands."""

import click
from pathlib import Path
from rich.console import Console
from loguru import logger

from ..ingestion import SbirIngester, ContractIngester


@click.group()
def data():
    """Data loading and ingestion commands."""
    pass


@data.command()
@click.option(
    "--file-path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the SBIR award data CSV file.",
)
@click.option(
    "--chunk-size",
    type=int,
    default=5000,
    help="Number of rows to process at a time."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def load_sbir(file_path: Path, chunk_size: int, verbose: bool):
    """Load SBIR award data from CSV file into database."""
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    
    ingester = SbirIngester(console=console, verbose=verbose)
    
    try:
        ingester.ingest(file_path, chunk_size=chunk_size)
        console.print("\n[green]✓ SBIR data loaded successfully[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Error loading SBIR data: {e}[/red]")
        raise click.Abort()


@data.command()
@click.option(
    "--file-path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the contract data CSV file.",
)
@click.option(
    "--chunk-size",
    type=int,
    default=50000,
    help="Number of rows to process at a time."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def load_contracts(file_path: Path, chunk_size: int, verbose: bool):
    """Load contract data from CSV file into database."""
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    
    ingester = ContractIngester(console=console, verbose=verbose)
    
    try:
        ingester.ingest(file_path, chunk_size=chunk_size)
        console.print("\n[green]✓ Contract data loaded successfully[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Error loading contract data: {e}[/red]")
        raise click.Abort()
```

#### Step 2.3: Migrate export_data.py to cli/export.py

**File:** `src/sbir_transition_classifier/cli/export.py`

```python
"""Data export CLI commands."""

import click
from pathlib import Path
from rich.console import Console
from loguru import logger

from ..scripts.export_data import (
    export_jsonl as _export_jsonl_impl,
    export_csv_summary as _export_csv_impl
)


@click.group()
def export():
    """Data export commands."""
    pass


@export.command()
@click.option(
    "--output-path",
    type=click.Path(path_type=Path),
    default="output/detections.jsonl",
    help="Path to the output JSONL file."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def jsonl(output_path: Path, verbose: bool):
    """Export detections to JSONL format."""
    # Call the implementation from scripts module
    # (We'll refactor the actual logic later)
    console = Console()
    
    try:
        _export_jsonl_impl(str(output_path), verbose)
        console.print(f"\n[green]✓ Exported to {output_path}[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Export failed: {e}[/red]")
        raise click.Abort()


@export.command()
@click.option(
    "--output-path",
    type=click.Path(path_type=Path),
    default="output/summary.csv",
    help="Path to the output CSV file."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging"
)
def csv(output_path: Path, verbose: bool):
    """Export detection summary to CSV format."""
    console = Console()
    
    try:
        _export_csv_impl(str(output_path))
        console.print(f"\n[green]✓ Exported to {output_path}[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Export failed: {e}[/red]")
        raise click.Abort()
```

#### Step 2.4: Update main CLI to Include New Commands

**File:** `src/sbir_transition_classifier/cli/main.py`

Update imports:

```python
from .data import data
from .export import export
```

Add to command registration (after existing commands):

```python
# Add command groups
main.add_command(data)
main.add_command(export)
```

#### Step 2.5: Update Documentation

**File:** `README.md`

Replace the "Step-by-Step Processing" section:

```markdown
### Usage

#### 1. Quick Bulk Processing (Recommended)
```bash
poetry run sbir-detect bulk-process --verbose
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
poetry run sbir-detect export jsonl --output-path output/detections.jsonl

# Export as CSV summary
poetry run sbir-detect export csv --output-path output/summary.csv
```

#### 3. View All Commands

```bash
poetry run sbir-detect --help
```
```

**Commit:** `git commit -m "feat(cli): consolidate data and export commands"`

#### Step 2.6: Add Deprecation Warnings to Old Scripts

**File:** `src/sbir_transition_classifier/scripts/load_bulk_data.py`

Add at the top of the file (after imports):

```python
import warnings

warnings.warn(
    "Direct script invocation is deprecated. Use 'sbir-detect data load-sbir' instead.",
    DeprecationWarning,
    stacklevel=2
)
```

Do the same for:
- `scripts/export_data.py`
- `scripts/enhanced_analysis.py`

**Commit:** `git commit -m "deprecate: add warnings to old script invocations"`

---

### Task 3: Expand Test Suite (12-16 hours)

#### Step 3.1: Create Shared Test Fixtures

**File:** `tests/conftest.py`

```python
"""Shared pytest fixtures for SBIR transition classifier tests."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from typing import Generator

from sqlalchemy.orm import Session

from sbir_transition_classifier.db.database import Base, engine, SessionLocal
from sbir_transition_classifier.core import models


@pytest.fixture(scope="session")
def test_db():
    """Create test database schema once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db) -> Generator[Session, None, None]:
    """Provide a clean database session for each test."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Clean up all data after each test
        session.query(models.Detection).delete()
        session.query(models.Contract).delete()
        session.query(models.SbirAward).delete()
        session.query(models.VendorIdentifier).delete()
        session.query(models.Vendor).delete()
        session.commit()
        session.close()


@pytest.fixture
def sample_vendor(db_session: Session) -> models.Vendor:
    """Create a sample vendor for testing."""
    vendor = models.Vendor(
        name="Test Vendor Inc",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(vendor)
    db_session.flush()
    return vendor


@pytest.fixture
def sample_sbir_award(db_session: Session, sample_vendor: models.Vendor) -> models.SbirAward:
    """Create a sample SBIR Phase II award."""
    completion_date = datetime.utcnow() - timedelta(days=180)  # 6 months ago
    
    award = models.SbirAward(
        vendor_id=sample_vendor.id,
        award_piid="TEST-SBIR-001",
        phase="Phase II",
        agency="Air Force",
        award_date=completion_date - timedelta(days=730),  # 2 years before completion
        completion_date=completion_date,
        topic="Advanced Widget Technology",
        raw_data={},
        created_at=datetime.utcnow()
    )
    db_session.add(award)
    db_session.flush()
    return award


@pytest.fixture
def sample_contract(db_session: Session, sample_vendor: models.Vendor) -> models.Contract:
    """Create a sample contract."""
    contract = models.Contract(
        vendor_id=sample_vendor.id,
        piid="TEST-CONTRACT-001",
        agency="Air Force",
        start_date=datetime.utcnow() - timedelta(days=90),  # 3 months ago
        naics_code="541712",
        psc_code="R425",
        competition_details={"extent_competed": "SOLE SOURCE"},
        raw_data={},
        created_at=datetime.utcnow()
    )
    db_session.add(contract)
    db_session.flush()
    return contract


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary configuration file."""
    config_content = """
schema_version: "1.0"

database:
  url: "sqlite:///:memory:"
  echo: false

detection:
  thresholds:
    high_confidence: 0.85
    likely_transition: 0.65
  
  weights:
    sole_source_bonus: 0.2
    timing_weight: 0.15
    agency_continuity: 0.25
    text_similarity: 0.1
  
  features:
    enable_cross_service: true
    enable_text_analysis: false
    enable_competed_contracts: true
  
  timing:
    max_months_after_phase2: 24
    min_months_after_phase2: 0

ingestion:
  data_formats:
    - csv
  encoding: utf-8
  chunk_size: 10000

output:
  formats:
    - jsonl
    - csv
  include_evidence: true
  evidence_detail_level: full
"""
    
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content)
    return config_path
```

**Commit:** `git commit -m "test: add shared pytest fixtures"`

#### Step 3.2: Create Config Tests

**File:** `tests/unit/config/test_loader.py`

```python
"""Tests for configuration loading."""

import pytest
from pathlib import Path

from sbir_transition_classifier.config.loader import ConfigLoader, ConfigLoadError
from sbir_transition_classifier.config.schema import ConfigSchema


def test_load_from_valid_file(temp_config_file: Path):
    """Test loading configuration from valid YAML file."""
    config = ConfigLoader.load_from_file(temp_config_file)
    
    assert isinstance(config, ConfigSchema)
    assert config.schema_version == "1.0"
    assert config.detection.thresholds.high_confidence == 0.85
    assert config.database.url == "sqlite:///:memory:"


def test_load_from_nonexistent_file():
    """Test loading configuration from non-existent file raises error."""
    with pytest.raises(ConfigLoadError, match="not found"):
        ConfigLoader.load_from_file(Path("nonexistent.yaml"))


def test_load_from_invalid_yaml(tmp_path: Path):
    """Test loading configuration from invalid YAML raises error."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("invalid: yaml: content:")
    
    with pytest.raises(ConfigLoadError, match="Invalid YAML"):
        ConfigLoader.load_from_file(invalid_file)


def test_load_from_dict():
    """Test loading configuration from dictionary."""
    config_dict = {
        "schema_version": "1.0",
        "detection": {
            "thresholds": {
                "high_confidence": 0.9,
                "likely_transition": 0.7
            }
        }
    }
    
    config = ConfigLoader.load_from_dict(config_dict)
    
    assert config.detection.thresholds.high_confidence == 0.9
    assert config.detection.thresholds.likely_transition == 0.7
```

**File:** `tests/unit/config/__init__.py` (empty file)

**Commit:** `git commit -m "test: add configuration loader tests"`

#### Step 3.3: Create Ingestion Tests

**File:** `tests/unit/ingestion/test_sbir_ingester.py`

```python
"""Tests for SBIR data ingestion."""

import pytest
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from rich.console import Console

from sbir_transition_classifier.ingestion.sbir import SbirIngester
from sbir_transition_classifier.core import models


@pytest.fixture
def sample_sbir_csv(tmp_path: Path) -> Path:
    """Create a sample SBIR CSV file."""
    csv_content = """Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic
Acme Corp,Phase II,Air Force,FA9550-20-C-0001,2020-01-15,2022-01-14,Widget Research,SBIR,Advanced Widgets
Beta Inc,Phase I,Navy,N00014-21-C-0001,2021-03-01,2021-09-01,Gadget Development,SBIR,Smart Gadgets"""
    
    csv_path = tmp_path / "sbir_test.csv"
    csv_path.write_text(csv_content)
    return csv_path


def test_sbir_ingestion_creates_vendors(db_session: Session, sample_sbir_csv: Path):
    """Test that SBIR ingestion creates vendor records."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)
    
    ingester.ingest(sample_sbir_csv, chunk_size=100)
    
    vendors = db_session.query(models.Vendor).all()
    assert len(vendors) == 2
    assert {v.name for v in vendors} == {"Acme Corp", "Beta Inc"}


def test_sbir_ingestion_creates_awards(db_session: Session, sample_sbir_csv: Path):
    """Test that SBIR ingestion creates award records."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)
    
    ingester.ingest(sample_sbir_csv, chunk_size=100)
    
    awards = db_session.query(models.SbirAward).all()
    assert len(awards) == 2
    
    phase2_award = next(a for a in awards if a.phase == "Phase II")
    assert phase2_award.award_piid == "FA9550-20-C-0001"
    assert phase2_award.agency == "Air Force"


def test_sbir_ingestion_handles_duplicates(db_session: Session, tmp_path: Path):
    """Test that re-ingesting same data doesn't create duplicates."""
    csv_content = """Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic
Acme Corp,Phase II,Air Force,FA9550-20-C-0001,2020-01-15,2022-01-14,Widget Research,SBIR,Advanced Widgets"""
    
    csv_path = tmp_path / "sbir_dup.csv"
    csv_path.write_text(csv_content)
    
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)
    
    # Ingest twice
    ingester.ingest(csv_path, chunk_size=100)
    ingester.ingest(csv_path, chunk_size=100)
    
    vendors = db_session.query(models.Vendor).all()
    awards = db_session.query(models.SbirAward).all()
    
    # Should only have one of each
    assert len(vendors) == 1
    assert len(awards) == 1
```

**File:** `tests/unit/ingestion/__init__.py` (empty file)

**Commit:** `git commit -m "test: add SBIR ingestion tests"`

#### Step 3.4: Create Detection Tests

**File:** `tests/unit/detection/test_scoring.py`

```python
"""Tests for detection scoring algorithms."""

import pytest
from datetime import datetime, timedelta

from sbir_transition_classifier.detection.scoring import ConfigurableScorer
from sbir_transition_classifier.config.schema import ConfigSchema


@pytest.fixture
def default_config():
    """Get default configuration."""
    return ConfigSchema()


@pytest.fixture
def scorer(default_config):
    """Create a scorer with default configuration."""
    return ConfigurableScorer(default_config)


def test_perfect_match_scores_high(scorer):
    """Test that a perfect match scores very high."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
    }
    
    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),  # 2 months after completion
        "competition_details": {"extent_competed": "SOLE SOURCE"},
    }
    
    score = scorer.score_transition(award_dict, contract_dict)
    
    assert score > 0.8  # Should be high confidence


def test_timing_too_late_scores_low(scorer):
    """Test that contract far after Phase II scores low."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2020, 1, 1),
        "phase": "Phase II",
    }
    
    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 1, 1),  # 3 years later
        "competition_details": {"extent_competed": "SOLE SOURCE"},
    }
    
    score = scorer.score_transition(award_dict, contract_dict)
    
    assert score < 0.3  # Should be low due to timing


def test_different_agency_reduces_score(scorer):
    """Test that different agencies reduce score."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
    }
    
    same_agency_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {},
    }
    
    diff_agency_contract = {
        "agency": "Navy",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {},
    }
    
    same_score = scorer.score_transition(award_dict, same_agency_contract)
    diff_score = scorer.score_transition(award_dict, diff_agency_contract)
    
    assert same_score > diff_score
```

**File:** `tests/unit/detection/__init__.py` (empty file)

**Commit:** `git commit -m "test: add detection scoring tests"`

#### Step 3.5: Update pytest Configuration

**File:** `pyproject.toml`

Add pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
]

[tool.coverage.run]
source = ["src/sbir_transition_classifier"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/scripts/*",  # Legacy scripts
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

**Commit:** `git commit -m "test: configure pytest and coverage"`

#### Step 3.6: Run Full Test Suite

```bash
# Run all tests with coverage
poetry run pytest --cov --cov-report=html --cov-report=term

# Check coverage
poetry run coverage report
```

**Commit:** `git commit -m "test: verify all tests pass"`

---

## Verification Checklist

After completing Phase 1, verify:

- [ ] All existing tests still pass
- [ ] New test coverage is above 50%
- [ ] Configuration can be loaded from YAML
- [ ] Database connection uses unified config
- [ ] CLI commands work: `sbir-detect data load-sbir --help`
- [ ] CLI commands work: `sbir-detect export jsonl --help`
- [ ] Old script invocations show deprecation warnings
- [ ] Documentation (README.md, AGENTS.md) is updated
- [ ] No import errors or circular dependencies

---

## Rollback Procedure

If something goes wrong:

```bash
# Reset to backup branch
git checkout backup/pre-refactor-YYYYMMDD

# Or reset specific files
git checkout HEAD~1 -- path/to/file.py

# Or abandon the feature branch
git checkout main
git branch -D refactor/consolidation-phase-1
```

---

## Next Steps

After Phase 1 is complete:

1. **Merge to main:**
   ```bash
   git checkout main
   git merge refactor/consolidation-phase-1
   git push
   ```

2. **Create Phase 2 branch:**
   ```bash
   git checkout -b refactor/consolidation-phase-2
   ```

3. **Begin Phase 2 tasks** (see REFACTORING_OPPORTUNITIES.md)

---

## Troubleshooting

### Issue: Import errors after moving modules

**Solution:** Update all import statements to use new paths. Run:
```bash
grep -r "from.*scripts" src/
```

### Issue: Tests fail with database errors

**Solution:** Ensure test database is clean:
```bash
rm -f sbir_transitions.db
poetry run pytest --create-db
```

### Issue: Configuration not loading

**Solution:** Check config file syntax:
```bash
poetry run sbir-detect config validate --config config/default.yaml
```

---

## Additional Resources

- [REFACTORING_OPPORTUNITIES.md](./REFACTORING_OPPORTUNITIES.md) - Full analysis
- [AGENTS.md](../AGENTS.md) - Coding guidelines
- [README.md](../README.md) - User documentation

---

**Questions?** Open an issue or contact the maintainers.