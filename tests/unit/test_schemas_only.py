"""
Test only the schemas without database models.
"""
import pytest

def test_detect_request_validation():
    """Test DetectRequest schema validation."""
    from src.sbir_transition_classifier.data.schemas import DetectRequest
    
    # Valid request with vendor_identifier
    request1 = DetectRequest(vendor_identifier="ABCDE12345")
    assert request1.vendor_identifier == "ABCDE12345"
    assert request1.sbir_award_piid is None
    
    # Valid request with sbir_award_piid
    request2 = DetectRequest(sbir_award_piid="W911NF-18-C-0033")
    assert request2.sbir_award_piid == "W911NF-18-C-0033"
    assert request2.vendor_identifier is None

def test_config_import():
    """Test that config can be imported."""
    from src.sbir_transition_classifier.core.config import settings
    assert settings.DATABASE_URL is not None
    assert "sqlite" in settings.DATABASE_URL

def test_basic_python_syntax():
    """Test that all Python files have valid syntax."""
    import py_compile
    import os
    
    src_dir = "src/sbir_transition_classifier"
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    py_compile.compile(filepath, doraise=True)
                except py_compile.PyCompileError as e:
                    pytest.fail(f"Syntax error in {filepath}: {e}")

def test_project_structure():
    """Test that the expected project structure exists."""
    import os
    
    expected_files = [
        "src/sbir_transition_classifier/__init__.py",
        "src/sbir_transition_classifier/api/main.py",
        "src/sbir_transition_classifier/core/models.py",
        "src/sbir_transition_classifier/core/config.py",
        "src/sbir_transition_classifier/data/schemas.py",
        "src/sbir_transition_classifier/db/database.py",
        "src/sbir_transition_classifier/detection/heuristics.py",
        "src/sbir_transition_classifier/detection/scoring.py",
        "src/sbir_transition_classifier/detection/main.py",
        "scripts/load_bulk_data.py",
        "scripts/export_data.py",
        "docker-compose.yml",
        "Dockerfile",
        "pyproject.toml",
        "README.md",
        "data/award_data.csv"
    ]
    
    for file_path in expected_files:
        assert os.path.exists(file_path), f"Expected file {file_path} does not exist"
