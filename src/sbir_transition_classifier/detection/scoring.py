"""Configuration-aware detection scoring algorithms with signal detection."""

from typing import Dict, Any
from datetime import timedelta
import pandas as pd

from ..config.schema import ConfigSchema
from ..config.loader import ConfigLoader
from ..core import models


# Global scorer instance for backward compatibility
_default_scorer = None


def get_default_scorer():
    """Get default scorer instance."""
    global _default_scorer
    if _default_scorer is None:
        # Load configuration using ConfigLoader with fallback to defaults
        try:
            config = ConfigLoader.load_default()
        except Exception:
            config = ConfigSchema()

        _default_scorer = ConfigurableScorer(config)
    return _default_scorer


def score_transition(sbir_award, contract) -> float:
    """
    Backward compatibility function for scoring transitions.

    Args:
        sbir_award: SBIR award model or dict
        contract: Contract model or dict

    Returns:
        Likelihood score between 0.0 and 1.0
    """
    scorer = get_default_scorer()

    # Convert models to dicts if needed
    if hasattr(sbir_award, "__dict__"):
        award_dict = {
            "agency": sbir_award.agency,
            "completion_date": sbir_award.completion_date,
            "topic": sbir_award.topic,
            "phase": sbir_award.phase,
        }
    else:
        award_dict = sbir_award

    if hasattr(contract, "__dict__"):
        contract_dict = {
            "agency": contract.agency,
            "start_date": contract.start_date,
            "competition_details": getattr(contract, "competition_details", {}),
            "raw_data": getattr(contract, "raw_data", {}),
        }
    else:
        contract_dict = contract

    return scorer.calculate_likelihood_score(award_dict, contract_dict)


def get_confidence_level(score: float) -> str:
    """
    Get confidence level for a given score.

    Args:
        score: Likelihood score

    Returns:
        Confidence level string
    """
    scorer = get_default_scorer()
    _, confidence = scorer.meets_threshold(score)
    return confidence


# Signal detection utility functions (migrated from heuristics.py)


def get_department(agency_string: str) -> str:
    """
    Enhanced department extraction with better mapping.

    Args:
        agency_string: Agency name string

    Returns:
        Department abbreviation (e.g., "DOD", "NASA", "DOE")
    """
    if not agency_string:
        return ""

    agency = agency_string.upper()

    # Department of Defense
    if any(x in agency for x in ["DEFENSE", "AIR FORCE", "NAVY", "ARMY"]):
        return "DOD"
    # NASA
    elif "NASA" in agency:
        return "NASA"
    # Department of Energy
    elif "ENERGY" in agency:
        return "DOE"
    # General Services Administration
    elif "GSA" in agency or "GENERAL SERVICES" in agency:
        return "GSA"
    # Department of Homeland Security
    elif "HOMELAND" in agency:
        return "DHS"
    # Default to first word
    else:
        return agency.split()[0] if agency else "UNKNOWN"


def get_confidence_signals(
    sbir_award: models.SbirAward, contract: models.Contract
) -> dict:
    """
    Enhanced confidence signals with relaxed agency matching.

    Args:
        sbir_award: SBIR award model
        contract: Contract model

    Returns:
        Dictionary of confidence signals
    """
    signals = {}

    # Enhanced agency matching
    sbir_agency = (sbir_award.agency or "").upper()
    contract_agency = (contract.agency or "").upper()

    # Signal 1: Direct agency match
    signals["same_agency"] = sbir_agency == contract_agency

    # Signal 2: Department-level match
    signals["same_department"] = get_department(sbir_agency) == get_department(
        contract_agency
    )

    # Signal 3: GSA reseller logic (GSA often resells DoD contracts)
    signals["gsa_reseller"] = (
        "GSA" in contract_agency or "GENERAL SERVICES" in contract_agency
    ) and (
        "DEFENSE" in sbir_agency
        or "AIR FORCE" in sbir_agency
        or "NAVY" in sbir_agency
        or "ARMY" in sbir_agency
    )

    # Signal 4: Cross-agency federal transition (still valid)
    signals["federal_transition"] = True  # Both are federal agencies

    # Signal 5: Enhanced competition analysis
    signals["sole_source"] = False
    signals["limited_competition"] = False
    signals["full_competition"] = False

    if contract.competition_details:
        extent_competed = str(
            contract.competition_details.get("extent_competed", "")
        ).upper()

        if "NOT AVAILABLE FOR COMPETITION" in extent_competed:
            signals["sole_source"] = True
        elif "NOT COMPETED" in extent_competed or "LIMITED" in extent_competed:
            signals["limited_competition"] = True
        elif "FULL AND OPEN" in extent_competed:
            signals["full_competition"] = True

    return signals


def get_text_based_signals(
    sbir_award: models.SbirAward, contract: models.Contract
) -> dict:
    """
    Analyzes text fields for signals linking an award and contract.

    Args:
        sbir_award: SBIR award model
        contract: Contract model

    Returns:
        Dictionary of text-based signals
    """
    signals = {"sbir_in_description": False, "topic_in_description": False}

    if not contract.raw_data or not isinstance(contract.raw_data, dict):
        return signals

    description = contract.raw_data.get("description", "").lower()
    if not description:
        return signals

    if "sbir" in description:
        signals["sbir_in_description"] = True

    if sbir_award.topic and sbir_award.topic.lower() in description:
        signals["topic_in_description"] = True

    return signals


class ConfigurableScorer:
    """Scoring algorithm that uses configuration parameters."""

    def __init__(self, config: ConfigSchema):
        self.config = config

    def calculate_likelihood_score(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any]
    ) -> float:
        """
        Calculate likelihood score using configured weights and features.

        Args:
            sbir_award: SBIR award data
            contract: Contract data

        Returns:
            Likelihood score between 0.0 and 1.0
        """
        score = 0.0

        # Base score for any potential match
        score += 0.2

        # Agency continuity scoring
        if self._agencies_match(sbir_award, contract):
            score += self.config.detection.weights.agency_continuity
        elif self.config.detection.features.enable_cross_service:
            # Reduced score for cross-service transitions
            score += self.config.detection.weights.agency_continuity * 0.5

        # Timing proximity scoring
        timing_score = self._calculate_timing_score(sbir_award, contract)
        score += timing_score * self.config.detection.weights.timing_weight

        # Sole source bonus
        if self._is_sole_source(contract):
            score += self.config.detection.weights.sole_source_bonus

        # Text similarity (if enabled)
        if self.config.detection.features.enable_text_analysis:
            text_score = self._calculate_text_similarity(sbir_award, contract)
            score += text_score * self.config.detection.weights.text_similarity

        # Competition type filtering
        if not self.config.detection.features.enable_competed_contracts:
            if not self._is_sole_source(contract):
                score *= 0.3  # Heavily penalize competed contracts if disabled

        # Strong penalty for very late contracts (> 365 days after Phase II completion)
        completion_date = sbir_award.get("completion_date")
        start_date = contract.get("start_date")
        if isinstance(completion_date, str):
            completion_date = pd.to_datetime(completion_date)
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if pd.notna(completion_date) and pd.notna(start_date):
            days_diff = (start_date - completion_date).days
            if days_diff > 365:
                # Apply multiplicative decay and subtractive penalty to ensure score falls below likely threshold
                score = max(0.0, score * 0.4 - 0.2)

        return min(score, 1.0)  # Cap at 1.0

    def meets_threshold(self, score: float) -> tuple[bool, str]:
        """
        Check if score meets configured thresholds.

        Args:
            score: Likelihood score

        Returns:
            Tuple of (meets_threshold, confidence_level)
        """
        if score >= self.config.detection.thresholds.high_confidence:
            return True, "High Confidence"
        elif score >= self.config.detection.thresholds.likely_transition:
            return True, "Likely Transition"
        else:
            return False, "Below Threshold"

    def is_within_timing_window(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any]
    ) -> bool:
        """
        Check if contract timing is within configured window.

        Args:
            sbir_award: SBIR award data
            contract: Contract data

        Returns:
            True if within timing window
        """
        from ..utils.dates import (
            is_within_timing_window as is_within_timing_window_util,
        )

        completion_date = sbir_award.get("completion_date")
        award_date = sbir_award.get("award_date")
        start_date = contract.get("start_date")

        if pd.isna(start_date):
            return False

        # Convert to datetime if needed
        if isinstance(completion_date, str):
            completion_date = pd.to_datetime(completion_date)
        if isinstance(award_date, str):
            award_date = pd.to_datetime(award_date)
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)

        return is_within_timing_window_util(
            award_date=award_date,
            contract_date=start_date,
            config=self.config,
            completion_date=completion_date,
        )

    def _agencies_match(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any]
    ) -> bool:
        """Check if agencies match exactly."""
        sbir_agency = str(sbir_award.get("agency", "")).lower().strip()
        contract_agency = str(contract.get("agency", "")).lower().strip()

        if not sbir_agency or not contract_agency:
            return False

        return sbir_agency == contract_agency

    def _calculate_timing_score(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any]
    ) -> float:
        """Calculate timing proximity score (closer = higher score)."""
        from ..utils.dates import get_months_between

        completion_date = sbir_award.get("completion_date")
        start_date = contract.get("start_date")

        if pd.isna(completion_date) or pd.isna(start_date):
            return 0.0

        # Convert to datetime if needed
        if isinstance(completion_date, str):
            completion_date = pd.to_datetime(completion_date)
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)

        months_diff = get_months_between(completion_date, start_date)

        # Score based on proximity (closer = higher score)
        max_months = self.config.detection.timing.max_months_after_phase2

        if months_diff < 0:
            return 0.0  # Contract started before SBIR completion
        elif months_diff <= 3:  # Within 3 months
            return 1.0
        elif months_diff <= 12:  # Within 1 year
            return 1.0 - (months_diff - 3) / (12 - 3) * 0.5
        elif months_diff <= max_months:
            return 0.5 - (months_diff - 12) / (max_months - 12) * 0.5
        else:
            return 0.0

    def _is_sole_source(self, contract: Dict[str, Any]) -> bool:
        """Check if contract is sole source."""
        competition_details = contract.get("competition_details", {})

        if isinstance(competition_details, dict):
            # Check for boolean sole_source flag
            if competition_details.get("sole_source", False):
                return True

            # Check for extent_competed string in competition_details
            extent_competed = str(
                competition_details.get("extent_competed", "")
            ).lower()
            if "not competed" in extent_competed or "sole source" in extent_competed:
                return True

        # Check raw data for competition indicators as fallback
        raw_data = contract.get("raw_data", {})
        if isinstance(raw_data, dict):
            extent_competed = str(raw_data.get("extent_competed", "")).lower()
            return "not competed" in extent_competed or "sole source" in extent_competed

        return False

    def _calculate_text_similarity(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any]
    ) -> float:
        """Calculate text similarity between award topic and contract description."""
        # Get text fields
        award_topic = str(sbir_award.get("topic", "")).lower()

        # Try multiple contract description fields
        contract_desc = ""
        raw_data = contract.get("raw_data", {})
        if isinstance(raw_data, dict):
            contract_desc = str(raw_data.get("description", "")).lower()
            if not contract_desc:
                contract_desc = str(
                    raw_data.get("product_or_service_description", "")
                ).lower()

        if not award_topic or not contract_desc:
            return 0.0

        # Simple keyword-based similarity
        award_words = set(self._extract_keywords(award_topic))
        contract_words = set(self._extract_keywords(contract_desc))

        if not award_words:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(award_words.intersection(contract_words))
        union = len(award_words.union(contract_words))

        return intersection / union if union > 0 else 0.0

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction - remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "this",
            "that",
            "these",
            "those",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
        }

        words = text.split()
        keywords = []

        for word in words:
            # Clean word
            word = "".join(c for c in word if c.isalnum()).lower()

            # Filter out short words and stop words
            if len(word) >= 3 and word not in stop_words:
                keywords.append(word)

        return keywords

    def create_evidence_bundle(
        self, sbir_award: Dict[str, Any], contract: Dict[str, Any], score: float
    ) -> Dict[str, Any]:
        """Create detailed evidence bundle for detection."""
        completion_date = sbir_award.get("completion_date")
        start_date = contract.get("start_date")

        evidence = {
            "likelihood_score": score,
            "config_version": self.config.schema_version,
            "scoring_components": {
                "agency_continuity": self._agencies_match(sbir_award, contract),
                "timing_score": self._calculate_timing_score(sbir_award, contract),
                "sole_source": self._is_sole_source(contract),
                "text_similarity": self._calculate_text_similarity(sbir_award, contract)
                if self.config.detection.features.enable_text_analysis
                else None,
            },
            "timing_analysis": {
                "sbir_completion": completion_date.isoformat()
                if pd.notna(completion_date)
                else None,
                "contract_start": start_date.isoformat()
                if pd.notna(start_date)
                else None,
                "days_difference": (start_date - completion_date).days
                if pd.notna(completion_date) and pd.notna(start_date)
                else None,
                "within_window": self.is_within_timing_window(sbir_award, contract),
            },
            "configuration_used": {
                "thresholds": self.config.detection.thresholds.dict(),
                "weights": self.config.detection.weights.dict(),
                "features": self.config.detection.features.dict(),
                "timing": self.config.detection.timing.dict(),
            },
        }

        return evidence
