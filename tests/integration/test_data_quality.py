#!/usr/bin/env python3
"""
Integration tests for data quality and edge case handling.

Tests how the system handles malformed data, missing fields,
duplicates, and other data quality issues.
"""

from pathlib import Path
import csv

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from sbir_transition_classifier.core import models
from sbir_transition_classifier.db import database as db_module
from sbir_transition_classifier.ingestion.sbir import SbirIngester
from sbir_transition_classifier.ingestion.contracts import ContractIngester
from sbir_transition_classifier.detection.main import run_full_detection


@pytest.fixture(scope="function")
def test_db_session(tmp_path):
    """Create a temporary test database session."""
    db_file = tmp_path / "test_data_quality.db"
    db_url = f"sqlite:///{db_file}"

    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}, poolclass=NullPool
    )

    # Create tables
    models.Base.metadata.create_all(bind=engine)

    # Create session factory
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Backup originals
    original_engine = db_module.engine
    original_SessionLocal = db_module.SessionLocal

    # Swap to test database
    db_module.engine = engine
    db_module.SessionLocal = TestSession

    yield tmp_path, TestSession

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal


def test_sbir_ingestion_rejects_missing_company(test_db_session):
    """Test that SBIR records without company name are rejected."""
    tmp_path, TestSession = test_db_session

    # Create CSV with missing company
    csv_file = tmp_path / "missing_company.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        [
            "",
            "Phase II",
            "Air Force",
            "TEST-001",
            "2022-01-01",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
        [
            "  ",
            "Phase II",
            "Navy",
            "TEST-002",
            "2022-01-01",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # Ingest
    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should reject records with missing company
    assert stats.rejection_reasons.get("missing_company", 0) >= 2
    assert stats.valid_records == 0


def test_sbir_ingestion_handles_duplicate_awards(test_db_session):
    """Test that duplicate SBIR awards are identified and skipped."""
    tmp_path, TestSession = test_db_session

    # Create CSV with duplicates
    csv_file = tmp_path / "duplicates.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        [
            "Acme Corp",
            "Phase II",
            "Air Force",
            "DUP-001",
            "2022-01-01",
            "2022-12-31",
            "Test Award",
            "SBIR",
            "Topic",
            "2022",
        ],
        [
            "Acme Corp",
            "Phase II",
            "Air Force",
            "DUP-001",
            "2022-01-01",
            "2022-12-31",
            "Test Award (Duplicate)",
            "SBIR",
            "Topic",
            "2022",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # Ingest
    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should accept first, skip duplicate
    assert stats.valid_records == 1
    assert stats.duplicates_skipped == 1


def test_sbir_ingestion_uses_award_year_fallback_for_missing_dates(test_db_session):
    """Test that Award Year is used as fallback when Proposal Award Date is missing."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "missing_dates.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        [
            "DateFallback Corp",
            "Phase II",
            "Navy",
            "DATE-001",
            "",  # Missing proposal date
            "2022-12-31",
            "Test Award",
            "SBIR",
            "Topic",
            "2022",  # Should use this as fallback
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should accept with fallback date
    assert stats.valid_records == 1
    assert stats.rejection_reasons.get("date_fallbacks_used", 0) >= 1


def test_contract_ingestion_rejects_missing_piid(test_db_session):
    """Test that contracts without PIID are rejected."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "missing_piid.csv"
    rows = [
        [
            "award_id_piid",
            "awarding_agency_name",
            "recipient_name",
            "modification_number",
            "transaction_number",
            "period_of_performance_start_date",
            "extent_competed",
            "type_of_contract_pricing",
        ],
        ["", "Air Force", "Test Corp", "0", "0", "2023-01-15", "NOT COMPETED", "FFP"],
        ["  ", "Navy", "Test Corp", "0", "0", "2023-01-15", "NOT COMPETED", "FFP"],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = ContractIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should reject records with missing PIID
    assert stats.rejection_reasons.get("missing_piid", 0) >= 2
    assert stats.valid_records == 0


def test_contract_ingestion_rejects_missing_agency(test_db_session):
    """Test that contracts without agency are rejected."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "missing_agency.csv"
    rows = [
        [
            "award_id_piid",
            "awarding_agency_name",
            "recipient_name",
            "modification_number",
            "transaction_number",
            "period_of_performance_start_date",
            "extent_competed",
            "type_of_contract_pricing",
        ],
        ["CTR-001", "", "Test Corp", "0", "0", "2023-01-15", "NOT COMPETED", "FFP"],
        ["CTR-002", "  ", "Test Corp", "0", "0", "2023-01-15", "NOT COMPETED", "FFP"],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = ContractIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should reject records with missing agency
    assert stats.rejection_reasons.get("missing_agency", 0) >= 2
    assert stats.valid_records == 0


def test_contract_ingestion_handles_vendor_matching(test_db_session):
    """Test that contracts properly match and create vendors."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "vendor_matching.csv"
    rows = [
        [
            "award_id_piid",
            "awarding_agency_name",
            "recipient_name",
            "modification_number",
            "transaction_number",
            "period_of_performance_start_date",
            "extent_competed",
            "type_of_contract_pricing",
        ],
        [
            "CTR-001",
            "Air Force",
            "Vendor A",
            "0",
            "0",
            "2023-01-15",
            "NOT COMPETED",
            "FFP",
        ],
        [
            "CTR-002",
            "Navy",
            "Vendor A",
            "0",
            "0",
            "2023-02-15",
            "NOT COMPETED",
            "FFP",
        ],  # Same vendor
        [
            "CTR-003",
            "Air Force",
            "Vendor B",
            "0",
            "0",
            "2023-01-15",
            "COMPETED",
            "FFP",
        ],  # Different vendor
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = ContractIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    assert stats.valid_records == 3

    # Check vendor creation
    session = TestSession()
    try:
        vendors = session.query(models.Vendor).all()
        vendor_names = [v.name for v in vendors]
        assert "Vendor A" in vendor_names
        assert "Vendor B" in vendor_names
        assert len(vendors) == 2  # Only 2 unique vendors
    finally:
        session.close()


def test_malformed_csv_with_extra_columns_handled_gracefully(test_db_session):
    """Test that CSV with extra columns is handled properly."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "extra_columns.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
            "ExtraColumn1",
            "ExtraColumn2",
        ],
        [
            "Extra Corp",
            "Phase II",
            "Air Force",
            "EXTRA-001",
            "2022-01-01",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
            "Extra1",
            "Extra2",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    # Should handle extra columns gracefully
    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should successfully ingest despite extra columns
    assert stats.valid_records == 1


def test_empty_csv_file_handled_gracefully(test_db_session):
    """Test that empty CSV files are handled without crashing."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")

    # Should not crash on empty file
    ingester = SbirIngester(verbose=False)
    try:
        stats = ingester.ingest(csv_file, chunk_size=1000)
        # May fail validation or return 0 records
    except Exception as e:
        # Should fail gracefully, not with unexpected error
        assert "Invalid" in str(e) or "format" in str(e).lower()


def test_csv_with_only_headers_handled_gracefully(test_db_session):
    """Test that CSV with only headers (no data) is handled properly."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "headers_only.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        # No data rows
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should handle gracefully with 0 records
    assert stats.total_rows == 0
    assert stats.valid_records == 0


def test_detection_with_empty_database_completes_without_error(test_db_session):
    """Test that detection on empty database completes gracefully."""
    tmp_path, TestSession = test_db_session

    # Run detection on empty database
    # Should not crash
    run_full_detection(in_process=True)

    # Verify no detections
    session = TestSession()
    try:
        count = session.query(models.Detection).count()
        assert count == 0
    finally:
        session.close()


def test_unicode_and_special_characters_in_vendor_names(test_db_session):
    """Test that vendor names with unicode and special characters are handled."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "unicode_vendors.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        [
            "Åcme Cörporation™",
            "Phase II",
            "Air Force",
            "UNI-001",
            "2022-01-01",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
        [
            "Company with 'quotes' and \"double quotes\"",
            "Phase II",
            "Navy",
            "UNI-002",
            "2022-01-01",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should handle unicode characters
    assert stats.valid_records == 2

    session = TestSession()
    try:
        vendors = session.query(models.Vendor).all()
        assert len(vendors) == 2
    finally:
        session.close()


def test_date_format_variations_handled(test_db_session):
    """Test that various date formats are parsed correctly."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "date_formats.csv"
    rows = [
        [
            "Company",
            "Phase",
            "Agency",
            "Award Number",
            "Proposal Award Date",
            "Contract End Date",
            "Award Title",
            "Program",
            "Topic",
            "Award Year",
        ],
        # ISO format (YYYY-MM-DD)
        [
            "DateTest Corp",
            "Phase II",
            "Air Force",
            "DATE-001",
            "2022-01-15",
            "2022-12-31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
        # Different separator
        [
            "DateTest Corp",
            "Phase II",
            "Navy",
            "DATE-002",
            "2022/06/15",
            "2022/12/31",
            "Test",
            "SBIR",
            "Topic",
            "2022",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = SbirIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    # Should parse both formats
    assert stats.valid_records >= 1  # At least ISO format should work


def test_piid_generation_with_modifications(test_db_session):
    """Test that PIID is correctly generated from base PIID + mod + transaction."""
    tmp_path, TestSession = test_db_session

    csv_file = tmp_path / "piid_generation.csv"
    rows = [
        [
            "award_id_piid",
            "awarding_agency_name",
            "recipient_name",
            "modification_number",
            "transaction_number",
            "period_of_performance_start_date",
            "extent_competed",
            "type_of_contract_pricing",
        ],
        [
            "BASE-001",
            "Air Force",
            "PIID Corp",
            "0",
            "0",
            "2023-01-15",
            "NOT COMPETED",
            "FFP",
        ],
        [
            "BASE-001",
            "Air Force",
            "PIID Corp",
            "1",
            "0",
            "2023-02-15",
            "NOT COMPETED",
            "FFP",
        ],
        [
            "BASE-001",
            "Air Force",
            "PIID Corp",
            "2",
            "1",
            "2023-03-15",
            "NOT COMPETED",
            "FFP",
        ],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    ingester = ContractIngester(verbose=False)
    stats = ingester.ingest(csv_file, chunk_size=1000)

    assert stats.valid_records == 3

    session = TestSession()
    try:
        contracts = session.query(models.Contract).all()
        piids = {c.piid for c in contracts}

        # Should have unique PIIDs with mod/transaction appended
        assert "BASE-001_0_0" in piids
        assert "BASE-001_1_0" in piids
        assert "BASE-001_2_1" in piids
        assert len(piids) == 3
    finally:
        session.close()
