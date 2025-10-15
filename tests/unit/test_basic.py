"""
Basic unit tests that don't require database connections.
"""
import pytest

def test_basic_imports():
    """Test that basic modules can be imported."""
    # Test data schemas
    from src.sbir_transition_classifier.data.schemas import DetectRequest
    assert DetectRequest is not None

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
