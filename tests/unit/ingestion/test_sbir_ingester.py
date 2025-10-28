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
    csv_content = """Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic,Award Year
Acme Corp,Phase II,Air Force,FA9550-20-C-0001,2020-01-15,2022-01-14,Widget Research,SBIR,Advanced Widgets,2020
Beta Inc,Phase I,Navy,N00014-21-C-0001,2021-03-01,2021-09-01,Gadget Development,SBIR,Smart Gadgets,2021
Gamma LLC,Phase II,Army,W911NF-19-C-0001,2019-06-01,2021-06-01,Sensor Tech,SBIR,Advanced Sensors,2019"""

    csv_path = tmp_path / "sbir_test.csv"
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def minimal_sbir_csv(tmp_path: Path) -> Path:
    """Create a minimal SBIR CSV with just required fields."""
    csv_content = """Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic,Award Year
TestCo,Phase I,Air Force,TEST-001,2020-01-01,2020-12-31,Test Award,SBIR,Test Topic,2020"""

    csv_path = tmp_path / "minimal_sbir.csv"
    csv_path.write_text(csv_content)
    return csv_path


def test_sbir_ingestion_creates_vendors(db_session: Session, sample_sbir_csv: Path):
    """Test that SBIR ingestion creates vendor records."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(sample_sbir_csv, chunk_size=100)

    vendors = db_session.query(models.Vendor).all()
    vendor_names = {v.name for v in vendors}
    # Check that all expected vendors are present (may have more from other tests)
    assert {"Acme Corp", "Beta Inc", "Gamma LLC"}.issubset(vendor_names)
    assert len(vendors) >= 3


def test_sbir_ingestion_creates_awards(db_session: Session, sample_sbir_csv: Path):
    """Test that SBIR ingestion creates award records."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(sample_sbir_csv, chunk_size=100)

    awards = db_session.query(models.SbirAward).all()
    assert len(awards) == 3

    phase2_awards = [a for a in awards if a.phase == "Phase II"]
    assert len(phase2_awards) == 2

    # Check specific award details
    acme_award = next(a for a in awards if "FA9550" in a.award_piid)
    assert acme_award.phase == "Phase II"
    assert acme_award.agency == "Air Force"
    assert acme_award.topic == "Advanced Widgets"


def test_sbir_ingestion_handles_duplicates(db_session: Session, tmp_path: Path):
    """Test that re-ingesting same data doesn't create duplicates."""
    csv_content = """Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic,Award Year
Acme Corp,Phase II,Air Force,FA9550-20-C-0001,2020-01-15,2022-01-14,Widget Research,SBIR,Advanced Widgets,2020"""

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


def test_sbir_ingestion_links_vendor_to_award(
    db_session: Session, minimal_sbir_csv: Path
):
    """Test that awards are correctly linked to vendors."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(minimal_sbir_csv, chunk_size=100)

    vendor = db_session.query(models.Vendor).first()
    award = db_session.query(models.SbirAward).first()

    assert award.vendor_id == vendor.id
    assert vendor.name == "TestCo"


def test_sbir_ingestion_parses_dates_correctly(
    db_session: Session, minimal_sbir_csv: Path
):
    """Test that dates are correctly parsed."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(minimal_sbir_csv, chunk_size=100)

    award = db_session.query(models.SbirAward).first()

    assert award.award_date is not None
    assert award.completion_date is not None
    assert award.award_date.year == 2020
    assert award.completion_date.year == 2020


def test_sbir_ingestion_stores_raw_data(db_session: Session, minimal_sbir_csv: Path):
    """Test that raw data is stored in JSON field."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(minimal_sbir_csv, chunk_size=100)

    award = db_session.query(models.SbirAward).first()

    assert award.raw_data is not None
    assert isinstance(award.raw_data, dict)


def test_sbir_ingestion_handles_missing_file():
    """Test that ingesting non-existent file raises appropriate error."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    with pytest.raises(Exception):
        ingester.ingest(Path("nonexistent.csv"), chunk_size=100)


def test_sbir_ingestion_processes_multiple_phases(
    db_session: Session, sample_sbir_csv: Path
):
    """Test that both Phase I and Phase II awards are processed."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(sample_sbir_csv, chunk_size=100)

    phase1_count = db_session.query(models.SbirAward).filter_by(phase="Phase I").count()
    phase2_count = (
        db_session.query(models.SbirAward).filter_by(phase="Phase II").count()
    )

    assert phase1_count == 1
    assert phase2_count == 2


def test_sbir_ingestion_handles_different_agencies(
    db_session: Session, sample_sbir_csv: Path
):
    """Test that awards from different agencies are processed."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(sample_sbir_csv, chunk_size=100)

    agencies = {award.agency for award in db_session.query(models.SbirAward).all()}

    assert agencies == {"Air Force", "Navy", "Army"}


def test_sbir_ingestion_creates_timestamps(db_session: Session, minimal_sbir_csv: Path):
    """Test that created_at timestamps are set."""
    console = Console()
    ingester = SbirIngester(console=console, verbose=False)

    ingester.ingest(minimal_sbir_csv, chunk_size=100)

    award = db_session.query(models.SbirAward).first()
    vendor = db_session.query(models.Vendor).first()

    assert award.created_at is not None
    assert vendor.created_at is not None
    assert isinstance(award.created_at, datetime)
    assert isinstance(vendor.created_at, datetime)
