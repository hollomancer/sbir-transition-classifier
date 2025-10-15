"""CLI evidence viewer for local file-based evidence review."""

import json
from pathlib import Path
from typing import List, Dict, Any

import click
from loguru import logger


@click.command()
@click.option(
    '--evidence-dir', '-e',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to evidence directory'
)
@click.option(
    '--detection-id', '-d',
    help='Specific detection ID to view (optional)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['summary', 'full', 'json']),
    default='summary',
    help='Output format'
)
@click.option(
    '--confidence', '-c',
    type=click.Choice(['High Confidence', 'Likely Transition']),
    help='Filter by confidence level'
)
def view_evidence(evidence_dir: Path, detection_id: str, format: str, confidence: str):
    """View evidence bundles from local files."""
    
    try:
        viewer = EvidenceViewer(evidence_dir)
        
        if detection_id:
            # View specific detection
            viewer.view_single_detection(detection_id, format)
        else:
            # List all detections
            viewer.list_detections(confidence, format)
    
    except Exception as e:
        logger.error(f"Evidence viewing failed: {e}")
        raise click.ClickException(f"Failed to view evidence: {e}")


@click.command()
@click.option(
    '--evidence-dir', '-e',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to evidence directory'
)
def list_evidence(evidence_dir: Path):
    """List all available evidence bundles."""
    
    try:
        viewer = EvidenceViewer(evidence_dir)
        detections = viewer.discover_evidence_bundles()
        
        if not detections:
            click.echo("No evidence bundles found.")
            return
        
        click.echo(f"Found {len(detections)} evidence bundles:\n")
        
        # Group by confidence
        high_confidence = [d for d in detections if d.get('confidence') == 'High Confidence']
        likely_transitions = [d for d in detections if d.get('confidence') == 'Likely Transition']
        
        if high_confidence:
            click.echo(f"High Confidence ({len(high_confidence)}):")
            for detection in high_confidence:
                click.echo(f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}")
        
        if likely_transitions:
            click.echo(f"\nLikely Transitions ({len(likely_transitions)}):")
            for detection in likely_transitions:
                click.echo(f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}")
        
        click.echo(f"\nUse 'sbir-detect view-evidence --detection-id <id>' to view details")
    
    except Exception as e:
        logger.error(f"Evidence listing failed: {e}")
        raise click.ClickException(f"Failed to list evidence: {e}")


@click.command()
@click.option(
    '--evidence-dir', '-e',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to evidence directory'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file for report (optional, prints to stdout if not specified)'
)
def evidence_report(evidence_dir: Path, output: Path):
    """Generate comprehensive evidence report."""
    
    try:
        viewer = EvidenceViewer(evidence_dir)
        report = viewer.generate_report()
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report)
            click.echo(f"Evidence report written to: {output}")
        else:
            click.echo(report)
    
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise click.ClickException(f"Failed to generate report: {e}")


class EvidenceViewer:
    """Local file-based evidence viewer."""
    
    def __init__(self, evidence_dir: Path):
        self.evidence_dir = evidence_dir
    
    def discover_evidence_bundles(self) -> List[Dict[str, Any]]:
        """Discover all evidence bundles in directory."""
        detections = []
        
        for detection_dir in self.evidence_dir.iterdir():
            if not detection_dir.is_dir():
                continue
            
            evidence_file = detection_dir / "evidence.json"
            if not evidence_file.exists():
                continue
            
            try:
                with open(evidence_file, 'r', encoding='utf-8') as f:
                    evidence_data = json.load(f)
                
                detection_info = {
                    'detection_id': evidence_data['detection_metadata']['detection_id'],
                    'likelihood_score': evidence_data['detection_metadata']['likelihood_score'],
                    'confidence': evidence_data['detection_metadata']['confidence'],
                    'sbir_piid': evidence_data['sbir_award']['piid'],
                    'contract_piid': evidence_data['contract']['piid'],
                    'evidence_dir': detection_dir
                }
                
                detections.append(detection_info)
                
            except Exception as e:
                logger.warning(f"Failed to read evidence from {detection_dir}: {e}")
        
        return sorted(detections, key=lambda x: x['likelihood_score'], reverse=True)
    
    def view_single_detection(self, detection_id: str, format: str):
        """View details for a specific detection."""
        # Find detection directory
        detection_dir = None
        
        for dir_path in self.evidence_dir.iterdir():
            if dir_path.is_dir() and detection_id in str(dir_path.name):
                detection_dir = dir_path
                break
        
        if not detection_dir:
            raise click.ClickException(f"Detection not found: {detection_id}")
        
        if format == 'summary':
            self._show_summary(detection_dir)
        elif format == 'full':
            self._show_full_details(detection_dir)
        elif format == 'json':
            self._show_json(detection_dir)
    
    def list_detections(self, confidence_filter: str, format: str):
        """List all detections with optional filtering."""
        detections = self.discover_evidence_bundles()
        
        if confidence_filter:
            detections = [d for d in detections if d['confidence'] == confidence_filter]
        
        if not detections:
            click.echo("No detections found matching criteria.")
            return
        
        if format == 'summary':
            self._list_summary(detections)
        elif format == 'full':
            for detection in detections:
                self._show_full_details(detection['evidence_dir'])
                click.echo("-" * 80)
        elif format == 'json':
            click.echo(json.dumps(detections, indent=2, default=str))
    
    def _show_summary(self, detection_dir: Path):
        """Show summary view of detection."""
        summary_file = detection_dir / "summary.txt"
        
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                click.echo(f.read())
        else:
            # Fallback to JSON summary
            evidence_file = detection_dir / "evidence.json"
            with open(evidence_file, 'r', encoding='utf-8') as f:
                evidence_data = json.load(f)
            
            self._print_json_summary(evidence_data)
    
    def _show_full_details(self, detection_dir: Path):
        """Show full details of detection."""
        evidence_file = detection_dir / "evidence.json"
        
        with open(evidence_file, 'r', encoding='utf-8') as f:
            evidence_data = json.load(f)
        
        # Print structured view
        click.echo("DETECTION DETAILS")
        click.echo("=" * 50)
        
        metadata = evidence_data['detection_metadata']
        click.echo(f"Detection ID: {metadata['detection_id']}")
        click.echo(f"Confidence: {metadata['confidence']}")
        click.echo(f"Score: {metadata['likelihood_score']:.3f}")
        click.echo(f"Created: {metadata['created_at']}")
        click.echo()
        
        # SBIR Award
        sbir = evidence_data['sbir_award']
        click.echo("SBIR AWARD:")
        click.echo(f"  PIID: {sbir['piid']}")
        click.echo(f"  Phase: {sbir['phase']}")
        click.echo(f"  Agency: {sbir['agency']}")
        click.echo(f"  Completion: {sbir['completion_date']}")
        click.echo(f"  Topic: {sbir['topic']}")
        click.echo()
        
        # Contract
        contract = evidence_data['contract']
        click.echo("CONTRACT:")
        click.echo(f"  PIID: {contract['piid']}")
        click.echo(f"  Agency: {contract['agency']}")
        click.echo(f"  Start Date: {contract['start_date']}")
        click.echo(f"  NAICS: {contract['naics_code']}")
        click.echo(f"  PSC: {contract['psc_code']}")
        click.echo()
        
        # Analysis
        analysis = evidence_data['analysis']
        click.echo("ANALYSIS:")
        
        transition = analysis.get('transition_analysis', {})
        if transition:
            timing = transition.get('timing_analysis', {})
            click.echo(f"  Days after completion: {timing.get('days_after_completion')}")
            click.echo(f"  Timing category: {timing.get('timing_category')}")
            
            agency = transition.get('agency_analysis', {})
            click.echo(f"  Same agency: {agency.get('same_agency')}")
        
        # Risk factors
        risks = analysis.get('risk_assessment', [])
        if risks:
            click.echo("\nRISK FACTORS:")
            for risk in risks:
                click.echo(f"  • {risk}")
    
    def _show_json(self, detection_dir: Path):
        """Show raw JSON data."""
        evidence_file = detection_dir / "evidence.json"
        
        with open(evidence_file, 'r', encoding='utf-8') as f:
            evidence_data = json.load(f)
        
        click.echo(json.dumps(evidence_data, indent=2, default=str))
    
    def _list_summary(self, detections: List[Dict[str, Any]]):
        """Show summary list of detections."""
        click.echo(f"{'ID':<10} {'Score':<6} {'Confidence':<15} {'SBIR PIID':<15} {'Contract PIID':<15}")
        click.echo("-" * 80)
        
        for detection in detections:
            click.echo(
                f"{detection['detection_id'][:8]:<10} "
                f"{detection['likelihood_score']:<6.3f} "
                f"{detection['confidence']:<15} "
                f"{detection['sbir_piid']:<15} "
                f"{detection['contract_piid']:<15}"
            )
    
    def _print_json_summary(self, evidence_data: Dict[str, Any]):
        """Print summary from JSON data."""
        metadata = evidence_data['detection_metadata']
        sbir = evidence_data['sbir_award']
        contract = evidence_data['contract']
        
        click.echo(f"Detection: {metadata['detection_id']}")
        click.echo(f"Confidence: {metadata['confidence']} (Score: {metadata['likelihood_score']:.3f})")
        click.echo(f"SBIR: {sbir['piid']} ({sbir['agency']})")
        click.echo(f"Contract: {contract['piid']} ({contract['agency']})")
    
    def generate_report(self) -> str:
        """Generate comprehensive evidence report."""
        detections = self.discover_evidence_bundles()
        
        report_lines = []
        report_lines.append("SBIR TRANSITION DETECTION EVIDENCE REPORT")
        report_lines.append("=" * 60)
        report_lines.append(f"Generated: {click.get_current_context().obj or 'Unknown'}")
        report_lines.append(f"Total Detections: {len(detections)}")
        report_lines.append("")
        
        # Summary statistics
        high_confidence = [d for d in detections if d['confidence'] == 'High Confidence']
        likely_transitions = [d for d in detections if d['confidence'] == 'Likely Transition']
        
        report_lines.append("SUMMARY STATISTICS")
        report_lines.append("-" * 20)
        report_lines.append(f"High Confidence: {len(high_confidence)}")
        report_lines.append(f"Likely Transitions: {len(likely_transitions)}")
        
        if detections:
            avg_score = sum(d['likelihood_score'] for d in detections) / len(detections)
            report_lines.append(f"Average Score: {avg_score:.3f}")
        
        report_lines.append("")
        
        # Detailed listings
        if high_confidence:
            report_lines.append("HIGH CONFIDENCE DETECTIONS")
            report_lines.append("-" * 30)
            for detection in high_confidence:
                report_lines.append(f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}")
                report_lines.append(f"    SBIR: {detection['sbir_piid']}")
                report_lines.append(f"    Contract: {detection['contract_piid']}")
                report_lines.append("")
        
        if likely_transitions:
            report_lines.append("LIKELY TRANSITIONS")
            report_lines.append("-" * 20)
            for detection in likely_transitions:
                report_lines.append(f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}")
                report_lines.append(f"    SBIR: {detection['sbir_piid']}")
                report_lines.append(f"    Contract: {detection['contract_piid']}")
                report_lines.append("")
        
        return "\n".join(report_lines)
