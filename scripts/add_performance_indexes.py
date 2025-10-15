#!/usr/bin/env python3
"""
Add performance indexes to existing database.
Run this after updating the models to add indexes to existing tables.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import text
from src.sbir_transition_classifier.db.database import engine
from loguru import logger

def add_indexes():
    """Add indexes to improve query performance."""
    
    indexes = [
        # Single column indexes
        "CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name);",
        "CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_vendor_id ON vendor_identifiers(vendor_id);",
        "CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_type ON vendor_identifiers(identifier_type);",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_vendor_id ON sbir_awards(vendor_id);",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_piid ON sbir_awards(award_piid);",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_phase ON sbir_awards(phase);",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_agency ON sbir_awards(agency);",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_award_date ON sbir_awards(award_date);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_vendor_id ON contracts(vendor_id);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_agency ON contracts(agency);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_naics ON contracts(naics_code);",
        "CREATE INDEX IF NOT EXISTS idx_contracts_psc ON contracts(psc_code);",
        "CREATE INDEX IF NOT EXISTS idx_detections_sbir_award_id ON detections(sbir_award_id);",
        "CREATE INDEX IF NOT EXISTS idx_detections_contract_id ON detections(contract_id);",
        "CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections(confidence);",
        "CREATE INDEX IF NOT EXISTS idx_detections_date ON detections(detection_date);",
        
        # Composite indexes for common query patterns
        "CREATE INDEX IF NOT EXISTS idx_vendor_agency_date ON sbir_awards(vendor_id, agency, completion_date);",
        "CREATE INDEX IF NOT EXISTS idx_contract_vendor_agency ON contracts(vendor_id, agency, start_date);",
        "CREATE INDEX IF NOT EXISTS idx_detection_score_confidence ON detections(likelihood_score, confidence);",
    ]
    
    with engine.connect() as conn:
        for sql in indexes:
            try:
                logger.info(f"Creating index: {sql}")
                conn.execute(text(sql))
                conn.commit()
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
    
    logger.info("Index creation complete!")

if __name__ == "__main__":
    add_indexes()
