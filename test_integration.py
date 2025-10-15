#!/usr/bin/env python3
"""Integration test script for SBIR transition detection."""

import sys
import os
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sbir_transition_classifier.data.local_loader import LocalDataLoader
from sbir_transition_classifier.config.loader import ConfigLoader
from sbir_transition_classifier.detection.pipeline import ConfigurableDetectionPipeline

def test_data_loading():
    """Test data loading and column mapping."""
    print("=== Testing Data Loading ===")
    
    # Load SBIR data
    sbir_file = Path("data/award_data.csv")
    print(f"Loading SBIR data from {sbir_file}")
    
    # Load raw data to check structure
    df = pd.read_csv(sbir_file, low_memory=False)
    print(f"Raw SBIR data shape: {df.shape}")
    print(f"Phase II awards: {len(df[df['Phase'] == 'Phase II'])}")
    
    # Test our loader
    sbir_awards = LocalDataLoader.load_sbir_awards(sbir_file)
    print(f"Loaded SBIR awards: {len(sbir_awards)}")
    
    # Check Phase II after standardization
    phase2_awards = [a for a in sbir_awards if str(a.get('phase', '')).upper() == 'II']
    print(f"Phase II awards after standardization: {len(phase2_awards)}")
    
    if phase2_awards:
        print("Sample Phase II award:")
        sample = phase2_awards[0]
        for key in ['award_piid', 'phase', 'agency', 'completion_date', 'vendor_name']:
            print(f"  {key}: {sample.get(key)}")
    
    # Load contract data
    contract_file = Path("data/FY2026_All_Contracts_Full_20251008_1.csv")
    print(f"\nLoading contract data from {contract_file}")
    
    contracts = LocalDataLoader.load_contracts(contract_file)
    print(f"Loaded contracts: {len(contracts)}")
    
    if contracts:
        print("Sample contract:")
        sample = contracts[0]
        for key in ['piid', 'agency', 'start_date', 'vendor_name']:
            print(f"  {key}: {sample.get(key)}")
    
    return sbir_awards, contracts

def test_detection_pipeline():
    """Test the detection pipeline with sample data."""
    print("\n=== Testing Detection Pipeline ===")
    
    # Load configuration
    config = ConfigLoader.load_from_file("config/default.yaml")
    print("Configuration loaded successfully")
    
    # Load data
    sbir_awards, contracts = test_data_loading()
    
    # Create a small test dataset
    phase2_awards = [a for a in sbir_awards if str(a.get('phase', '')).upper() == 'II'][:100]  # First 100 Phase II
    test_contracts = contracts[:1000]  # First 1000 contracts
    
    print(f"\nTesting with {len(phase2_awards)} Phase II awards and {len(test_contracts)} contracts")
    
    # Run detection
    pipeline = ConfigurableDetectionPipeline(config)
    detections = pipeline.run_detection(phase2_awards, test_contracts)
    
    print(f"Detections found: {len(detections)}")
    
    if detections:
        print("Sample detection:")
        sample = detections[0]
        print(f"  Score: {sample.likelihood_score:.3f}")
        print(f"  Confidence: {sample.confidence}")
        print(f"  SBIR PIID: {sample.sbir_award.award_piid}")
        print(f"  Contract PIID: {sample.contract.piid}")
    
    return detections

def create_test_data():
    """Create minimal test data to verify the pipeline works."""
    print("\n=== Creating Test Data ===")
    
    from datetime import datetime, timedelta
    import uuid
    
    # Create a test Phase II award
    completion_date = datetime(2023, 6, 1)
    test_award = {
        'id': str(uuid.uuid4()),
        'award_piid': 'TEST-SBIR-001',
        'phase': 'II',
        'agency': 'Department of Defense',
        'award_date': datetime(2022, 6, 1),
        'completion_date': completion_date,
        'topic': 'Advanced Materials Research',
        'vendor_name': 'Test Company Inc'
    }
    
    # Create a matching contract (should be detected)
    test_contract = {
        'id': str(uuid.uuid4()),
        'piid': 'TEST-CONTRACT-001',
        'agency': 'Department of Defense',
        'start_date': completion_date + timedelta(days=90),  # 3 months after
        'naics_code': '541712',
        'psc_code': 'R425',
        'vendor_name': 'Test Company Inc',
        'competition_details': {'sole_source': True}
    }
    
    print("Created test SBIR award and contract")
    
    # Test detection
    config = ConfigLoader.load_from_file("config/default.yaml")
    pipeline = ConfigurableDetectionPipeline(config)
    
    detections = pipeline.run_detection([test_award], [test_contract])
    
    print(f"Test detections found: {len(detections)}")
    
    if detections:
        detection = detections[0]
        print(f"  Score: {detection.likelihood_score:.3f}")
        print(f"  Confidence: {detection.confidence}")
        print("  Test data detection successful!")
    else:
        print("  No detections found with test data - investigating...")
        
        # Debug the pipeline
        scorer = pipeline.scorer
        
        # Check timing window
        in_window = scorer.is_within_timing_window(test_award, test_contract)
        print(f"  In timing window: {in_window}")
        
        # Check vendor match
        vendor_match = pipeline._vendors_match(test_award, test_contract)
        print(f"  Vendor match: {vendor_match}")
        
        # Calculate score
        score = scorer.calculate_likelihood_score(test_award, test_contract)
        print(f"  Likelihood score: {score:.3f}")
        
        # Check threshold
        meets_threshold, confidence = scorer.meets_threshold(score)
        print(f"  Meets threshold: {meets_threshold} ({confidence})")

if __name__ == "__main__":
    print("SBIR Transition Detection - Integration Test")
    print("=" * 50)
    
    try:
        # Test with synthetic data first
        create_test_data()
        
        # Test with real data
        test_detection_pipeline()
        
        print("\n=== Integration Test Complete ===")
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
