"""Output file generation for detection results."""

import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

from loguru import logger

from ..config.schema import ConfigSchema
from ..data.models import DetectionSession
from ..data.schemas import Detection


class OutputGenerator:
    """Generates output files from detection results."""
    
    def __init__(self, config: ConfigSchema, session: DetectionSession):
        self.config = config
        self.session = session
    
    def generate_outputs(self, detections: List[Detection], output_dir: Path) -> List[Path]:
        """
        Generate all configured output formats.
        
        Args:
            detections: List of detection results
            output_dir: Directory to write output files
            
        Returns:
            List of generated file paths
        """
        output_files = []
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate each requested format
        for format_type in self.config.output.formats:
            try:
                if format_type == "jsonl":
                    file_path = self._generate_jsonl(detections, output_dir)
                elif format_type == "csv":
                    file_path = self._generate_csv(detections, output_dir)
                elif format_type == "excel":
                    file_path = self._generate_excel(detections, output_dir)
                else:
                    logger.warning(f"Unknown output format: {format_type}")
                    continue
                
                output_files.append(file_path)
                logger.info(f"Generated {format_type} output: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate {format_type} output: {e}")
        
        # Generate summary report
        summary_path = self._generate_summary(detections, output_dir)
        output_files.append(summary_path)
        
        # Generate evidence bundles if requested
        if self.config.output.include_evidence:
            from ..data.evidence import EvidenceBundleGenerator
            
            evidence_gen = EvidenceBundleGenerator(self.session)
            evidence_artifacts = evidence_gen.generate_evidence_bundles(detections, output_dir)
            
            if evidence_artifacts:
                evidence_dir = output_dir / "evidence"
                output_files.append(evidence_dir)
                logger.info(f"Generated {len(evidence_artifacts)} evidence bundles")
        
        return output_files
    
    def _generate_jsonl(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate JSONL output file."""
        file_path = output_dir / "detections.jsonl"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for detection in detections:
                record = {
                    'detection_id': str(detection.id),
                    'session_id': str(self.session.session_id),
                    'likelihood_score': detection.likelihood_score,
                    'confidence': detection.confidence,
                    'sbir_award': {
                        'piid': detection.sbir_award.award_piid,
                        'phase': detection.sbir_award.phase,
                        'agency': detection.sbir_award.agency,
                        'completion_date': detection.sbir_award.completion_date.isoformat(),
                        'topic': detection.sbir_award.topic
                    },
                    'contract': {
                        'piid': detection.contract.piid,
                        'agency': detection.contract.agency,
                        'start_date': detection.contract.start_date.isoformat(),
                        'naics_code': detection.contract.naics_code,
                        'psc_code': detection.contract.psc_code
                    },
                    'evidence_bundle': detection.evidence_bundle,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                f.write(json.dumps(record) + '\n')
        
        return file_path
    
    def _generate_csv(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate CSV output file."""
        file_path = output_dir / "detections.csv"
        
        # Flatten detection data for CSV
        records = []
        for detection in detections:
            record = {
                'detection_id': str(detection.id),
                'session_id': str(self.session.session_id),
                'likelihood_score': detection.likelihood_score,
                'confidence': detection.confidence,
                'sbir_piid': detection.sbir_award.award_piid,
                'sbir_phase': detection.sbir_award.phase,
                'sbir_agency': detection.sbir_award.agency,
                'sbir_completion_date': detection.sbir_award.completion_date.isoformat(),
                'sbir_topic': detection.sbir_award.topic,
                'contract_piid': detection.contract.piid,
                'contract_agency': detection.contract.agency,
                'contract_start_date': detection.contract.start_date.isoformat(),
                'contract_naics_code': detection.contract.naics_code,
                'contract_psc_code': detection.contract.psc_code,
                'agency_match': detection.sbir_award.agency == detection.contract.agency,
                'timing_days': (detection.contract.start_date - detection.sbir_award.completion_date).days,
                'created_at': datetime.utcnow().isoformat()
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        df.to_csv(file_path, index=False)
        
        return file_path
    
    def _generate_excel(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate Excel output file with multiple sheets."""
        file_path = output_dir / "detections.xlsx"
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Main detections sheet
            records = []
            for detection in detections:
                record = {
                    'Detection ID': str(detection.id),
                    'Likelihood Score': detection.likelihood_score,
                    'Confidence': detection.confidence,
                    'SBIR PIID': detection.sbir_award.award_piid,
                    'SBIR Phase': detection.sbir_award.phase,
                    'SBIR Agency': detection.sbir_award.agency,
                    'SBIR Completion': detection.sbir_award.completion_date.strftime('%Y-%m-%d'),
                    'Contract PIID': detection.contract.piid,
                    'Contract Agency': detection.contract.agency,
                    'Contract Start': detection.contract.start_date.strftime('%Y-%m-%d'),
                    'Agency Match': detection.sbir_award.agency == detection.contract.agency,
                    'Days After Completion': (detection.contract.start_date - detection.sbir_award.completion_date).days
                }
                records.append(record)
            
            df = pd.DataFrame(records)
            df.to_excel(writer, sheet_name='Detections', index=False)
            
            # Summary statistics sheet
            summary_data = self._calculate_summary_stats(detections)
            summary_df = pd.DataFrame(list(summary_data.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return file_path
    
    def _generate_summary(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate summary report."""
        file_path = output_dir / "summary.txt"
        
        stats = self._calculate_summary_stats(detections)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("SBIR Transition Detection Summary Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Session ID: {self.session.session_id}\n")
            f.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            f.write(f"Configuration: {self.session.config_used}\n\n")
            
            f.write("Detection Results:\n")
            f.write("-" * 20 + "\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")
            
            f.write("\nConfiguration Parameters:\n")
            f.write("-" * 25 + "\n")
            f.write(f"High Confidence Threshold: {self.config.detection.thresholds.high_confidence}\n")
            f.write(f"Likely Transition Threshold: {self.config.detection.thresholds.likely_transition}\n")
            f.write(f"Search Window: {self.config.detection.timing.min_months_after_phase2}-{self.config.detection.timing.max_months_after_phase2} months\n")
            f.write(f"Cross-Service Detection: {self.config.detection.features.enable_cross_service}\n")
            f.write(f"Text Analysis: {self.config.detection.features.enable_text_analysis}\n")
        
        return file_path
    
    def _generate_evidence_bundles(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate evidence bundle files."""
        evidence_dir = output_dir / "evidence"
        evidence_dir.mkdir(exist_ok=True)
        
        for detection in detections:
            detection_dir = evidence_dir / str(detection.id)
            detection_dir.mkdir(exist_ok=True)
            
            # Full evidence JSON
            evidence_file = detection_dir / "evidence.json"
            with open(evidence_file, 'w', encoding='utf-8') as f:
                evidence_data = {
                    'detection_id': str(detection.id),
                    'likelihood_score': detection.likelihood_score,
                    'confidence': detection.confidence,
                    'sbir_award': detection.sbir_award.dict(),
                    'contract': detection.contract.dict(),
                    'evidence_bundle': detection.evidence_bundle,
                    'session_metadata': {
                        'session_id': str(self.session.session_id),
                        'config_used': self.session.config_used,
                        'config_checksum': self.session.config_checksum
                    }
                }
                json.dump(evidence_data, f, indent=2, default=str)
            
            # Human-readable summary
            if self.config.output.evidence_detail_level == "full":
                summary_file = detection_dir / "summary.txt"
                self._write_evidence_summary(detection, summary_file)
        
        return evidence_dir
    
    def _write_evidence_summary(self, detection: Detection, file_path: Path):
        """Write human-readable evidence summary."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Detection Evidence Summary\n")
            f.write("=" * 30 + "\n\n")
            
            f.write(f"Detection ID: {detection.id}\n")
            f.write(f"Likelihood Score: {detection.likelihood_score:.3f}\n")
            f.write(f"Confidence Level: {detection.confidence}\n\n")
            
            f.write("SBIR Award Details:\n")
            f.write("-" * 20 + "\n")
            f.write(f"PIID: {detection.sbir_award.award_piid}\n")
            f.write(f"Phase: {detection.sbir_award.phase}\n")
            f.write(f"Agency: {detection.sbir_award.agency}\n")
            f.write(f"Completion Date: {detection.sbir_award.completion_date.strftime('%Y-%m-%d')}\n")
            f.write(f"Topic: {detection.sbir_award.topic}\n\n")
            
            f.write("Contract Details:\n")
            f.write("-" * 17 + "\n")
            f.write(f"PIID: {detection.contract.piid}\n")
            f.write(f"Agency: {detection.contract.agency}\n")
            f.write(f"Start Date: {detection.contract.start_date.strftime('%Y-%m-%d')}\n")
            f.write(f"NAICS Code: {detection.contract.naics_code}\n")
            f.write(f"PSC Code: {detection.contract.psc_code}\n\n")
            
            f.write("Evidence Analysis:\n")
            f.write("-" * 18 + "\n")
            days_diff = (detection.contract.start_date - detection.sbir_award.completion_date).days
            f.write(f"Time Gap: {days_diff} days after SBIR completion\n")
            f.write(f"Agency Match: {'Yes' if detection.sbir_award.agency == detection.contract.agency else 'No'}\n")
            
            if detection.evidence_bundle:
                for key, value in detection.evidence_bundle.items():
                    if key not in ['score']:
                        f.write(f"{key.replace('_', ' ').title()}: {value}\n")
    
    def _calculate_summary_stats(self, detections: List[Detection]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not detections:
            return {
                'Total Detections': 0,
                'High Confidence': 0,
                'Likely Transitions': 0,
                'Average Score': 0.0
            }
        
        high_confidence = sum(1 for d in detections if d.confidence == "High Confidence")
        likely_transitions = len(detections) - high_confidence
        avg_score = sum(d.likelihood_score for d in detections) / len(detections)
        
        # Agency analysis
        same_agency = sum(1 for d in detections if d.sbir_award.agency == d.contract.agency)
        
        return {
            'Total Detections': len(detections),
            'High Confidence': high_confidence,
            'Likely Transitions': likely_transitions,
            'Average Score': round(avg_score, 3),
            'Same Agency Transitions': same_agency,
            'Cross-Agency Transitions': len(detections) - same_agency
        }
