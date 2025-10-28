"""CLI commands for data hygiene operations."""

import click
from pathlib import Path
from rich.console import Console

from ..data.cleaning import DataCleaner, create_sample_files_robust

console = Console()


@click.group()
def hygiene():
    """Data hygiene and cleaning commands."""
    pass


@hygiene.command()
@click.option(
    "--data-dir", type=click.Path(exists=True), default="./data", help="Data directory"
)
@click.option(
    "--test-dir",
    type=click.Path(),
    default="./test_data",
    help="Test data output directory",
)
@click.option("--sample-size", type=int, default=1000, help="Sample size for each file")
def create_test_data(data_dir: str, test_dir: str, sample_size: int):
    """Create test data samples in separate directory."""
    data_path = Path(data_dir)
    test_path = Path(test_dir)
    test_path.mkdir(exist_ok=True)

    console.print(f"🧹 Creating test data from {data_path}")
    console.print(f"📁 Output directory: {test_path}")
    console.print(f"📊 Sample size: {sample_size:,} rows per file")

    sample_files = create_sample_files_robust(data_path, sample_size)

    # Move samples to test directory
    moved_files = []
    for sample_file in sample_files:
        if sample_file.name.startswith("sample_"):
            new_name = sample_file.name.replace("sample_", "")
            new_path = test_path / new_name
            sample_file.rename(new_path)
            moved_files.append(new_path)

    console.print(f"✅ Created {len(moved_files)} test files")
    for file_path in moved_files:
        file_size = file_path.stat().st_size / 1024 / 1024
        console.print(f"  📄 {file_path.name} ({file_size:.1f} MB)")


@hygiene.command()
@click.option(
    "--input-file", type=click.Path(exists=True), required=True, help="Input CSV file"
)
@click.option("--output-file", type=click.Path(), help="Output file (optional)")
@click.option("--sample-size", type=int, help="Create sample of N rows")
def clean_file(input_file: str, output_file: str, sample_size: int):
    """Clean a single CSV file with streaming processing."""
    input_path = Path(input_file)
    output_path = Path(output_file) if output_file else None

    console.print(f"🧹 Cleaning {input_path}")

    cleaner = DataCleaner()

    try:
        cleaned_path = cleaner.clean_csv_file_streaming(
            input_path, output_path, sample_size
        )
        console.print(f"✅ Cleaned file saved to: {cleaned_path}")

    except Exception as e:
        console.print(f"❌ Error: {e}")


@hygiene.command()
@click.option(
    "--test-dir", type=click.Path(), default="./test_data", help="Test data directory"
)
@click.option(
    "--run-detection", is_flag=True, help="Run detection pipeline after setup"
)
def test_pipeline(test_dir: str, run_detection: bool):
    """Run end-to-end test using test data directory."""
    import subprocess
    import sys

    test_path = Path(test_dir)

    if not test_path.exists():
        console.print(f"❌ Test directory {test_path} not found")
        console.print("💡 Run 'hygiene create-test-data' first")
        return

    console.print(f"🧪 Running test pipeline with {test_path}")

    # Count test files
    test_files = list(test_path.glob("*.csv"))
    console.print(f"📁 Found {len(test_files)} test files")

    if run_detection:
        console.print("🚀 Running detection pipeline on test data...")

        cmd = [
            sys.executable,
            "-m",
            "src.sbir_transition_classifier.cli.main",
            "bulk-process",
            "--data-dir",
            str(test_path),
            "--chunk-size",
            "100",
            "--verbose",
        ]

        result = subprocess.run(cmd, cwd=test_path.parent)

        if result.returncode == 0:
            console.print("✅ Test pipeline completed successfully!")
        else:
            console.print("❌ Test pipeline failed")
    else:
        console.print("💡 Add --run-detection to test the full pipeline")
