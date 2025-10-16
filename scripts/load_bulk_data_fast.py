import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import polars as pl
import uuid
import click
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.sbir_transition_classifier.db.database import SessionLocal, engine
from src.sbir_transition_classifier.core import models
from loguru import logger
import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

def init_db():
    models.Base.metadata.create_all(bind=engine)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--file-path', default='data/award_data.csv', help='Path to the SBIR award data CSV file.')
@click.option('--chunk-size', default=10000, help='Number of rows to process at a time.')
@click.option('--use-polars', is_flag=True, help='Use Polars for faster CSV reading')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_sbir_data_fast(file_path, chunk_size, use_polars, verbose):
    """Fast SBIR data loader with optimized CSV reading and bulk operations."""
    console = Console()
    start_time = time.time()
    
    data_file = Path(file_path)
    if not data_file.exists():
        console.print(f"[red]❌ Error: File not found: {file_path}[/red]")
        return
    
    file_size = data_file.stat().st_size / (1024 * 1024)
    console.print(f"🚀 Fast SBIR Loader: {data_file.name} ({file_size:.1f} MB)")
    
    init_db()
    db = SessionLocal()
    
    try:
        if use_polars:
            # Polars is 2-5x faster for large CSV files
            df = pl.read_csv(file_path, ignore_errors=True).to_pandas()
        else:
            # Optimized pandas settings
            df = pd.read_csv(
                file_path,
                dtype=str,
                engine='c',  # Use C engine (fastest)
                na_filter=False,  # Don't convert to NaN (faster)
                keep_default_na=False,  # Don't interpret strings as NaN
                low_memory=False
            )
        
        total_rows = len(df)
        console.print(f"📊 Loaded {total_rows:,} rows in {time.time() - start_time:.1f}s")
        
        # Bulk vendor creation using raw SQL
        vendor_names = df['Company'].dropna().str.strip()
        vendor_names = vendor_names[vendor_names != ''].unique()
        
        # Use raw SQL for bulk vendor insert
        vendor_values = [f"('{name.replace(\"'\", \"''\")}', NOW())" for name in vendor_names]
        if vendor_values:
            vendor_sql = f"""
            INSERT INTO vendors (name, created_at) 
            VALUES {','.join(vendor_values)}
            ON CONFLICT (name) DO NOTHING
            """
            db.execute(text(vendor_sql))
            db.commit()
        
        # Get vendor ID mapping
        vendor_map = {}
        for vendor in db.query(models.Vendor).all():
            vendor_map[vendor.name] = vendor.id
        
        # Bulk award creation
        awards_data = []
        for _, row in df.iterrows():
            company = str(row.get('Company', '')).strip()
            if not company or company not in vendor_map:
                continue
                
            # Fast date parsing
            award_date = pd.to_datetime(row.get('Proposal Award Date'), errors='coerce')
            if pd.isna(award_date):
                award_year = row.get('Award Year')
                if award_year and str(award_year).isdigit():
                    award_date = pd.Timestamp(year=int(award_year), month=1, day=1)
            
            if pd.isna(award_date):
                continue
                
            awards_data.append({
                'vendor_id': vendor_map[company],
                'award_piid': str(row.get('Award Number', '')),
                'phase': str(row.get('Phase', '')),
                'agency': str(row.get('Agency', '')),
                'award_date': award_date,
                'created_at': pd.Timestamp.now()
            })
        
        # Bulk insert awards
        if awards_data:
            db.bulk_insert_mappings(models.SbirAward, awards_data)
            db.commit()
        
        total_time = time.time() - start_time
        console.print(f"✅ Processed {len(awards_data):,} awards in {total_time:.1f}s")
        console.print(f"🚀 Rate: {len(awards_data)/total_time:.0f} awards/sec")
        
    finally:
        db.close()

@cli.command()
@click.option('--file-path', required=True, help='Path to the USAspending CSV file.')
@click.option('--chunk-size', default=100000, help='Larger chunks for better performance.')
@click.option('--use-polars', is_flag=True, help='Use Polars for faster CSV reading')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_contracts_fast(file_path, chunk_size, use_polars, verbose):
    """Fast contract loader with optimized bulk operations."""
    console = Console()
    start_time = time.time()
    
    file_path = Path(file_path)
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    console.print(f"🚀 Fast Contract Loader: {file_path.name} ({file_size_mb:.1f} MB)")
    
    db = SessionLocal()
    
    try:
        # Process in optimized chunks
        chunk_reader = pd.read_csv(
            file_path,
            chunksize=chunk_size,
            dtype=str,
            engine='c',
            na_filter=False,
            keep_default_na=False,
            usecols=['award_id_piid', 'awarding_agency_name', 'recipient_name', 
                    'modification_number', 'transaction_number', 'period_of_performance_start_date']
        )
        
        total_processed = 0
        total_inserted = 0
        vendor_cache = {}
        
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), console=console) as progress:
            task = progress.add_task("Processing chunks...", total=None)
            
            for chunk_df in chunk_reader:
                # Vectorized data cleaning
                chunk_df = chunk_df.dropna(subset=['award_id_piid', 'awarding_agency_name'])
                chunk_df = chunk_df[chunk_df['award_id_piid'].str.strip() != '']
                
                # Bulk vendor creation for chunk
                recipients = chunk_df['recipient_name'].dropna().str.strip().unique()
                new_vendors = []
                
                for recipient in recipients:
                    if recipient and recipient not in vendor_cache:
                        vendor = db.query(models.Vendor).filter_by(name=recipient).first()
                        if vendor:
                            vendor_cache[recipient] = vendor.id
                        else:
                            new_vendor = models.Vendor(name=recipient, created_at=pd.Timestamp.now())
                            new_vendors.append(new_vendor)
                
                if new_vendors:
                    db.add_all(new_vendors)
                    db.flush()
                    for vendor in new_vendors:
                        vendor_cache[vendor.name] = vendor.id
                
                # Prepare contract data
                contracts_data = []
                for _, row in chunk_df.iterrows():
                    recipient = str(row.get('recipient_name', '')).strip()
                    vendor_id = vendor_cache.get(recipient)
                    
                    piid = f"{row['award_id_piid']}_{row.get('modification_number', '0')}_{row.get('transaction_number', '0')}"
                    
                    contracts_data.append({
                        'id': uuid.uuid4(),
                        'vendor_id': vendor_id,
                        'piid': piid,
                        'agency': row['awarding_agency_name'],
                        'start_date': pd.to_datetime(row.get('period_of_performance_start_date'), errors='coerce'),
                        'competition_details': {}
                    })
                
                # Bulk insert contracts
                if contracts_data:
                    db.bulk_insert_mappings(models.Contract, contracts_data)
                    db.commit()
                    total_inserted += len(contracts_data)
                
                total_processed += len(chunk_df)
                progress.update(task, description=f"Processed {total_processed:,} rows, inserted {total_inserted:,} contracts")
        
        total_time = time.time() - start_time
        console.print(f"✅ Processed {total_processed:,} rows, inserted {total_inserted:,} contracts")
        console.print(f"🚀 Rate: {total_processed/total_time:.0f} rows/sec")
        
    finally:
        db.close()

if __name__ == '__main__':
    cli()
