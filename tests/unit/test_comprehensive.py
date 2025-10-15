"""
Comprehensive test suite that validates the core functionality without external dependencies.
"""
import pytest
import os

def test_all_python_files_compile():
    """Test that all Python files in the project compile without syntax errors."""
    import py_compile
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    for root, dirs, files in os.walk("scripts"):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Test compilation
    for filepath in python_files:
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"Syntax error in {filepath}: {e}")

def test_project_structure_complete():
    """Test that all expected files and directories exist."""
    expected_structure = {
        # Core source files
        "src/sbir_transition_classifier/__init__.py": "file",
        "src/sbir_transition_classifier/api/": "dir",
        "src/sbir_transition_classifier/api/__init__.py": "file",
        "src/sbir_transition_classifier/api/main.py": "file",
        "src/sbir_transition_classifier/core/": "dir",
        "src/sbir_transition_classifier/core/__init__.py": "file",
        "src/sbir_transition_classifier/core/config.py": "file",
        "src/sbir_transition_classifier/core/models.py": "file",
        "src/sbir_transition_classifier/data/": "dir",
        "src/sbir_transition_classifier/data/__init__.py": "file",
        "src/sbir_transition_classifier/data/schemas.py": "file",
        "src/sbir_transition_classifier/db/": "dir",
        "src/sbir_transition_classifier/db/__init__.py": "file",
        "src/sbir_transition_classifier/db/database.py": "file",
        "src/sbir_transition_classifier/detection/": "dir",
        "src/sbir_transition_classifier/detection/__init__.py": "file",
        "src/sbir_transition_classifier/detection/heuristics.py": "file",
        "src/sbir_transition_classifier/detection/scoring.py": "file",
        "src/sbir_transition_classifier/detection/main.py": "file",
        
        # Scripts
        "scripts/": "dir",
        "scripts/__init__.py": "file",
        "scripts/load_bulk_data.py": "file",
        "scripts/export_data.py": "file",
        
        # Configuration files
        "pyproject.toml": "file",
        "docker-compose.yml": "file",
        "Dockerfile": "file",
        ".gitignore": "file",
        ".dockerignore": "file",
        "README.md": "file",
        
        # Test structure
        "tests/": "dir",
        "tests/__init__.py": "file",
        "tests/unit/": "dir",
        "tests/unit/__init__.py": "file",
        "tests/integration/": "dir",
        "tests/integration/__init__.py": "file",
        
        # Data file
        "data/award_data.csv": "file"
    }
    
    for path, expected_type in expected_structure.items():
        if expected_type == "file":
            assert os.path.isfile(path), f"Expected file {path} does not exist"
        elif expected_type == "dir":
            assert os.path.isdir(path), f"Expected directory {path} does not exist"

def test_schemas_validation():
    """Test that Pydantic schemas work correctly."""
    from src.sbir_transition_classifier.data.schemas import DetectRequest
    
    # Test valid requests
    request1 = DetectRequest(vendor_identifier="ABCDE12345")
    assert request1.vendor_identifier == "ABCDE12345"
    assert request1.sbir_award_piid is None
    
    request2 = DetectRequest(sbir_award_piid="W911NF-18-C-0033")
    assert request2.sbir_award_piid == "W911NF-18-C-0033"
    assert request2.vendor_identifier is None
    
    # Test that both can be provided
    request3 = DetectRequest(vendor_identifier="ABCDE12345", sbir_award_piid="W911NF-18-C-0033")
    assert request3.vendor_identifier == "ABCDE12345"
    assert request3.sbir_award_piid == "W911NF-18-C-0033"

def test_config_settings():
    """Test that configuration settings are properly loaded."""
    from src.sbir_transition_classifier.core.config import settings
    
    assert settings.DATABASE_URL is not None
    assert isinstance(settings.DATABASE_URL, str)
    assert len(settings.DATABASE_URL) > 0
    assert "sqlite" in settings.DATABASE_URL

def test_docker_configuration():
    """Test that Docker configuration files are valid."""
    import yaml
    
    # Test docker-compose.yml
    with open("docker-compose.yml", "r") as f:
        compose_config = yaml.safe_load(f)
    
    assert "services" in compose_config
    assert "api" in compose_config["services"]
    # No longer expecting db service since we're using SQLite
    
    # Test that Dockerfile exists and has basic structure
    with open("Dockerfile", "r") as f:
        dockerfile_content = f.read()
    
    assert "FROM python:" in dockerfile_content
    assert "WORKDIR" in dockerfile_content
    assert "COPY" in dockerfile_content
    assert "CMD" in dockerfile_content or "ENTRYPOINT" in dockerfile_content

def test_readme_completeness():
    """Test that README.md contains essential information."""
    with open("README.md", "r") as f:
        readme_content = f.read()
    
    essential_sections = [
        "# SBIR Transition Detection System",
        "## Overview",
        "## Features",
        "## Quick Start",
        "## Architecture",
        "## API Reference"
    ]
    
    for section in essential_sections:
        assert section in readme_content, f"README.md missing section: {section}"

def test_pyproject_toml_structure():
    """Test that pyproject.toml has the required structure."""
    import tomllib
    
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    
    assert "tool" in config
    assert "poetry" in config["tool"]
    assert "dependencies" in config["tool"]["poetry"]
    
    # Check for key dependencies
    deps = config["tool"]["poetry"]["dependencies"]
    required_deps = ["fastapi", "sqlalchemy", "pandas", "loguru"]
    
    for dep in required_deps:
        assert dep in deps, f"Missing required dependency: {dep}"
