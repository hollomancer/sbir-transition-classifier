"""Configuration schema definitions using Pydantic.

This module consolidates configuration schema, defaults, and validation logic.
"""

from pathlib import Path
from typing import List, Literal, Optional, Dict, Any, Union

import yaml
from pydantic import BaseModel, Field, validator, ValidationError


class ThresholdsConfig(BaseModel):
    """Score thresholds for detection classification."""

    high_confidence: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum score for high-confidence detection",
    )
    likely_transition: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum score for likely transition detection",
    )

    @validator("likely_transition")
    def validate_threshold_ordering(cls, v, values):
        """Ensure likely_transition <= high_confidence."""
        if "high_confidence" in values and v > values["high_confidence"]:
            raise ValueError(
                "likely_transition threshold must be <= high_confidence threshold"
            )
        return v


class WeightsConfig(BaseModel):
    """Feature weights for scoring algorithm."""

    sole_source_bonus: float = Field(
        default=0.2, ge=0.0, description="Additional weight for sole-source contracts"
    )
    timing_weight: float = Field(
        default=0.15,
        ge=0.0,
        description="Weight for timing proximity to Phase II completion",
    )
    agency_continuity: float = Field(
        default=0.25, ge=0.0, description="Weight for same agency/service continuation"
    )
    text_similarity: float = Field(
        default=0.1, ge=0.0, description="Weight for description text similarity"
    )


class FeaturesConfig(BaseModel):
    """Feature toggle flags."""

    enable_cross_service: bool = Field(
        default=True, description="Include cross-service transitions in detection"
    )
    enable_text_analysis: bool = Field(
        default=False, description="Use text similarity analysis"
    )
    enable_competed_contracts: bool = Field(
        default=True, description="Include competed contracts in detection"
    )


class TimingConfig(BaseModel):
    """Timing constraints for detection."""

    max_months_after_phase2: int = Field(
        default=24,
        ge=1,
        le=60,
        description="Maximum months after Phase II completion to search",
    )
    min_months_after_phase2: int = Field(
        default=0,
        ge=0,
        le=12,
        description="Minimum months after Phase II completion to search",
    )

    @validator("min_months_after_phase2")
    def validate_timing_ordering(cls, v, values):
        """Ensure min_months < max_months."""
        if (
            "max_months_after_phase2" in values
            and v >= values["max_months_after_phase2"]
        ):
            raise ValueError(
                "min_months_after_phase2 must be < max_months_after_phase2"
            )
        return v


class IngestionConfig(BaseModel):
    """Parameters for data ingestion."""

    data_formats: List[Literal["csv", "json"]] = Field(
        default=["csv"],
        min_items=1,
        description="List of supported data formats for ingestion.",
    )
    encoding: str = Field(default="utf-8", description="Encoding for input files.")
    chunk_size: int = Field(
        default=10000,
        gt=0,
        description="Number of rows to process at a time for large files.",
    )
    max_records: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum number of records to process from input data. 0 means no limit.",
    )


class DetectionConfig(BaseModel):
    """Detection algorithm configuration."""

    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    eligible_phases: List[Literal["Phase I", "Phase II"]] = Field(
        default=["Phase I", "Phase II"],
        min_items=1,
        description="SBIR award phases considered eligible for detection",
    )


class OutputConfig(BaseModel):
    """Output format and content configuration."""

    formats: List[Literal["jsonl", "csv", "excel"]] = Field(
        default=["jsonl", "csv"],
        min_items=1,
        description="Output file formats to generate",
    )
    include_evidence: bool = Field(
        default=True, description="Include detailed evidence bundles"
    )
    evidence_detail_level: Literal["summary", "full"] = Field(
        default="full", description="Level of detail in evidence bundles"
    )


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: str = Field(
        default="sqlite:///./sbir_transitions.db",
        description="SQLAlchemy database connection URL",
    )
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Database connection pool size (non-SQLite only)",
    )
    pool_timeout: int = Field(
        default=30, ge=1, description="Connection pool timeout in seconds"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "SBIR_DB_"  # Allow SBIR_DB_URL env var override


class ConfigSchema(BaseModel):
    """Complete configuration schema for SBIR transition classifier."""

    schema_version: Literal["1.0"] = Field(
        default="1.0", description="Configuration schema version"
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database connection settings"
    )
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"  # Reject unknown fields
        validate_assignment = True  # Validate on assignment


# ============================================================================
# DEFAULT CONFIGURATION TEMPLATES
# ============================================================================


class DefaultConfig:
    """Provides default configuration templates."""

    @staticmethod
    def get_default_dict() -> Dict[str, Any]:
        """Get default configuration as dictionary."""
        config = ConfigSchema()
        return config.dict()

    @staticmethod
    def get_default_yaml() -> str:
        """Get default configuration as YAML string."""
        config_dict = DefaultConfig.get_default_dict()
        return yaml.dump(config_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def write_default_config(output_path: Path) -> None:
        """
        Write default configuration to file.

        Args:
            output_path: Path where to write the configuration
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        yaml_content = DefaultConfig.get_default_yaml()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

    @staticmethod
    def get_high_precision_template() -> Dict[str, Any]:
        """Get high-precision configuration template."""
        config = ConfigSchema()

        # Modify for high precision
        config.detection.thresholds.high_confidence = 0.90
        config.detection.thresholds.likely_transition = 0.80
        config.detection.weights.sole_source_bonus = 0.3
        config.detection.weights.agency_continuity = 0.4
        config.detection.weights.text_similarity = 0.05
        config.detection.features.enable_cross_service = False
        config.detection.features.enable_competed_contracts = False
        config.detection.timing.max_months_after_phase2 = 18

        return config.dict()

    @staticmethod
    def get_broad_discovery_template() -> Dict[str, Any]:
        """Get broad discovery configuration template."""
        config = ConfigSchema()

        # Modify for broad discovery
        config.detection.thresholds.high_confidence = 0.70
        config.detection.thresholds.likely_transition = 0.50
        config.detection.weights.timing_weight = 0.2
        config.detection.weights.text_similarity = 0.15
        config.detection.features.enable_text_analysis = True
        config.detection.timing.max_months_after_phase2 = 36
        config.output.formats = ["jsonl", "csv", "excel"]

        return config.dict()

    @staticmethod
    def write_template(template_name: str, output_path: Path) -> None:
        """
        Write configuration template to file.

        Args:
            template_name: Name of template ('default', 'high-precision', 'broad-discovery')
            output_path: Path where to write the configuration
        """
        if template_name == "default":
            config_dict = DefaultConfig.get_default_dict()
        elif template_name == "high-precision":
            config_dict = DefaultConfig.get_high_precision_template()
        elif template_name == "broad-discovery":
            config_dict = DefaultConfig.get_broad_discovery_template()
        else:
            raise ValueError(f"Unknown template: {template_name}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        yaml_content = yaml.dump(config_dict, default_flow_style=False, sort_keys=False)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================


class ValidationResult:
    """Result of configuration validation."""

    def __init__(
        self, valid: bool, errors: List[str] = None, warnings: List[str] = None
    ):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.valid

    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)


class ConfigValidator:
    """Validates configuration files and provides detailed error reporting."""

    @staticmethod
    def validate_file(config_path: Union[str, Path]) -> ValidationResult:
        """
        Validate configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            ValidationResult with detailed error information
        """
        result = ValidationResult(valid=True)
        config_path = Path(config_path)

        # Check file existence
        if not config_path.exists():
            result.add_error(f"Configuration file not found: {config_path}")
            return result

        if not config_path.is_file():
            result.add_error(f"Path is not a file: {config_path}")
            return result

        # Check YAML syntax
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_error(f"Invalid YAML syntax: {e}")
            return result
        except Exception as e:
            result.add_error(f"Failed to read file: {e}")
            return result

        if raw_config is None:
            result.add_error("Configuration file is empty")
            return result

        # Validate schema
        try:
            ConfigSchema(**raw_config)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                value = error.get("input", "N/A")

                # Provide helpful error messages
                if "ensure this value is greater than or equal to" in message:
                    min_val = message.split(
                        "ensure this value is greater than or equal to "
                    )[1]
                    result.add_error(
                        f"{field}: Value must be >= {min_val} (got: {value})"
                    )
                elif "ensure this value is less than or equal to" in message:
                    max_val = message.split(
                        "ensure this value is less than or equal to "
                    )[1]
                    result.add_error(
                        f"{field}: Value must be <= {max_val} (got: {value})"
                    )
                elif "unexpected value" in message:
                    result.add_error(f"{field}: Invalid value '{value}'. {message}")
                else:
                    result.add_error(f"{field}: {message} (got: {value})")

        # Additional semantic validation
        if result.valid:
            try:
                from .loader import ConfigLoader, ConfigLoadError

                config = ConfigLoader.load_from_file(config_path)
                ConfigValidator._validate_semantic_rules(config, result)
            except ConfigLoadError:
                pass  # Already handled above

        return result

    @staticmethod
    def validate_dict(config_dict: dict) -> ValidationResult:
        """
        Validate configuration dictionary.

        Args:
            config_dict: Configuration as dictionary

        Returns:
            ValidationResult with detailed error information
        """
        result = ValidationResult(valid=True)

        try:
            config = ConfigSchema(**config_dict)
            ConfigValidator._validate_semantic_rules(config, result)
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                value = error.get("input", "N/A")
                result.add_error(f"{field}: {message} (got: {value})")

        return result

    @staticmethod
    def _validate_semantic_rules(config: ConfigSchema, result: ValidationResult):
        """Validate semantic rules not covered by Pydantic."""

        # Check threshold ordering
        if (
            config.detection.thresholds.likely_transition
            > config.detection.thresholds.high_confidence
        ):
            result.add_error(
                f"likely_transition threshold ({config.detection.thresholds.likely_transition}) "
                f"must be <= high_confidence threshold ({config.detection.thresholds.high_confidence})"
            )

        # Check timing ordering
        if (
            config.detection.timing.min_months_after_phase2
            >= config.detection.timing.max_months_after_phase2
        ):
            result.add_error(
                f"min_months_after_phase2 ({config.detection.timing.min_months_after_phase2}) "
                f"must be < max_months_after_phase2 ({config.detection.timing.max_months_after_phase2})"
            )

        # Warnings for potentially problematic configurations
        if config.detection.thresholds.high_confidence < 0.5:
            result.add_warning(
                "High confidence threshold is very low (<0.5), may produce many false positives"
            )

        if config.detection.timing.max_months_after_phase2 > 48:
            result.add_warning(
                "Search window is very long (>48 months), may impact performance"
            )

        if (
            not config.detection.features.enable_cross_service
            and not config.detection.features.enable_competed_contracts
        ):
            result.add_warning(
                "Both cross-service and competed contracts disabled, detection scope is very narrow"
            )

    @staticmethod
    def get_validation_summary(result: ValidationResult) -> str:
        """Get human-readable validation summary."""
        if result.valid:
            summary = "✓ Configuration is valid"
            if result.warnings:
                summary += f" ({len(result.warnings)} warnings)"
        else:
            summary = f"✗ Configuration is invalid ({len(result.errors)} errors"
            if result.warnings:
                summary += f", {len(result.warnings)} warnings"
            summary += ")"

        return summary

    @staticmethod
    def format_errors_and_warnings(result: ValidationResult) -> str:
        """Format errors and warnings for display."""
        lines = []

        if result.errors:
            lines.append("Errors:")
            for error in result.errors:
                lines.append(f"  • {error}")

        if result.warnings:
            if lines:
                lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  • {warning}")

        return "\n".join(lines)
