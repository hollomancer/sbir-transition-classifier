"""Data hygiene and cleaning functions."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

console = Console()


class DataCleaner:
    """Handles data cleaning and validation with progress feedback."""
    
    def clean_csv_file_streaming(self, file_path: Path, output_path: Path = None, 
                                sample_size: int = None, chunk_size: int = 10000) -> Path:
        """Clean a CSV file using streaming with progress feedback."""
        if not output_path:
            output_path = file_path.parent / f"clean_{file_path.name}"
        
        console.print(f"🧹 Processing {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        try:
            # Get total rows for progress (approximate)
            with open(file_path, 'r') as f:
                total_lines = sum(1 for _ in f) - 1  # Subtract header
            
            if sample_size and sample_size < total_lines:
                total_lines = sample_size
            
            processed_rows = 0
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(f"Cleaning {file_path.name}", total=total_lines)
                
                # Process in chunks
                first_chunk = True
                
                for chunk in pd.read_csv(file_path, chunksize=chunk_size, dtype=str, 
                                       on_bad_lines='skip', low_memory=False):
                    
                    # Apply sample limit
                    if sample_size and processed_rows >= sample_size:
                        break
                    
                    if sample_size:
                        remaining = sample_size - processed_rows
                        if len(chunk) > remaining:
                            chunk = chunk.head(remaining)
                    
                    # Clean the chunk
                    cleaned_chunk = self.clean_dataframe(chunk)
                    
                    # Write to output
                    mode = 'w' if first_chunk else 'a'
                    header = first_chunk
                    cleaned_chunk.to_csv(output_path, mode=mode, header=header, index=False)
                    
                    processed_rows += len(chunk)
                    progress.update(task, advance=len(chunk))
                    first_chunk = False
            
            console.print(f"✅ Cleaned {processed_rows:,} rows → {output_path}")
            return output_path
            
        except Exception as e:
            console.print(f"❌ Error processing {file_path}: {e}")
            raise
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean a pandas DataFrame efficiently."""
        # Handle NaN values - vectorized operation
        df = df.replace(['nan', 'NaN', 'null', 'NULL', ''], None)
        df = df.where(pd.notnull(df), None)
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        return df
    
    def validate_file_quick(self, file_path: Path) -> Dict[str, Any]:
        """Quick validation of a file without loading it all."""
        try:
            # Read just first few rows
            sample = pd.read_csv(file_path, nrows=100, on_bad_lines='skip')
            
            return {
                'valid': True,
                'columns': len(sample.columns),
                'sample_rows': len(sample),
                'has_data': not sample.empty,
                'null_columns': sample.isnull().all().sum()
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }


def create_sample_files_robust(data_dir: Path, sample_size: int = 1000) -> List[Path]:
    """Create sample files with progress feedback and error handling."""
    cleaner = DataCleaner()
    sample_files = []
    
    # Find CSV files to process
    csv_files = [f for f in data_dir.glob("*.csv") 
                 if not f.name.startswith(("sample_", "clean_"))]
    
    console.print(f"📁 Found {len(csv_files)} files to process")
    
    for csv_file in csv_files:
        try:
            # Quick validation first
            validation = cleaner.validate_file_quick(csv_file)
            if not validation['valid']:
                console.print(f"⚠️  Skipping {csv_file.name}: {validation['error']}")
                continue
            
            sample_path = data_dir / f"sample_{csv_file.name}"
            
            # Skip if sample already exists and is recent
            if sample_path.exists():
                console.print(f"⏭️  Sample exists: {sample_path.name}")
                sample_files.append(sample_path)
                continue
            
            # Create sample with streaming
            result_path = cleaner.clean_csv_file_streaming(
                csv_file, 
                sample_path,
                sample_size,
                chunk_size=5000  # Smaller chunks for better progress
            )
            sample_files.append(result_path)
            
        except Exception as e:
            console.print(f"❌ Failed to process {csv_file.name}: {e}")
            continue
    
    return sample_files
