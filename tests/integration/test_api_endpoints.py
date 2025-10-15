"""
Integration tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.sbir_transition_classifier.api.main import app
import uuid

client = TestClient(app)

def test_detect_endpoint_valid_request():
    """Test the /detect endpoint with valid input."""
    with patch('src.sbir_transition_classifier.api.main.detection.main.run_full_detection') as mock_detection:
        response = client.post(
            "/detect",
            json={"vendor_identifier": "ABCDE12345"}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] == "Analysis has been accepted and is in progress."
        
        # Verify the background task was triggered
        mock_detection.assert_called_once()

def test_detect_endpoint_invalid_request():
    """Test the /detect endpoint with invalid input."""
    response = client.post(
        "/detect",
        json={}  # Missing required fields
    )
    
    assert response.status_code == 400
    assert "Either vendor_identifier or sbir_award_piid must be provided" in response.json()["detail"]

def test_detect_endpoint_empty_identifier():
    """Test the /detect endpoint with empty identifier."""
    response = client.post(
        "/detect",
        json={"vendor_identifier": ""}
    )
    
    assert response.status_code == 400
    assert "vendor_identifier cannot be empty" in response.json()["detail"]

@patch('src.sbir_transition_classifier.api.main.SessionLocal')
def test_evidence_endpoint_found(mock_session_local):
    """Test the /evidence endpoint when detection is found."""
    # Mock database session and query
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock detection record
    mock_detection = MagicMock()
    mock_detection.evidence_bundle = {
        "detection_id": "test-uuid",
        "likelihood_score": 0.85,
        "confidence": "High Confidence"
    }
    
    mock_db.query.return_value.filter.return_value.first.return_value = mock_detection
    
    test_uuid = uuid.uuid4()
    response = client.get(f"/evidence/{test_uuid}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["likelihood_score"] == 0.85
    assert data["confidence"] == "High Confidence"

@patch('src.sbir_transition_classifier.api.main.SessionLocal')
def test_evidence_endpoint_not_found(mock_session_local):
    """Test the /evidence endpoint when detection is not found."""
    # Mock database session and query
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock no detection found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    test_uuid = uuid.uuid4()
    response = client.get(f"/evidence/{test_uuid}")
    
    assert response.status_code == 404
    assert "Detection not found" in response.json()["detail"]

def test_evidence_endpoint_invalid_uuid():
    """Test the /evidence endpoint with invalid UUID."""
    response = client.get("/evidence/invalid-uuid")
    
    assert response.status_code == 422  # Validation error
