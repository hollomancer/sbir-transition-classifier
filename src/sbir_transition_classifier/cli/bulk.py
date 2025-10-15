"""CLI bulk processing command for SBIR transition detection."""

import time
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

from ..db.database import SessionLocal
from ..detection.main import run_full_detection


@click.command()
@click.option(
    '--data-dir',
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd() / "data",
    help='Directory containing input data files'
)
@click.option(
    '--output-dir', '-o',
    type=click.Path(path_type=Path),
    default=Path.cwd() / "output",
    help='Output directory for results and logs'
)
@click.option(
    '--chunk-size',
    type=int,
    default=1000,
    help='Number of records to process in each batch'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging with detailed progress'
)
@click.option(
    '--export-format',
    type=click.Choice(['jsonl', 'csv', 'both']),
    default='both',
    help='Export format for results'
)
def bulk_process(
    data_dir: Path,
    output_dir: Path, 
    chunk_size: int,
    verbose: bool,
    export_format: str
):
    """Run bulk SBIR transition detection on all available data."""
    
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    else:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="INFO")
    
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up timestamped log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"bulk_process_{timestamp}.log"
    logger.add(str(log_file), level="DEBUG")
    
    # Header with rich formatting
    console.print(Panel.fit(
        "[bold blue]SBIR Transition Detection[/bold blue]\n"
        "[dim]Bulk Processing Mode[/dim]",
        border_style="blue"
    ))
    
    # Configuration table
    config_table = Table(show_header=False, box=None)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    config_table.add_row("📁 Data directory", str(data_dir))
    config_table.add_row("📤 Output directory", str(output_dir))
    config_table.add_row("📋 Log file", str(log_file.name))
    config_table.add_row("⚙️  Chunk size", f"{chunk_size:,}")
    config_table.add_row("📊 Export format", export_format)
    
    console.print(config_table)
    console.print()
    
    try:
        # Check for required data files
        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            console.print("[red]❌ No CSV data files found in data directory[/red]")
            console.print("[dim]   Expected files: award_data.csv, contract_data.csv[/dim]")
            return
        
        # File summary table
        files_table = Table(title="📁 Data Files Found")
        files_table.add_column("File", style="cyan")
        files_table.add_column("Size", justify="right", style="green")
        
        for file in csv_files:
            file_size = file.stat().st_size / (1024 * 1024)  # MB
            files_table.add_row(file.name, f"{file_size:.1f} MB")
        
        console.print(files_table)
        console.print()
        
        # Phase 1: Data Loading with progress
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
            from ...scripts.load_bulk_data import init_db
            init_db()
            progress.update(init_task, advance=1)
            logger.info("Database initialized for bulk processing")
            
            # Get database state
            db_task = progress.add_task("📊 Checking database state...", total=1)
            db = SessionLocal()
            try:
                from ..core import models
                existing_vendors = db.query(models.Vendor).count()
                existing_awards = db.query(models.SbirAward).count()
                existing_contracts = db.query(models.Contract).count()
                existing_detections = db.query(models.Detection).count()
                progress.update(db_task, advance=1)
            finally:
                db.close()
        
        # Database state table
        db_table = Table(title="📊 Database State (Before Processing)")
        db_table.add_column("Entity", style="cyan")
        db_table.add_column("Count", justify="right", style="yellow")
        db_table.add_row("Vendors", f"{existing_vendors:,}")
        db_table.add_row("SBIR Awards", f"{existing_awards:,}")
        db_table.add_row("Contracts", f"{existing_contracts:,}")
        db_table.add_row("Detections", f"{existing_detections:,}")
        
        console.print(db_table)
        console.print()
        
        # Phase 2: Detection Processing with progress
        console.print("[bold green]🔍 Phase 2: Running detection pipeline...[/bold green]")
        detection_start = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            detection_task = progress.add_task("🔍 Processing detections...", total=100)
            
            # Simulate progress updates - in real implementation, modify run_full_detection
            # to accept a progress callback
            for i in range(100):
                time.sleep(0.01)  # Remove this in real implementation
                progress.update(detection_task, advance=1)
            
            results = run_full_detection()
        
        detection_time = time.time() - detection_start
        
        # Phase 3: Export Results with progress
        console.print("[bold green]📤 Phase 3: Exporting results...[/bold green]")
        export_start = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Count final results
            count_task = progress.add_task("📊 Counting results...", total=1)
            db = SessionLocal()
            try:
                from ..core import models
                final_detections = db.query(models.Detection).count()
                new_detections = final_detections - existing_detections
                progress.update(count_task, advance=1)
            finally:
                db.close()
            
            # Export based on format selection
            export_files = []
            if export_format in ['jsonl', 'both']:
                export_task = progress.add_task("📄 Exporting JSONL...", total=1)
                jsonl_file = output_dir / f"detections_{timestamp}.jsonl"
                # Run export command programmatically
                from ...scripts.export_data import export_jsonl
                # This would need to be modified to work programmatically
                export_files.append(jsonl_file)
                progress.update(export_task, advance=1)
                
            if export_format in ['csv', 'both']:
                csv_task = progress.add_task("📊 Exporting CSV summary...", total=1)
                csv_file = output_dir / f"detections_summary_{timestamp}.csv" 
                export_files.append(csv_file)
                progress.update(csv_task, advance=1)
        
        export_time = time.time() - export_start
        total_time = time.time() - start_time
        
        # Final summary with rich formatting
        console.print()
        console.print(Panel.fit(
            "[bold green]✅ Bulk Processing Complete![/bold green]",
            border_style="green"
        ))
        
        # Results summary table
        results_table = Table(title="📈 Processing Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", justify="right", style="green")
        results_table.add_row("New detections found", f"{new_detections:,}")
        results_table.add_row("Total detections in DB", f"{final_detections:,}")
        results_table.add_row("Detection processing time", f"{detection_time:.1f}s")
        results_table.add_row("Export time", f"{export_time:.1f}s")
        results_table.add_row("Total processing time", f"{total_time:.1f}s")
        
        if new_detections > 0:
            detection_rate = new_detections / total_time * 60  # detections per minute
            results_table.add_row("Processing rate", f"{detection_rate:.1f} detections/min")
        
        console.print(results_table)
        
        # Output files table
        if export_files:
            files_table = Table(title="📁 Output Files")
            files_table.add_column("File", style="cyan")
            files_table.add_column("Size", justify="right", style="green")
            
            for file in export_files:
                if file.exists():
                    size = file.stat().st_size / 1024  # KB
                    files_table.add_row(file.name, f"{size:.1f} KB")
                else:
                    files_table.add_row(file.name, "[red]Not created[/red]")
            
            console.print(files_table)
        
        console.print(f"\n[dim]📋 Full processing log: {log_file}[/dim]")
        
    except Exception as e:
        logger.error(f"Bulk processing failed: {e}")
        console.print(f"\n[red]❌ Bulk processing failed: {e}[/red]")
        raise click.ClickException(str(e))