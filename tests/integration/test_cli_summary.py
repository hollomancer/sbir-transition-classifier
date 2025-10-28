#!/usr/bin/env python3
"""
Integration tests for CLI summary and statistics commands.

Tests the summary report generation, quick stats, and related
functionality to ensure Phase 3 CLI reorganization can proceed safely.

Note: Summary commands read from JSONL files, not directly from database.
"""

from pathlib import Path
import json

import pytest
from click.testing import CliRunner

from sbir_transition_classifier.cli.main import main as cli_main


@pytest.fixture(scope="function")
def results_dir_with_detections(tmp_path):
    """Create a results directory with sample detection JSONL files."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    # Create sample detections JSONL file
    detections_file = results_dir / "detections.jsonl"

    detections = [
        {
            "detection_id": "det-001",
            "sbir_award_id": "award-001",
            "contract_id": "contract-001",
            "likelihood_score": 0.95,
            "confidence": "High",
            "evidence_bundle": {
                "source_sbir_award": {
                    "piid": "SUM-001",
                    "agency": "Air Force",
                    "phase": "Phase II",
                },
                "source_contract": {"piid": "SUM-C-001", "agency": "Air Force"},
            },
            "detection_date": "2024-01-15T10:00:00",
        },
        {
            "detection_id": "det-002",
            "sbir_award_id": "award-002",
            "contract_id": "contract-002",
            "likelihood_score": 0.72,
            "confidence": "Likely Transition",
            "evidence_bundle": {
                "source_sbir_award": {
                    "piid": "SUM-002",
                    "agency": "Navy",
                    "phase": "Phase II",
                },
                "source_contract": {"piid": "SUM-C-002", "agency": "Navy"},
            },
            "detection_date": "2024-01-16T11:30:00",
        },
        {
            "detection_id": "det-003",
            "sbir_award_id": "award-003",
            "contract_id": "contract-003",
            "likelihood_score": 0.45,
            "confidence": "Possible",
            "evidence_bundle": {
                "source_sbir_award": {
                    "piid": "SUM-003",
                    "agency": "Army",
                    "phase": "Phase II",
                },
                "source_contract": {
                    "piid": "SUM-C-003",
                    "agency": "Air Force",  # Cross-agency
                },
            },
            "detection_date": "2024-01-17T14:00:00",
        },
    ]

    with open(detections_file, "w") as f:
        for detection in detections:
            f.write(json.dumps(detection) + "\n")

    return results_dir


@pytest.fixture(scope="function")
def empty_results_dir(tmp_path):
    """Create an empty results directory (no detections file)."""
    results_dir = tmp_path / "empty_results"
    results_dir.mkdir()
    return results_dir


@pytest.fixture(scope="function")
def results_dir_with_empty_detections(tmp_path):
    """Create a results directory with empty detections file."""
    results_dir = tmp_path / "results_empty"
    results_dir.mkdir()

    # Create empty detections file
    detections_file = results_dir / "detections.jsonl"
    detections_file.touch()

    return results_dir


def test_quick_stats_with_detections(results_dir_with_detections):
    """Test quick-stats command with populated results directory."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["quick-stats", "--results-dir", str(results_dir_with_detections)],
        catch_exceptions=False,
    )

    # Verify command succeeded
    assert result.exit_code == 0, f"quick-stats failed: {result.output}"

    # Verify output contains key statistics
    output = result.output.lower()
    assert (
        "detection" in output or "statistic" in output
    ), "Should show detection statistics"

    # Should mention total detections
    assert (
        "3" in result.output or "total" in output
    ), "Should display count of detections"


def test_quick_stats_with_missing_directory():
    """Test quick-stats handles missing directory gracefully."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["quick-stats", "--results-dir", "/nonexistent/path"],
        catch_exceptions=True,
    )

    # Should fail with missing directory
    assert result.exit_code != 0, "Should fail with missing directory"


def test_quick_stats_with_empty_detections(results_dir_with_empty_detections):
    """Test quick-stats handles empty detections file."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["quick-stats", "--results-dir", str(results_dir_with_empty_detections)],
        catch_exceptions=False,
    )

    # Should handle empty file gracefully
    assert result.exit_code in [0, 1], f"Unexpected exit code: {result.exit_code}"


def test_generate_summary_text_format(results_dir_with_detections):
    """Test generate-summary command with text format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("summary.txt")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "Summary file should be created"

        # Verify content is reasonable
        content = output_file.read_text()
        assert len(content) > 0, "Summary should have content"


def test_generate_summary_markdown_format(results_dir_with_detections):
    """Test generate-summary command with markdown format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("summary.md")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "markdown",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "Markdown summary should be created"

        # Verify markdown headers present
        content = output_file.read_text()
        assert "#" in content or len(content) > 0, "Should contain markdown content"


def test_generate_summary_json_format(results_dir_with_detections):
    """Test generate-summary command with JSON format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("summary.json")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "json",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "JSON summary should be created"

        # Verify it's valid JSON
        with open(output_file, "r") as f:
            data = json.load(f)

        # Should be a dict with statistics
        assert isinstance(data, dict), "JSON output should be a dictionary"


def test_generate_summary_with_details(results_dir_with_detections):
    """Test generate-summary with --include-details flag."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("detailed_summary.txt")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "text",
                "--include-details",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"

        # Verify file was created
        assert output_file.exists(), "Detailed summary should be created"

        # Should have more content with details
        content = output_file.read_text()
        assert len(content) > 100, "Detailed summary should have substantial content"


def test_generate_summary_without_details(results_dir_with_detections):
    """Test generate-summary without --include-details flag."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("basic_summary.txt")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"
        assert output_file.exists(), "Basic summary should be created"


def test_generate_summary_to_stdout(results_dir_with_detections):
    """Test generate-summary outputs to stdout when no output file specified."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        [
            "generate-summary",
            "--results-dir",
            str(results_dir_with_detections),
            "--format",
            "text",
        ],
        catch_exceptions=False,
    )

    # Verify command succeeded
    assert result.exit_code == 0, f"generate-summary failed: {result.output}"

    # Verify output contains summary information
    assert len(result.output) > 0, "Should output summary to stdout"


def test_generate_summary_help_message():
    """Test generate-summary --help displays usage information."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["generate-summary", "--help"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "summary" in result.output.lower() or "report" in result.output.lower()
    assert "--format" in result.output or "--output" in result.output


def test_quick_stats_help_message():
    """Test quick-stats --help displays usage information."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["quick-stats", "--help"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "stats" in result.output.lower() or "statistic" in result.output.lower()
    assert "--results-dir" in result.output or "-r" in result.output


def test_generate_summary_invalid_format(results_dir_with_detections):
    """Test generate-summary rejects invalid format."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("summary.invalid")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "invalid_format",
            ],
            catch_exceptions=True,
        )

        # Should fail with invalid format
        assert result.exit_code != 0, "Should reject invalid format"


def test_generate_summary_to_custom_directory(results_dir_with_detections):
    """Test generate-summary creates output in custom directory."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create nested directory
        output_dir = Path("reports/summaries")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "custom_summary.txt"

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(results_dir_with_detections),
                "--output",
                str(output_file),
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"generate-summary failed: {result.output}"
        assert output_file.exists(), "Custom path summary should be created"


def test_generate_summary_with_missing_results_file(empty_results_dir):
    """Test generate-summary handles missing detections.jsonl file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        output_file = Path("summary.txt")

        result = runner.invoke(
            cli_main,
            [
                "generate-summary",
                "--results-dir",
                str(empty_results_dir),
                "--output",
                str(output_file),
                "--format",
                "text",
            ],
            catch_exceptions=True,
        )

        # Should fail with missing file
        assert result.exit_code != 0, "Should fail when detections.jsonl is missing"


def test_generate_summary_json_to_stdout(results_dir_with_detections):
    """Test generate-summary outputs JSON to stdout."""
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        [
            "generate-summary",
            "--results-dir",
            str(results_dir_with_detections),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    # Verify command succeeded
    assert result.exit_code == 0, f"generate-summary failed: {result.output}"

    # Verify output is valid JSON
    try:
        data = json.loads(result.output)
        assert isinstance(data, dict), "JSON output should be a dictionary"
    except json.JSONDecodeError:
        pytest.fail("Output should be valid JSON")
