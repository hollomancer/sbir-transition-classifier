#!/usr/bin/env python3
"""
Benchmark CSV loading performance improvements.
"""

import time
import pandas as pd
import polars as pl
from pathlib import Path
import subprocess
import sys

def benchmark_csv_reading():
    """Compare different CSV reading approaches."""
    print("🏁 CSV Reading Performance Benchmark")
    print("=" * 50)
    
    # Find a test CSV file
    data_dir = Path("data")
    csv_files = list(data_dir.glob("*.csv"))
    
    if not csv_files:
        print("❌ No CSV files found for benchmarking")
        return
    
    test_file = csv_files[0]
    file_size = test_file.stat().st_size / (1024 * 1024)
    print(f"📁 Test file: {test_file.name} ({file_size:.1f} MB)")
    
    results = {}
    
    # 1. Current pandas approach
    print("\n🐼 Testing current pandas approach...")
    start = time.time()
    try:
        df1 = pd.read_csv(test_file, dtype=str, on_bad_lines='skip', encoding='utf-8', quoting=1)
        results['current_pandas'] = time.time() - start
        row_count = len(df1)
        print(f"   ✅ Loaded {row_count:,} rows in {results['current_pandas']:.2f}s")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results['current_pandas'] = None
    
    # 2. Optimized pandas
    print("\n🚀 Testing optimized pandas...")
    start = time.time()
    try:
        df2 = pd.read_csv(
            test_file,
            dtype=str,
            engine='c',
            na_filter=False,
            keep_default_na=False,
            low_memory=False
        )
        results['optimized_pandas'] = time.time() - start
        print(f"   ✅ Loaded {len(df2):,} rows in {results['optimized_pandas']:.2f}s")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results['optimized_pandas'] = None
    
    # 3. Polars (if available)
    print("\n⚡ Testing Polars...")
    start = time.time()
    try:
        df3 = pl.read_csv(test_file, ignore_errors=True).to_pandas()
        results['polars'] = time.time() - start
        print(f"   ✅ Loaded {len(df3):,} rows in {results['polars']:.2f}s")
    except Exception as e:
        print(f"   ❌ Failed (install with: pip install polars): {e}")
        results['polars'] = None
    
    # 4. Chunked reading
    print("\n📦 Testing chunked reading...")
    start = time.time()
    try:
        chunk_count = 0
        total_rows = 0
        for chunk in pd.read_csv(test_file, chunksize=50000, dtype=str, engine='c', na_filter=False):
            chunk_count += 1
            total_rows += len(chunk)
        results['chunked'] = time.time() - start
        print(f"   ✅ Processed {total_rows:,} rows in {chunk_count} chunks in {results['chunked']:.2f}s")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results['chunked'] = None
    
    # Summary
    print("\n📊 Performance Summary:")
    print("-" * 40)
    
    baseline = results.get('current_pandas')
    if baseline:
        for method, duration in results.items():
            if duration:
                speedup = baseline / duration
                rate = row_count / duration if 'row_count' in locals() else 0
                print(f"{method:20}: {duration:6.2f}s ({speedup:4.1f}x) - {rate:,.0f} rows/sec")
    
    return results

def benchmark_bulk_operations():
    """Test bulk database operations."""
    print("\n🗄️  Database Operations Benchmark")
    print("=" * 50)
    
    # Test with sample data
    sample_data = [
        {'name': f'Company_{i}', 'value': i} 
        for i in range(10000)
    ]
    
    from src.sbir_transition_classifier.db.database import SessionLocal
    from src.sbir_transition_classifier.core import models
    
    db = SessionLocal()
    
    try:
        # 1. Individual inserts
        print("🐌 Testing individual inserts...")
        start = time.time()
        for i in range(100):  # Smaller sample
            vendor = models.Vendor(name=f'test_vendor_{i}', created_at=pd.Timestamp.now())
            db.add(vendor)
            db.commit()
        individual_time = time.time() - start
        print(f"   Individual: {individual_time:.2f}s for 100 records")
        
        # Cleanup
        db.query(models.Vendor).filter(models.Vendor.name.like('test_vendor_%')).delete()
        db.commit()
        
        # 2. Bulk inserts
        print("🚀 Testing bulk inserts...")
        start = time.time()
        vendors = [models.Vendor(name=f'bulk_vendor_{i}', created_at=pd.Timestamp.now()) for i in range(100)]
        db.add_all(vendors)
        db.commit()
        bulk_time = time.time() - start
        print(f"   Bulk: {bulk_time:.2f}s for 100 records")
        
        # Cleanup
        db.query(models.Vendor).filter(models.Vendor.name.like('bulk_vendor_%')).delete()
        db.commit()
        
        speedup = individual_time / bulk_time if bulk_time > 0 else 0
        print(f"   🎯 Bulk operations are {speedup:.1f}x faster")
        
    finally:
        db.close()

def main():
    """Run all benchmarks."""
    print("🚀 CSV Loading Performance Analysis")
    print("=" * 70)
    
    # CSV reading benchmarks
    csv_results = benchmark_csv_reading()
    
    # Database operation benchmarks
    try:
        benchmark_bulk_operations()
    except Exception as e:
        print(f"❌ Database benchmark failed: {e}")
    
    # Recommendations
    print("\n💡 Optimization Recommendations:")
    print("-" * 40)
    
    if csv_results.get('polars') and csv_results.get('current_pandas'):
        polars_speedup = csv_results['current_pandas'] / csv_results['polars']
        if polars_speedup > 1.5:
            print(f"✅ Use Polars for {polars_speedup:.1f}x faster CSV reading")
    
    if csv_results.get('optimized_pandas') and csv_results.get('current_pandas'):
        pandas_speedup = csv_results['current_pandas'] / csv_results['optimized_pandas']
        if pandas_speedup > 1.2:
            print(f"✅ Use optimized pandas settings for {pandas_speedup:.1f}x speedup")
    
    print("✅ Use bulk database operations (10-50x faster than individual inserts)")
    print("✅ Increase chunk sizes to 50K-100K for large files")
    print("✅ Use vectorized operations instead of row-by-row processing")
    print("✅ Disable pandas NA conversion for string-only data")

if __name__ == "__main__":
    main()
