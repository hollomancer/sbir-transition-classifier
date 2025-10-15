import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import dask.dataframe as dd
import click
from sqlalchemy.orm import Session
from src.sbir_transition_classifier.db.database import SessionLocal, engine
from src.sbir_transition_classifier.core import models
from loguru import logger
import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

def init_db():
    models.Base.metadata.create_all(bind=engine)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--file-path', default='data/award_data.csv', help='Path to the SBIR award data CSV file.')
@click.option('--chunk-size', default=10000, help='Number of rows to process at a time.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_sbir_data(file_path, chunk_size, verbose):
    """Loads SBIR award data from a CSV file into the database."""
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    
    # Check if file exists
    data_file = Path(file_path)
    if not data_file.exists():
        logger.error(f"Data file not found: {file_path}")
        console.print(f"[red]❌ Error: File not found: {file_path}[/red]")
        return
    
    file_size = data_file.stat().st_size / (1024 * 1024)  # MB
    logger.info(f"Processing file: {file_path} ({file_size:.1f} MB)")
    
    # Header
    console.print(Panel.fit(
        "[bold blue]SBIR Data Loader[/bold blue]\n"
        f"[dim]Processing: {data_file.name} ({file_size:.1f} MB)[/dim]",
        border_style="blue"
    ))
    
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Initialize database
        init_task = progress.add_task("🔄 Initializing database...", total=1)
        init_db()
        progress.update(init_task, advance=1)
        logger.info("Database initialized successfully")
        
        # Read CSV with Dask
        read_task = progress.add_task("📁 Reading CSV file...", total=1)
        logger.info(f"Reading CSV with Dask (chunk size: {chunk_size})")
        ddf = dd.read_csv(file_path)
        total_rows = len(ddf)
        progress.update(read_task, advance=1)
        logger.info(f"Total rows to process: {total_rows:,}")
        
        db: Session = SessionLocal()
        processed_rows = 0
        vendors_created = 0
        awards_created = 0
        errors = 0
        
        try:
            partitions = list(ddf.partitions)
            total_partitions = len(partitions)
            
            # Main processing task
            process_task = progress.add_task(
                f"📊 Processing {total_partitions} partitions...", 
                total=total_partitions
            )
            
            for i, partition in enumerate(partitions, 1):
                partition_start = time.time()
                
                df = partition.compute()
                partition_vendors = 0
                partition_awards = 0
                partition_errors = 0
                
                for _, row in df.iterrows():
                    try:
                        # Basic data cleaning and vendor handling
                        company_name = row.get('Company')
                        if not company_name or pd.isna(company_name):
                            partition_errors += 1
                            continue
                        
                        company_name = str(company_name).strip()
                        if not company_name:
                            partition_errors += 1
                            continue

                        vendor = db.query(models.Vendor).filter(models.Vendor.name == company_name).first()
                        if not vendor:
                            vendor = models.Vendor(name=company_name)
                            db.add(vendor)
                            db.flush()  # Get the ID without committing
                            partition_vendors += 1

                        award = models.SbirAward(
                            vendor_id=vendor.id,
                            award_piid=row.get('Award Number', ''),
                            phase=row.get('Phase', ''),
                            agency=row.get('Agency', ''),
                            # Add robust date parsing
                            # award_date=pd.to_datetime(row.get('Award Date'), errors='coerce'),
                            # completion_date=pd.to_datetime(row.get('End Date'), errors='coerce'),
                            topic=row.get('Topic', ''),
                        )
                        db.add(award)
                        partition_awards += 1
                        
                    except Exception as e:
                        partition_errors += 1
                        if verbose:
                            logger.warning(f"Error processing row: {e}")
                
                db.commit()
                partition_time = time.time() - partition_start
                processed_rows += len(df)
                vendors_created += partition_vendors
                awards_created += partition_awards
                errors += partition_errors
                
                # Update progress
                progress.update(process_task, advance=1)
                
                if verbose:
                    logger.info(f"Partition {i}: {partition_vendors} vendors, {partition_awards} awards, {partition_errors} errors")

        finally:
            db.close()
        
        total_time = time.time() - start_time
        
        # Results summary
        console.print()
        console.print(Panel.fit(
            "[bold green]✅ Data Loading Complete![/bold green]",
            border_style="green"
        ))
        
        # Summary table
        summary_table = Table(title="📈 Loading Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right", style="green")
        summary_table.add_row("Total rows processed", f"{processed_rows:,}")
        summary_table.add_row("New vendors created", f"{vendors_created:,}")
        summary_table.add_row("Awards imported", f"{awards_created:,}")
        summary_table.add_row("Errors encountered", f"{errors:,}")
        summary_table.add_row("Total time", f"{total_time:.1f}s")
        summary_table.add_row("Processing rate", f"{processed_rows/total_time:.0f} rows/sec")
        
        console.print(summary_table)
        
        if errors > 0:
            console.print(f"[yellow]⚠️  {errors} rows had errors and were skipped. Use --verbose for details.[/yellow]")

@cli.command()
def load_usaspending_data():
    """Placeholder for loading USAspending data."""
    console = Console()
    console.print("[yellow]USAspending data loading is not yet implemented.[/yellow]")

if __name__ == '__main__':
    cli()
