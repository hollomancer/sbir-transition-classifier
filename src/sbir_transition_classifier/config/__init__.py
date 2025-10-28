"""Configuration management for SBIR transition classifier.

This module provides unified configuration handling with schema validation,
default templates, and validation utilities all consolidated in one place.
"""

from .loader import ConfigLoader
from .schema import ConfigSchema, ConfigValidator, DefaultConfig, ValidationResult

__all__ = [
    "ConfigLoader",
    "ConfigSchema",
    "ConfigValidator",
    "DefaultConfig",
    "ValidationResult",
]
