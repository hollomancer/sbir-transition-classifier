"""
Data ingestion layer for SBIR transition detection system.

This module provides standardized data ingestion capabilities for:
- SBIR award data from various CSV formats
- Federal contract data from USAspending bulk downloads
- Data validation, transformation, and quality reporting
"""

from .base import BaseIngester
from .sbir import SbirIngester
from .contracts import ContractIngester
from .factory import create_ingester

__all__ = [
    'BaseIngester',
    'SbirIngester', 
    'ContractIngester',
    'create_ingester'
]
