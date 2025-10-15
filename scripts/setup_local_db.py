#!/usr/bin/env python3
"""
Local database setup script for SBIR transition classifier.

Creates and initializes SQLite database for local execution.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
import sqlite3
from datetime import datetime


def create_local_database(db_path: Path) -> bool:
    """
    Create local SQLite database with required tables.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database (creates if doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create vendors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create vendor_identifiers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendor_identifiers (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                identifier_type TEXT NOT NULL,
                identifier_value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id)
            )
        """)
        
        # Create sbir_awards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sbir_awards (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                award_piid TEXT NOT NULL,
                phase TEXT NOT NULL,
                agency TEXT NOT NULL,
                award_date TIMESTAMP NOT NULL,
                completion_date TIMESTAMP NOT NULL,
                topic TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id)
            )
        """)
        
        # Create contracts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                piid TEXT NOT NULL,
                parent_piid TEXT,
                agency TEXT NOT NULL,
                start_date TIMESTAMP NOT NULL,
                naics_code TEXT,
                psc_code TEXT,
                competition_details TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id)
            )
        """)
        
        # Create detections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id TEXT PRIMARY KEY,
                sbir_award_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                likelihood_score REAL NOT NULL,
                confidence TEXT NOT NULL,
                evidence_bundle TEXT,
                config_version TEXT,
                local_session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sbir_award_id) REFERENCES sbir_awards (id),
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        # Create detection_sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detection_sessions (
                session_id TEXT PRIMARY KEY,
                config_used TEXT NOT NULL,
                config_checksum TEXT NOT NULL,
                input_datasets TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                status TEXT NOT NULL,
                output_path TEXT NOT NULL,
                detection_count INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        
        # Create evidence_bundle_artifacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_bundle_artifacts (
                bundle_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                detection_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                summary_path TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                file_size INTEGER NOT NULL,
                evidence_type TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES detection_sessions (session_id),
                FOREIGN KEY (detection_id) REFERENCES detections (id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vendor_identifiers_value ON vendor_identifiers (identifier_value)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sbir_awards_piid ON sbir_awards (award_piid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contracts_piid ON contracts (piid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_session ON detections (local_session_id)")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully created local database at {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create local database: {e}")
        return False


def main():
    """Main entry point."""
    # Default database location
    db_path = Path.cwd() / "data" / "local.db"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    logger.info(f"Setting up local database at {db_path}")
    
    if create_local_database(db_path):
        logger.info("Local database setup completed successfully")
        print(f"Database created at: {db_path}")
    else:
        logger.error("Local database setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
