"""Data export CLI commands."""

import click
from pathlib import Path
from rich.console import Console
from loguru import logger

from ..scripts.export_data import (
    export_jsonl as _export_jsonl_impl,
    export_csv_summary as _export_csv_impl,
)


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
        _export_jsonl_impl(str(output_path), verbose)
        console.print(f"\n[green]✓ Exported to {output_path}[/green]")
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
        _export_csv_impl(str(output_path))
        console.print(f"\n[green]✓ Exported to {output_path}[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Export failed: {e}[/red]")
        raise click.Abort()
