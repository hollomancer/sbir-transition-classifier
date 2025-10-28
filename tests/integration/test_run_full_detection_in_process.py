#!/usr/bin/env python3
"""
Integration test: run_full_detection(in_process=True) end-to-end using small CSVs.

This test:
- Creates a temporary SQLite database and swaps the package SessionLocal/engine
  to point to the test engine for the duration of the test.
- Writes minimal SBIR and contract CSV files expected by the ingesters.
- Runs the SBIR and contract ingesters to populate the DB.
- Invokes `run_full_detection(in_process=True)` to run the detection pipeline
  serially (no multiprocessing) and asserts that detections are created.

This test is intended to be reasonably fast and deterministic for CI.
"""

from datetime import datetime, timedelta
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
def tmp_sqlite_session(tmp_path):
    """Create a temporary sqlite DB and swap package SessionLocal/engine for test scope."""
    db_file = tmp_path / "test_pipeline.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}, poolclass=NullPool
    )
    # Create tables on the test engine
    models.Base.metadata.create_all(bind=engine)
    # Create a test session factory
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    # Backup original references
    orig_SessionLocal = getattr(db_module, "SessionLocal", None)
    orig_engine = getattr(db_module, "engine", None)

    # Swap in test session + engine
    db_module.SessionLocal = TestSession
    db_module.engine = engine

    try:
        yield TestSession
    finally:
        # Restore original package SessionLocal and engine
        if orig_SessionLocal is not None:
            db_module.SessionLocal = orig_SessionLocal
        else:
            try:
                delattr(db_module, "SessionLocal")
            except Exception:
                pass
        if orig_engine is not None:
            db_module.engine = orig_engine
        else:
            try:
                delattr(db_module, "engine")
            except Exception:
                pass


def _write_sample_sbir_csv(path: Path):
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
        ],
        # A single Phase II award; award number present in Award Number column
        [
            "Acme Widgets",
            "Phase II",
            "Air Force",
            "FA0001",
            "2022-01-01",
            "2022-12-31",
            "Widget Research",
            "SBIR",
            "Widgets",
        ],
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def _write_sample_contract_csv(path: Path):
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
        # Contract that references the SBIR award PIID and starts within window (+60 days)
        [
            "FA0001",
            "Air Force",
            "Acme Widgets",
            "0",
            "0",
            "2023-03-01",
            "NOT COMPETED",
            "Firm-Fixed-Price",
        ],
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def test_run_full_detection_in_process(tmp_path, tmp_sqlite_session):
    """
    Full integration test using the in-process detection mode.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    award_csv = data_dir / "award_data.csv"
    contract_csv = data_dir / "contracts_1.csv"

    # Write small CSV fixtures
    _write_sample_sbir_csv(award_csv)
    _write_sample_contract_csv(contract_csv)

    # Instantiate ingesters and run ingestion (they use db_module.SessionLocal which
    # has been swapped to the test session factory by the fixture)
    sbir_ingester = SbirIngester(verbose=False)
    stats_award = sbir_ingester.ingest(award_csv, chunk_size=1000)
    assert (
        stats_award.valid_records >= 1
    ), "SBIR ingester should register at least one valid record"

    contract_ingester = ContractIngester(verbose=False)
    stats_contract = contract_ingester.ingest(contract_csv, chunk_size=1000)
    assert (
        stats_contract.valid_records >= 1
    ), "Contract ingester should register at least one valid record"

    # Now run the detection pipeline in-process (deterministic, no multiprocessing)
    # This will query the DB and write detections to the same DB
    run_full_detection(in_process=True)

    # Check that detections were created
    Session = db_module.SessionLocal
    session = Session()
    try:
        det_count = session.query(models.Detection).count()
        assert det_count >= 1, f"Expected at least 1 detection, got {det_count}"

        # Basic sanity checks on the first detection
        detection = session.query(models.Detection).first()
        assert detection.likelihood_score is not None
        assert detection.evidence_bundle is not None
        assert detection.sbir_award_id is not None
        assert detection.contract_id is not None

        # Evidence bundle should contain source_sbir_award and source_contract structure
        eb = detection.evidence_bundle or {}
        assert "source_sbir_award" in eb
        assert "source_contract" in eb

    finally:
        session.close()
