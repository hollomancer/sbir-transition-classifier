#!/usr/bin/env python3
"""
Test script to verify performance optimizations are working.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
from sqlalchemy import text
from src.sbir_transition_classifier.db.database import engine, SessionLocal
from src.sbir_transition_classifier.core import models
from loguru import logger

def test_database_performance():
    """Test database query performance with new indexes."""
    
    db = SessionLocal()
    
    try:
        # Test 1: Vendor name lookup (should use new index)
        start = time.time()
        result = db.query(models.Vendor).filter(models.Vendor.name.like('%Test%')).first()
        vendor_lookup_time = time.time() - start
        logger.info(f"Vendor name lookup: {vendor_lookup_time:.4f}s")
        
        # Test 2: SBIR award agency filtering (should use new index)
        start = time.time()
        result = db.query(models.SbirAward).filter(models.SbirAward.agency == 'DOD').limit(10).all()
        agency_filter_time = time.time() - start
        logger.info(f"Agency filtering: {agency_filter_time:.4f}s")
        
        # Test 3: Join query (should benefit from foreign key indexes)
        start = time.time()
        result = db.query(models.SbirAward).join(models.Vendor).filter(
            models.Vendor.name.like('%Corp%')
        ).limit(10).all()
        join_time = time.time() - start
        logger.info(f"Join query: {join_time:.4f}s")
        
        # Test 4: Check if indexes exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename IN ('vendors', 'sbir_awards', 'contracts', 'detections')
                ORDER BY indexname;
            """))
            indexes = [row[0] for row in result]
            logger.info(f"Found {len(indexes)} indexes")
            for idx in indexes:
                if 'idx_' in idx:
                    logger.info(f"  - {idx}")
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
    finally:
        db.close()

def test_chunk_size_setting():
    """Verify chunk size defaults are updated."""
    
    # Import CLI modules to check defaults
    from src.sbir_transition_classifier.cli.bulk import bulk_process
    
    # Check if the default chunk size is updated
    for param in bulk_process.params:
        if param.name == 'chunk_size':
            logger.info(f"Bulk process chunk size default: {param.default}")
            assert param.default == 5000, f"Expected 5000, got {param.default}"
            break
    
    logger.info("✅ Chunk size optimization verified")

if __name__ == "__main__":
    logger.info("Testing performance optimizations...")
    
    test_chunk_size_setting()
    test_database_performance()
    
    logger.info("✅ All optimization tests complete!")
