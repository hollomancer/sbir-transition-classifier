"""Local execution data models."""

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Any

from pydantic import BaseModel, Field, ConfigDict


class SessionStatus(str, Enum):
    """Detection session status."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EvidenceType(str, Enum):
    """Evidence bundle type."""

    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    LIKELY_TRANSITION = "LIKELY_TRANSITION"
    CROSS_SERVICE = "CROSS_SERVICE"


class DetectionSessionBase(BaseModel):
    """Base model for detection session."""

    config_used: str = Field(description="Path to configuration file used")
    config_checksum: str = Field(description="Hash of config at runtime")
    input_datasets: List[str] = Field(description="Paths to input data files")
    output_path: str = Field(description="Directory containing results")


class DetectionSessionCreate(DetectionSessionBase):
    """Model for creating detection session."""

    pass


class DetectionSession(DetectionSessionBase):
    """Complete detection session model."""

    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    status: SessionStatus = SessionStatus.RUNNING
    detection_count: int = 0
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceBundleArtifactBase(BaseModel):
    """Base model for evidence bundle artifact."""

    session_id: uuid.UUID = Field(description="Parent detection session")
    detection_id: uuid.UUID = Field(description="Links to detection record")
    file_path: str = Field(description="Path to evidence JSON file")
    summary_path: str = Field(description="Path to human-readable summary")
    evidence_type: EvidenceType = Field(description="Type of evidence")


class EvidenceBundleArtifactCreate(EvidenceBundleArtifactBase):
    """Model for creating evidence bundle artifact."""

    pass


class EvidenceBundleArtifact(EvidenceBundleArtifactBase):
    """Complete evidence bundle artifact model."""

    bundle_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    file_size: int = Field(description="Size in bytes")

    model_config = ConfigDict(from_attributes=True)


class LocalConfigProfile(BaseModel):
    """Local configuration profile metadata."""

    config_path: str = Field(description="Absolute path to YAML file")
    version: str = Field(description="Configuration schema version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: str = Field(description="SHA256 hash for integrity verification")

    @classmethod
    def from_file(cls, config_path: Path) -> "LocalConfigProfile":
        """Create profile from configuration file."""
        import hashlib

        stat = config_path.stat()

        # Calculate checksum
        with open(config_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        return cls(
            config_path=str(config_path.absolute()),
            version="1.0",  # Default version
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            checksum=checksum,
        )
