#!/usr/bin/env python3
"""
Configuration validation and display utility.
"""

from pathlib import Path
from sbir_transition_classifier.config.loader import ConfigLoader
from sbir_transition_classifier.config.schema import ConfigSchema


def load_and_validate_config():
    """Load and validate the detection configuration."""
    try:
        config_path = ConfigLoader.get_default_config_path()
        config = ConfigLoader.load_from_file(config_path)
        print(f"✅ Configuration loaded from: {config_path}")
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def display_config(config: ConfigSchema):
    """Display configuration in a readable format."""
    print("\n📋 Current Detection Configuration:")
    print("=" * 50)

    # Detection settings
    print("\n🔍 Detection Settings:")
    thresholds = config.detection.thresholds
    print(f"  High Confidence Threshold: {thresholds.high_confidence}")
    print(f"  Likely Transition Threshold: {thresholds.likely_transition}")

    # Weights
    print("\n⚖️  Scoring Weights:")
    weights = config.detection.weights
    for key, value in weights.dict().items():
        print(f"  {key.replace('_', ' ').title()}: {value}")

    # Features
    print("\n🎛️  Feature Flags:")
    features = config.detection.features
    for key, value in features.dict().items():
        status = "✅ Enabled" if value else "❌ Disabled"
        print(f"  {key.replace('_', ' ').title()}: {status}")

    # Timing
    print("\n⏰ Timing Configuration:")
    timing = config.detection.timing
    print(f"  Max Months After Phase II: {timing.max_months_after_phase2}")
    print(f"  Min Months After Phase II: {timing.min_months_after_phase2}")

    # Eligible phases
    print("\n🎯 Candidate Selection:")
    print(f"  Eligible Phases: {', '.join(config.detection.eligible_phases)}")


if __name__ == "__main__":
    config = load_and_validate_config()
    if config:
        display_config(config)
        print(f"\n📊 Schema Version: {config.schema_version}")
    else:
        exit(1)
