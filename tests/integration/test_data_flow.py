"""
Integration tests for the main data ingestion and detection flow.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.sbir_transition_classifier.core.models import Base, Vendor, SbirAward, Contract, Detection
from src.sbir_transition_classifier.detection.main import run_full_detection
from src.sbir_transition_classifier.db.database import get_db
import tempfile
import os

@pytest.fixture
def test_db():
    """Create a temporary test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    return override_get_db, TestingSessionLocal

def test_data_ingestion_flow(test_db):
    """Test that data can be ingested and stored properly."""
    override_get_db, TestingSessionLocal = test_db
    
    # Create test data
    db = TestingSessionLocal()
    
    # Create a test vendor
    vendor = Vendor(name="Test Vendor Inc.")
    db.add(vendor)
    db.commit()
    
    # Create a test SBIR award
    sbir_award = SbirAward(
        vendor_id=vendor.id,
        award_piid="TEST-SBIR-001",
        phase="Phase II",
        agency="TEST AGENCY",
        topic="Test Topic",
        raw_data={"test": "data"}
    )
    db.add(sbir_award)
    db.commit()
    
    # Create a test contract
    contract = Contract(
        vendor_id=vendor.id,
        piid="TEST-CONTRACT-001",
        agency="TEST AGENCY",
        naics_code="541712",
        psc_code="R425",
        competition_details={"sole_source": True},
        raw_data={"test": "contract"}
    )
    db.add(contract)
    db.commit()
    
    # Verify data was stored
    assert db.query(Vendor).count() == 1
    assert db.query(SbirAward).count() == 1
    assert db.query(Contract).count() == 1
    
    db.close()

@patch('src.sbir_transition_classifier.detection.main.SessionLocal')
def test_detection_flow(mock_session_local, test_db):
    """Test that the detection process runs without errors."""
    override_get_db, TestingSessionLocal = test_db
    
    # Mock the session to use our test database
    mock_session_local.return_value = TestingSessionLocal()
    
    # Mock the detection process to avoid actual ML computation
    with patch('src.sbir_transition_classifier.detection.heuristics.find_candidate_contracts') as mock_find, \
         patch('src.sbir_transition_classifier.detection.scoring.score_detection') as mock_score:
        
        mock_find.return_value = []
        mock_score.return_value = 0.5
        
        # This should run without errors
        try:
            run_full_detection()
            assert True  # If we get here, the function ran successfully
        except Exception as e:
            pytest.fail(f"Detection flow failed: {e}")

def test_end_to_end_detection():
    """Test a simplified end-to-end detection scenario."""
    # This test would ideally use a real database with sample data
    # For now, we'll just verify the detection logic can be called
    from src.sbir_transition_classifier.detection.heuristics import analyze_high_confidence_signals
    from src.sbir_transition_classifier.detection.scoring import score_detection
    
    # Mock data structures
    mock_sbir = {
        'agency': 'DEPT OF DEFENSE',
        'completion_date': '2020-01-15',
        'topic': 'AI/ML'
    }
    
    mock_contract = {
        'agency': 'DEPT OF DEFENSE',
        'start_date': '2020-09-01',
        'competition_details': {'sole_source': True}
    }
    
    # Test heuristics
    signals = analyze_high_confidence_signals(mock_sbir, mock_contract)
    assert isinstance(signals, dict)
    
    # Test scoring
    score = score_detection(signals)
    assert 0.0 <= score <= 1.0
