"""Configuration reset and template generation utilities."""

from pathlib import Path
from typing import Optional

from loguru import logger

from .defaults import DefaultConfig


class ConfigReset:
    """Handles configuration reset and template generation."""
    
    @staticmethod
    def reset_to_default(output_path: Path, backup_existing: bool = True) -> bool:
        """
        Reset configuration to default values.
        
        Args:
            output_path: Path where to write the default configuration
            backup_existing: Whether to backup existing file if it exists
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Backup existing file if requested
            if backup_existing and output_path.exists():
                backup_path = output_path.with_suffix(f"{output_path.suffix}.backup")
                counter = 1
                while backup_path.exists():
                    backup_path = output_path.with_suffix(f"{output_path.suffix}.backup.{counter}")
                    counter += 1
                
                output_path.rename(backup_path)
                logger.info(f"Backed up existing configuration to {backup_path}")
            
            # Write default configuration
            DefaultConfig.write_default_config(output_path)
            logger.info(f"Default configuration written to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            return False
    
    @staticmethod
    def generate_template(template_name: str, output_path: Path, overwrite: bool = False) -> bool:
        """
        Generate configuration template.
        
        Args:
            template_name: Name of template to generate
            output_path: Path where to write the template
            overwrite: Whether to overwrite existing file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if output_path.exists() and not overwrite:
                logger.error(f"File already exists: {output_path}. Use --overwrite to replace.")
                return False
            
            DefaultConfig.write_template(template_name, output_path)
            logger.info(f"Template '{template_name}' written to {output_path}")
            return True
            
        except ValueError as e:
            logger.error(f"Invalid template name: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to generate template: {e}")
            return False
    
    @staticmethod
    def list_available_templates() -> list[str]:
        """List available configuration templates."""
        return ["default", "high-precision", "broad-discovery"]
    
    @staticmethod
    def get_template_description(template_name: str) -> Optional[str]:
        """Get description of configuration template."""
        descriptions = {
            "default": "Standard configuration with balanced detection parameters",
            "high-precision": "Conservative settings to minimize false positives",
            "broad-discovery": "Aggressive settings to maximize detection coverage"
        }
        return descriptions.get(template_name)
