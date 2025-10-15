"""Configuration schema definitions using Pydantic."""

from typing import List, Literal
from pydantic import BaseModel, Field, validator


class ThresholdsConfig(BaseModel):
    """Score thresholds for detection classification."""
    
    high_confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum score for high-confidence detection"
    )
    likely_transition: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum score for likely transition detection"
    )
    
    @validator('likely_transition')
    def validate_threshold_ordering(cls, v, values):
        """Ensure likely_transition <= high_confidence."""
        if 'high_confidence' in values and v > values['high_confidence']:
            raise ValueError('likely_transition threshold must be <= high_confidence threshold')
        return v


class WeightsConfig(BaseModel):
    """Feature weights for scoring algorithm."""
    
    sole_source_bonus: float = Field(
        default=0.2,
        ge=0.0,
        description="Additional weight for sole-source contracts"
    )
    timing_weight: float = Field(
        default=0.15,
        ge=0.0,
        description="Weight for timing proximity to Phase II completion"
    )
    agency_continuity: float = Field(
        default=0.25,
        ge=0.0,
        description="Weight for same agency/service continuation"
    )
    text_similarity: float = Field(
        default=0.1,
        ge=0.0,
        description="Weight for description text similarity"
    )


class FeaturesConfig(BaseModel):
    """Feature toggle flags."""
    
    enable_cross_service: bool = Field(
        default=True,
        description="Include cross-service transitions in detection"
    )
    enable_text_analysis: bool = Field(
        default=False,
        description="Use text similarity analysis"
    )
    enable_competed_contracts: bool = Field(
        default=True,
        description="Include competed contracts in detection"
    )


class TimingConfig(BaseModel):
    """Timing constraints for detection."""
    
    max_months_after_phase2: int = Field(
        default=24,
        ge=1,
        le=60,
        description="Maximum months after Phase II completion to search"
    )
    min_months_after_phase2: int = Field(
        default=0,
        ge=0,
        le=12,
        description="Minimum months after Phase II completion to search"
    )
    
    @validator('min_months_after_phase2')
    def validate_timing_ordering(cls, v, values):
        """Ensure min_months < max_months."""
        if 'max_months_after_phase2' in values and v >= values['max_months_after_phase2']:
            raise ValueError('min_months_after_phase2 must be < max_months_after_phase2')
        return v


class DetectionConfig(BaseModel):
    """Detection algorithm configuration."""
    
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)


class OutputConfig(BaseModel):
    """Output format and content configuration."""
    
    formats: List[Literal["jsonl", "csv", "excel"]] = Field(
        default=["jsonl", "csv"],
        min_items=1,
        description="Output file formats to generate"
    )
    include_evidence: bool = Field(
        default=True,
        description="Include detailed evidence bundles"
    )
    evidence_detail_level: Literal["summary", "full"] = Field(
        default="full",
        description="Level of detail in evidence bundles"
    )


class ConfigSchema(BaseModel):
    """Complete configuration schema for SBIR transition classifier."""
    
    schema_version: Literal["1.0"] = Field(
        default="1.0",
        description="Configuration schema version"
    )
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    
    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Reject unknown fields
        validate_assignment = True  # Validate on assignment
