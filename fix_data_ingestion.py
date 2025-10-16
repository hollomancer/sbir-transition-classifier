#!/usr/bin/env python3
"""Minimal data cleaning fixes for contract ingestion."""

import pandas as pd
import numpy as np
from pathlib import Path

def clean_contract_data(df):
    """Clean contract data for ingestion."""
    
    # 1. Handle NaN values - convert to None/NULL
    df = df.replace({np.nan: None, 'nan': None, 'NaN': None})
    
    # 2. Create unique PIID by combining with modification number
    df['unique_piid'] = df['award_id_piid'].astype(str) + '_' + df['modification_number'].astype(str)
    
    # 3. Convert numeric fields properly
    numeric_cols = ['federal_action_obligation', 'parent_award_agency_id']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 4. Clean agency names
    if 'parent_award_agency_name' in df.columns:
        df['parent_award_agency_name'] = df['parent_award_agency_name'].str.strip()
    
    return df

def process_csv_file(input_path, output_path):
    """Process a single CSV file with cleaning."""
    print(f"Processing {input_path}...")
    
    # Read in chunks to handle large files
    chunk_size = 50000
    cleaned_chunks = []
    
    for chunk in pd.read_csv(input_path, chunksize=chunk_size, dtype=str):
        cleaned_chunk = clean_contract_data(chunk)
        cleaned_chunks.append(cleaned_chunk)
    
    # Combine and save
    df_cleaned = pd.concat(cleaned_chunks, ignore_index=True)
    df_cleaned.to_csv(output_path, index=False)
    print(f"Cleaned {len(df_cleaned):,} records -> {output_path}")

if __name__ == "__main__":
    data_dir = Path("data")
    cleaned_dir = Path("data/cleaned")
    cleaned_dir.mkdir(exist_ok=True)
    
    # Process all contract CSV files
    for csv_file in data_dir.glob("FY2024_All_Contracts_Full_*.csv"):
        output_file = cleaned_dir / f"cleaned_{csv_file.name}"
        process_csv_file(csv_file, output_file)
