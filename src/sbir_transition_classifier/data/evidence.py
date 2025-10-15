"""Evidence bundle generation for offline review."""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from loguru import logger

from .models import EvidenceBundleArtifact, EvidenceType, DetectionSession
from ..data.schemas import Detection


class EvidenceBundleGenerator:
    """Generates comprehensive evidence bundles for offline review."""
    
    def __init__(self, session: DetectionSession):
        self.session = session
    
    def generate_evidence_bundles(self, detections: List[Detection], output_dir: Path) -> List[EvidenceBundleArtifact]:
        """
        Generate evidence bundles for all detections.
        
        Args:
            detections: List of detection results
            output_dir: Base output directory
            
        Returns:
            List of created evidence bundle artifacts
        """
        evidence_dir = output_dir / "evidence"
        evidence_dir.mkdir(exist_ok=True)
        
        artifacts = []
        
        for detection in detections:
            try:
                artifact = self._generate_single_bundle(detection, evidence_dir)
                artifacts.append(artifact)
                logger.debug(f"Generated evidence bundle for detection {detection.id}")
            except Exception as e:
                logger.error(f"Failed to generate evidence bundle for detection {detection.id}: {e}")
        
        logger.info(f"Generated {len(artifacts)} evidence bundles")
        return artifacts
    
    def _generate_single_bundle(self, detection: Detection, evidence_dir: Path) -> EvidenceBundleArtifact:
        """Generate evidence bundle for a single detection."""
        
        # Create detection-specific directory
        detection_dir = evidence_dir / str(detection.id)
        detection_dir.mkdir(exist_ok=True)
        
        # Generate evidence files
        evidence_file = self._create_evidence_json(detection, detection_dir)
        summary_file = self._create_evidence_summary(detection, detection_dir)
        
        # Create source document links
        self._create_source_links(detection, detection_dir)
        
        # Determine evidence type
        evidence_type = self._classify_evidence_type(detection)
        
        # Calculate file size
        file_size = evidence_file.stat().st_size + summary_file.stat().st_size
        
        # Create artifact record
        artifact = EvidenceBundleArtifact(
            session_id=self.session.session_id,
            detection_id=detection.id,
            file_path=str(evidence_file),
            summary_path=str(summary_file),
            evidence_type=evidence_type,
            file_size=file_size
        )
        
        return artifact
    
    def _create_evidence_json(self, detection: Detection, detection_dir: Path) -> Path:
        """Create comprehensive evidence JSON file."""
        evidence_file = detection_dir / "evidence.json"
        
        evidence_data = {
            "detection_metadata": {
                "detection_id": str(detection.id),
                "likelihood_score": detection.likelihood_score,
                "confidence": detection.confidence,
                "created_at": datetime.utcnow().isoformat(),
                "session_id": str(self.session.session_id)
            },
            "sbir_award": {
                "id": str(detection.sbir_award.id),
                "piid": detection.sbir_award.award_piid,
                "phase": detection.sbir_award.phase,
                "agency": detection.sbir_award.agency,
                "award_date": detection.sbir_award.award_date.isoformat(),
                "completion_date": detection.sbir_award.completion_date.isoformat(),
                "topic": detection.sbir_award.topic,
                "vendor_id": str(detection.sbir_award.vendor_id),
                "raw_data": detection.sbir_award.raw_data
            },
            "contract": {
                "id": str(detection.contract.id),
                "piid": detection.contract.piid,
                "parent_piid": detection.contract.parent_piid,
                "agency": detection.contract.agency,
                "start_date": detection.contract.start_date.isoformat(),
                "naics_code": detection.contract.naics_code,
                "psc_code": detection.contract.psc_code,
                "vendor_id": str(detection.contract.vendor_id),
                "competition_details": detection.contract.competition_details,
                "raw_data": detection.contract.raw_data
            },
            "analysis": {
                "evidence_bundle": detection.evidence_bundle,
                "transition_analysis": self._analyze_transition(detection),
                "risk_assessment": self._assess_risk_factors(detection),
                "validation_checklist": self._create_validation_checklist(detection)
            },
            "session_context": {
                "config_used": self.session.config_used,
                "config_checksum": self.session.config_checksum,
                "input_datasets": self.session.input_datasets,
                "output_path": self.session.output_path
            }
        }
        
        with open(evidence_file, 'w', encoding='utf-8') as f:
            json.dump(evidence_data, f, indent=2, default=str)
        
        return evidence_file
    
    def _create_evidence_summary(self, detection: Detection, detection_dir: Path) -> Path:
        """Create human-readable evidence summary."""
        summary_file = detection_dir / "summary.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("SBIR TRANSITION DETECTION EVIDENCE\n")
            f.write("=" * 50 + "\n\n")
            
            # Detection overview
            f.write(f"Detection ID: {detection.id}\n")
            f.write(f"Confidence Level: {detection.confidence}\n")
            f.write(f"Likelihood Score: {detection.likelihood_score:.3f}\n")
            f.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            
            # SBIR award details
            f.write("SBIR AWARD DETAILS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Award PIID: {detection.sbir_award.award_piid}\n")
            f.write(f"Phase: {detection.sbir_award.phase}\n")
            f.write(f"Agency: {detection.sbir_award.agency}\n")
            f.write(f"Award Date: {detection.sbir_award.award_date.strftime('%Y-%m-%d')}\n")
            f.write(f"Completion Date: {detection.sbir_award.completion_date.strftime('%Y-%m-%d')}\n")
            f.write(f"Research Topic: {detection.sbir_award.topic}\n\n")
            
            # Contract details
            f.write("CONTRACT DETAILS\n")
            f.write("-" * 17 + "\n")
            f.write(f"Contract PIID: {detection.contract.piid}\n")
            if detection.contract.parent_piid:
                f.write(f"Parent PIID: {detection.contract.parent_piid}\n")
            f.write(f"Agency: {detection.contract.agency}\n")
            f.write(f"Start Date: {detection.contract.start_date.strftime('%Y-%m-%d')}\n")
            f.write(f"NAICS Code: {detection.contract.naics_code}\n")
            f.write(f"PSC Code: {detection.contract.psc_code}\n\n")
            
            # Transition analysis
            f.write("TRANSITION ANALYSIS\n")
            f.write("-" * 19 + "\n")
            
            days_diff = (detection.contract.start_date - detection.sbir_award.completion_date).days
            f.write(f"Time Gap: {days_diff} days after SBIR completion\n")
            
            agency_match = detection.sbir_award.agency == detection.contract.agency
            f.write(f"Agency Continuity: {'Yes' if agency_match else 'No'}\n")
            
            # Evidence details
            if detection.evidence_bundle:
                f.write("\nEVIDENCE DETAILS\n")
                f.write("-" * 16 + "\n")
                
                scoring = detection.evidence_bundle.get('scoring_components', {})
                if scoring:
                    f.write(f"Sole Source Contract: {'Yes' if scoring.get('sole_source') else 'No'}\n")
                    f.write(f"Timing Score: {scoring.get('timing_score', 0):.3f}\n")
                    if scoring.get('text_similarity') is not None:
                        f.write(f"Text Similarity: {scoring.get('text_similarity', 0):.3f}\n")
            
            # Risk assessment
            risk_factors = self._assess_risk_factors(detection)
            if risk_factors:
                f.write("\nRISK ASSESSMENT\n")
                f.write("-" * 15 + "\n")
                for risk in risk_factors:
                    f.write(f"• {risk}\n")
            
            # Validation checklist
            f.write("\nVALIDATION CHECKLIST\n")
            f.write("-" * 20 + "\n")
            checklist = self._create_validation_checklist(detection)
            for item in checklist:
                status = "✓" if item['status'] else "○"
                f.write(f"{status} {item['description']}\n")
        
        return summary_file
    
    def _create_source_links(self, detection: Detection, detection_dir: Path):
        """Create links to source documents."""
        sources_dir = detection_dir / "sources"
        sources_dir.mkdir(exist_ok=True)
        
        # Create reference files (not actual copies to save space)
        sbir_ref = sources_dir / "sbir_award_reference.txt"
        with open(sbir_ref, 'w') as f:
            f.write(f"SBIR Award Reference\n")
            f.write(f"PIID: {detection.sbir_award.award_piid}\n")
            f.write(f"Agency: {detection.sbir_award.agency}\n")
            f.write(f"Phase: {detection.sbir_award.phase}\n")
            f.write(f"Original Data Source: {self.session.input_datasets}\n")
        
        contract_ref = sources_dir / "contract_reference.txt"
        with open(contract_ref, 'w') as f:
            f.write(f"Contract Reference\n")
            f.write(f"PIID: {detection.contract.piid}\n")
            f.write(f"Agency: {detection.contract.agency}\n")
            f.write(f"Start Date: {detection.contract.start_date.strftime('%Y-%m-%d')}\n")
            f.write(f"Original Data Source: {self.session.input_datasets}\n")
    
    def _classify_evidence_type(self, detection: Detection) -> EvidenceType:
        """Classify evidence type based on detection characteristics."""
        if detection.confidence == "High Confidence":
            return EvidenceType.HIGH_CONFIDENCE
        elif detection.sbir_award.agency != detection.contract.agency:
            return EvidenceType.CROSS_SERVICE
        else:
            return EvidenceType.LIKELY_TRANSITION
    
    def _analyze_transition(self, detection: Detection) -> Dict[str, Any]:
        """Analyze transition characteristics."""
        days_diff = (detection.contract.start_date - detection.sbir_award.completion_date).days
        
        return {
            "timing_analysis": {
                "days_after_completion": days_diff,
                "timing_category": self._categorize_timing(days_diff),
                "within_typical_range": 30 <= days_diff <= 730  # 1 month to 2 years
            },
            "agency_analysis": {
                "same_agency": detection.sbir_award.agency == detection.contract.agency,
                "sbir_agency": detection.sbir_award.agency,
                "contract_agency": detection.contract.agency
            },
            "contract_characteristics": {
                "has_parent_piid": bool(detection.contract.parent_piid),
                "naics_code": detection.contract.naics_code,
                "psc_code": detection.contract.psc_code
            }
        }
    
    def _categorize_timing(self, days: int) -> str:
        """Categorize timing gap."""
        if days < 0:
            return "Before SBIR completion"
        elif days <= 90:
            return "Immediate (0-3 months)"
        elif days <= 365:
            return "Short-term (3-12 months)"
        elif days <= 730:
            return "Medium-term (1-2 years)"
        else:
            return "Long-term (>2 years)"
    
    def _assess_risk_factors(self, detection: Detection) -> List[str]:
        """Assess potential risk factors for false positives."""
        risks = []
        
        # Timing risks
        days_diff = (detection.contract.start_date - detection.sbir_award.completion_date).days
        if days_diff < 30:
            risks.append("Very short gap between SBIR completion and contract start")
        elif days_diff > 1095:  # 3 years
            risks.append("Long gap between SBIR completion and contract start")
        
        # Agency risks
        if detection.sbir_award.agency != detection.contract.agency:
            risks.append("Cross-agency transition (requires additional validation)")
        
        # Score risks
        if detection.likelihood_score < 0.75:
            risks.append("Moderate likelihood score (consider manual review)")
        
        # Data quality risks
        if not detection.sbir_award.topic:
            risks.append("Missing SBIR topic information")
        
        if not detection.contract.naics_code:
            risks.append("Missing contract NAICS code")
        
        return risks
    
    def _create_validation_checklist(self, detection: Detection) -> List[Dict[str, Any]]:
        """Create validation checklist for manual review."""
        checklist = []
        
        # Basic data validation
        checklist.append({
            "description": "SBIR award has completion date",
            "status": bool(detection.sbir_award.completion_date),
            "category": "data_quality"
        })
        
        checklist.append({
            "description": "Contract has start date",
            "status": bool(detection.contract.start_date),
            "category": "data_quality"
        })
        
        # Timing validation
        days_diff = (detection.contract.start_date - detection.sbir_award.completion_date).days
        checklist.append({
            "description": "Contract starts after SBIR completion",
            "status": days_diff > 0,
            "category": "timing"
        })
        
        checklist.append({
            "description": "Timing gap is reasonable (30 days - 3 years)",
            "status": 30 <= days_diff <= 1095,
            "category": "timing"
        })
        
        # Agency validation
        checklist.append({
            "description": "Agency information available for both records",
            "status": bool(detection.sbir_award.agency and detection.contract.agency),
            "category": "agency"
        })
        
        # Score validation
        checklist.append({
            "description": "Likelihood score meets threshold",
            "status": detection.likelihood_score >= 0.65,  # Assuming minimum threshold
            "category": "scoring"
        })
        
        return checklist
