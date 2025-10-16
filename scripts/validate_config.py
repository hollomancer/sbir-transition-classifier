#!/usr/bin/env python3
"""
Configuration validation and display utility.
"""

import yaml
import os
from pathlib import Path

def load_and_validate_config():
    """Load and validate the classification configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'classification.yaml'
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ Configuration loaded from: {config_path}")
        return config
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def display_config(config):
    """Display configuration in a readable format."""
    print("\n📋 Current Classification Configuration:")
    print("=" * 50)
    
    # Detection settings
    print("\n🔍 Detection Settings:")
    thresholds = config['detection']['thresholds']
    print(f"  High Confidence Threshold: {thresholds['high_confidence']}")
    print(f"  Likely Transition Threshold: {thresholds['likely_transition']}")
    
    # Weights
    print("\n⚖️  Scoring Weights:")
    weights = config['detection']['weights']
    for key, value in weights.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Features
    print("\n🎛️  Feature Flags:")
    features = config['detection']['features']
    for key, value in features.items():
        status = "✅ Enabled" if value else "❌ Disabled"
        print(f"  {key.replace('_', ' ').title()}: {status}")
    
    # Timing
    print("\n⏰ Timing Configuration:")
    timing = config['detection']['timing']
    print(f"  Max Months After Award: {timing['max_months_after_award']}")
    print(f"  Min Months After Award: {timing['min_months_after_award']}")
    
    # Candidate selection
    print("\n🎯 Candidate Selection:")
    selection = config['candidate_selection']
    print(f"  Eligible Phases: {', '.join(selection['eligible_phases'])}")
    print(f"  Search Window: {selection['search_window_days']} days")
    print(f"  Base Score: {selection['base_score']}")

if __name__ == "__main__":
    config = load_and_validate_config()
    if config:
        display_config(config)
        print(f"\n📊 Schema Version: {config.get('schema_version', 'Unknown')}")
    else:
        exit(1)
