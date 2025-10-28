"""Data loading CLI commands."""

import click
from pathlib import Path
from rich.console import Console
from loguru import logger

from ..ingestion import SbirIngester, ContractIngester


@click.group()
def data():
    """Data loading and ingestion commands."""
    pass


@data.command()
@click.option(
    "--file-path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the SBIR award data CSV file.",
)
@click.option(
    "--chunk-size", type=int, default=5000, help="Number of rows to process at a time."
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def load_sbir(file_path: Path, chunk_size: int, verbose: bool):
    """Load SBIR award data from CSV file into database."""
    console = Console()

    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")

    ingester = SbirIngester(console=console, verbose=verbose)

    try:
        ingester.ingest(file_path, chunk_size=chunk_size)
        console.print("\n[green]✓ SBIR data loaded successfully[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Error loading SBIR data: {e}[/red]")
        raise click.Abort()


@data.command()
@click.option(
    "--file-path",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to the contract data CSV file.",
)
@click.option(
    "--chunk-size", type=int, default=50000, help="Number of rows to process at a time."
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def load_contracts(file_path: Path, chunk_size: int, verbose: bool):
    """Load contract data from CSV file into database."""
    console = Console()

    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")

    ingester = ContractIngester(console=console, verbose=verbose)

    try:
        ingester.ingest(file_path, chunk_size=chunk_size)
        console.print("\n[green]✓ Contract data loaded successfully[/green]")
    except Exception as e:
        console.print(f"\n[red]✗ Error loading contract data: {e}[/red]")
        raise click.Abort()
