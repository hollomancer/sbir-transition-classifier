#!/usr/bin/env python3
"""Add database indexes for performance optimization."""

from sqlalchemy import text
from src.sbir_transition_classifier.db.database import engine

def add_performance_indexes():
    """Add indexes to speed up detection queries."""
    
    indexes = [
        # Vendor lookup indexes
        "CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name)",
        
        # Vendor identifier indexes  
        "CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_vendor_id ON vendor_identifiers(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_type ON vendor_identifiers(identifier_type)",
        "CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_value ON vendor_identifiers(identifier_value)",
        
        # SBIR award indexes for detection queries
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_vendor_id ON sbir_awards(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_piid ON sbir_awards(award_piid)",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_phase ON sbir_awards(phase)",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_agency ON sbir_awards(agency)",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_completion_date ON sbir_awards(completion_date)",
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_award_date ON sbir_awards(award_date)",
        
        # Contract indexes for candidate searches
        "CREATE INDEX IF NOT EXISTS idx_contracts_vendor_id ON contracts(vendor_id)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_piid ON contracts(piid)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_agency ON contracts(agency)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_start_date ON contracts(start_date)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_naics_code ON contracts(naics_code)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_psc_code ON contracts(psc_code)",
        
        # Composite indexes for common query patterns
        "CREATE INDEX IF NOT EXISTS idx_sbir_awards_vendor_completion ON sbir_awards(vendor_id, completion_date)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_vendor_start ON contracts(vendor_id, start_date)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_agency_start ON contracts(agency, start_date)",
    ]
    
    with engine.connect() as conn:
        for idx_sql in indexes:
            print(f"Adding index: {idx_sql.split('ON')[1].strip()}")
            conn.execute(text(idx_sql))
            conn.commit()
    
    print(f"✅ Added {len(indexes)} performance indexes")

if __name__ == "__main__":
    add_performance_indexes()
