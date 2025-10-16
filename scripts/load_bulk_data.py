import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import hashlib
import uuid
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
@click.option('--chunk-size', default=5000, help='Number of rows to process at a time.')
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
    
    # Enhanced statistics tracking
    stats = {
        'total_rows': 0,
        'valid_awards': 0,
        'skipped_missing_company': 0,
        'skipped_missing_dates': 0,
        'skipped_invalid_dates': 0,
        'vendors_created': 0,
        'vendors_reused': 0,
        'processing_errors': 0,
        'date_fallbacks_used': 0
    }
    
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
        
        # Read CSV with better error handling
        read_task = progress.add_task("📁 Reading CSV file...", total=1)
        logger.info(f"Reading CSV with pandas (chunk size: {chunk_size})")
        try:
            # Use pandas with robust error handling for malformed CSV files
            ddf = pd.read_csv(file_path, dtype=str, on_bad_lines='skip', encoding='utf-8', quoting=1)
            # Convert to dask for processing
            ddf = dd.from_pandas(ddf, npartitions=max(1, len(ddf) // chunk_size))
            stats['total_rows'] = len(ddf)
        except Exception as e:
            console.print(f"[red]Error reading CSV: {e}[/red]")
            return
        progress.update(read_task, advance=1)
        logger.info(f"Total rows to process: {stats['total_rows']:,}")
        
        db: Session = SessionLocal()
        
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
                partition_stats = {
                    'vendors_created': 0,
                    'vendors_reused': 0,
                    'awards_created': 0,
                    'missing_company': 0,
                    'missing_dates': 0,
                    'invalid_dates': 0,
                    'date_fallbacks': 0,
                    'errors': 0
                }
                
                # Batch processing - collect all operations before committing
                vendors_to_create = []
                awards_to_create = []
                vendor_cache = {}
                
                for _, row in df.iterrows():
                    try:
                        # Basic data cleaning and vendor handling
                        company_name = row.get('Company')
                        if not company_name or pd.isna(company_name):
                            partition_stats['missing_company'] += 1
                            continue
                        
                        company_name = str(company_name).strip()
                        if not company_name:
                            partition_stats['missing_company'] += 1
                            continue

                        # Check cache first, then database
                        vendor_id = vendor_cache.get(company_name)
                        if not vendor_id:
                            vendor = db.query(models.Vendor).filter(models.Vendor.name == company_name).first()
                            if vendor:
                                vendor_id = vendor.id
                                vendor_cache[company_name] = vendor_id
                                partition_stats['vendors_reused'] += 1
                            else:
                                # Queue for batch creation
                                vendor_obj = models.Vendor(name=company_name, created_at=pd.Timestamp.now())
                                vendors_to_create.append(vendor_obj)
                                vendor_cache[company_name] = vendor_obj  # Temporary reference
                                partition_stats['vendors_created'] += 1

                        # Enhanced date handling with Award Year fallback for 100% recovery
                        award_date = None
                        completion_date = None
                        used_fallback = False
                        
                        # Try multiple date fields in order of preference
                        date_fields = [
                            ('Proposal Award Date', 'primary award date'),
                            ('Date of Notification', 'notification date'),
                            ('Solicitation Close Date', 'solicitation close'),
                            ('Proposal Receipt Date', 'proposal receipt')
                        ]
                        
                        for field_name, description in date_fields:
                            if award_date is None:  # Only if we haven't found a date yet
                                field_value = row.get(field_name)
                                if field_value and str(field_value).lower() not in ['nan', 'null', '']:
                                    parsed_date = pd.to_datetime(field_value, errors='coerce')
                                    if not pd.isna(parsed_date):
                                        award_date = parsed_date
                                        break
                        
                        # Final fallback: Use Award Year as January 1st of that year
                        if pd.isna(award_date):
                            award_year = row.get('Award Year')
                            if award_year and str(award_year).lower() not in ['nan', 'null', '']:
                                try:
                                    year_int = int(award_year)
                                    if 1905 <= year_int <= 2025:  # Reasonable year range
                                        award_date = pd.Timestamp(year=year_int, month=1, day=1)
                                        used_fallback = True
                                        partition_stats['date_fallbacks'] += 1
                                except (ValueError, TypeError):
                                    pass
                        
                        # Try Contract End Date for completion, but make it optional
                        contract_end = row.get('Contract End Date')
                        if contract_end and str(contract_end).lower() not in ['nan', 'null', '']:
                            completion_date = pd.to_datetime(contract_end, errors='coerce')
                        
                        # Skip only if we have no award date at all (should be very rare now)
                        if pd.isna(award_date):
                            partition_stats['missing_dates'] += 1
                            continue

                        award_data = {
                            'award_piid': str(row.get('Award Number', '')).strip() if pd.notna(row.get('Award Number')) else '',
                            'phase': str(row.get('Phase', '')).strip() if pd.notna(row.get('Phase')) else '',
                            'agency': str(row.get('Agency', '')).strip() if pd.notna(row.get('Agency')) else '',
                            'topic': str(row.get('Topic', '')).strip() if pd.notna(row.get('Topic')) else '',
                            'award_date': award_date,
                            'completion_date': completion_date,  # Can be None
                            'created_at': pd.Timestamp.now(),
                        }
                        awards_to_create.append((company_name, award_data))
                        partition_stats['awards_created'] += 1
                        
                    except Exception as e:
                        partition_stats['errors'] += 1
                        if verbose:
                            logger.warning(f"Error processing row: {e}")
                
                # Batch insert vendors
                if vendors_to_create:
                    db.add_all(vendors_to_create)
                    db.flush()  # Get IDs without committing
                    
                    # Update cache with actual IDs
                    for vendor_obj in vendors_to_create:
                        vendor_cache[vendor_obj.name] = vendor_obj.id
                
                # Batch insert awards
                award_objects = []
                for company_name, award_data in awards_to_create:
                    vendor_id = vendor_cache[company_name]
                    if hasattr(vendor_id, 'id'):  # Handle vendor objects
                        vendor_id = vendor_id.id
                    
                    award = models.SbirAward(vendor_id=vendor_id, **award_data)
                    award_objects.append(award)
                
                if award_objects:
                    db.add_all(award_objects)
                
                # Single commit for entire partition
                db.commit()
                
                # Update global stats
                for key in partition_stats:
                    if key == 'awards_created':
                        stats['valid_awards'] += partition_stats[key]
                    elif key == 'missing_company':
                        stats['skipped_missing_company'] += partition_stats[key]
                    elif key == 'missing_dates':
                        stats['skipped_missing_dates'] += partition_stats[key]
                    elif key == 'date_fallbacks':
                        stats['date_fallbacks_used'] += partition_stats[key]
                    elif key == 'errors':
                        stats['processing_errors'] += partition_stats[key]
                    elif key in stats:
                        stats[key] += partition_stats[key]
                
                partition_time = time.time() - partition_start
                
                # Update progress with detailed info
                progress.update(process_task, advance=1)
                
                # Show periodic detailed stats every 4 partitions
                if verbose and i % 4 == 0:
                    console.print(f"[dim]Partition {i}/{total_partitions}: "
                                f"{partition_stats['awards_created']} awards, "
                                f"{partition_stats['vendors_created']} new vendors, "
                                f"{partition_stats['missing_company'] + partition_stats['missing_dates']} rejected[/dim]")

        finally:
            db.close()
        
        total_time = time.time() - start_time
        
        # Results summary
        console.print()
        console.print(Panel.fit(
            "[bold green]✅ SBIR Data Loading Complete![/bold green]",
            border_style="green"
        ))
        
        # Detailed summary table with rejection reasons
        summary_table = Table(title="📈 SBIR Loading Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", justify="right", style="green")
        summary_table.add_column("Percentage", justify="right", style="yellow")
        
        # Calculate percentages
        total_processed = stats['total_rows']
        retention_rate = (stats['valid_awards'] / total_processed * 100) if total_processed > 0 else 0
        
        summary_table.add_row("Total rows processed", f"{total_processed:,}", "100.0%")
        summary_table.add_row("✅ Awards imported", f"{stats['valid_awards']:,}", f"{retention_rate:.1f}%")
        summary_table.add_row("🏢 New vendors created", f"{stats['vendors_created']:,}", "")
        summary_table.add_row("🔄 Existing vendors reused", f"{stats['vendors_reused']:,}", "")
        
        # Rejection breakdown
        if stats['skipped_missing_company'] > 0:
            pct = stats['skipped_missing_company'] / total_processed * 100
            summary_table.add_row("❌ Missing company name", f"{stats['skipped_missing_company']:,}", f"{pct:.1f}%")
        
        if stats['skipped_missing_dates'] > 0:
            pct = stats['skipped_missing_dates'] / total_processed * 100
            summary_table.add_row("❌ No valid dates found", f"{stats['skipped_missing_dates']:,}", f"{pct:.1f}%")
        
        if stats['date_fallbacks_used'] > 0:
            pct = stats['date_fallbacks_used'] / total_processed * 100
            summary_table.add_row("🔄 Award Year fallbacks used", f"{stats['date_fallbacks_used']:,}", f"{pct:.1f}%")
        
        if stats['processing_errors'] > 0:
            pct = stats['processing_errors'] / total_processed * 100
            summary_table.add_row("⚠️  Processing errors", f"{stats['processing_errors']:,}", f"{pct:.1f}%")
        
        summary_table.add_row("⏱️  Total processing time", f"{total_time:.1f}s", "")
        summary_table.add_row("🚀 Processing rate", f"{total_processed/total_time:.0f} rows/sec", "")
        
        console.print(summary_table)
        
        # Data quality insights
        if stats['date_fallbacks_used'] > 0:
            console.print(f"[yellow]💡 Data Quality Note: {stats['date_fallbacks_used']:,} records used Award Year fallback for missing dates[/yellow]")
        
        total_rejected = stats['skipped_missing_company'] + stats['skipped_missing_dates'] + stats['processing_errors']
        if total_rejected > 0:
            console.print(f"[yellow]⚠️  {total_rejected:,} rows rejected. Use --verbose for detailed error tracking.[/yellow]")

@cli.command()
@click.option('--file-path', required=True, help='Path to the USAspending CSV file.')
@click.option('--chunk-size', default=50000, help='Number of records to process in each batch.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_usaspending_data(file_path, chunk_size, verbose):
    """Load USAspending contract data from CSV file."""
    console = Console()
    
    if verbose:
        logger.remove()
        logger.add(lambda msg: console.print(msg, style="dim"), level="DEBUG")
    
    file_path = Path(file_path)
    if not file_path.exists():
        console.print(f"[red]Error: File {file_path} not found.[/red]")
        return
    
    # Enhanced file info
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    console.print(Panel.fit(
        "[bold blue]Contract Data Loader[/bold blue]\n"
        f"[dim]Processing: {file_path.name} ({file_size_mb:.1f} MB)[/dim]",
        border_style="blue"
    ))
    
    # Initialize comprehensive statistics tracking
    stats = {
        'total_rows': 0,
        'valid_contracts': 0,
        'skipped_missing_piid': 0,
        'skipped_missing_agency': 0,
        'skipped_missing_recipient': 0,
        'skipped_duplicates': 0,
        'vendors_created': 0,
        'vendors_reused': 0,
        'processing_errors': 0,
        'malformed_dates': 0
    }
    
    start_time = time.time()
    db = SessionLocal()
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            # Estimate total rows for progress tracking
            analyze_task = progress.add_task("🔍 Analyzing file structure...", total=1)
            with open(file_path, 'r') as f:
                stats['total_rows'] = sum(1 for _ in f) - 1  # Subtract header
            progress.update(analyze_task, advance=1)
            
            console.print(f"📋 Total rows to process: {stats['total_rows']:,}")
            
            load_task = progress.add_task(
                f"📥 Processing {file_path.name}", 
                total=stats['total_rows']
            )
            
            processed_rows = 0
            all_contract_data = []
            vendor_cache = {}
            chunk_count = 0
            
            for chunk_df in pd.read_csv(file_path, chunksize=chunk_size, low_memory=False, dtype=str, on_bad_lines='skip'):
                chunk_count += 1
                chunk_stats = {
                    'valid': 0,
                    'missing_piid': 0,
                    'missing_agency': 0,
                    'missing_recipient': 0,
                    'vendors_created': 0,
                    'vendors_reused': 0,
                    'errors': 0,
                    'malformed_dates': 0
                }
                
                # Process each chunk
                for _, row in chunk_df.iterrows():
                    try:
                        # Skip rows with missing critical data
                        piid = str(row.get('award_id_piid', '')).strip()
                        if not piid or piid.lower() in ['nan', 'null', '']:
                            chunk_stats['missing_piid'] += 1
                            continue
                            
                        agency = str(row.get('awarding_agency_name', '')).strip()
                        if not agency or agency.lower() in ['nan', 'null', '']:
                            chunk_stats['missing_agency'] += 1
                            continue
                        
                        recipient_name = str(row.get('recipient_name', '')).strip()
                        if not recipient_name or recipient_name.lower() in ['nan', 'null', '']:
                            chunk_stats['missing_recipient'] += 1
                            continue
                    
                        # Get or create vendor
                        vendor_id = None
                        # Check cache first
                        vendor_id = vendor_cache.get(recipient_name)
                        if not vendor_id:
                            # Check database
                            vendor = db.query(models.Vendor).filter(models.Vendor.name == recipient_name).first()
                            if vendor:
                                vendor_id = vendor.id
                                vendor_cache[recipient_name] = vendor_id
                                chunk_stats['vendors_reused'] += 1
                            else:
                                # Create new vendor
                                vendor = models.Vendor(name=recipient_name, created_at=pd.Timestamp.now())
                                db.add(vendor)
                                db.flush()  # Get ID
                                vendor_id = vendor.id
                                vendor_cache[recipient_name] = vendor_id
                                chunk_stats['vendors_created'] += 1
                        
                        # Create unique key from PIID + modification number + transaction number
                        mod_number = str(row.get('modification_number', '0')).strip()
                        trans_number = str(row.get('transaction_number', '0')).strip()
                        unique_piid = f"{piid}_{mod_number}_{trans_number}"
                        
                        # Handle NaN values in start_date
                        start_date_raw = row.get('period_of_performance_start_date')
                        if pd.isna(start_date_raw) or str(start_date_raw).lower() in ['nan', 'null', '']:
                            start_date = None
                        else:
                            start_date = pd.to_datetime(start_date_raw, errors='coerce')
                            if pd.isna(start_date):
                                chunk_stats['malformed_dates'] += 1
                                start_date = None
                        
                        # Generate unique ID and map fields
                        contract_data = {
                            'id': uuid.uuid4(),
                            'vendor_id': vendor_id,
                            'piid': unique_piid,
                            'agency': agency,
                            'start_date': start_date,
                            'competition_details': {
                                'extent_competed': str(row.get('extent_competed', '')),
                                'type_of_contract_pricing': str(row.get('type_of_contract_pricing', ''))
                            }
                        }
                        
                        all_contract_data.append(contract_data)
                        chunk_stats['valid'] += 1
                        
                    except Exception as e:
                        chunk_stats['errors'] += 1
                        if verbose:
                            logger.warning(f"Error processing row: {e}")
                        continue
                
                # Update global stats
                for key in chunk_stats:
                    if key in stats:
                        if key == 'valid':
                            stats['valid_contracts'] += chunk_stats[key]
                        elif key == 'missing_piid':
                            stats['skipped_missing_piid'] += chunk_stats[key]
                        elif key == 'missing_agency':
                            stats['skipped_missing_agency'] += chunk_stats[key]
                        elif key == 'missing_recipient':
                            stats['skipped_missing_recipient'] += chunk_stats[key]
                        elif key == 'errors':
                            stats['processing_errors'] += chunk_stats[key]
                        elif key == 'malformed_dates':
                            stats['malformed_dates'] += chunk_stats[key]
                        elif key == 'vendors_created':
                            stats['vendors_created'] += chunk_stats[key]
                        elif key == 'vendors_reused':
                            stats['vendors_reused'] += chunk_stats[key]
                
                processed_rows += len(chunk_df)
                progress.update(load_task, advance=len(chunk_df))
                
                # Show periodic detailed stats every 4 chunks
                if verbose and chunk_count % 4 == 0:
                    console.print(f"[dim]Chunk {chunk_count}: "
                                f"{chunk_stats['valid']} valid, "
                                f"{chunk_stats['vendors_created']} new vendors, "
                                f"{sum(chunk_stats[k] for k in ['missing_piid', 'missing_agency', 'missing_recipient', 'errors'])} rejected[/dim]")
            
            # Handle duplicates by processing contracts individually
            if all_contract_data:
                insert_task = progress.add_task(
                    f"💾 Inserting {len(all_contract_data):,} contracts...", 
                    total=len(all_contract_data)
                )
                
                inserted = 0
                duplicates = 0
                batch_size = 1000
                
                for i in range(0, len(all_contract_data), batch_size):
                    batch = all_contract_data[i:i + batch_size]
                    
                    for contract_data in batch:
                        try:
                            # Check if contract already exists
                            existing = db.query(models.Contract).filter_by(piid=contract_data['piid']).first()
                            if not existing:
                                contract = models.Contract(**contract_data)
                                db.add(contract)
                                inserted += 1
                            else:
                                duplicates += 1
                        except Exception as e:
                            if verbose:
                                logger.warning(f"Failed to insert contract {contract_data.get('piid', 'unknown')}: {e}")
                            continue
                    
                    # Commit batch
                    try:
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        if verbose:
                            logger.warning(f"Batch commit failed: {e}")
                    
                    progress.update(insert_task, advance=len(batch))
                
                stats['valid_contracts'] = inserted
                stats['skipped_duplicates'] = duplicates
        
        total_time = time.time() - start_time
        
        # Results summary
        console.print()
        console.print(Panel.fit(
            "[bold green]✅ Contract Data Loading Complete![/bold green]",
            border_style="green"
        ))
        
        # Detailed summary table with rejection reasons
        summary_table = Table(title="📈 Contract Loading Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", justify="right", style="green")
        summary_table.add_column("Percentage", justify="right", style="yellow")
        
        # Calculate percentages
        total_processed = stats['total_rows']
        retention_rate = (stats['valid_contracts'] / total_processed * 100) if total_processed > 0 else 0
        
        summary_table.add_row("Total rows processed", f"{total_processed:,}", "100.0%")
        summary_table.add_row("✅ Contracts imported", f"{stats['valid_contracts']:,}", f"{retention_rate:.1f}%")
        summary_table.add_row("🏢 New vendors created", f"{stats['vendors_created']:,}", "")
        summary_table.add_row("🔄 Existing vendors reused", f"{stats['vendors_reused']:,}", "")
        
        # Rejection breakdown
        if stats['skipped_missing_piid'] > 0:
            pct = stats['skipped_missing_piid'] / total_processed * 100
            summary_table.add_row("❌ Missing PIID", f"{stats['skipped_missing_piid']:,}", f"{pct:.1f}%")
        
        if stats['skipped_missing_agency'] > 0:
            pct = stats['skipped_missing_agency'] / total_processed * 100
            summary_table.add_row("❌ Missing agency", f"{stats['skipped_missing_agency']:,}", f"{pct:.1f}%")
        
        if stats['skipped_missing_recipient'] > 0:
            pct = stats['skipped_missing_recipient'] / total_processed * 100
            summary_table.add_row("❌ Missing recipient", f"{stats['skipped_missing_recipient']:,}", f"{pct:.1f}%")
        
        if stats['skipped_duplicates'] > 0:
            pct = stats['skipped_duplicates'] / total_processed * 100
            summary_table.add_row("🔄 Duplicate PIIDs skipped", f"{stats['skipped_duplicates']:,}", f"{pct:.1f}%")
        
        if stats['malformed_dates'] > 0:
            pct = stats['malformed_dates'] / total_processed * 100
            summary_table.add_row("⚠️  Malformed dates", f"{stats['malformed_dates']:,}", f"{pct:.1f}%")
        
        if stats['processing_errors'] > 0:
            pct = stats['processing_errors'] / total_processed * 100
            summary_table.add_row("⚠️  Processing errors", f"{stats['processing_errors']:,}", f"{pct:.1f}%")
        
        summary_table.add_row("⏱️  Total processing time", f"{total_time:.1f}s", "")
        summary_table.add_row("🚀 Processing rate", f"{total_processed/total_time:.0f} rows/sec", "")
        
        console.print(summary_table)
        
        # Data quality insights
        total_rejected = (stats['skipped_missing_piid'] + stats['skipped_missing_agency'] + 
                         stats['skipped_missing_recipient'] + stats['processing_errors'])
        if total_rejected > 0:
            console.print(f"[yellow]⚠️  {total_rejected:,} rows rejected due to missing required fields. Use --verbose for detailed tracking.[/yellow]")
        
        if stats['malformed_dates'] > 0:
            console.print(f"[yellow]💡 Data Quality Note: {stats['malformed_dates']:,} records had unparseable dates (set to NULL)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error loading data: {e}[/red]")
        db.rollback()
    finally:
        db.close()

@cli.command()
@click.option('--file-path', required=True, help='Path to the USAspending CSV file.')
@click.option('--chunk-size', default=100000, help='Larger chunks for better performance.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_usaspending_data_fast(file_path, chunk_size, verbose):
    """Optimized contract loader with 3-5x performance improvements."""
    console = Console()
    start_time = time.time()
    
    file_path = Path(file_path)
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    console.print(Panel.fit(
        "[bold green]🚀 Fast Contract Data Loader[/bold green]\n"
        f"[dim]Processing: {file_path.name} ({file_size_mb:.1f} MB)[/dim]",
        border_style="green"
    ))
    
    db = SessionLocal()
    
    try:
        # Optimized CSV reading - only load required columns
        required_cols = ['award_id_piid', 'awarding_agency_name', 'recipient_name', 
                        'modification_number', 'transaction_number', 'period_of_performance_start_date',
                        'extent_competed', 'type_of_contract_pricing']
        
        chunk_reader = pd.read_csv(
            file_path,
            chunksize=chunk_size,
            dtype=str,
            engine='c',  # Fastest engine
            na_filter=False,  # Don't convert to NaN
            keep_default_na=False,  # Don't interpret strings as NaN
            usecols=required_cols,
            on_bad_lines='skip'
        )
        
        total_processed = 0
        total_inserted = 0
        vendor_cache = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("🚀 Fast processing...", total=None)
            
            for chunk_num, chunk_df in enumerate(chunk_reader, 1):
                chunk_start = time.time()
                
                # Vectorized filtering - much faster than row-by-row
                valid_mask = (
                    chunk_df['award_id_piid'].notna() & 
                    (chunk_df['award_id_piid'].str.strip() != '') &
                    chunk_df['awarding_agency_name'].notna() &
                    (chunk_df['awarding_agency_name'].str.strip() != '')
                )
                chunk_df = chunk_df[valid_mask]
                
                if len(chunk_df) == 0:
                    continue
                
                # Bulk vendor processing
                recipients = chunk_df['recipient_name'].fillna('').str.strip()
                recipients = recipients[recipients != ''].unique()
                
                # Batch check existing vendors
                existing_vendors = db.query(models.Vendor).filter(
                    models.Vendor.name.in_(recipients)
                ).all()
                
                for vendor in existing_vendors:
                    vendor_cache[vendor.name] = vendor.id
                
                # Create new vendors in bulk
                new_vendor_names = [name for name in recipients if name not in vendor_cache]
                if new_vendor_names:
                    new_vendors = [
                        models.Vendor(name=name, created_at=pd.Timestamp.now())
                        for name in new_vendor_names
                    ]
                    db.add_all(new_vendors)
                    db.flush()  # Get IDs
                    
                    for vendor in new_vendors:
                        vendor_cache[vendor.name] = vendor.id
                
                # Vectorized contract data preparation
                chunk_df['unique_piid'] = (
                    chunk_df['award_id_piid'].astype(str) + '_' +
                    chunk_df['modification_number'].fillna('0').astype(str) + '_' +
                    chunk_df['transaction_number'].fillna('0').astype(str)
                )
                
                # Prepare bulk insert data
                contracts_data = []
                for _, row in chunk_df.iterrows():
                    recipient = str(row.get('recipient_name', '')).strip()
                    vendor_id = vendor_cache.get(recipient)
                    
                    contracts_data.append({
                        'id': uuid.uuid4(),
                        'vendor_id': vendor_id,
                        'piid': row['unique_piid'],
                        'agency': row['awarding_agency_name'],
                        'start_date': pd.to_datetime(row.get('period_of_performance_start_date'), errors='coerce'),
                        'competition_details': {
                            'extent_competed': str(row.get('extent_competed', '')),
                            'type_of_contract_pricing': str(row.get('type_of_contract_pricing', ''))
                        }
                    })
                
                # Bulk insert - much faster than individual inserts
                if contracts_data:
                    db.bulk_insert_mappings(models.Contract, contracts_data)
                    db.commit()
                    total_inserted += len(contracts_data)
                
                total_processed += len(chunk_df)
                chunk_time = time.time() - chunk_start
                
                progress.update(task, description=f"Chunk {chunk_num}: {total_processed:,} processed, {total_inserted:,} inserted ({len(chunk_df)/chunk_time:.0f} rows/sec)")
        
        total_time = time.time() - start_time
        
        # Results
        console.print()
        console.print(Panel.fit(
            "[bold green]🚀 Fast Loading Complete![/bold green]",
            border_style="green"
        ))
        
        summary_table = Table(title="⚡ Performance Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right", style="green")
        
        summary_table.add_row("Total rows processed", f"{total_processed:,}")
        summary_table.add_row("Contracts inserted", f"{total_inserted:,}")
        summary_table.add_row("Processing time", f"{total_time:.1f}s")
        summary_table.add_row("🚀 Processing rate", f"{total_processed/total_time:.0f} rows/sec")
        summary_table.add_row("💾 Insert rate", f"{total_inserted/total_time:.0f} contracts/sec")
        
        console.print(summary_table)
        
    finally:
        db.close()

@cli.command()
@click.option('--file-path', default='data/award_data.csv', help='Path to the SBIR award data CSV file.')
@click.option('--chunk-size', default=20000, help='Larger chunks for better performance.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def load_sbir_data_fast(file_path, chunk_size, verbose):
    """Optimized SBIR loader with 2-3x performance improvements."""
    console = Console()
    start_time = time.time()
    
    data_file = Path(file_path)
    if not data_file.exists():
        console.print(f"[red]❌ Error: File not found: {file_path}[/red]")
        return
    
    file_size = data_file.stat().st_size / (1024 * 1024)
    console.print(Panel.fit(
        "[bold green]🚀 Fast SBIR Data Loader[/bold green]\n"
        f"[dim]Processing: {data_file.name} ({file_size:.1f} MB)[/dim]",
        border_style="green"
    ))
    
    init_db()
    db = SessionLocal()
    
    try:
        # Optimized CSV reading
        df = pd.read_csv(
            file_path,
            dtype=str,
            engine='c',
            na_filter=False,
            keep_default_na=False,
            on_bad_lines='skip'
        )
        
        console.print(f"📊 Loaded {len(df):,} rows in {time.time() - start_time:.1f}s")
        
        # Vectorized data cleaning
        df = df[df['Company'].notna() & (df['Company'].str.strip() != '')]
        
        # Bulk vendor creation
        vendor_names = df['Company'].str.strip().unique()
        
        # Check existing vendors in bulk
        existing_vendors = {v.name: v.id for v in db.query(models.Vendor).filter(models.Vendor.name.in_(vendor_names)).all()}
        
        # Create new vendors
        new_vendor_names = [name for name in vendor_names if name not in existing_vendors]
        if new_vendor_names:
            new_vendors = [models.Vendor(name=name, created_at=pd.Timestamp.now()) for name in new_vendor_names]
            db.add_all(new_vendors)
            db.flush()
            
            for vendor in new_vendors:
                existing_vendors[vendor.name] = vendor.id
        
        # Vectorized date processing
        df['award_date'] = pd.to_datetime(df['Proposal Award Date'], errors='coerce')
        
        # Award Year fallback for missing dates
        missing_dates = df['award_date'].isna()
        df.loc[missing_dates, 'award_date'] = pd.to_datetime(df.loc[missing_dates, 'Award Year'], format='%Y', errors='coerce')
        
        # Filter valid records
        valid_records = df[df['award_date'].notna() & df['Company'].isin(existing_vendors.keys())].copy()
        
        # Prepare bulk insert data
        awards_data = []
        for _, row in valid_records.iterrows():
            awards_data.append({
                'vendor_id': existing_vendors[row['Company'].strip()],
                'award_piid': str(row.get('Award Number', '')),
                'phase': str(row.get('Phase', '')),
                'agency': str(row.get('Agency', '')),
                'topic': str(row.get('Topic', '')),
                'award_date': row['award_date'],
                'completion_date': pd.to_datetime(row.get('Contract End Date'), errors='coerce'),
                'created_at': pd.Timestamp.now()
            })
        
        # Bulk insert
        if awards_data:
            db.bulk_insert_mappings(models.SbirAward, awards_data)
            db.commit()
        
        total_time = time.time() - start_time
        
        # Results
        console.print()
        console.print(Panel.fit(
            "[bold green]🚀 Fast SBIR Loading Complete![/bold green]",
            border_style="green"
        ))
        
        summary_table = Table(title="⚡ Performance Results")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right", style="green")
        
        summary_table.add_row("Total rows read", f"{len(df):,}")
        summary_table.add_row("Valid awards processed", f"{len(awards_data):,}")
        summary_table.add_row("New vendors created", f"{len(new_vendor_names):,}")
        summary_table.add_row("Processing time", f"{total_time:.1f}s")
        summary_table.add_row("🚀 Processing rate", f"{len(awards_data)/total_time:.0f} awards/sec")
        
        console.print(summary_table)
        
    finally:
        db.close()
if __name__ == '__main__':
    cli()
