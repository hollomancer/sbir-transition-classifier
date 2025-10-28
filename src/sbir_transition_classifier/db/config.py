"""Database configuration management."""

from pathlib import Path
from typing import Optional

from loguru import logger

from ..config.loader import ConfigLoader, ConfigLoadError
from ..config.schema import DatabaseConfig


def get_database_config(config_path: Optional[Path] = None) -> DatabaseConfig:
    """
    Load database configuration from unified config file.

    Args:
        config_path: Optional path to config file. If None, uses default.

    Returns:
        DatabaseConfig instance

    Raises:
        ConfigLoadError: If config cannot be loaded
    """
    try:
        if config_path:
            full_config = ConfigLoader.load_from_file(config_path)
        else:
            # Try to load default, fall back to defaults if not found
            try:
                full_config = ConfigLoader.load_default()
            except ConfigLoadError:
                logger.warning("No config file found, using default database settings")
                return DatabaseConfig()

        return full_config.database
    except Exception as e:
        logger.warning(f"Failed to load database config: {e}, using defaults")
        return DatabaseConfig()


# Singleton instance
_db_config: Optional[DatabaseConfig] = None


def get_db_config_singleton() -> DatabaseConfig:
    """Get singleton database configuration instance."""
    global _db_config
    if _db_config is None:
        _db_config = get_database_config()
    return _db_config
