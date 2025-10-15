"""Default configuration templates and utilities."""

from pathlib import Path
from typing import Dict, Any

import yaml

from .schema import ConfigSchema


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
        
        with open(output_path, 'w', encoding='utf-8') as f:
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
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
