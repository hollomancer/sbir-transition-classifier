import os
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from sbir_transition_classifier.config.loader import ConfigLoader
from sbir_transition_classifier.config.schema import ConfigSchema
from sbir_transition_classifier.db.database import Base, SessionLocal, engine
from sbir_transition_classifier.core import models
from sbir_transition_classifier.db import queries
from sbir_transition_classifier.ingestion import SbirIngester
from sbir_transition_classifier.detection import scoring


def reset_db():
    # Drop and recreate all tables on the current engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_config_loads_and_has_phases():
    cfg = ConfigLoader.load_default()
    assert isinstance(cfg, ConfigSchema)
    assert "Phase II" in cfg.detection.eligible_phases
    assert (
        cfg.detection.timing.max_months_after_phase2
        >= cfg.detection.timing.min_months_after_phase2
    )


def test_config_ordering_validations():
    # Threshold ordering: likely_transition must be <= high_confidence
    with pytest.raises(ValidationError):
        ConfigSchema(
            detection={
                "thresholds": {
                    "high_confidence": 0.80,
                    "likely_transition": 0.90,  # invalid ordering
                }
            }
        )

    # Timing ordering: min must be < max
    with pytest.raises(ValidationError):
        ConfigSchema(
            detection={
                "timing": {
                    "min_months_after_phase2": 24,
                    "max_months_after_phase2": 24,  # invalid (must be strictly less)
                }
            }
        )


def test_scoring_thresholds_and_labels():
    cfg = ConfigSchema()  # defaults: high=0.85, likely=0.65
    scorer = scoring.ConfigurableScorer(cfg)

    assert scorer.meets_threshold(0.90) == (True, "High Confidence")
    assert scorer.meets_threshold(0.70) == (True, "Likely Transition")
    assert scorer.meets_threshold(0.50) == (False, "Below Threshold")


def test_heuristics_timing_window_filters_contracts():
    reset_db()
    db = SessionLocal()
    try:
        # Create a vendor
        vendor = models.Vendor(name="Acme Test Co", created_at=datetime.utcnow())
        db.add(vendor)
        db.flush()

        # Create Phase II award with known completion date
        completion = datetime.utcnow().replace(microsecond=0)
        award = models.SbirAward(
            vendor_id=vendor.id,
            award_piid="AWD-001",
            phase="Phase II",
            agency="Air Force",
            award_date=completion - timedelta(days=30),
            completion_date=completion,
            topic="Test Topic",
            created_at=datetime.utcnow(),
        )
        db.add(award)
        db.flush()

        # Contract within default window (24 months): +60 days
        within = models.Contract(
            vendor_id=vendor.id,
            piid="CNTR-001_0_0",
            agency="Air Force",
            start_date=completion + timedelta(days=60),
            competition_details={"extent_competed": "FULL AND OPEN COMPETITION"},
            created_at=datetime.utcnow(),
        )
        db.add(within)

        # Contract outside default window: +800 days ( > 24 months )
        outside = models.Contract(
            vendor_id=vendor.id,
            piid="CNTR-002_0_0",
            agency="Air Force",
            start_date=completion + timedelta(days=800),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        db.add(outside)
        db.commit()

        candidates = queries.find_candidate_contracts(db, award)
        piids = {c.piid for c in candidates}

        assert "CNTR-001_0_0" in piids
        assert "CNTR-002_0_0" not in piids
        assert len(piids) == 1
    finally:
        db.close()


def test_sbir_ingestion_dedupe(tmp_path):
    reset_db()
    db = SessionLocal()
    try:
        # Create a small SBIR CSV with a duplicate row
        csv_path = tmp_path / "award_data.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "Company,Phase,Agency,Award Number,Proposal Award Date,Contract End Date,Award Title,Program,Topic,Award Year",
                    "Acme Widgets,Phase II,Air Force,FA0001,2022-01-01,2022-12-31,Widget Research,SBIR,Widgets,2022",
                    "Acme Widgets,Phase II,Air Force,FA0001,2022-01-01,2022-12-31,Widget Research,SBIR,Widgets,2022",
                ]
            ),
            encoding="utf-8",
        )

        ingester = SbirIngester(verbose=False)

        # First ingest should insert 1 award and skip the duplicate row in-batch
        stats1 = ingester.ingest(csv_path, chunk_size=1000)
        awards_count1 = db.query(models.SbirAward).count()
        assert stats1.valid_records == 1
        assert stats1.duplicates_skipped >= 1
        assert awards_count1 == 1

        # Second ingest should insert 0 new awards and skip both rows as duplicates
        stats2 = ingester.ingest(csv_path, chunk_size=1000)
        awards_count2 = db.query(models.SbirAward).count()
        assert stats2.valid_records == 0
        assert stats2.duplicates_skipped >= 2
        assert awards_count2 == 1
    finally:
        db.close()
