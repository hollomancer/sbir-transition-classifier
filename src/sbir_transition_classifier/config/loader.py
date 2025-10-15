"""YAML configuration file loader."""

import os
from pathlib import Path
from typing import Union

import yaml
from loguru import logger
from pydantic import ValidationError

from .schema import ConfigSchema


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""
    pass


class ConfigLoader:
    """Loads and validates YAML configuration files."""
    
    @staticmethod
    def load_from_file(config_path: Union[str, Path]) -> ConfigSchema:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Validated configuration schema
            
        Raises:
            ConfigLoadError: If file cannot be loaded or validated
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigLoadError(f"Configuration file not found: {config_path}")
        
        if not config_path.is_file():
            raise ConfigLoadError(f"Configuration path is not a file: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Invalid YAML syntax in {config_path}: {e}")
        except Exception as e:
            raise ConfigLoadError(f"Failed to read configuration file {config_path}: {e}")
        
        if raw_config is None:
            raise ConfigLoadError(f"Configuration file is empty: {config_path}")
        
        try:
            config = ConfigSchema(**raw_config)
            logger.info(f"Successfully loaded configuration from {config_path}")
            return config
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                value = error.get('input', 'N/A')
                error_details.append(f"  - {field}: {message} (got: {value})")
            
            error_msg = f"Configuration validation failed for {config_path}:\n" + "\n".join(error_details)
            raise ConfigLoadError(error_msg)
    
    @staticmethod
    def load_from_dict(config_dict: dict) -> ConfigSchema:
        """
        Load configuration from dictionary.
        
        Args:
            config_dict: Configuration as dictionary
            
        Returns:
            Validated configuration schema
            
        Raises:
            ConfigLoadError: If validation fails
        """
        try:
            return ConfigSchema(**config_dict)
        except ValidationError as e:
            error_details = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                message = error['msg']
                value = error.get('input', 'N/A')
                error_details.append(f"  - {field}: {message} (got: {value})")
            
            error_msg = "Configuration validation failed:\n" + "\n".join(error_details)
            raise ConfigLoadError(error_msg)
    
    @staticmethod
    def get_default_config_path() -> Path:
        """Get path to default configuration file."""
        # Assume we're running from project root or with proper PYTHONPATH
        current_dir = Path.cwd()
        
        # Try common locations
        candidates = [
            current_dir / "config" / "default.yaml",
            current_dir / ".." / "config" / "default.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        raise ConfigLoadError("Could not find default configuration file")
    
    @staticmethod
    def load_default() -> ConfigSchema:
        """Load default configuration."""
        default_path = ConfigLoader.get_default_config_path()
        return ConfigLoader.load_from_file(default_path)
