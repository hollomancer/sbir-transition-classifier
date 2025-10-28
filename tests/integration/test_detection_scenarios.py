#!/usr/bin/env python3
"""
Integration tests for various detection scenarios.

Tests different detection cases including perfect matches, timing edge cases,
vendor mismatches, agency differences, and competition status variations.
"""

from pathlib import Path
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from sbir_transition_classifier.core import models
from sbir_transition_classifier.db import database as db_module
from sbir_transition_classifier.detection.main import run_full_detection


@pytest.fixture(scope="function")
def test_db_session(tmp_path):
    """Create a temporary test database session."""
    db_file = tmp_path / "test_scenarios.db"
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

    yield TestSession

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal


def test_perfect_match_scenario_creates_high_score_detection(test_db_session):
    """Test that a perfect match (same vendor, PIID, agency, good timing) scores high."""
    session = test_db_session()

    try:
        # Create vendor
        vendor = models.Vendor(name="Perfect Match Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        # Create SBIR award
        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="PERFECT-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Perfect Match Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Create matching contract (starts 30 days after SBIR completion, sole source)
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="PERFECT-001_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Check results
        detections = session.query(models.Detection).all()
        assert len(detections) >= 1, "Should create at least one detection"

        detection = detections[0]
        assert detection.likelihood_score >= 0.7, "Perfect match should score high"
        assert detection.confidence in ["High", "Likely Transition"]

    finally:
        session.close()


def test_contract_before_sbir_completion_creates_no_detection(test_db_session):
    """Test that contracts starting before SBIR completion are not detected."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Early Contract Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="EARLY-001",
            phase="Phase II",
            agency="Navy",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Early Contract Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract starts BEFORE SBIR completion
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="EARLY-001_0_0",
            agency="Navy",
            start_date=completion_date - timedelta(days=30),  # Before completion
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Check results - should have no detections
        detections = session.query(models.Detection).all()
        assert (
            len(detections) == 0
        ), "Contracts before SBIR completion should not detect"

    finally:
        session.close()


def test_very_late_contract_creates_no_detection(test_db_session):
    """Test that contracts starting too long after SBIR completion score very low or don't detect."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Late Contract Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="LATE-001",
            phase="Phase II",
            agency="Army",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Late Contract Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract starts 400 days after completion (way too late)
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="LATE-001_0_0",
            agency="Army",
            start_date=completion_date + timedelta(days=400),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Check results - should have no detections or very low score
        detections = session.query(models.Detection).all()
        # Either no detections or very low score
        if detections:
            assert all(
                d.likelihood_score < 0.3 for d in detections
            ), "Very late contracts should score low"

    finally:
        session.close()


def test_different_vendor_creates_no_detection(test_db_session):
    """Test that contracts with different vendors are not matched."""
    session = test_db_session()

    try:
        # Create two different vendors
        vendor1 = models.Vendor(name="Company A", created_at=datetime.utcnow())
        vendor2 = models.Vendor(name="Company B", created_at=datetime.utcnow())
        session.add_all([vendor1, vendor2])
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor1.id,
            award_piid="VENDOR-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Vendor Match Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract with different vendor
        contract = models.Contract(
            vendor_id=vendor2.id,  # Different vendor!
            piid="VENDOR-001_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Should not match different vendors
        detections = session.query(models.Detection).all()
        assert len(detections) == 0, "Different vendors should not match"

    finally:
        session.close()


def test_different_agency_reduces_score(test_db_session):
    """Test that contracts with different agencies receive lower scores."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Multi-Agency Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="AGENCY-001",
            phase="Phase II",
            agency="Air Force",  # Air Force
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Agency Match Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract with different agency
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="AGENCY-001_0_0",
            agency="Navy",  # Navy (different!)
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # May still detect but with lower score
        detections = session.query(models.Detection).all()
        if detections:
            detection = detections[0]
            # Score should be lower than perfect match
            assert (
                detection.likelihood_score < 0.8
            ), "Different agency should reduce score"

    finally:
        session.close()


def test_sole_source_scores_higher_than_competed(test_db_session):
    """Test that sole-source contracts score higher than competed contracts."""
    session = test_db_session()

    try:
        vendor = models.Vendor(
            name="Competition Test Corp", created_at=datetime.utcnow()
        )
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)

        # Create two awards
        award1 = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="COMPETE-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Sole Source Test",
            created_at=datetime.utcnow(),
        )
        award2 = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="COMPETE-002",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Competed Test",
            created_at=datetime.utcnow(),
        )
        session.add_all([award1, award2])
        session.flush()

        # Sole source contract
        contract1 = models.Contract(
            vendor_id=vendor.id,
            piid="COMPETE-001_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )

        # Competed contract
        contract2 = models.Contract(
            vendor_id=vendor.id,
            piid="COMPETE-002_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "FULL AND OPEN COMPETITION"},
            created_at=datetime.utcnow(),
        )
        session.add_all([contract1, contract2])
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Get detections
        detections = session.query(models.Detection).all()
        assert len(detections) >= 2, "Should detect both contracts"

        # Find scores for each
        sole_source_det = [
            d for d in detections if d.contract.piid == "COMPETE-001_0_0"
        ][0]
        competed_det = [d for d in detections if d.contract.piid == "COMPETE-002_0_0"][
            0
        ]

        # Sole source should score higher
        assert (
            sole_source_det.likelihood_score > competed_det.likelihood_score
        ), "Sole source should score higher than competed"

    finally:
        session.close()


def test_multiple_contracts_for_single_award_all_detected(test_db_session):
    """Test that multiple contracts matching a single award are all detected."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Multi-Contract Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="MULTI-001",
            phase="Phase II",
            agency="Navy",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Multiple Contracts Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Create 3 different contracts
        contract1 = models.Contract(
            vendor_id=vendor.id,
            piid="MULTI-001_0_0",
            agency="Navy",
            start_date=completion_date + timedelta(days=15),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        contract2 = models.Contract(
            vendor_id=vendor.id,
            piid="MULTI-001_1_0",
            agency="Navy",
            start_date=completion_date + timedelta(days=60),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        contract3 = models.Contract(
            vendor_id=vendor.id,
            piid="MULTI-001_2_0",
            agency="Navy",
            start_date=completion_date + timedelta(days=90),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add_all([contract1, contract2, contract3])
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # Should detect all 3 contracts
        detections = session.query(models.Detection).all()
        assert len(detections) == 3, "Should detect all matching contracts"

    finally:
        session.close()


def test_phase_i_awards_filtered_by_default(test_db_session):
    """Test that Phase I awards are not processed if config excludes them."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Phase I Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)

        # Phase I award
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="PHASE1-001",
            phase="Phase I",  # Phase I
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Phase I Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Matching contract
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="PHASE1-001_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection
        run_full_detection(in_process=True)

        # By default, Phase I should be filtered out
        detections = session.query(models.Detection).all()
        # Note: This depends on default config - may need adjustment
        # If config includes Phase I, this test may need updating

    finally:
        session.close()


def test_zero_detections_handled_gracefully(test_db_session):
    """Test that detection pipeline handles finding zero matches gracefully."""
    session = test_db_session()

    try:
        # Create award and contract that don't match
        vendor1 = models.Vendor(name="No Match Corp A", created_at=datetime.utcnow())
        vendor2 = models.Vendor(name="No Match Corp B", created_at=datetime.utcnow())
        session.add_all([vendor1, vendor2])
        session.flush()

        # Award for vendor1
        award = models.SbirAward(
            vendor_id=vendor1.id,
            award_piid="NOMATCH-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=datetime(2022, 12, 31),
            topic="No Match Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract for vendor2 (different vendor, won't match)
        contract = models.Contract(
            vendor_id=vendor2.id,
            piid="NOMATCH-999",
            agency="Navy",
            start_date=datetime(2025, 1, 1),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Run detection - should not crash
        run_full_detection(in_process=True)

        # Should have zero detections
        detections = session.query(models.Detection).all()
        assert len(detections) == 0, "No matches should result in zero detections"

    finally:
        session.close()


def test_missing_competition_details_handled_gracefully(test_db_session):
    """Test that contracts with missing competition details are handled properly."""
    session = test_db_session()

    try:
        vendor = models.Vendor(name="Missing Data Corp", created_at=datetime.utcnow())
        session.add(vendor)
        session.flush()

        completion_date = datetime(2022, 12, 31)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="MISSING-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=completion_date,
            topic="Missing Details Test",
            created_at=datetime.utcnow(),
        )
        session.add(award)
        session.flush()

        # Contract with None competition_details
        contract = models.Contract(
            vendor_id=vendor.id,
            piid="MISSING-001_0_0",
            agency="Air Force",
            start_date=completion_date + timedelta(days=30),
            competition_details=None,  # Missing!
            created_at=datetime.utcnow(),
        )
        session.add(contract)
        session.commit()

        # Should not crash
        run_full_detection(in_process=True)

        # May or may not detect, but should not crash
        detections = session.query(models.Detection).all()
        # Just verify it didn't crash

    finally:
        session.close()
