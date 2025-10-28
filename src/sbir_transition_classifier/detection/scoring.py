"""Configuration-aware detection scoring algorithms."""

from typing import Dict, Any
from datetime import timedelta
import pandas as pd

from ..config.schema import ConfigSchema
from ..config.loader import ConfigLoader


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
        completion_date = sbir_award.get("completion_date")
        start_date = contract.get("start_date")

        if pd.isna(completion_date) or pd.isna(start_date):
            return False

        # Convert to datetime if needed
        if isinstance(completion_date, str):
            completion_date = pd.to_datetime(completion_date)
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)

        # Calculate timing bounds
        min_date = completion_date + timedelta(
            days=30 * self.config.detection.timing.min_months_after_phase2
        )
        max_date = completion_date + timedelta(
            days=30 * self.config.detection.timing.max_months_after_phase2
        )

        return min_date <= start_date <= max_date

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
        completion_date = sbir_award.get("completion_date")
        start_date = contract.get("start_date")

        if pd.isna(completion_date) or pd.isna(start_date):
            return 0.0

        # Convert to datetime if needed
        if isinstance(completion_date, str):
            completion_date = pd.to_datetime(completion_date)
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)

        days_diff = (start_date - completion_date).days

        # Score based on proximity (closer = higher score)
        max_days = 30 * self.config.detection.timing.max_months_after_phase2

        if days_diff <= 0:
            return 0.0  # Contract started before SBIR completion
        elif days_diff <= 90:  # Within 3 months
            return 1.0
        elif days_diff <= 365:  # Within 1 year
            return 1.0 - (days_diff - 90) / (365 - 90) * 0.5
        elif days_diff <= max_days:
            return 0.5 - (days_diff - 365) / (max_days - 365) * 0.5
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
