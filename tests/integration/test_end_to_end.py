#!/usr/bin/env python3
"""
Integration test: end-to-end small pipeline run

This test sets up a temporary SQLite database, inserts a vendor, an SBIR Phase II award,
and a contract that falls within the configured detection window. It then invokes the
synchronous detection path and asserts that at least one Detection row is produced.

Note: This is a lightweight integration test that avoids multiprocessing paths (which
can be brittle in CI). It exercises ingestion->heuristics->scoring->DB write flow via
the synchronous helper `run_detection_for_award`.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from sbir_transition_classifier.core import models
import sbir_transition_classifier.db.database as db_module
import sbir_transition_classifier.detection.main as detection_main


@pytest.fixture(scope="function")
def tmp_sqlite_session(tmp_path):
    """
    Create a temporary sqlite DB and swap the package SessionLocal/engine to point
    at the test engine for the duration of the test.
    """
    # Prepare temp sqlite URL and engine
    db_file = tmp_path / "test_integration.db"
    db_url = f"sqlite:///{db_file}"

    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}, poolclass=NullPool
    )

    # Create tables using the package's metadata
    models.Base.metadata.create_all(bind=engine)

    # Create a test Session factory
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Backup original SessionLocal and engine, then swap in test ones
    orig_SessionLocal = getattr(db_module, "SessionLocal", None)
    orig_engine = getattr(db_module, "engine", None)
    db_module.SessionLocal = TestSession
    db_module.engine = engine

    try:
        yield TestSession
    finally:
        # Restore original SessionLocal and engine to avoid side-effects
        if orig_SessionLocal is not None:
            db_module.SessionLocal = orig_SessionLocal
        else:
            delattr(db_module, "SessionLocal")
        if orig_engine is not None:
            db_module.engine = orig_engine
        else:
            delattr(db_module, "engine")


def test_end_to_end_detection(tmp_sqlite_session):
    """
    Insert a vendor, a Phase II SBIR award, and a contract within the detection window.
    Run the synchronous detection function and assert that a detection is written.
    """
    Session = tmp_sqlite_session
    db = Session()

    try:
        # Create vendor
        vendor = models.Vendor(name="Integration Test Co", created_at=datetime.utcnow())
        db.add(vendor)
        db.flush()  # ensure vendor.id is available

        # Create a Phase II award with a recent completion date
        completion = datetime.utcnow().replace(microsecond=0)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="INT-AWD-001",
            phase="Phase II",
            agency="Air Force",
            award_date=completion - timedelta(days=30),
            completion_date=completion,
            topic="Integration Widgets",
            created_at=datetime.utcnow(),
        )
        db.add(award)
        db.flush()

        # Create a contract that starts within the default detection window (+60 days)
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="INT-CNTR-001",
            agency="Air Force",
            start_date=completion + timedelta(days=60),
            competition_details={"extent_competed": "NOT COMPETED"},
            raw_data={"description": "Follow-on work for Integration Widgets"},
            created_at=datetime.utcnow(),
        )
        db.add(contract)
        db.commit()

        # At this point the DB has vendor, award, and contract. Run detection synchronously.
        # Use the synchronous helper to avoid multiprocessing complexity in tests.
        detection_main.run_detection_for_award(db, award)

        # Refresh and assert detections were created
        det_count = db.query(models.Detection).count()
        assert det_count >= 1, "Expected at least one detection to be created"

        detection = db.query(models.Detection).first()
        assert detection.likelihood_score is not None
        assert detection.evidence_bundle is not None
        assert detection.sbir_award_id == award.id
        assert detection.contract_id == contract.id

    finally:
        db.close()
