"""Data export CLI commands."""

import json
import time
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from loguru import logger
from rich.console import Console
from sqlalchemy.orm import Session

from ..core import models
from ..db import database as db_module


def export_detections_to_jsonl(
    output_path: Path, verbose: bool = False, console: Optional[Console] = None
) -> int:
    """
    Export all detections to JSONL format.

    Args:
        output_path: Path to output JSONL file
        verbose: Enable verbose logging
        console: Rich console for output (creates new one if None)

    Returns:
        Number of detections exported
    """
    if console is None:
        console = Console()

    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")

    start_time = time.time()
    console.print(f"📤 Exporting detections to {output_path}...")

    db: Session = db_module.SessionLocal()
    try:
        # Get count first for progress tracking
        total_count = db.query(models.Detection).count()

        if total_count == 0:
            console.print("⚠️  No detections found in database.")
            return 0

        console.print(f"🔍 Found {total_count:,} detections to export")

        detections = db.query(models.Detection).all()

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        exported_count = 0
        with open(output_path, "w") as f:
            for i, detection in enumerate(detections, 1):
                try:
                    # Serialize detection to JSONL
                    detection_data = {
                        "detection_id": str(detection.id),
                        "likelihood_score": detection.likelihood_score,
                        "confidence": detection.confidence,
                        "evidence_bundle": detection.evidence_bundle,
                    }
                    f.write(json.dumps(detection_data) + "\n")
                    exported_count += 1

                    # Progress indicator every 100 records or at the end
                    if i % 100 == 0 or i == total_count:
                        progress = (i / total_count) * 100
                        console.print(
                            f"📊 Progress: {i:,}/{total_count:,} ({progress:.1f}%)"
                        )

                except Exception as e:
                    if verbose:
                        logger.warning(f"Error exporting detection {detection.id}: {e}")
                    continue

        export_time = time.time() - start_time
        file_size = output_path.stat().st_size / 1024  # KB

        console.print(f"\n✅ Export complete!")
        console.print(f"📈 Summary:")
        console.print(f"   • Records exported: {exported_count:,}")
        console.print(f"   • Output file: {output_path}")
        console.print(f"   • File size: {file_size:.1f} KB")
        console.print(f"   • Export time: {export_time:.1f} seconds")

        return exported_count

    finally:
        db.close()


def export_detections_to_csv(
    output_path: Path, verbose: bool = False, console: Optional[Console] = None
) -> int:
    """
    Export detection summary to CSV format.

    Args:
        output_path: Path to output CSV file
        verbose: Enable verbose logging
        console: Rich console for output (creates new one if None)

    Returns:
        Number of summary rows exported
    """
    if console is None:
        console = Console()

    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")

    console.print(f"📤 Exporting detection summary to {output_path}...")

    db: Session = db_module.SessionLocal()
    try:
        # Query all detections with related data
        detections = db.query(models.Detection).all()

        if not detections:
            console.print("⚠️  No detections found in database.")
            # Create empty CSV with headers
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(
                columns=[
                    "detection_id",
                    "vendor_id",
                    "agency",
                    "fiscal_year",
                    "score",
                ]
            )
            df.to_csv(output_path, index=False)
            console.print(
                f"[yellow]⚠️  Created empty CSV with headers at {output_path}[/yellow]"
            )
            return 0

        # Build data for CSV export
        data = []
        for det in detections:
            try:
                # Extract fiscal year from contract start date if available
                fiscal_year = None
                if det.contract and det.contract.start_date:
                    fiscal_year = det.contract.start_date.year

                # Extract agency from contract if available
                agency = None
                if det.contract:
                    agency = det.contract.agency

                # Extract vendor_id from contract if available
                vendor_id = None
                if det.contract:
                    vendor_id = str(det.contract.vendor_id)

                data.append(
                    {
                        "detection_id": str(det.id),
                        "vendor_id": vendor_id,
                        "agency": agency,
                        "fiscal_year": fiscal_year,
                        "score": det.likelihood_score,
                    }
                )
            except Exception as e:
                if verbose:
                    logger.warning(f"Error processing detection {det.id}: {e}")
                continue

        if not data:
            console.print("[yellow]⚠️  No valid detections to export[/yellow]")
            return 0

        # Create DataFrame and aggregate
        df = pd.DataFrame(data)

        # Perform aggregation by fiscal_year, agency, vendor_id
        summary_df = (
            df.groupby(["fiscal_year", "agency", "vendor_id"])
            .agg(
                detection_count=("detection_id", "count"),
                average_score=("score", "mean"),
            )
            .reset_index()
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to CSV
        summary_df.to_csv(output_path, index=False)

        console.print(
            f"\n[green]✓ Exported {len(summary_df)} summary rows to {output_path}[/green]"
        )

        return len(summary_df)

    finally:
        db.close()


# Legacy compatibility functions for bulk_process
def export_jsonl(output_path: str, verbose: bool = False):
    """
    Legacy wrapper for JSONL export (for bulk_process compatibility).

    Args:
        output_path: String path to output file
        verbose: Enable verbose logging
    """
    export_detections_to_jsonl(Path(output_path), verbose=verbose)


def export_csv_summary(output_path: str):
    """
    Legacy wrapper for CSV export (for bulk_process compatibility).

    Args:
        output_path: String path to output file
    """
    export_detections_to_csv(Path(output_path), verbose=False)


@click.group()
def export():
    """Data export commands."""
    pass


@export.command()
@click.option(
    "--output-path",
    type=click.Path(path_type=Path),
    default="output/detections.jsonl",
    help="Path to the output JSONL file.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def jsonl(output_path: Path, verbose: bool):
    """Export detections to JSONL format."""
    console = Console()

    try:
        export_detections_to_jsonl(output_path, verbose, console)
    except Exception as e:
        console.print(f"\n[red]✗ Export failed: {e}[/red]")
        raise click.Abort()


@export.command()
@click.option(
    "--output-path",
    type=click.Path(path_type=Path),
    default="output/summary.csv",
    help="Path to the output CSV file.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def csv(output_path: Path, verbose: bool):
    """Export detection summary to CSV format."""
    console = Console()

    try:
        export_detections_to_csv(output_path, verbose, console)
    except Exception as e:
        console.print(f"\n[red]✗ Export failed: {e}[/red]")
        raise click.Abort()
