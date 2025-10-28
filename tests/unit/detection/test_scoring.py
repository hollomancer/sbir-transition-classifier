"""Tests for detection scoring algorithms."""

import pytest
from datetime import datetime, timedelta

from sbir_transition_classifier.detection.scoring import ConfigurableScorer
from sbir_transition_classifier.config.schema import ConfigSchema


@pytest.fixture
def default_config():
    """Get default configuration."""
    return ConfigSchema()


@pytest.fixture
def scorer(default_config):
    """Create a scorer with default configuration."""
    return ConfigurableScorer(default_config)


def test_perfect_match_scores_high(scorer):
    """Test that a perfect match scores very high."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Advanced Widgets",
    }

    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),  # 2 months after completion
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    score = scorer.calculate_likelihood_score(award_dict, contract_dict)

    assert score > 0.8  # Should be high confidence


def test_timing_too_late_scores_low(scorer):
    """Test that contract far after Phase II scores low."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2020, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 1, 1),  # 3 years later
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    score = scorer.calculate_likelihood_score(award_dict, contract_dict)

    assert score < 0.3  # Should be low due to timing


def test_different_agency_reduces_score(scorer):
    """Test that different agencies reduce score."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    same_agency_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {},
        "naics_code": "541712",
    }

    diff_agency_contract = {
        "agency": "Navy",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {},
        "naics_code": "541712",
    }

    same_score = scorer.calculate_likelihood_score(award_dict, same_agency_contract)
    diff_score = scorer.calculate_likelihood_score(award_dict, diff_agency_contract)

    assert same_score > diff_score


def test_sole_source_increases_score(scorer):
    """Test that sole source contracts score higher."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    sole_source_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    competed_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {"extent_competed": "FULL AND OPEN COMPETITION"},
        "naics_code": "541712",
    }

    sole_score = scorer.calculate_likelihood_score(award_dict, sole_source_contract)
    competed_score = scorer.calculate_likelihood_score(award_dict, competed_contract)

    assert sole_score > competed_score


def test_timing_within_window_scores_higher(scorer):
    """Test that contracts within timing window score higher."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    # Contract 3 months after completion (within window)
    near_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 4, 1),
        "competition_details": {},
        "naics_code": "541712",
    }

    # Contract 18 months after completion (still in window but further)
    far_contract = {
        "agency": "Air Force",
        "start_date": datetime(2024, 7, 1),
        "competition_details": {},
        "naics_code": "541712",
    }

    near_score = scorer.calculate_likelihood_score(award_dict, near_contract)
    far_score = scorer.calculate_likelihood_score(award_dict, far_contract)

    assert near_score > far_score


def test_score_range_is_valid(scorer):
    """Test that scores are always between 0 and 1."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    contract_dict = {
        "agency": "Navy",
        "start_date": datetime(2025, 1, 1),  # Very late
        "competition_details": {},
        "naics_code": "541712",
    }

    score = scorer.calculate_likelihood_score(award_dict, contract_dict)

    assert 0.0 <= score <= 1.0


def test_custom_config_affects_scoring():
    """Test that custom configuration affects scoring results."""
    # Create config with very high sole source bonus
    custom_config = ConfigSchema()
    custom_config.detection.weights.sole_source_bonus = 0.5

    custom_scorer = ConfigurableScorer(custom_config)

    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    sole_source_contract = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    # Default scorer
    default_scorer = ConfigurableScorer(ConfigSchema())
    default_score = default_scorer.calculate_likelihood_score(
        award_dict, sole_source_contract
    )

    # Custom scorer with higher sole source weight
    custom_score = custom_scorer.calculate_likelihood_score(
        award_dict, sole_source_contract
    )

    # Custom scorer should give higher score due to higher sole source bonus
    assert custom_score >= default_score


def test_phase_i_awards_can_be_scored(scorer):
    """Test that Phase I awards can also be scored."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase I",
        "topic": "Test",
    }

    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    score = scorer.calculate_likelihood_score(award_dict, contract_dict)

    # Should still produce a valid score
    assert 0.0 <= score <= 1.0
    assert score > 0  # Should have some positive score


def test_contract_before_completion_scores_zero(scorer):
    """Test that contracts before award completion score very low."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 6, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 1, 1),  # Before completion
        "competition_details": {"extent_competed": "SOLE SOURCE"},
        "naics_code": "541712",
    }

    score = scorer.calculate_likelihood_score(award_dict, contract_dict)

    # Should score very low or zero
    assert score < 0.1


def test_missing_competition_details_handled(scorer):
    """Test that missing competition details are handled gracefully."""
    award_dict = {
        "agency": "Air Force",
        "completion_date": datetime(2023, 1, 1),
        "phase": "Phase II",
        "topic": "Test",
    }

    contract_dict = {
        "agency": "Air Force",
        "start_date": datetime(2023, 3, 1),
        "competition_details": None,  # Missing
        "naics_code": "541712",
    }

    # Should not raise an error
    score = scorer.calculate_likelihood_score(award_dict, contract_dict)
    assert 0.0 <= score <= 1.0
