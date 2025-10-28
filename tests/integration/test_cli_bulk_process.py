#!/usr/bin/env python3
"""
Integration test: CLI `bulk-process` end-to-end smoke test using CliRunner.

This test runs the `sbir-detect bulk-process` command in an isolated filesystem,
creates small sample SBIR and contract CSV files, and asserts the command exits
successfully and produces output artifacts (or at least initializes the local DB).

Notes:
- The test keeps the dataset minimal for speed.
- It avoids asserting exact exported filenames (those include timestamps). Instead
  it checks the output directory for any CSV/JSONL artifacts or the presence of
  the created SQLite DB file.
"""

from pathlib import Path
import csv

from click.testing import CliRunner

from sbir_transition_classifier.cli.main import main as cli_main


def _write_sample_sbir(csv_path: Path) -> None:
    """Write a minimal SBIR award CSV expected by SbirIngester."""
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
            "Acme Widgets",
            "Phase II",
            "Air Force",
            "FA0001",
            "2022-01-01",
            "2022-12-31",
            "Widget Research",
            "SBIR",
            "Widgets",
            "2022",
        ],
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def _write_sample_contract(csv_path: Path) -> None:
    """Write a minimal contract CSV expected by ContractIngester."""
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
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


def test_cli_bulk_process_end_to_end_smoke():
    """
    Smoke test that invokes `bulk-process` in an isolated filesystem.

    Expectations:
    - command exits with code 0
    - output directory contains at least one exported file (jsonl/csv) OR
      the local SQLite DB file (`sbir_transitions.db`) exists in the working dir.
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create data and output directories in the isolated workspace
        data_dir = Path("data")
        output_dir = Path("output")
        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database in the isolated filesystem
        from sbir_transition_classifier.db.database import Base, engine

        Base.metadata.create_all(bind=engine)

        # Write sample CSVs
        award_csv = data_dir / "award_data.csv"
        contract_csv = data_dir / "contracts_1.csv"
        _write_sample_sbir(award_csv)
        _write_sample_contract(contract_csv)

        # Run the CLI bulk-process command (with verbose output for debugging)
        result = runner.invoke(
            cli_main,
            [
                "bulk-process",
                "--data-dir",
                str(data_dir),
                "--output-dir",
                str(output_dir),
                "--verbose",
            ],
            catch_exceptions=False,
        )

        # Basic assertions about CLI execution
        assert (
            result.exit_code == 0
        ), f"bulk-process failed: {result.exit_code}\nOutput:\n{result.output}\nException: {result.exception}"

        # Check for expected artifacts: any jsonl/csv in output dir or the sqlite DB
        exported_files = (
            list(output_dir.glob("*.jsonl"))
            + list(output_dir.glob("*.csv"))
            + list(output_dir.glob("*detections*"))
        )

        db_file = Path("sbir_transitions.db")

        assert exported_files or db_file.exists(), (
            "Expected export files in output directory or local SQLite DB to be created; "
            f"output_dir contents: {list(output_dir.iterdir())}, cwd files: {list(Path('.').glob('*'))}"
        )
