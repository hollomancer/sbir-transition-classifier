"""Local offline detection service."""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from loguru import logger
import pandas as pd

from ..config.schema import ConfigSchema
from ..data.models import DetectionSession, SessionStatus
from ..data.schemas import Detection, SbirAward, Contract


class LocalDetectionService:
    """Handles offline SBIR transition detection."""
    
    def __init__(self, config: ConfigSchema, session: DetectionSession):
        self.config = config
        self.session = session
        self.sbir_awards: List[Dict[str, Any]] = []
        self.contracts: List[Dict[str, Any]] = []
    
    def run_detection(self) -> List[Detection]:
        """
        Execute complete detection workflow.
        
        Returns:
            List of detected transitions
        """
        try:
            logger.info("Starting local detection workflow")
            
            # Load data
            self._load_data()
            
            # Run detection algorithm
            detections = self._detect_transitions()
            
            logger.info(f"Detection workflow completed. Found {len(detections)} transitions.")
            return detections
            
        except Exception as e:
            logger.error(f"Detection workflow failed: {e}")
            self.session.status = SessionStatus.FAILED
            self.session.error_message = str(e)
            raise
    
    def _load_data(self):
        """Load SBIR awards and contracts data."""
        logger.info("Loading input datasets")
        
        for dataset_path in self.session.input_datasets:
            path = Path(dataset_path)
            
            if not path.exists():
                logger.warning(f"Dataset file not found: {path}")
                continue
            
            try:
                if 'sbir' in path.name.lower() or 'award' in path.name.lower():
                    self._load_sbir_data(path)
                elif 'contract' in path.name.lower() or 'fpds' in path.name.lower():
                    self._load_contract_data(path)
                else:
                    logger.info(f"Skipping unknown dataset: {path.name}")
                    
            except Exception as e:
                logger.error(f"Failed to load dataset {path}: {e}")
        
        logger.info(f"Loaded {len(self.sbir_awards)} SBIR awards and {len(self.contracts)} contracts")
    
    def _load_sbir_data(self, path: Path):
        """Load SBIR awards data from file."""
        logger.info(f"Loading SBIR data from {path}")
        
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(path)
        elif path.suffix.lower() in ['.json', '.jsonl']:
            df = pd.read_json(path, lines=path.suffix == '.jsonl')
        else:
            logger.warning(f"Unsupported file format: {path.suffix}")
            return
        
        # Convert to standard format
        for _, row in df.iterrows():
            award = {
                'id': str(uuid.uuid4()),
                'award_piid': row.get('piid', row.get('award_piid', '')),
                'phase': row.get('phase', ''),
                'agency': row.get('agency', ''),
                'award_date': pd.to_datetime(row.get('award_date', '')),
                'completion_date': pd.to_datetime(row.get('completion_date', '')),
                'topic': row.get('topic', ''),
                'vendor_name': row.get('vendor_name', ''),
                'raw_data': row.to_dict()
            }
            self.sbir_awards.append(award)
    
    def _load_contract_data(self, path: Path):
        """Load contracts data from file."""
        logger.info(f"Loading contract data from {path}")
        
        if path.suffix.lower() == '.csv':
            df = pd.read_csv(path)
        elif path.suffix.lower() in ['.json', '.jsonl']:
            df = pd.read_json(path, lines=path.suffix == '.jsonl')
        else:
            logger.warning(f"Unsupported file format: {path.suffix}")
            return
        
        # Convert to standard format
        for _, row in df.iterrows():
            contract = {
                'id': str(uuid.uuid4()),
                'piid': row.get('piid', ''),
                'parent_piid': row.get('parent_piid', ''),
                'agency': row.get('agency', ''),
                'start_date': pd.to_datetime(row.get('start_date', '')),
                'naics_code': row.get('naics_code', ''),
                'psc_code': row.get('psc_code', ''),
                'vendor_name': row.get('vendor_name', ''),
                'competition_details': row.get('competition_details', {}),
                'raw_data': row.to_dict()
            }
            self.contracts.append(contract)
    
    def _detect_transitions(self) -> List[Detection]:
        """Run transition detection algorithm."""
        logger.info("Running transition detection algorithm")
        
        detections = []
        
        # Filter to Phase II awards only
        phase2_awards = [a for a in self.sbir_awards if a.get('phase') == 'II']
        logger.info(f"Processing {len(phase2_awards)} Phase II awards")
        
        for award in phase2_awards:
            award_detections = self._find_transitions_for_award(award)
            detections.extend(award_detections)
        
        return detections
    
    def _find_transitions_for_award(self, award: Dict[str, Any]) -> List[Detection]:
        """Find potential transitions for a specific SBIR award."""
        detections = []
        
        # Calculate search window
        completion_date = award['completion_date']
        if pd.isna(completion_date):
            return detections
        
        min_date = completion_date + timedelta(days=30 * self.config.detection.timing.min_months_after_phase2)
        max_date = completion_date + timedelta(days=30 * self.config.detection.timing.max_months_after_phase2)
        
        # Find matching contracts
        for contract in self.contracts:
            if pd.isna(contract['start_date']):
                continue
            
            # Check timing window
            if not (min_date <= contract['start_date'] <= max_date):
                continue
            
            # Check vendor match (simplified - would need proper vendor matching)
            if not self._vendors_match(award, contract):
                continue
            
            # Calculate likelihood score
            score = self._calculate_likelihood_score(award, contract)
            
            # Check if meets threshold
            if score >= self.config.detection.thresholds.likely_transition:
                confidence = "High Confidence" if score >= self.config.detection.thresholds.high_confidence else "Likely Transition"
                
                detection = Detection(
                    id=uuid.uuid4(),
                    sbir_award=self._create_sbir_award_obj(award),
                    contract=self._create_contract_obj(contract),
                    likelihood_score=score,
                    confidence=confidence,
                    evidence_bundle=self._create_evidence_bundle(award, contract, score)
                )
                
                detections.append(detection)
        
        return detections
    
    def _vendors_match(self, award: Dict[str, Any], contract: Dict[str, Any]) -> bool:
        """Check if vendors match between award and contract."""
        # Simplified vendor matching - in real implementation would use proper vendor resolution
        award_vendor = award.get('vendor_name', '').lower().strip()
        contract_vendor = contract.get('vendor_name', '').lower().strip()
        
        if not award_vendor or not contract_vendor:
            return False
        
        # Simple name matching
        return award_vendor == contract_vendor
    
    def _calculate_likelihood_score(self, award: Dict[str, Any], contract: Dict[str, Any]) -> float:
        """Calculate likelihood score for potential transition."""
        score = 0.0
        
        # Base score
        score += 0.3
        
        # Agency continuity
        if award.get('agency', '').lower() == contract.get('agency', '').lower():
            score += self.config.detection.weights.agency_continuity
        
        # Sole source bonus
        competition = contract.get('competition_details', {})
        if isinstance(competition, dict) and competition.get('sole_source', False):
            score += self.config.detection.weights.sole_source_bonus
        
        # Timing proximity (closer to completion = higher score)
        completion_date = award['completion_date']
        start_date = contract['start_date']
        days_diff = (start_date - completion_date).days
        
        if days_diff <= 365:  # Within 1 year
            timing_bonus = self.config.detection.weights.timing_weight * (1 - days_diff / 365)
            score += timing_bonus
        
        # Text similarity (if enabled)
        if self.config.detection.features.enable_text_analysis:
            text_score = self._calculate_text_similarity(award, contract)
            score += text_score * self.config.detection.weights.text_similarity
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_text_similarity(self, award: Dict[str, Any], contract: Dict[str, Any]) -> float:
        """Calculate text similarity between award and contract descriptions."""
        # Simplified text similarity - would use proper NLP in real implementation
        award_topic = award.get('topic', '').lower()
        contract_desc = str(contract.get('raw_data', {}).get('description', '')).lower()
        
        if not award_topic or not contract_desc:
            return 0.0
        
        # Simple keyword overlap
        award_words = set(award_topic.split())
        contract_words = set(contract_desc.split())
        
        if not award_words:
            return 0.0
        
        overlap = len(award_words.intersection(contract_words))
        return overlap / len(award_words)
    
    def _create_sbir_award_obj(self, award: Dict[str, Any]) -> SbirAward:
        """Create SbirAward object from dictionary."""
        return SbirAward(
            id=uuid.UUID(award['id']),
            vendor_id=uuid.uuid4(),  # Placeholder
            award_piid=award['award_piid'],
            phase=award['phase'],
            agency=award['agency'],
            award_date=award['award_date'],
            completion_date=award['completion_date'],
            topic=award['topic'],
            raw_data=award['raw_data'],
            created_at=datetime.utcnow()
        )
    
    def _create_contract_obj(self, contract: Dict[str, Any]) -> Contract:
        """Create Contract object from dictionary."""
        return Contract(
            id=uuid.UUID(contract['id']),
            vendor_id=uuid.uuid4(),  # Placeholder
            piid=contract['piid'],
            parent_piid=contract.get('parent_piid'),
            agency=contract['agency'],
            start_date=contract['start_date'],
            naics_code=contract.get('naics_code', ''),
            psc_code=contract.get('psc_code', ''),
            competition_details=contract.get('competition_details'),
            raw_data=contract['raw_data'],
            created_at=datetime.utcnow()
        )
    
    def _create_evidence_bundle(self, award: Dict[str, Any], contract: Dict[str, Any], score: float) -> Dict[str, Any]:
        """Create evidence bundle for detection."""
        return {
            'score': score,
            'award_completion': award['completion_date'].isoformat() if pd.notna(award['completion_date']) else None,
            'contract_start': contract['start_date'].isoformat() if pd.notna(contract['start_date']) else None,
            'agency_match': award.get('agency') == contract.get('agency'),
            'timing_days': (contract['start_date'] - award['completion_date']).days if pd.notna(award['completion_date']) and pd.notna(contract['start_date']) else None,
            'vendor_match_method': 'name_exact',
            'config_version': self.config.schema_version
        }
