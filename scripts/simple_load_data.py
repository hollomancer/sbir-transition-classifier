#!/usr/bin/env python3
"""Simple data loader to work around dask dtype issues"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
from sqlalchemy.orm import Session
from sbir_transition_classifier.db.database import SessionLocal, engine
from sbir_transition_classifier.core import models
from loguru import logger
import time
from datetime import datetime

def init_db():
    """Initialize database tables"""
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def load_sbir_data_simple(file_path: str, chunk_size: int = 10000):
    """Load SBIR data using pandas with chunking"""
    logger.info(f"Loading SBIR data from {file_path}")
    
    init_db()
    db: Session = SessionLocal()
    
    try:
        # Read CSV in chunks to handle large file
        chunk_iter = pd.read_csv(file_path, chunksize=chunk_size, dtype=str)
        
        total_processed = 0
        vendors_created = 0
        awards_created = 0
        errors = 0
        
        for chunk_num, df in enumerate(chunk_iter, 1):
            logger.info(f"Processing chunk {chunk_num} ({len(df)} rows)")
            
            for _, row in df.iterrows():
                try:
                    # Get company name
                    company_name = str(row.get('Company', '')).strip()
                    if not company_name or company_name.lower() == 'nan':
                        errors += 1
                        continue
                    
                    # Check if vendor exists
                    vendor = db.query(models.Vendor).filter(models.Vendor.name == company_name).first()
                    if not vendor:
                        vendor = models.Vendor(
                            name=company_name,
                            created_at=datetime.utcnow()
                        )
                        db.add(vendor)
                        db.flush()  # Get the ID
                        vendors_created += 1
                    
                    # Create SBIR award
                    award = models.SbirAward(
                        vendor_id=vendor.id,
                        award_piid=str(row.get('Agency Tracking Number', '')),
                        phase=str(row.get('Phase', '')),
                        agency=str(row.get('Agency', '')),
                        award_date=pd.to_datetime(row.get('Proposal Award Date'), errors='coerce'),
                        completion_date=pd.to_datetime(row.get('Contract End Date'), errors='coerce'),
                        topic=str(row.get('Award Title', '')),
                        raw_data=row.to_dict(),
                        created_at=datetime.utcnow()
                    )
                    db.add(award)
                    awards_created += 1
                    
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error processing row: {e}")
            
            # Commit after each chunk
            db.commit()
            total_processed += len(df)
            
            logger.info(f"Chunk {chunk_num}: {len(df)} rows processed, {vendors_created} vendors total, {awards_created} awards total")
        
        logger.info(f"Total: {total_processed} rows, {vendors_created} vendors, {awards_created} awards, {errors} errors")
        
    finally:
        db.close()

def load_contract_data_simple(file_path: str, chunk_size: int = 10000):
    """Load contract data using pandas with chunking"""
    logger.info(f"Loading contract data from {file_path}")
    
    db: Session = SessionLocal()
    
    try:
        # Read CSV in chunks
        chunk_iter = pd.read_csv(file_path, chunksize=chunk_size, dtype=str)
        
        total_processed = 0
        contracts_created = 0
        errors = 0
        
        for chunk_num, df in enumerate(chunk_iter, 1):
            logger.info(f"Processing chunk {chunk_num} ({len(df)} rows)")
            
            for _, row in df.iterrows():
                try:
                    # Get vendor name from correct column
                    vendor_name = str(row.get('recipient_name', '')).strip()
                    if not vendor_name or vendor_name.lower() == 'nan':
                        errors += 1
                        continue
                    
                    # Find or create vendor
                    vendor = db.query(models.Vendor).filter(models.Vendor.name == vendor_name).first()
                    if not vendor:
                        vendor = models.Vendor(
                            name=vendor_name,
                            created_at=datetime.utcnow()
                        )
                        db.add(vendor)
                        db.flush()
                    
                    # Create contract with correct column mappings
                    piid = str(row.get('award_id_piid', ''))
                    if not piid or piid == 'nan':
                        errors += 1
                        continue
                        
                    # Check for duplicates
                    existing_contract = db.query(models.Contract).filter(models.Contract.piid == piid).first()
                    if existing_contract:
                        continue  # Skip duplicates
                    
                    contract = models.Contract(
                        vendor_id=vendor.id,
                        piid=piid,
                        agency=str(row.get('awarding_agency_name', '')),
                        start_date=pd.to_datetime(row.get('action_date'), errors='coerce'),
                        naics_code=str(row.get('naics_code', '')),
                        psc_code=str(row.get('product_or_service_code', '')),
                        competition_details={
                            'extent_competed': row.get('extent_competed', ''),
                            'sole_source': 'NOT COMPETED' in str(row.get('extent_competed', '')).upper()
                        },
                        raw_data=row.to_dict(),
                        created_at=datetime.utcnow()
                    )
                    db.add(contract)
                    contracts_created += 1
                    
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error processing row: {e}")
            
            # Commit after each chunk
            db.commit()
            total_processed += len(df)
            
            logger.info(f"Chunk {chunk_num}: {len(df)} rows processed, {contracts_created} contracts total")
        
        logger.info(f"Total: {total_processed} rows, {contracts_created} contracts, {errors} errors")
        
    finally:
        db.close()

if __name__ == '__main__':
    import sys
    
    logger.info("Starting simple data loading")
    
    # Load SBIR data
    logger.info("Loading SBIR awards...")
    load_sbir_data_simple('data/award_data.csv', chunk_size=1000)
    
    # Load contract data
    logger.info("Loading contracts...")
    load_contract_data_simple('data/FY2026_All_Contracts_Full_20251008_1.csv', chunk_size=1000)
    
    logger.info("Data loading complete!")