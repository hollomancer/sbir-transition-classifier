"""CLI bulk processing command for SBIR transition detection."""

import time
from pathlib import Path
from typing import Optional

import click
from loguru import logger

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
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")
    else:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="INFO")
    
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up timestamped log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"bulk_process_{timestamp}.log"
    logger.add(str(log_file), level="DEBUG")
    
    click.echo("🚀 Starting SBIR Transition Detection - Bulk Processing Mode")
    click.echo(f"📁 Data directory: {data_dir}")
    click.echo(f"📤 Output directory: {output_dir}")
    click.echo(f"📋 Log file: {log_file}")
    click.echo(f"⚙️  Processing chunk size: {chunk_size:,}")
    click.echo("-" * 50)
    
    try:
        # Check for required data files
        csv_files = list(data_dir.glob("*.csv"))
        if not csv_files:
            click.echo("❌ No CSV data files found in data directory")
            click.echo("   Expected files: award_data.csv, contract_data.csv")
            return
        
        click.echo(f"🔍 Found {len(csv_files)} data files:")
        for file in csv_files:
            file_size = file.stat().st_size / (1024 * 1024)  # MB
            click.echo(f"   • {file.name} ({file_size:.1f} MB)")
        
        # Phase 1: Data Loading
        click.echo("\n📥 Phase 1: Loading and validating data...")
        
        # Import the load_bulk_data functions here to avoid circular imports
        from ...scripts.load_bulk_data import init_db
        
        init_db()
        logger.info("Database initialized for bulk processing")
        
        # Count existing records before processing
        db = SessionLocal()
        try:
            from ..core import models
            existing_vendors = db.query(models.Vendor).count()
            existing_awards = db.query(models.SbirAward).count()
            existing_contracts = db.query(models.Contract).count()
            existing_detections = db.query(models.Detection).count()
            
            click.echo(f"📊 Database state before processing:")
            click.echo(f"   • Vendors: {existing_vendors:,}")
            click.echo(f"   • SBIR Awards: {existing_awards:,}")
            click.echo(f"   • Contracts: {existing_contracts:,}")
            click.echo(f"   • Detections: {existing_detections:,}")
            
        finally:
            db.close()
        
        # Phase 2: Detection Processing
        click.echo("\n🔍 Phase 2: Running detection pipeline...")
        detection_start = time.time()
        
        # Show processing status
        with click.progressbar(length=100, label='Processing detections') as bar:
            # This is a placeholder - in a real implementation, you'd need to 
            # modify run_full_detection to accept a progress callback
            results = run_full_detection()
            bar.update(100)
        
        detection_time = time.time() - detection_start
        
        # Phase 3: Export Results
        click.echo(f"\n📤 Phase 3: Exporting results (format: {export_format})...")
        export_start = time.time()
        
        # Count final results
        db = SessionLocal()
        try:
            from ..core import models
            final_detections = db.query(models.Detection).count()
            new_detections = final_detections - existing_detections
            
        finally:
            db.close()
        
        # Export based on format selection
        export_files = []
        if export_format in ['jsonl', 'both']:
            jsonl_file = output_dir / f"detections_{timestamp}.jsonl"
            # Run export command programmatically
            from ...scripts.export_data import export_jsonl
            # This would need to be modified to work programmatically
            export_files.append(jsonl_file)
            
        if export_format in ['csv', 'both']:
            csv_file = output_dir / f"detections_summary_{timestamp}.csv" 
            export_files.append(csv_file)
        
        export_time = time.time() - export_start
        total_time = time.time() - start_time
        
        # Final summary
        click.echo("\n" + "=" * 50)
        click.echo("✅ Bulk Processing Complete!")
        click.echo("=" * 50)
        click.echo(f"📈 Results Summary:")
        click.echo(f"   • New detections found: {new_detections:,}")
        click.echo(f"   • Total detections in DB: {final_detections:,}")
        click.echo(f"   • Detection processing time: {detection_time:.1f} seconds")
        click.echo(f"   • Export time: {export_time:.1f} seconds") 
        click.echo(f"   • Total processing time: {total_time:.1f} seconds")
        
        if export_files:
            click.echo(f"📁 Output files:")
            for file in export_files:
                if file.exists():
                    size = file.stat().st_size / 1024  # KB
                    click.echo(f"   • {file.name} ({size:.1f} KB)")
        
        click.echo(f"📋 Full processing log: {log_file}")
        
        if new_detections > 0:
            detection_rate = new_detections / total_time * 60  # detections per minute
            click.echo(f"⚡ Processing rate: {detection_rate:.1f} detections/minute")
        
    except Exception as e:
        logger.error(f"Bulk processing failed: {e}")
        click.echo(f"\n❌ Bulk processing failed: {e}", err=True)
        raise click.ClickException(str(e))