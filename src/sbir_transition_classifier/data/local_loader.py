"""Local data loading utilities for offline processing."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import json
from loguru import logger


class LocalDataLoader:
    """Handles loading data from local files for offline processing."""
    
    @staticmethod
    def load_sbir_awards(file_path: Path) -> List[Dict[str, Any]]:
        """
        Load SBIR awards from local file.
        
        Args:
            file_path: Path to SBIR awards data file
            
        Returns:
            List of SBIR award dictionaries
        """
        logger.info(f"Loading SBIR awards from {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"SBIR awards file not found: {file_path}")
        
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            elif file_path.suffix.lower() == '.json':
                df = pd.read_json(file_path)
            elif file_path.suffix.lower() == '.jsonl':
                df = pd.read_json(file_path, lines=True)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Standardize column names
            df = LocalDataLoader._standardize_sbir_columns(df)
            
            # Convert to list of dictionaries
            awards = df.to_dict('records')
            
            logger.info(f"Loaded {len(awards)} SBIR awards")
            return awards
            
        except Exception as e:
            logger.error(f"Failed to load SBIR awards from {file_path}: {e}")
            raise
    
    @staticmethod
    def load_contracts(file_path: Path) -> List[Dict[str, Any]]:
        """
        Load contracts from local file.
        
        Args:
            file_path: Path to contracts data file
            
        Returns:
            List of contract dictionaries
        """
        logger.info(f"Loading contracts from {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Contracts file not found: {file_path}")
        
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            elif file_path.suffix.lower() == '.json':
                df = pd.read_json(file_path)
            elif file_path.suffix.lower() == '.jsonl':
                df = pd.read_json(file_path, lines=True)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Standardize column names
            df = LocalDataLoader._standardize_contract_columns(df)
            
            # Convert to list of dictionaries
            contracts = df.to_dict('records')
            
            logger.info(f"Loaded {len(contracts)} contracts")
            return contracts
            
        except Exception as e:
            logger.error(f"Failed to load contracts from {file_path}: {e}")
            raise
    
    @staticmethod
    def discover_data_files(data_dir: Path) -> Dict[str, List[Path]]:
        """
        Discover data files in directory.
        
        Args:
            data_dir: Directory to search for data files
            
        Returns:
            Dictionary mapping data types to file paths
        """
        logger.info(f"Discovering data files in {data_dir}")
        
        files = {
            'sbir_awards': [],
            'contracts': [],
            'unknown': []
        }
        
        if not data_dir.exists():
            logger.warning(f"Data directory does not exist: {data_dir}")
            return files
        
        # Search for data files
        for file_path in data_dir.rglob('*'):
            if not file_path.is_file():
                continue
            
            if file_path.suffix.lower() not in ['.csv', '.json', '.jsonl']:
                continue
            
            # Classify file based on name patterns
            name_lower = file_path.name.lower()
            
            if any(keyword in name_lower for keyword in ['sbir', 'award', 'phase']):
                files['sbir_awards'].append(file_path)
            elif any(keyword in name_lower for keyword in ['contract', 'fpds', 'usaspending']):
                files['contracts'].append(file_path)
            else:
                files['unknown'].append(file_path)
        
        logger.info(f"Found {len(files['sbir_awards'])} SBIR files, "
                   f"{len(files['contracts'])} contract files, "
                   f"{len(files['unknown'])} unknown files")
        
        return files
    
    @staticmethod
    def _standardize_sbir_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize SBIR awards column names."""
        # Common column name mappings
        column_mappings = {
            'Contract': 'award_piid',
            'piid': 'award_piid',
            'award_id': 'award_piid',
            'contract_piid': 'award_piid',
            'Phase': 'phase',
            'phase_number': 'phase',
            'sbir_phase': 'phase',
            'Agency': 'agency',
            'awarding_agency': 'agency',
            'agency_name': 'agency',
            'Proposal Award Date': 'award_date',
            'start_date': 'award_date',
            'award_start_date': 'award_date',
            'Contract End Date': 'completion_date',
            'end_date': 'completion_date',
            'award_end_date': 'completion_date',
            'Award Title': 'topic',
            'research_topic': 'topic',
            'topic_title': 'topic',
            'Company': 'vendor_name',
            'company_name': 'vendor_name',
            'contractor_name': 'vendor_name',
            'recipient_name': 'vendor_name'
        }
        
        # Rename columns
        df = df.rename(columns=column_mappings)
        
        # Ensure required columns exist
        required_columns = ['award_piid', 'phase', 'agency', 'award_date', 'completion_date']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Convert date columns
        date_columns = ['award_date', 'completion_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Clean phase values - extract just the phase number/name
        if 'phase' in df.columns:
            df['phase'] = df['phase'].astype(str).str.replace('Phase ', '', regex=False).str.strip()
        
        return df
    
    @staticmethod
    def _standardize_contract_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize contracts column names."""
        # Common column name mappings
        column_mappings = {
            'award_id_piid': 'piid',
            'contract_piid': 'piid',
            'award_piid': 'piid',
            'parent_award_id_piid': 'parent_piid',
            'parent_award_piid': 'parent_piid',
            'idv_piid': 'parent_piid',
            'contracting_agency_name': 'agency',
            'awarding_agency_name': 'agency',
            'awarding_agency': 'agency',
            'agency_name': 'agency',
            'period_of_performance_start_date': 'start_date',
            'contract_start_date': 'start_date',
            'primary_naics_code': 'naics_code',
            'naics': 'naics_code',
            'primary_naics': 'naics_code',
            'product_or_service_code': 'psc_code',
            'psc': 'psc_code',
            'product_service_code': 'psc_code',
            'recipient_name': 'vendor_name',
            'company_name': 'vendor_name',
            'contractor_name': 'vendor_name',
            'extent_competed': 'competition_type',
            'type_of_contract_pricing': 'pricing_type'
        }
        
        # Rename columns
        df = df.rename(columns=column_mappings)
        
        # Ensure required columns exist
        required_columns = ['piid', 'agency', 'start_date']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        
        # Convert date columns
        date_columns = ['start_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    @staticmethod
    def validate_data_quality(data: List[Dict[str, Any]], data_type: str) -> Dict[str, Any]:
        """
        Validate data quality and return statistics.
        
        Args:
            data: List of data records
            data_type: Type of data ('sbir_awards' or 'contracts')
            
        Returns:
            Dictionary with validation statistics
        """
        if not data:
            return {'total_records': 0, 'valid_records': 0, 'issues': ['No data loaded']}
        
        total_records = len(data)
        valid_records = 0
        issues = []
        
        if data_type == 'sbir_awards':
            required_fields = ['award_piid', 'phase', 'agency']
            for record in data:
                if all(record.get(field) for field in required_fields):
                    valid_records += 1
                    
        elif data_type == 'contracts':
            required_fields = ['piid', 'agency']
            for record in data:
                if all(record.get(field) for field in required_fields):
                    valid_records += 1
        
        # Check for common issues
        if valid_records < total_records * 0.9:
            issues.append(f"High number of records missing required fields ({total_records - valid_records}/{total_records})")
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'completion_rate': valid_records / total_records if total_records > 0 else 0,
            'issues': issues
        }
