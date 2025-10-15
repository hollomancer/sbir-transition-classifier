"""
Simple API tests with mocked dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@patch('src.sbir_transition_classifier.api.main.SessionLocal')
@patch('src.sbir_transition_classifier.api.main.run_full_detection')
def test_detect_endpoint_valid_request(mock_detection, mock_session):
    """Test the /detect endpoint with valid input."""
    from src.sbir_transition_classifier.api.main import app
    
    client = TestClient(app)
    
    response = client.post(
        "/detect",
        json={"vendor_identifier": "ABCDE12345"}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "status" in data
    assert data["status"] == "Analysis has been accepted and is in progress."

def test_detect_endpoint_invalid_request():
    """Test the /detect endpoint with invalid input."""
    from src.sbir_transition_classifier.api.main import app
    
    client = TestClient(app)
    
    response = client.post(
        "/detect",
        json={}  # Missing required fields
    )
    
    assert response.status_code == 400
    assert "Either vendor_identifier or sbir_award_piid must be provided" in response.json()["detail"]

def test_detect_endpoint_empty_identifier():
    """Test the /detect endpoint with empty identifier."""
    from src.sbir_transition_classifier.api.main import app
    
    client = TestClient(app)
    
    response = client.post(
        "/detect",
        json={"vendor_identifier": ""}
    )
    
    assert response.status_code == 400
    assert "Either vendor_identifier or sbir_award_piid must be provided" in response.json()["detail"]
