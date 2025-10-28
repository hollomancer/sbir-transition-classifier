"""Tests for configuration loading."""

import pytest
from pathlib import Path

from sbir_transition_classifier.config.loader import ConfigLoader, ConfigLoadError
from sbir_transition_classifier.config.schema import ConfigSchema


def test_load_from_valid_file(temp_config_file: Path):
    """Test loading configuration from valid YAML file."""
    config = ConfigLoader.load_from_file(temp_config_file)

    assert isinstance(config, ConfigSchema)
    assert config.schema_version == "1.0"
    assert config.detection.thresholds.high_confidence == 0.85
    assert config.database.url == "sqlite:///:memory:"


def test_load_from_nonexistent_file():
    """Test loading configuration from non-existent file raises error."""
    with pytest.raises(ConfigLoadError, match="not found"):
        ConfigLoader.load_from_file(Path("nonexistent.yaml"))


def test_load_from_invalid_yaml(tmp_path: Path):
    """Test loading configuration from invalid YAML raises error."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("invalid: yaml: content:")

    with pytest.raises(ConfigLoadError, match="Invalid YAML"):
        ConfigLoader.load_from_file(invalid_file)


def test_load_from_empty_file(tmp_path: Path):
    """Test loading configuration from empty file raises error."""
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("")

    with pytest.raises(ConfigLoadError, match="empty"):
        ConfigLoader.load_from_file(empty_file)


def test_load_from_dict():
    """Test loading configuration from dictionary."""
    config_dict = {
        "schema_version": "1.0",
        "detection": {"thresholds": {"high_confidence": 0.9, "likely_transition": 0.7}},
    }

    config = ConfigLoader.load_from_dict(config_dict)

    assert config.detection.thresholds.high_confidence == 0.9
    assert config.detection.thresholds.likely_transition == 0.7


def test_load_from_dict_with_invalid_data():
    """Test loading configuration from dict with invalid data raises error."""
    config_dict = {
        "schema_version": "1.0",
        "detection": {
            "thresholds": {
                "high_confidence": 0.5,
                "likely_transition": 0.9,  # Invalid: greater than high_confidence
            }
        },
    }

    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_dict(config_dict)


def test_load_with_database_config(temp_config_file: Path):
    """Test that database configuration is properly loaded."""
    config = ConfigLoader.load_from_file(temp_config_file)

    assert hasattr(config, "database")
    assert config.database.url == "sqlite:///:memory:"
    assert config.database.echo is False
    assert config.database.pool_size == 5
    assert config.database.pool_timeout == 30


def test_config_uses_defaults_for_missing_sections():
    """Test that missing sections use default values."""
    minimal_config = {"schema_version": "1.0"}

    config = ConfigLoader.load_from_dict(minimal_config)

    # Should have default values
    assert config.database.url == "sqlite:///./sbir_transitions.db"
    assert config.detection.thresholds.high_confidence == 0.85
    assert config.ingestion.chunk_size == 10000


def test_config_rejects_unknown_fields(tmp_path: Path):
    """Test that configuration rejects unknown fields."""
    config_with_extra = tmp_path / "extra.yaml"
    config_with_extra.write_text(
        """
schema_version: "1.0"
unknown_field: "should fail"
"""
    )

    with pytest.raises(ConfigLoadError):
        ConfigLoader.load_from_file(config_with_extra)


def test_config_validates_threshold_ordering(tmp_path: Path):
    """Test that threshold validation works correctly."""
    invalid_thresholds = tmp_path / "invalid_thresholds.yaml"
    invalid_thresholds.write_text(
        """
schema_version: "1.0"
detection:
  thresholds:
    high_confidence: 0.6
    likely_transition: 0.8
"""
    )

    with pytest.raises(ConfigLoadError, match="likely_transition"):
        ConfigLoader.load_from_file(invalid_thresholds)


def test_config_validates_timing_ordering(tmp_path: Path):
    """Test that timing validation works correctly."""
    invalid_timing = tmp_path / "invalid_timing.yaml"
    invalid_timing.write_text(
        """
schema_version: "1.0"
detection:
  timing:
    min_months_after_phase2: 24
    max_months_after_phase2: 12
"""
    )

    with pytest.raises(ConfigLoadError, match="min_months_after_phase2"):
        ConfigLoader.load_from_file(invalid_timing)
