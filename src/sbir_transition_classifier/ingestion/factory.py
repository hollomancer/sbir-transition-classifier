"""Factory for creating appropriate data ingesters."""

from pathlib import Path
from typing import Optional
from rich.console import Console

from .base import BaseIngester
from .sbir import SbirIngester
from .contracts import ContractIngester

def create_ingester(file_path: Path, console: Optional[Console] = None, verbose: bool = False) -> BaseIngester:
    """Create appropriate ingester based on file characteristics."""
    
    # Auto-detect file type based on name patterns
    file_name = file_path.name.lower()
    
    if 'award' in file_name or 'sbir' in file_name:
        return SbirIngester(console=console, verbose=verbose)
    elif 'contract' in file_name or 'usaspending' in file_name or 'fy20' in file_name:
        return ContractIngester(console=console, verbose=verbose)
    else:
        # Try to detect by examining file structure
        try:
            import pandas as pd
            df = pd.read_csv(file_path, nrows=5)
            
            # Check for SBIR-specific columns
            sbir_cols = ['Company', 'Award Number', 'Phase', 'Agency']
            if all(col in df.columns for col in sbir_cols):
                return SbirIngester(console=console, verbose=verbose)
            
            # Check for contract-specific columns
            contract_cols = ['award_id_piid', 'awarding_agency_name', 'recipient_name']
            if all(col in df.columns for col in contract_cols):
                return ContractIngester(console=console, verbose=verbose)
            
        except Exception:
            pass
    
    raise ValueError(f"Cannot determine ingester type for file: {file_path}")

def ingest_file(file_path: Path, console: Optional[Console] = None, verbose: bool = False, **kwargs):
    """Convenience function to ingest a file with auto-detection."""
    ingester = create_ingester(file_path, console=console, verbose=verbose)
    return ingester.ingest(file_path, **kwargs)
