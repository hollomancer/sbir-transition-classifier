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
    if verbose:
        logger.remove()
        logger.add(lambda msg: click.echo(msg, err=True), level="DEBUG")
    
    # Check if file exists
    data_file = Path(file_path)
    if not data_file.exists():
        logger.error(f"Data file not found: {file_path}")
        click.echo(f"❌ Error: File not found: {file_path}", err=True)
        return
    
    file_size = data_file.stat().st_size / (1024 * 1024)  # MB
    logger.info(f"Processing file: {file_path} ({file_size:.1f} MB)")
    
    click.echo(f"🔄 Initializing database...")
    start_time = time.time()
    init_db()
    logger.info("Database initialized successfully")
    
    click.echo(f"📁 Loading SBIR data from {file_path}...")
    
    try:
        # Use Dask for potentially large files
        logger.info(f"Reading CSV with Dask (chunk size: {chunk_size})")
        ddf = dd.read_csv(file_path)
        total_rows = len(ddf)
        logger.info(f"Total rows to process: {total_rows:,}")
        
        db: Session = SessionLocal()
        processed_rows = 0
        vendors_created = 0
        awards_created = 0
        errors = 0
        
        try:
            partitions = list(ddf.partitions)
            total_partitions = len(partitions)
            
            for i, partition in enumerate(partitions, 1):
                partition_start = time.time()
                click.echo(f"📊 Processing partition {i}/{total_partitions}...", nl=False)
                
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
                
                # Progress indicator
                progress = (processed_rows / total_rows) * 100
                click.echo(f" ✅ {len(df):,} rows ({partition_time:.1f}s) - Progress: {progress:.1f}%")
                
                if verbose:
                    logger.info(f"Partition {i}: {partition_vendors} vendors, {partition_awards} awards, {partition_errors} errors")

        finally:
            db.close()
        
        total_time = time.time() - start_time
        click.echo(f"\n✅ Finished loading SBIR data!")
        click.echo(f"📈 Summary:")
        click.echo(f"   • Total rows processed: {processed_rows:,}")
        click.echo(f"   • New vendors created: {vendors_created:,}")
        click.echo(f"   • Awards imported: {awards_created:,}")
        click.echo(f"   • Errors encountered: {errors:,}")
        click.echo(f"   • Total time: {total_time:.1f} seconds")
        click.echo(f"   • Processing rate: {processed_rows/total_time:.0f} rows/sec")
        
        if errors > 0:
            click.echo(f"⚠️  {errors} rows had errors and were skipped. Use --verbose for details.")
    
    except Exception as e:
        logger.error(f"Failed to load SBIR data: {e}")
        click.echo(f"❌ Error loading data: {e}", err=True)
        raise

@cli.command()
def load_usaspending_data():
    """Placeholder for loading USAspending data."""
    click.echo("USAspending data loading is not yet implemented.")

if __name__ == '__main__':
    cli()
