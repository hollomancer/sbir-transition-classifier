"""CLI bulk processing command for SBIR transition detection."""

import time
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from rich.table import Table

from ..db.database import SessionLocal
from ..detection.main import run_full_detection
from ..data.hygiene import create_sample_files_robust
from ..scripts.export_data import (
    export_jsonl as export_jsonl_cmd,
    export_csv_summary as export_csv_summary_cmd,
)


def load_csv_file(csv_file_info):
    """Load a single CSV file via ContractIngester."""
    csv_file_path, data_dir_parent = csv_file_info
    from ..ingestion import ContractIngester
    from rich.console import Console

    try:
        ingester = ContractIngester(console=Console(), verbose=False)
        ingester.ingest(csv_file_path, chunk_size=50000)
        return csv_file_path.name, 0
    except Exception:
        return csv_file_path.name, 1


@click.command()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd() / "data",
    help="Directory containing input data files",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd() / "output",
    help="Output directory for results and logs",
)
@click.option(
    "--chunk-size",
    type=int,
    default=5000,
    help="Number of records to process in each batch",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging with detailed progress",
)
@click.option("--quiet", "-q", is_flag=True, help="Minimal output - just results")
@click.option(
    "--export-format",
    type=click.Choice(["jsonl", "csv", "both"]),
    default="both",
    help="Export format for results",
)
@click.option(
    "--use-samples", is_flag=True, help="Use sample files created by hygiene system"
)
@click.option(
    "--create-samples", is_flag=True, help="Create sample files before processing"
)
@click.option(
    "--sample-size", type=int, default=1000, help="Sample size when creating samples"
)
@click.option(
    "--in-process",
    is_flag=True,
    help="Run detection serially in-process (useful for testing and CI)",
)
def bulk_process(
    data_dir: Path,
    output_dir: Path,
    chunk_size: int,
    verbose: bool,
    quiet: bool,
    export_format: str,
    use_samples: bool,
    create_samples: bool,
    sample_size: int,
    in_process: bool,
):
    """Run bulk SBIR transition detection on all available data."""

    console = Console(quiet=quiet)

    if verbose and not quiet:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    elif quiet:
        logger.remove()  # Suppress all logging in quiet mode
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
    console.print(
        Panel.fit(
            "[bold blue]SBIR Transition Detection[/bold blue]\n"
            "[dim]Bulk Processing Mode[/dim]",
            border_style="blue",
        )
    )

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
            console.print(
                "[dim]   Expected files: award_data.csv, contract_data.csv[/dim]"
            )
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

        # Initialize database connection
        from ..core import models
        from ..db.database import SessionLocal

        db = SessionLocal()

        # Phase 1: Load CSV Data if needed
        award_exists = db.query(models.SbirAward.id).limit(1).first()
        contract_exists = db.query(models.Contract.id).limit(1).first()

        # Load SBIR awards first if needed
        if not award_exists:
            award_file = data_dir / "award_data.csv"
            if award_file.exists():
                console.print(
                    "[bold blue]🔍 Phase 1a: Loading SBIR awards...[/bold blue]"
                )
                console.print(
                    f"📊 Loading SBIR data from {award_file.name}", style="cyan"
                )

                try:
                    # Use new ingestion layer
                    from ..ingestion import SbirIngester

                    ingester = SbirIngester(console=console, verbose=verbose)
                    stats = ingester.ingest(award_file, chunk_size=chunk_size)

                    console.print(
                        f"✅ SBIR ingestion complete: {stats.valid_records:,} awards loaded "
                        f"({stats.retention_rate:.1f}% retention)",
                        style="green",
                    )

                except Exception as e:
                    console.print(f"❌ Error loading SBIR awards: {e}", style="red")
                    return
            else:
                console.print(
                    "⚠️  No award_data.csv found, skipping SBIR loading", style="yellow"
                )
        else:
            latest_award_meta = (
                db.query(models.SbirAward.phase, models.SbirAward.created_at)
                .order_by(models.SbirAward.created_at.desc())
                .first()
            )
            latest_phase, created_at = (
                latest_award_meta if latest_award_meta else (None, None)
            )
            latest_phase = latest_phase or "unknown phase"
            created_display = created_at.isoformat() if created_at else "unknown time"
            console.print(
                f"[dim]⏭️  SBIR awards already present (latest record: {latest_phase} at {created_display}). Skipping Phase 1a.[/dim]"
            )

        # Load contract data - check for new files
        csv_files = [f for f in data_dir.glob("*.csv") if f.name != "award_data.csv"]

        # Get list of already processed files from database
        processed_files = set()
        if contract_exists:
            existing_contract_count = db.query(models.Contract).count()

            # More accurate detection: based on actual file sizes, estimate ~4500 contracts per file
            actual_contracts_per_file = 4500  # Conservative estimate based on real data
            expected_total = len(csv_files) * actual_contracts_per_file

            # Only process if we have significantly fewer contracts than expected
            # Use 80% threshold to account for variation in file sizes
            if existing_contract_count < expected_total * 0.8:
                console.print(
                    f"[yellow]🔍 Detected potential new contract files ({existing_contract_count:,} contracts vs {len(csv_files)} files)[/yellow]"
                )
                new_files_detected = True
            else:
                console.print(
                    f"[green]✅ Contract data appears complete ({existing_contract_count:,} contracts from {len(csv_files)} files)[/green]"
                )
                new_files_detected = False
        else:
            new_files_detected = True

        if new_files_detected and csv_files:
            console.print(
                "[bold blue]🔍 Phase 1b: Loading contract data...[/bold blue]"
            )

            # Load contract data from CSV files
            csv_files = [
                f for f in data_dir.glob("*.csv") if f.name != "award_data.csv"
            ]
            if csv_files:
                console.print(
                    f"📊 Found {len(csv_files)} contract CSV files to load",
                    style="cyan",
                )

                # Show file inventory with sizes
                files_table = Table(title="📁 Contract Files to Process")
                files_table.add_column("File", style="cyan")
                files_table.add_column("Size", justify="right", style="green")
                files_table.add_column("Status", style="yellow")

                total_size_mb = 0
                for file in csv_files:
                    file_size = file.stat().st_size / (1024 * 1024)  # MB
                    total_size_mb += file_size
                    files_table.add_row(file.name, f"{file_size:.1f} MB", "Pending")

                files_table.add_row("[bold]Total", f"[bold]{total_size_mb:.1f} MB", "")
                console.print(files_table)
                console.print()

                # Process files sequentially with detailed progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                    overall_task = progress.add_task(
                        "📥 Loading all contract files", total=len(csv_files)
                    )

                    # Track cumulative statistics across all files
                    cumulative_stats = {
                        "total_files": len(csv_files),
                        "files_processed": 0,
                        "total_rows": 0,
                        "total_contracts": 0,
                        "total_vendors": 0,
                        "total_rejected": 0,
                        "processing_time": 0,
                    }

                    for i, csv_file in enumerate(csv_files, 1):
                        file_start_time = time.time()

                        # Update progress description
                        progress.update(
                            overall_task,
                            description=f"📥 Loading {csv_file.name} ({i}/{len(csv_files)})",
                        )

                        console.print(
                            f"\n[bold cyan]Processing file {i}/{len(csv_files)}: {csv_file.name}[/bold cyan]"
                        )

                        try:
                            # Use new ingestion layer
                            from ..ingestion import ContractIngester

                            ingester = ContractIngester(
                                console=console, verbose=verbose
                            )

                            # Get contract count before loading
                            contracts_before = db.query(models.Contract).count()

                            # Ingest using new layer
                            stats = ingester.ingest(csv_file, chunk_size=chunk_size)

                            # Get contract count after loading
                            contracts_after = db.query(models.Contract).count()
                            new_contracts = contracts_after - contracts_before

                            file_time = time.time() - file_start_time

                            # Update cumulative stats
                            cumulative_stats["files_processed"] += 1
                            cumulative_stats["total_contracts"] += new_contracts
                            cumulative_stats["processing_time"] += file_time

                            # Show file completion summary
                            console.print(
                                f"  ✅ {csv_file.name}: {new_contracts:,} contracts loaded "
                                f"({stats.retention_rate:.1f}% retention) in {file_time:.1f}s",
                                style="green",
                            )

                        except Exception as e:
                            console.print(
                                f"  ❌ {csv_file.name}: Error - {e}", style="red"
                            )

                        progress.update(overall_task, advance=1)

                        # Show cumulative progress every few files
                        if i % 2 == 0 or i == len(csv_files):
                            console.print(
                                f"[dim]Progress: {cumulative_stats['files_processed']}/{cumulative_stats['total_files']} files, "
                                f"{cumulative_stats['total_contracts']:,} total contracts loaded[/dim]"
                            )

                # Final contract loading summary
                final_contract_count = db.query(models.Contract).count()
                console.print()
                console.print(
                    Panel.fit(
                        f"[bold green]✅ Contract Loading Complete![/bold green]\n"
                        f"[dim]Loaded {final_contract_count:,} contracts from {len(csv_files)} files in {cumulative_stats['processing_time']:.1f}s[/dim]",
                        border_style="green",
                    )
                )

                # Contract loading summary table
                loading_table = Table(title="📊 Multi-File Loading Summary")
                loading_table.add_column("Metric", style="cyan")
                loading_table.add_column("Value", justify="right", style="green")
                loading_table.add_row(
                    "Files processed",
                    f"{cumulative_stats['files_processed']}/{cumulative_stats['total_files']}",
                )
                loading_table.add_row(
                    "Total contracts loaded", f"{final_contract_count:,}"
                )
                loading_table.add_row(
                    "Total processing time",
                    f"{cumulative_stats['processing_time']:.1f}s",
                )
                loading_table.add_row(
                    "Average per file",
                    f"{cumulative_stats['processing_time']/len(csv_files):.1f}s",
                )
                if cumulative_stats["processing_time"] > 0:
                    loading_table.add_row(
                        "Loading rate",
                        f"{final_contract_count/cumulative_stats['processing_time']:.0f} contracts/sec",
                    )

                console.print(loading_table)

            else:
                console.print("⚠️  No contract CSV files found", style="yellow")
        elif contract_exists and not new_files_detected:
            latest_contract_meta = (
                db.query(models.Contract.agency, models.Contract.created_at)
                .order_by(models.Contract.created_at.desc())
                .first()
            )
            latest_agency, contract_created_at = (
                latest_contract_meta if latest_contract_meta else (None, None)
            )
            latest_agency = latest_agency or "unknown agency"
            contract_created_display = (
                contract_created_at.isoformat()
                if contract_created_at
                else "unknown time"
            )
            console.print(
                f"[dim]⏭️  Contract data up to date ({db.query(models.Contract).count():,} contracts, latest: {latest_agency}). Skipping Phase 1b.[/dim]"
            )
        else:
            console.print(
                "⚠️  No contract CSV files found for processing", style="yellow"
            )

        console.print()

        # Phase 1: Data Loading with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Initialize database
            init_task = progress.add_task("🔄 Initializing database...", total=1)
            # Initialize database using package models/engine (avoid manipulating sys.path)
            from ..core import models
            from ..db.database import engine

            models.Base.metadata.create_all(bind=engine)
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
        console.print(
            "[bold green]🔍 Phase 3: Running detection pipeline...[/bold green]"
        )
        detection_start = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            detection_task = progress.add_task("🔍 Processing detections...", total=100)

            # Simulate progress updates - in real implementation, modify run_full_detection
            # to accept a progress callback
            for i in range(100):
                time.sleep(0.01)  # Remove this in real implementation
                progress.update(detection_task, advance=1)

            # Run detection pipeline; allow single-process deterministic mode for testing
            results = run_full_detection(in_process=in_process)

        detection_time = time.time() - detection_start

        # Phase 4: Export Results with progress
        console.print("[bold green]📤 Phase 4: Exporting results...[/bold green]")
        export_start = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
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
            if export_format in ["jsonl", "both"]:
                export_task = progress.add_task("📄 Exporting JSONL...", total=1)
                jsonl_file = output_dir / f"detections_{timestamp}.jsonl"

                # Run export directly without spawning subprocess
                try:
                    export_jsonl_cmd(output_path=str(jsonl_file), verbose=False)
                    export_files.append(jsonl_file)
                except Exception as e:
                    logger.error(f"JSONL export failed: {e}")
                progress.update(export_task, advance=1)

            if export_format in ["csv", "both"]:
                csv_task = progress.add_task("📊 Exporting CSV summary...", total=1)
                csv_file = output_dir / f"detections_summary_{timestamp}.csv"

                # Run export directly without spawning subprocess
                try:
                    export_csv_summary_cmd(output_path=str(csv_file))
                    export_files.append(csv_file)
                except Exception as e:
                    logger.error(f"CSV summary export failed: {e}")
                progress.update(csv_task, advance=1)

        export_time = time.time() - export_start

        # Phase 5: Generate Transition Statistics Overview
        console.print(
            "[bold blue]📊 Phase 5: Generating transition statistics...[/bold blue]"
        )
        stats_start = time.time()

        try:
            from ..analysis import (
                generate_transition_overview,
                analyze_transition_perspectives,
            )

            # Overall statistics
            transition_stats = generate_transition_overview(console=console)

            # Dual-perspective analysis
            perspective_stats = analyze_transition_perspectives(console=console)

        except Exception as e:
            console.print(f"[yellow]⚠️ Statistics generation failed: {e}[/yellow]")
            transition_stats = None
            perspective_stats = None

        stats_time = time.time() - stats_start
        total_time = time.time() - start_time

        # Final summary with rich formatting
        console.print()
        console.print(
            Panel.fit(
                "[bold green]✅ Bulk Processing Complete![/bold green]",
                border_style="green",
            )
        )

        # Results summary table
        results_table = Table(title="📈 Processing Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", justify="right", style="green")
        results_table.add_row("New detections found", f"{new_detections:,}")
        results_table.add_row("Total detections in DB", f"{final_detections:,}")
        results_table.add_row("Detection processing time", f"{detection_time:.1f}s")
        results_table.add_row("Export time", f"{export_time:.1f}s")
        results_table.add_row("Statistics generation time", f"{stats_time:.1f}s")
        results_table.add_row("Total processing time", f"{total_time:.1f}s")

        if new_detections > 0:
            detection_rate = new_detections / total_time * 60  # detections per minute
            results_table.add_row(
                "Processing rate", f"{detection_rate:.1f} detections/min"
            )

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
        import traceback

        logger.error(f"Bulk processing failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        console.print(f"\n[red]❌ Bulk processing failed: {e}[/red]")
        raise click.ClickException(str(e))
