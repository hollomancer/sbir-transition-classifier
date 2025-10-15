"""Configuration validation with detailed error reporting."""

from pathlib import Path
from typing import Dict, List, Union, Tuple

import yaml
from pydantic import ValidationError

from .loader import ConfigLoader, ConfigLoadError
from .schema import ConfigSchema


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self, valid: bool, errors: List[str] = None, warnings: List[str] = None):
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
            with open(config_path, 'r', encoding='utf-8') as f:
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
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                value = error.get('input', 'N/A')
                
                # Provide helpful error messages
                if 'ensure this value is greater than or equal to' in message:
                    min_val = message.split('ensure this value is greater than or equal to ')[1]
                    result.add_error(f"{field}: Value must be >= {min_val} (got: {value})")
                elif 'ensure this value is less than or equal to' in message:
                    max_val = message.split('ensure this value is less than or equal to ')[1]
                    result.add_error(f"{field}: Value must be <= {max_val} (got: {value})")
                elif 'unexpected value' in message:
                    result.add_error(f"{field}: Invalid value '{value}'. {message}")
                else:
                    result.add_error(f"{field}: {message} (got: {value})")
        
        # Additional semantic validation
        if result.valid:
            try:
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
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                value = error.get('input', 'N/A')
                result.add_error(f"{field}: {message} (got: {value})")
        
        return result
    
    @staticmethod
    def _validate_semantic_rules(config: ConfigSchema, result: ValidationResult):
        """Validate semantic rules not covered by Pydantic."""
        
        # Check threshold ordering
        if config.detection.thresholds.likely_transition > config.detection.thresholds.high_confidence:
            result.add_error(
                f"likely_transition threshold ({config.detection.thresholds.likely_transition}) "
                f"must be <= high_confidence threshold ({config.detection.thresholds.high_confidence})"
            )
        
        # Check timing ordering
        if config.detection.timing.min_months_after_phase2 >= config.detection.timing.max_months_after_phase2:
            result.add_error(
                f"min_months_after_phase2 ({config.detection.timing.min_months_after_phase2}) "
                f"must be < max_months_after_phase2 ({config.detection.timing.max_months_after_phase2})"
            )
        
        # Warnings for potentially problematic configurations
        if config.detection.thresholds.high_confidence < 0.5:
            result.add_warning("High confidence threshold is very low (<0.5), may produce many false positives")
        
        if config.detection.timing.max_months_after_phase2 > 48:
            result.add_warning("Search window is very long (>48 months), may impact performance")
        
        if not config.detection.features.enable_cross_service and not config.detection.features.enable_competed_contracts:
            result.add_warning("Both cross-service and competed contracts disabled, detection scope is very narrow")
    
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
