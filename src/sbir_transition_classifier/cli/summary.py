"""CLI summary report generation for detection results."""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import click
from loguru import logger


@click.command()
@click.option(
    '--results-dir', '-r',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to results directory containing detection outputs'
)
@click.option(
    '--output', '-o',
    type=click.Path(path_type=Path),
    help='Output file for summary report (prints to stdout if not specified)'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['text', 'markdown', 'json']),
    default='text',
    help='Output format for summary report'
)
@click.option(
    '--include-details',
    is_flag=True,
    help='Include detailed analysis in report'
)
def generate_summary(results_dir: Path, output: Path, format: str, include_details: bool):
    """Generate human-readable summary report from detection results."""
    
    try:
        generator = SummaryReportGenerator(results_dir)
        
        if format == 'text':
            report = generator.generate_text_report(include_details)
        elif format == 'markdown':
            report = generator.generate_markdown_report(include_details)
        elif format == 'json':
            report = generator.generate_json_report()
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                if format == 'json':
                    json.dump(report, f, indent=2, default=str)
                else:
                    f.write(report)
            click.echo(f"Summary report written to: {output}")
        else:
            if format == 'json':
                click.echo(json.dumps(report, indent=2, default=str))
            else:
                click.echo(report)
    
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise click.ClickException(f"Failed to generate summary: {e}")


@click.command()
@click.option(
    '--results-dir', '-r',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to results directory'
)
def quick_stats(results_dir: Path):
    """Show quick statistics from detection results."""
    
    try:
        generator = SummaryReportGenerator(results_dir)
        stats = generator.calculate_statistics()
        
        click.echo("DETECTION STATISTICS")
        click.echo("=" * 25)
        click.echo(f"Total Detections: {stats['total_detections']}")
        click.echo(f"High Confidence: {stats['high_confidence']}")
        click.echo(f"Likely Transitions: {stats['likely_transitions']}")
        
        if stats['total_detections'] > 0:
            click.echo(f"Average Score: {stats['average_score']:.3f}")
            click.echo(f"Same Agency: {stats['same_agency_count']}")
            click.echo(f"Cross Agency: {stats['cross_agency_count']}")
    
    except Exception as e:
        logger.error(f"Statistics calculation failed: {e}")
        raise click.ClickException(f"Failed to calculate statistics: {e}")


class SummaryReportGenerator:
    """Generates human-readable summary reports from detection results."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.detections = self._load_detections()
    
    def _load_detections(self) -> List[Dict[str, Any]]:
        """Load detection results from JSONL file."""
        detections_file = self.results_dir / "detections.jsonl"
        
        if not detections_file.exists():
            raise FileNotFoundError(f"Detections file not found: {detections_file}")
        
        detections = []
        with open(detections_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    detections.append(json.loads(line))
        
        return detections
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not self.detections:
            return {
                'total_detections': 0,
                'high_confidence': 0,
                'likely_transitions': 0,
                'average_score': 0.0,
                'same_agency_count': 0,
                'cross_agency_count': 0
            }
        
        high_confidence = sum(1 for d in self.detections if d['confidence'] == 'High Confidence')
        likely_transitions = len(self.detections) - high_confidence
        
        total_score = sum(d['likelihood_score'] for d in self.detections)
        average_score = total_score / len(self.detections)
        
        same_agency = sum(1 for d in self.detections 
                         if d['sbir_award']['agency'] == d['contract']['agency'])
        cross_agency = len(self.detections) - same_agency
        
        return {
            'total_detections': len(self.detections),
            'high_confidence': high_confidence,
            'likely_transitions': likely_transitions,
            'average_score': average_score,
            'same_agency_count': same_agency,
            'cross_agency_count': cross_agency,
            'score_distribution': self._calculate_score_distribution(),
            'timing_analysis': self._analyze_timing_patterns(),
            'agency_breakdown': self._analyze_agency_patterns()
        }
    
    def generate_text_report(self, include_details: bool = False) -> str:
        """Generate text format summary report."""
        stats = self.calculate_statistics()
        
        lines = []
        lines.append("SBIR TRANSITION DETECTION SUMMARY REPORT")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Results Directory: {self.results_dir}")
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 17)
        lines.append(f"Total Transitions Detected: {stats['total_detections']}")
        lines.append(f"High Confidence Detections: {stats['high_confidence']}")
        lines.append(f"Likely Transitions: {stats['likely_transitions']}")
        
        if stats['total_detections'] > 0:
            lines.append(f"Average Likelihood Score: {stats['average_score']:.3f}")
            
            confidence_rate = (stats['high_confidence'] / stats['total_detections']) * 100
            lines.append(f"High Confidence Rate: {confidence_rate:.1f}%")
        
        lines.append("")
        
        # Agency Analysis
        lines.append("AGENCY ANALYSIS")
        lines.append("-" * 15)
        lines.append(f"Same Agency Transitions: {stats['same_agency_count']}")
        lines.append(f"Cross-Agency Transitions: {stats['cross_agency_count']}")
        
        if stats['total_detections'] > 0:
            same_agency_rate = (stats['same_agency_count'] / stats['total_detections']) * 100
            lines.append(f"Same Agency Rate: {same_agency_rate:.1f}%")
        
        lines.append("")
        
        # Score Distribution
        lines.append("SCORE DISTRIBUTION")
        lines.append("-" * 18)
        score_dist = stats['score_distribution']
        for range_name, count in score_dist.items():
            lines.append(f"{range_name}: {count}")
        
        lines.append("")
        
        # Timing Analysis
        lines.append("TIMING ANALYSIS")
        lines.append("-" * 15)
        timing = stats['timing_analysis']
        for category, count in timing.items():
            lines.append(f"{category}: {count}")
        
        lines.append("")
        
        if include_details:
            lines.extend(self._generate_detailed_analysis())
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 15)
        lines.extend(self._generate_recommendations(stats))
        
        return "\n".join(lines)
    
    def generate_markdown_report(self, include_details: bool = False) -> str:
        """Generate Markdown format summary report."""
        stats = self.calculate_statistics()
        
        lines = []
        lines.append("# SBIR Transition Detection Summary Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Results Directory:** `{self.results_dir}`")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Total Transitions Detected:** {stats['total_detections']}")
        lines.append(f"- **High Confidence Detections:** {stats['high_confidence']}")
        lines.append(f"- **Likely Transitions:** {stats['likely_transitions']}")
        
        if stats['total_detections'] > 0:
            lines.append(f"- **Average Likelihood Score:** {stats['average_score']:.3f}")
            confidence_rate = (stats['high_confidence'] / stats['total_detections']) * 100
            lines.append(f"- **High Confidence Rate:** {confidence_rate:.1f}%")
        
        lines.append("")
        
        # Agency Analysis
        lines.append("## Agency Analysis")
        lines.append("")
        lines.append("| Type | Count | Percentage |")
        lines.append("|------|-------|------------|")
        
        if stats['total_detections'] > 0:
            same_pct = (stats['same_agency_count'] / stats['total_detections']) * 100
            cross_pct = (stats['cross_agency_count'] / stats['total_detections']) * 100
            lines.append(f"| Same Agency | {stats['same_agency_count']} | {same_pct:.1f}% |")
            lines.append(f"| Cross-Agency | {stats['cross_agency_count']} | {cross_pct:.1f}% |")
        
        lines.append("")
        
        # Score Distribution
        lines.append("## Score Distribution")
        lines.append("")
        lines.append("| Score Range | Count |")
        lines.append("|-------------|-------|")
        
        score_dist = stats['score_distribution']
        for range_name, count in score_dist.items():
            lines.append(f"| {range_name} | {count} |")
        
        lines.append("")
        
        if include_details:
            lines.extend(self._generate_detailed_markdown())
        
        return "\n".join(lines)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON format summary report."""
        stats = self.calculate_statistics()
        
        return {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'results_directory': str(self.results_dir),
                'total_detections_analyzed': len(self.detections)
            },
            'summary_statistics': stats,
            'top_detections': self._get_top_detections(10),
            'recommendations': self._generate_recommendations(stats)
        }
    
    def _calculate_score_distribution(self) -> Dict[str, int]:
        """Calculate score distribution across ranges."""
        distribution = {
            '0.90-1.00 (Excellent)': 0,
            '0.80-0.89 (Very Good)': 0,
            '0.70-0.79 (Good)': 0,
            '0.60-0.69 (Fair)': 0,
            '0.50-0.59 (Poor)': 0,
            'Below 0.50 (Very Poor)': 0
        }
        
        for detection in self.detections:
            score = detection['likelihood_score']
            
            if score >= 0.90:
                distribution['0.90-1.00 (Excellent)'] += 1
            elif score >= 0.80:
                distribution['0.80-0.89 (Very Good)'] += 1
            elif score >= 0.70:
                distribution['0.70-0.79 (Good)'] += 1
            elif score >= 0.60:
                distribution['0.60-0.69 (Fair)'] += 1
            elif score >= 0.50:
                distribution['0.50-0.59 (Poor)'] += 1
            else:
                distribution['Below 0.50 (Very Poor)'] += 1
        
        return distribution
    
    def _analyze_timing_patterns(self) -> Dict[str, int]:
        """Analyze timing patterns in detections."""
        patterns = {
            'Immediate (0-3 months)': 0,
            'Short-term (3-12 months)': 0,
            'Medium-term (1-2 years)': 0,
            'Long-term (>2 years)': 0,
            'Unknown timing': 0
        }
        
        for detection in self.detections:
            evidence = detection.get('evidence_bundle', {})
            timing_analysis = evidence.get('timing_analysis', {})
            days_diff = timing_analysis.get('days_difference')
            
            if days_diff is None:
                patterns['Unknown timing'] += 1
            elif days_diff <= 90:
                patterns['Immediate (0-3 months)'] += 1
            elif days_diff <= 365:
                patterns['Short-term (3-12 months)'] += 1
            elif days_diff <= 730:
                patterns['Medium-term (1-2 years)'] += 1
            else:
                patterns['Long-term (>2 years)'] += 1
        
        return patterns
    
    def _analyze_agency_patterns(self) -> Dict[str, int]:
        """Analyze agency patterns in detections."""
        agency_counts = {}
        
        for detection in self.detections:
            sbir_agency = detection['sbir_award']['agency']
            contract_agency = detection['contract']['agency']
            
            # Count SBIR agencies
            if sbir_agency not in agency_counts:
                agency_counts[sbir_agency] = {'sbir_count': 0, 'contract_count': 0}
            agency_counts[sbir_agency]['sbir_count'] += 1
            
            # Count contract agencies
            if contract_agency not in agency_counts:
                agency_counts[contract_agency] = {'sbir_count': 0, 'contract_count': 0}
            agency_counts[contract_agency]['contract_count'] += 1
        
        return agency_counts
    
    def _get_top_detections(self, limit: int) -> List[Dict[str, Any]]:
        """Get top detections by score."""
        sorted_detections = sorted(self.detections, 
                                 key=lambda x: x['likelihood_score'], 
                                 reverse=True)
        
        return sorted_detections[:limit]
    
    def _generate_detailed_analysis(self) -> List[str]:
        """Generate detailed analysis section."""
        lines = []
        
        lines.append("DETAILED ANALYSIS")
        lines.append("-" * 17)
        
        # Top detections
        top_detections = self._get_top_detections(5)
        lines.append("Top 5 Detections by Score:")
        
        for i, detection in enumerate(top_detections, 1):
            lines.append(f"{i}. Score: {detection['likelihood_score']:.3f} "
                        f"({detection['confidence']})")
            lines.append(f"   SBIR: {detection['sbir_award']['piid']} "
                        f"({detection['sbir_award']['agency']})")
            lines.append(f"   Contract: {detection['contract']['piid']} "
                        f"({detection['contract']['agency']})")
            lines.append("")
        
        return lines
    
    def _generate_detailed_markdown(self) -> List[str]:
        """Generate detailed analysis in Markdown format."""
        lines = []
        
        lines.append("## Detailed Analysis")
        lines.append("")
        
        # Top detections table
        lines.append("### Top Detections")
        lines.append("")
        lines.append("| Rank | Score | Confidence | SBIR PIID | Contract PIID |")
        lines.append("|------|-------|------------|-----------|---------------|")
        
        top_detections = self._get_top_detections(10)
        for i, detection in enumerate(top_detections, 1):
            lines.append(f"| {i} | {detection['likelihood_score']:.3f} | "
                        f"{detection['confidence']} | "
                        f"{detection['sbir_award']['piid']} | "
                        f"{detection['contract']['piid']} |")
        
        lines.append("")
        
        return lines
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if stats['total_detections'] == 0:
            recommendations.append("No transitions detected. Consider:")
            recommendations.append("- Reviewing detection thresholds")
            recommendations.append("- Checking input data quality")
            recommendations.append("- Expanding search criteria")
        else:
            if stats['high_confidence'] < stats['total_detections'] * 0.3:
                recommendations.append("Low high-confidence rate. Consider:")
                recommendations.append("- Reviewing scoring weights")
                recommendations.append("- Validating vendor matching logic")
            
            if stats['cross_agency_count'] > stats['same_agency_count']:
                recommendations.append("High cross-agency transition rate detected.")
                recommendations.append("- Verify vendor identification accuracy")
                recommendations.append("- Review cross-agency transition criteria")
            
            if stats['average_score'] < 0.7:
                recommendations.append("Low average scores detected. Consider:")
                recommendations.append("- Adjusting detection thresholds")
                recommendations.append("- Reviewing feature weights")
        
        return recommendations
