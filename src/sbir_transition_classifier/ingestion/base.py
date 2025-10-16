"""Base ingester interface for standardized data loading."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console

@dataclass
class IngestionStats:
    """Statistics from data ingestion process."""
    total_rows: int = 0
    valid_records: int = 0
    rejected_records: int = 0
    duplicates_skipped: int = 0
    rejection_reasons: Dict[str, int] = None
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.rejection_reasons is None:
            self.rejection_reasons = {}
    
    @property
    def retention_rate(self) -> float:
        """Calculate retention percentage."""
        return (self.valid_records / self.total_rows * 100) if self.total_rows > 0 else 0.0

class BaseIngester(ABC):
    """Abstract base class for data ingesters."""
    
    def __init__(self, console: Optional[Console] = None, verbose: bool = False):
        self.console = console or Console()
        self.verbose = verbose
        self.stats = IngestionStats()
    
    @abstractmethod
    def ingest(self, file_path: Path, **kwargs) -> IngestionStats:
        """Ingest data from file and return statistics."""
        pass
    
    @abstractmethod
    def validate_file(self, file_path: Path) -> bool:
        """Validate file format and structure."""
        pass
    
    def log_progress(self, message: str, style: str = "dim"):
        """Log progress message if verbose mode enabled."""
        if self.verbose:
            self.console.print(message, style=style)
