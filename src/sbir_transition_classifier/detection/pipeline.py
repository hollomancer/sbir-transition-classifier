"""Configuration-aware detection pipeline."""

import uuid
from typing import List, Dict, Any
from datetime import datetime

from loguru import logger

from ..config.schema import ConfigSchema
from ..data.schemas import Detection, SbirAward, Contract
from .scoring import ConfigurableScorer


class ConfigurableDetectionPipeline:
    """Detection pipeline that uses configuration parameters."""

    def __init__(self, config: ConfigSchema):
        self.config = config
        self.scorer = ConfigurableScorer(config)

    def run_detection(
        self, sbir_awards: List[Dict[str, Any]], contracts: List[Dict[str, Any]]
    ) -> List[Detection]:
        """
        Run complete detection pipeline with configuration.

        Args:
            sbir_awards: List of SBIR award data
            contracts: List of contract data

        Returns:
            List of detected transitions
        """
        logger.info("Starting configurable detection pipeline")

        detections = []

        # Determine eligible phases (unified)
        eligible_phases = ["Phase I", "Phase II"]

        # Filter to eligible phases
        eligible_awards = [
            a for a in sbir_awards if a.get("phase", "") in eligible_phases
        ]
        logger.info(
            f"Processing {len(eligible_awards)} awards from phases: {', '.join(eligible_phases)}"
        )

        for award in eligible_awards:
            award_detections = self._process_award(award, contracts)
            detections.extend(award_detections)

        logger.info(
            f"Detection pipeline completed. Found {len(detections)} transitions."
        )
        return detections

    def _process_award(
        self, award: Dict[str, Any], contracts: List[Dict[str, Any]]
    ) -> List[Detection]:
        """Process a single SBIR award against all contracts."""
        detections = []

        for contract in contracts:
            # Apply timing filter first (most selective)
            if not self.scorer.is_within_timing_window(award, contract):
                continue

            # Apply vendor matching (would need proper implementation)
            if not self._vendors_match(award, contract):
                continue

            # Apply feature filters
            if not self._passes_feature_filters(contract):
                continue

            # Calculate likelihood score
            score = self.scorer.calculate_likelihood_score(award, contract)

            # Check if meets threshold
            meets_threshold, confidence = self.scorer.meets_threshold(score)

            if meets_threshold:
                detection = self._create_detection(award, contract, score, confidence)
                detections.append(detection)

        return detections

    def _vendors_match(self, award: Dict[str, Any], contract: Dict[str, Any]) -> bool:
        """
        Check if vendors match between award and contract.

        This is a simplified implementation. In production, this would use
        proper vendor resolution with UEI, CAGE codes, DUNS numbers, etc.
        """
        award_vendor = str(award.get("vendor_name", "")).lower().strip()
        contract_vendor = str(contract.get("vendor_name", "")).lower().strip()

        if not award_vendor or not contract_vendor:
            return False

        # Exact name match
        if award_vendor == contract_vendor:
            return True

        # Fuzzy matching for common variations
        # Remove common suffixes/prefixes
        award_clean = self._clean_vendor_name(award_vendor)
        contract_clean = self._clean_vendor_name(contract_vendor)

        return award_clean == contract_clean

    def _clean_vendor_name(self, name: str) -> str:
        """Clean vendor name for matching."""
        # Remove common business suffixes
        suffixes = [
            " inc",
            " inc.",
            " corp",
            " corp.",
            " llc",
            " ltd",
            " ltd.",
            " co",
            " co.",
        ]

        name_clean = name.lower().strip()
        for suffix in suffixes:
            if name_clean.endswith(suffix):
                name_clean = name_clean[: -len(suffix)].strip()

        return name_clean

    def _passes_feature_filters(self, contract: Dict[str, Any]) -> bool:
        """Check if contract passes configured feature filters."""

        # Data quality filter: Check for PIID/date mismatches
        if self._has_date_mismatch(contract):
            return False

        # If competed contracts are disabled, only allow sole source
        if not self.config.detection.features.enable_competed_contracts:
            if not self.scorer._is_sole_source(contract):
                return False

        # Additional feature-based filters could go here

        return True

    def _has_date_mismatch(self, contract: Dict[str, Any]) -> bool:
        """Check if contract has suspicious PIID/date mismatch."""
        import re

        piid = contract.get("piid", "")
        start_date = contract.get("start_date")

        if not piid or not start_date:
            return False

        # Extract year from PIID
        year_match = re.search(r"20\d{2}", piid)
        if not year_match:
            return False

        piid_year = int(year_match.group())
        contract_year = (
            start_date.year if hasattr(start_date, "year") else int(str(start_date)[:4])
        )

        # Flag contracts with >2 year difference as suspicious
        return abs(piid_year - contract_year) > 2

    def _create_detection(
        self,
        award: Dict[str, Any],
        contract: Dict[str, Any],
        score: float,
        confidence: str,
    ) -> Detection:
        """Create Detection object from award and contract data."""

        # Create evidence bundle
        evidence_bundle = self.scorer.create_evidence_bundle(award, contract, score)

        # Create SBIR award object
        sbir_award = SbirAward(
            id=uuid.UUID(award.get("id", str(uuid.uuid4()))),
            vendor_id=uuid.uuid4(),  # Placeholder - would be resolved properly
            award_piid=award.get("award_piid", ""),
            phase=award.get("phase", ""),
            agency=award.get("agency", ""),
            award_date=award.get("award_date", datetime.utcnow()),
            completion_date=award.get("completion_date", datetime.utcnow()),
            topic=award.get("topic", ""),
            raw_data=award.get("raw_data", {}),
            created_at=datetime.utcnow(),
        )

        # Create contract object
        contract_obj = Contract(
            id=uuid.UUID(contract.get("id", str(uuid.uuid4()))),
            vendor_id=uuid.uuid4(),  # Placeholder - would be resolved properly
            piid=contract.get("piid", ""),
            parent_piid=contract.get("parent_piid"),
            agency=contract.get("agency", ""),
            start_date=contract.get("start_date", datetime.utcnow()),
            naics_code=contract.get("naics_code", ""),
            psc_code=contract.get("psc_code", ""),
            competition_details=contract.get("competition_details"),
            raw_data=contract.get("raw_data", {}),
            created_at=datetime.utcnow(),
        )

        # Create detection
        detection = Detection(
            id=uuid.uuid4(),
            sbir_award=sbir_award,
            contract=contract_obj,
            likelihood_score=score,
            confidence=confidence,
            evidence_bundle=evidence_bundle,
        )

        return detection

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline configuration and statistics."""
        return {
            "configuration": {
                "schema_version": self.config.schema_version,
                "thresholds": self.config.detection.thresholds.dict(),
                "weights": self.config.detection.weights.dict(),
                "features": self.config.detection.features.dict(),
                "timing": self.config.detection.timing.dict(),
                "output": self.config.output.dict(),
            },
            "pipeline_version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
        }

    def validate_input_data(
        self, sbir_awards: List[Dict[str, Any]], contracts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate input data quality."""
        validation_results = {
            "sbir_awards": {
                "total": len(sbir_awards),
                "phase2": len(
                    [a for a in sbir_awards if str(a.get("phase", "")).upper() == "II"]
                ),
                "missing_completion_date": len(
                    [a for a in sbir_awards if not a.get("completion_date")]
                ),
                "missing_vendor": len(
                    [a for a in sbir_awards if not a.get("vendor_name")]
                ),
            },
            "contracts": {
                "total": len(contracts),
                "missing_start_date": len(
                    [c for c in contracts if not c.get("start_date")]
                ),
                "missing_vendor": len(
                    [c for c in contracts if not c.get("vendor_name")]
                ),
                "missing_agency": len([c for c in contracts if not c.get("agency")]),
            },
        }

        # Calculate data quality scores
        if validation_results["sbir_awards"]["total"] > 0:
            validation_results["sbir_awards"]["quality_score"] = (
                validation_results["sbir_awards"]["total"]
                - validation_results["sbir_awards"]["missing_completion_date"]
                - validation_results["sbir_awards"]["missing_vendor"]
            ) / validation_results["sbir_awards"]["total"]

        if validation_results["contracts"]["total"] > 0:
            validation_results["contracts"]["quality_score"] = (
                validation_results["contracts"]["total"]
                - validation_results["contracts"]["missing_start_date"]
                - validation_results["contracts"]["missing_vendor"]
                - validation_results["contracts"]["missing_agency"]
            ) / validation_results["contracts"]["total"]

        return validation_results
