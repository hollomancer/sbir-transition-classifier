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
        updated_at=datetime.utcnow(),
    )
    db_session.add(vendor)
    db_session.flush()
    return vendor


@pytest.fixture
def sample_sbir_award(
    db_session: Session, sample_vendor: models.Vendor
) -> models.SbirAward:
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
        created_at=datetime.utcnow(),
    )
    db_session.add(award)
    db_session.flush()
    return award


@pytest.fixture
def sample_contract(
    db_session: Session, sample_vendor: models.Vendor
) -> models.Contract:
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
        created_at=datetime.utcnow(),
    )
    db_session.add(contract)
    db_session.flush()
    return contract


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary configuration file."""
    config_content = """schema_version: "1.0"

database:
  url: "sqlite:///:memory:"
  echo: false
  pool_size: 5
  pool_timeout: 30

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

  eligible_phases:
    - "Phase I"
    - "Phase II"

ingestion:
  data_formats:
    - csv
  encoding: utf-8
  chunk_size: 10000
  max_records: null

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
