"""
DEPRECATED: This module is deprecated.

Please use the unified configuration system:
    from sbir_transition_classifier.db.config import get_database_config

This file will be removed in version 0.2.0.
"""

import warnings
from pydantic_settings import BaseSettings

warnings.warn(
    "core.config is deprecated. Use db.config.get_database_config() instead.",
    DeprecationWarning,
    stacklevel=2,
)


class Settings(BaseSettings):
    """DEPRECATED: Use unified config system."""

    DATABASE_URL: str = "sqlite:///./sbir_transitions.db"

    class Config:
        env_file = ".env"


settings = Settings()
