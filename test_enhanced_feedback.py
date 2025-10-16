#!/usr/bin/env python3
"""
Test script to verify enhanced progress feedback and data quality reporting.
"""

import subprocess
import sys
from pathlib import Path

def test_sbir_loading():
    """Test SBIR data loading with enhanced feedback."""
    print("🧪 Testing SBIR data loading with enhanced feedback...")
    
    # Check if sample data exists
    sample_file = Path("data/award_data.csv")
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return False
    
    try:
        # Run SBIR loading with verbose output
        result = subprocess.run([
            'python', '-m', 'scripts.load_bulk_data', 'load-sbir-data',
            '--file-path', str(sample_file),
            '--chunk-size', '1000',
            '--verbose'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ SBIR loading test passed")
            print("📊 Output preview:")
            print(result.stdout[-500:])  # Show last 500 chars
            return True
        else:
            print(f"❌ SBIR loading test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ SBIR loading test timed out")
        return False
    except Exception as e:
        print(f"❌ SBIR loading test error: {e}")
        return False

def test_contract_loading():
    """Test contract data loading with enhanced feedback."""
    print("\n🧪 Testing contract data loading with enhanced feedback...")
    
    # Look for any contract CSV files
    data_dir = Path("data")
    contract_files = [f for f in data_dir.glob("*.csv") if f.name != "award_data.csv"]
    
    if not contract_files:
        print("❌ No contract CSV files found for testing")
        return False
    
    # Test with the first contract file
    test_file = contract_files[0]
    print(f"📁 Testing with: {test_file.name}")
    
    try:
        # Run contract loading with verbose output
        result = subprocess.run([
            'python', '-m', 'scripts.load_bulk_data', 'load-usaspending-data',
            '--file-path', str(test_file),
            '--chunk-size', '5000',
            '--verbose'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Contract loading test passed")
            print("📊 Output preview:")
            print(result.stdout[-500:])  # Show last 500 chars
            return True
        else:
            print(f"❌ Contract loading test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Contract loading test timed out")
        return False
    except Exception as e:
        print(f"❌ Contract loading test error: {e}")
        return False

def test_bulk_processing():
    """Test bulk processing with enhanced multi-file feedback."""
    print("\n🧪 Testing bulk processing with enhanced feedback...")
    
    try:
        # Run bulk processing with verbose output
        result = subprocess.run([
            'python', '-m', 'src.sbir_transition_classifier.cli.main', 'bulk-process',
            '--data-dir', './data',
            '--chunk-size', '1000',
            '--verbose'
        ], capture_output=True, text=True, timeout=900)
        
        if result.returncode == 0:
            print("✅ Bulk processing test passed")
            print("📊 Output preview:")
            print(result.stdout[-800:])  # Show last 800 chars
            return True
        else:
            print(f"❌ Bulk processing test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Bulk processing test timed out")
        return False
    except Exception as e:
        print(f"❌ Bulk processing test error: {e}")
        return False

def main():
    """Run all enhanced feedback tests."""
    print("🚀 Testing Enhanced Progress Feedback and Data Quality Reporting")
    print("=" * 70)
    
    tests = [
        ("SBIR Loading", test_sbir_loading),
        ("Contract Loading", test_contract_loading),
        ("Bulk Processing", test_bulk_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All enhanced feedback features working correctly!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
