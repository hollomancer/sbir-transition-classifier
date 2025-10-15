#!/usr/bin/env python3
"""
Setup script for SBIR Transition Classifier
Helps users get started with Poetry and the CLI tool.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    print("🚀 SBIR Transition Classifier Setup")
    print("=" * 40)
    
    # Check if Poetry is installed
    if not run_command("poetry --version", "Checking Poetry installation"):
        print("\n📦 Poetry is not installed. Please install it first:")
        print("   curl -sSL https://install.python-poetry.org | python3 -")
        print("   Or visit: https://python-poetry.org/docs/#installation")
        return False
    
    # Install dependencies
    if not run_command("poetry install", "Installing dependencies"):
        return False
    
    # Create data and output directories
    data_dir = Path("data")
    output_dir = Path("output")
    
    data_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    print("✅ Created data/ and output/ directories")
    
    # Test CLI installation
    if not run_command("poetry run sbir-detect --help", "Testing CLI installation"):
        print("⚠️  CLI test failed, but you can still use: poetry run python -m src.sbir_transition_classifier.cli.main")
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Place your SBIR award data in data/award_data.csv")
    print("2. Add USAspending bulk data files to data/ directory")
    print("3. Run: poetry run sbir-detect bulk-process --verbose")
    print("\n💡 Quick commands:")
    print("   poetry run sbir-detect --help          # Show all commands")
    print("   poetry run sbir-detect info            # System information")
    print("   poetry run sbir-detect bulk-process    # Run full pipeline")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
