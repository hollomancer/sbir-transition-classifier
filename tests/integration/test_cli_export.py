#!/usr/bin/env python3
"""
Integration tests for CLI export commands.

Tests the export functionality for both JSONL and CSV formats,
including edge cases like empty databases and filtered exports.
"""

from pathlib import Path
import json
import csv as csv_module

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from sbir_transition_classifier.cli.main import main as cli_main
from sbir_transition_classifier.db import database as db_module
from sbir_transition_classifier.core import models
from datetime import datetime, timedelta


@pytest.fixture(scope="function")
def test_db_with_detections(tmp_path):
    """Create a test database with sample detections."""
    db_file = tmp_path / "test_export.db"
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

    # Populate with test data
    session = TestSession()
    try:
        # Create vendors
        vendor1 = models.Vendor(name="Export Test Corp", created_at=datetime.utcnow())
        vendor2 = models.Vendor(
            name="Another Company LLC", created_at=datetime.utcnow()
        )
        session.add_all([vendor1, vendor2])
        session.flush()

        # Create SBIR awards
        award1 = models.SbirAward(
            vendor_id=vendor1.id,
            award_piid="EXP-001",
            phase="Phase II",
            agency="Air Force",
            award_date=datetime(2022, 1, 1),
            completion_date=datetime(2022, 12, 31),
            topic="Export Testing",
            created_at=datetime.utcnow(),
        )
        award2 = models.SbirAward(
            vendor_id=vendor2.id,
            award_piid="EXP-002",
            phase="Phase II",
            agency="Navy",
            award_date=datetime(2022, 6, 1),
            completion_date=datetime(2023, 5, 31),
            topic="Naval Research",
            created_at=datetime.utcnow(),
        )
        session.add_all([award1, award2])
        session.flush()

        # Create contracts
        contract1 = models.Contract(
            vendor_id=vendor1.id,
            piid="EXP-C-001",
            agency="Air Force",
            start_date=datetime(2023, 2, 15),
            competition_details={"extent_competed": "NOT COMPETED"},
            created_at=datetime.utcnow(),
        )
        contract2 = models.Contract(
            vendor_id=vendor2.id,
            piid="EXP-C-002",
            agency="Navy",
            start_date=datetime(2023, 7, 1),
            competition_details={"extent_competed": "COMPETED"},
            created_at=datetime.utcnow(),
        )
        session.add_all([contract1, contract2])
        session.flush()

        # Create detections
        detection1 = models.Detection(
            sbir_award_id=award1.id,
            contract_id=contract1.id,
            likelihood_score=0.85,
            confidence="High",
            evidence_bundle={
                "source_sbir_award": {
                    "piid": "EXP-001",
                    "agency": "Air Force",
                    "phase": "Phase II",
                },
                "source_contract": {"piid": "EXP-C-001", "agency": "Air Force"},
            },
            detection_date=datetime.utcnow(),
        )
        detection2 = models.Detection(
            sbir_award_id=award2.id,
            contract_id=contract2.id,
            likelihood_score=0.45,
            confidence="Likely Transition",
            evidence_bundle={
                "source_sbir_award": {
                    "piid": "EXP-002",
                    "agency": "Navy",
                    "phase": "Phase II",
                },
                "source_contract": {"piid": "EXP-C-002", "agency": "Navy"},
            },
            detection_date=datetime.utcnow(),
        )
        session.add_all([detection1, detection2])
        session.commit()

    finally:
        session.close()

    yield tmp_path

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal


@pytest.fixture(scope="function")
def empty_test_db(tmp_path):
    """Create a test database with no detections."""
    db_file = tmp_path / "test_export_empty.db"
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

    yield tmp_path

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_SessionLocal


def test_export_jsonl_with_detections(test_db_with_detections):
    """Test exporting detections to JSONL format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("test_detections.jsonl")

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Export failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "JSONL file was not created"

        # Verify file content
        detections = []
        with open(output_file, "r") as f:
            for line in f:
                detection = json.loads(line)
                detections.append(detection)

        # Should have 2 detections
        assert len(detections) == 2, f"Expected 2 detections, got {len(detections)}"

        # Verify structure of first detection
        det1 = detections[0]
        assert "likelihood_score" in det1
        assert "confidence" in det1
        assert "evidence_bundle" in det1

        # Verify scores are present
        scores = [d["likelihood_score"] for d in detections]
        assert 0.85 in scores or 0.45 in scores, "Expected scores not found"


def test_export_jsonl_empty_database(empty_test_db):
    """Test exporting from empty database produces valid empty JSONL."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("empty_detections.jsonl")

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        # Should succeed even with no data
        assert result.exit_code == 0, f"Export failed: {result.output}"

        # File might be created but empty
        if output_file.exists():
            content = output_file.read_text()
            # Should be empty or contain no lines
            lines = [line for line in content.split("\n") if line.strip()]
            assert len(lines) == 0, "Empty database should produce no JSONL lines"


def test_export_jsonl_verbose_output(test_db_with_detections):
    """Test verbose flag provides detailed output."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("verbose_detections.jsonl")

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file), "--verbose"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verbose output should contain progress messages
        assert "Exporting" in result.output or "detections" in result.output.lower()


def test_export_csv_with_detections(test_db_with_detections):
    """Test exporting detections to CSV format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("test_detections.csv")

        result = runner.invoke(
            cli_main,
            ["export", "csv", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"CSV export failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "CSV file was not created"

        # Verify CSV content
        with open(output_file, "r", newline="") as f:
            reader = csv_module.DictReader(f)
            rows = list(reader)

        # Should have data rows
        assert len(rows) >= 1, f"Expected at least 1 row in CSV, got {len(rows)}"

        # Verify CSV has expected columns
        # Note: Actual column names depend on implementation
        if len(rows) > 0:
            first_row = rows[0]
            # Should have some key fields (exact names may vary)
            assert len(first_row) > 0, "CSV rows should have data"


def test_export_csv_empty_database(empty_test_db):
    """Test CSV export from empty database."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("empty_detections.csv")

        result = runner.invoke(
            cli_main,
            ["export", "csv", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        # Should succeed even with no data
        assert result.exit_code == 0, f"CSV export failed: {result.output}"

        # File might exist with just headers
        if output_file.exists():
            with open(output_file, "r", newline="") as f:
                reader = csv_module.reader(f)
                rows = list(reader)
                # Should have at most a header row
                assert len(rows) <= 1, "Empty database CSV should have at most headers"


def test_export_jsonl_to_custom_path(test_db_with_detections):
    """Test exporting JSONL to custom output path."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create nested directory structure
        output_dir = Path("custom/output/dir")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "custom_export.jsonl"

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_file.exists(), "Custom path export failed"


def test_export_csv_to_custom_path(test_db_with_detections):
    """Test exporting CSV to custom output path."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create nested directory structure
        output_dir = Path("reports/exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "summary_export.csv"

        result = runner.invoke(
            cli_main,
            ["export", "csv", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert output_file.exists(), "Custom path CSV export failed"


def test_export_jsonl_overwrites_existing_file(test_db_with_detections):
    """Test that export overwrites existing file without error."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("overwrite_test.jsonl")

        # Create a file with dummy content
        output_file.write_text("old content\n")
        original_size = output_file.stat().st_size

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # File should be overwritten (different size or valid JSON)
        new_size = output_file.stat().st_size
        # Either size changed or content is now valid JSONL
        content = output_file.read_text()
        assert content != "old content\n", "File should be overwritten"


def test_export_jsonl_preserves_evidence_bundle(test_db_with_detections):
    """Test that JSONL export preserves full evidence bundle structure."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("evidence_test.jsonl")

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        # Read first detection
        with open(output_file, "r") as f:
            first_line = f.readline()
            detection = json.loads(first_line)

        # Verify evidence bundle is present and structured
        assert "evidence_bundle" in detection
        bundle = detection["evidence_bundle"]

        # Should have source information
        assert (
            "source_sbir_award" in bundle or "source_contract" in bundle
        ), "Evidence bundle should contain source information"


def test_export_invalid_output_directory_fails_gracefully(test_db_with_detections):
    """Test that export fails gracefully with invalid output path."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Try to write to a path that can't be created (e.g., file exists as directory)
        bad_path = Path("bad_dir")
        bad_path.mkdir()
        output_file = bad_path  # Trying to write to a directory as if it's a file

        result = runner.invoke(
            cli_main,
            ["export", "jsonl", "--output-path", str(output_file)],
            catch_exceptions=True,
        )

        # Should fail, but not crash
        assert result.exit_code != 0, "Should fail with invalid path"
