from ..core import models
from . import heuristics

import xgboost as xgb

def score_transition(sbir_award: models.SbirAward, contract: models.Contract) -> float:
    """
    Enhanced scoring with relaxed criteria for cross-agency transitions.
    """
    
    # 1. Gather signals from the heuristics module
    structural_signals = heuristics.get_confidence_signals(sbir_award, contract)
    text_signals = heuristics.get_text_based_signals(sbir_award, contract)

    # 2. Create a feature vector from these signals
    features = {
        **structural_signals,
        **text_signals
    }

    # 3. Enhanced scoring with relaxed weights
    weights = {
        'same_agency': 0.4,
        'same_department': 0.3,
        'gsa_reseller': 0.25,  # New: GSA reselling DoD contracts
        'federal_transition': 0.1,  # New: Any federal transition has value
        'sole_source': 0.3,
        'limited_competition': 0.2,  # New: Limited competition
        'full_competition': 0.1,  # New: Even full competition can be transition
        'sbir_in_description': 0.15,
        'topic_in_description': 0.1
    }

    score = sum(weights.get(feature, 0) for feature, value in features.items() if value)

    # Ensure score is capped at 1.0
    return min(score, 1.0)

def get_confidence_level(score: float) -> str:
    """
    Relaxed confidence thresholds to capture more transitions.
    """
    if score >= 0.7:
        return "High Confidence"
    elif score >= 0.4:  # Lowered from typical 0.6
        return "Likely Transition"
    elif score >= 0.2:  # New category for weak signals
        return "Possible Transition"
    else:
        return "Low Confidence"

