"""Consolidated reporting CLI commands for SBIR transition analysis.

This module consolidates summary reports, dual-perspective analysis, and evidence
viewing functionality into a unified reporting interface.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from ..analysis import analyze_transition_perspectives
from ..db.database import SessionLocal


# ============================================================================
# COMMAND GROUP
# ============================================================================


@click.group()
def reports():
    """Generate reports and view analysis results."""
    pass


# ============================================================================
# SUMMARY REPORT COMMANDS
# ============================================================================


@reports.command(name="summary")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to results directory containing detection outputs",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for summary report (prints to stdout if not specified)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "markdown", "json"]),
    default="text",
    help="Output format for summary report",
)
@click.option(
    "--include-details", is_flag=True, help="Include detailed analysis in report"
)
def generate_summary(
    results_dir: Path, output: Optional[Path], format: str, include_details: bool
):
    """Generate human-readable summary report from detection results."""

    try:
        generator = SummaryReportGenerator(results_dir)

        if format == "text":
            report = generator.generate_text_report(include_details)
        elif format == "markdown":
            report = generator.generate_markdown_report(include_details)
        elif format == "json":
            report = generator.generate_json_report()

        if output:
            with open(output, "w", encoding="utf-8") as f:
                if format == "json":
                    json.dump(report, f, indent=2, default=str)
                else:
                    f.write(report)
            click.echo(f"Summary report written to: {output}")
        else:
            if format == "json":
                click.echo(json.dumps(report, indent=2, default=str))
            else:
                click.echo(report)

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise click.ClickException(f"Failed to generate summary: {e}")


@reports.command(name="stats")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to results directory",
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

        if stats["total_detections"] > 0:
            click.echo(f"Average Score: {stats['average_score']:.3f}")
            click.echo(f"Same Agency: {stats['same_agency_count']}")
            click.echo(f"Cross Agency: {stats['cross_agency_count']}")

    except Exception as e:
        logger.error(f"Statistics calculation failed: {e}")
        raise click.ClickException(f"Failed to calculate statistics: {e}")


# ============================================================================
# DUAL-PERSPECTIVE REPORT COMMANDS
# ============================================================================


@reports.command(name="dual-perspective")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path.cwd() / "reports",
    help="Output directory for reports",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["console", "json", "csv"]),
    default="console",
    help="Report output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def dual_report(output_dir: Path, output_format: str, verbose: bool):
    """Generate dual-perspective SBIR transition report (Company vs Award level)."""

    console = Console()

    console.print(
        Panel.fit(
            "[bold blue]📊 SBIR Dual-Perspective Report Generator[/bold blue]\n"
            "[dim]Company-Level vs Award-Level Success Analysis[/dim]",
            border_style="blue",
        )
    )

    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Generate analysis
        perspectives = analyze_transition_perspectives(console=console)

        # Output based on format
        if output_format == "console":
            # Already displayed by analyze_transition_perspectives
            pass

        elif output_format == "json":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = output_dir / f"dual_perspective_report_{timestamp}.json"

            report_data = {
                "generated_at": datetime.now().isoformat(),
                "company_metrics": {
                    "total_companies": perspectives.total_companies_with_sbir,
                    "companies_with_transitions": perspectives.companies_with_transitions,
                    "success_rate_percent": perspectives.company_transition_rate,
                },
                "award_metrics": {
                    "total_awards": perspectives.total_sbir_awards,
                    "awards_with_transitions": perspectives.awards_with_transitions,
                    "success_rate_percent": perspectives.award_transition_rate,
                },
                "cross_perspective": {
                    "avg_awards_per_transitioning_company": perspectives.avg_awards_per_transitioning_company,
                    "avg_transitions_per_successful_company": perspectives.avg_transitions_per_successful_company,
                },
                "phase_breakdown": perspectives.awards_by_phase,
                "company_distribution": perspectives.companies_by_transition_count,
            }

            with open(json_file, "w") as f:
                json.dump(report_data, f, indent=2)

            console.print(f"📄 JSON report saved: {json_file}")

        elif output_format == "csv":
            import pandas as pd

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Summary metrics CSV
            summary_data = [
                ["Metric", "Company_Level", "Award_Level"],
                [
                    "Total",
                    perspectives.total_companies_with_sbir,
                    perspectives.total_sbir_awards,
                ],
                [
                    "With_Transitions",
                    perspectives.companies_with_transitions,
                    perspectives.awards_with_transitions,
                ],
                [
                    "Success_Rate_Percent",
                    perspectives.company_transition_rate,
                    perspectives.award_transition_rate,
                ],
            ]

            summary_file = output_dir / f"dual_perspective_summary_{timestamp}.csv"
            pd.DataFrame(summary_data[1:], columns=summary_data[0]).to_csv(
                summary_file, index=False
            )

            # Phase breakdown CSV
            if perspectives.awards_by_phase:
                phase_data = []
                for phase, data in perspectives.awards_by_phase.items():
                    phase_data.append(
                        [phase, data["total"], data["transitioned"], data["rate"]]
                    )

                phase_file = output_dir / f"phase_breakdown_{timestamp}.csv"
                pd.DataFrame(
                    phase_data,
                    columns=["Phase", "Total_Awards", "Transitioned", "Success_Rate"],
                ).to_csv(phase_file, index=False)
                console.print(f"📊 Phase breakdown saved: {phase_file}")

            console.print(f"📄 Summary CSV saved: {summary_file}")

        processing_time = time.time() - start_time

        # Final summary
        console.print()
        console.print(
            Panel.fit(
                f"[bold green]✅ Report Generation Complete![/bold green]\n"
                f"[dim]Processing time: {processing_time:.1f}s[/dim]",
                border_style="green",
            )
        )

        # Key takeaways
        console.print("\n[bold yellow]🎯 Key Takeaways:[/bold yellow]")
        console.print(
            f"• {perspectives.company_transition_rate:.1f}% of SBIR companies achieve commercialization"
        )
        console.print(
            f"• {perspectives.award_transition_rate:.1f}% of SBIR awards lead to follow-on contracts"
        )

        if perspectives.award_transition_rate > perspectives.company_transition_rate:
            console.print(
                "• Awards are more successful than companies at transitioning"
            )
            console.print("• Focus on helping companies achieve sustained success")

    except Exception as e:
        console.print(f"[red]❌ Report generation failed: {e}[/red]")
        raise click.ClickException(str(e))


# ============================================================================
# EVIDENCE VIEWING COMMANDS
# ============================================================================


@reports.command(name="view-evidence")
@click.option(
    "--evidence-dir",
    "-e",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to evidence directory",
)
@click.option("--detection-id", "-d", help="Specific detection ID to view (optional)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["summary", "full", "json"]),
    default="summary",
    help="Output format",
)
@click.option(
    "--confidence",
    "-c",
    type=click.Choice(["High Confidence", "Likely Transition"]),
    help="Filter by confidence level",
)
def view_evidence(
    evidence_dir: Path,
    detection_id: Optional[str],
    format: str,
    confidence: Optional[str],
):
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


@reports.command(name="list-evidence")
@click.option(
    "--evidence-dir",
    "-e",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to evidence directory",
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
        high_confidence = [
            d for d in detections if d.get("confidence") == "High Confidence"
        ]
        likely_transitions = [
            d for d in detections if d.get("confidence") == "Likely Transition"
        ]

        if high_confidence:
            click.echo(f"High Confidence ({len(high_confidence)}):")
            for detection in high_confidence:
                click.echo(
                    f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}"
                )

        if likely_transitions:
            click.echo(f"\nLikely Transition ({len(likely_transitions)}):")
            for detection in likely_transitions:
                click.echo(
                    f"  {detection['detection_id'][:8]}... - Score: {detection['likelihood_score']:.3f}"
                )

    except Exception as e:
        logger.error(f"Evidence listing failed: {e}")
        raise click.ClickException(f"Failed to list evidence: {e}")


@reports.command(name="evidence-report")
@click.option(
    "--evidence-dir",
    "-e",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to evidence directory",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for evidence report",
)
def evidence_report(evidence_dir: Path, output: Optional[Path]):
    """Generate comprehensive evidence report."""

    try:
        viewer = EvidenceViewer(evidence_dir)
        report = viewer.generate_report()

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(report)
            click.echo(f"Evidence report written to: {output}")
        else:
            click.echo(report)

    except Exception as e:
        logger.error(f"Evidence report generation failed: {e}")
        raise click.ClickException(f"Failed to generate evidence report: {e}")


# ============================================================================
# HELPER CLASSES
# ============================================================================


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
        with open(detections_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    detections.append(json.loads(line))

        return detections

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate summary statistics."""
        if not self.detections:
            return {
                "total_detections": 0,
                "high_confidence": 0,
                "likely_transitions": 0,
                "average_score": 0.0,
                "same_agency_count": 0,
                "cross_agency_count": 0,
            }

        high_confidence = sum(
            1 for d in self.detections if d["confidence"] == "High Confidence"
        )
        likely_transitions = len(self.detections) - high_confidence

        total_score = sum(d["likelihood_score"] for d in self.detections)
        average_score = total_score / len(self.detections)

        same_agency = sum(
            1
            for d in self.detections
            if d["sbir_award"]["agency"] == d["contract"]["agency"]
        )
        cross_agency = len(self.detections) - same_agency

        return {
            "total_detections": len(self.detections),
            "high_confidence": high_confidence,
            "likely_transitions": likely_transitions,
            "average_score": average_score,
            "same_agency_count": same_agency,
            "cross_agency_count": cross_agency,
            "score_distribution": self._calculate_score_distribution(),
            "timing_analysis": self._analyze_timing_patterns(),
            "agency_breakdown": self._analyze_agency_patterns(),
        }

    def generate_text_report(self, include_details: bool = False) -> str:
        """Generate plain text summary report."""
        stats = self.calculate_statistics()

        lines = [
            "SBIR TRANSITION DETECTION SUMMARY",
            "=" * 50,
            "",
            f"Total Detections: {stats['total_detections']}",
            f"High Confidence: {stats['high_confidence']}",
            f"Likely Transitions: {stats['likely_transitions']}",
            "",
            f"Average Score: {stats['average_score']:.3f}",
            f"Same Agency Transitions: {stats['same_agency_count']}",
            f"Cross Agency Transitions: {stats['cross_agency_count']}",
            "",
        ]

        if include_details and stats["total_detections"] > 0:
            lines.extend(self._generate_detailed_analysis(stats))

        return "\n".join(lines)

    def generate_markdown_report(self, include_details: bool = False) -> str:
        """Generate markdown summary report."""
        stats = self.calculate_statistics()

        lines = [
            "# SBIR Transition Detection Summary",
            "",
            "## Overview",
            "",
            f"- **Total Detections**: {stats['total_detections']}",
            f"- **High Confidence**: {stats['high_confidence']}",
            f"- **Likely Transitions**: {stats['likely_transitions']}",
            "",
            "## Statistics",
            "",
            f"- **Average Score**: {stats['average_score']:.3f}",
            f"- **Same Agency**: {stats['same_agency_count']}",
            f"- **Cross Agency**: {stats['cross_agency_count']}",
            "",
        ]

        if include_details and stats["total_detections"] > 0:
            lines.extend(self._generate_detailed_markdown(stats))

        return "\n".join(lines)

    def generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON summary report."""
        return self.calculate_statistics()

    def _calculate_score_distribution(self) -> Dict[str, int]:
        """Calculate distribution of likelihood scores."""
        if not self.detections:
            return {}

        distribution = {
            "0.0-0.2": 0,
            "0.2-0.4": 0,
            "0.4-0.6": 0,
            "0.6-0.8": 0,
            "0.8-1.0": 0,
        }

        for detection in self.detections:
            score = detection["likelihood_score"]
            if score < 0.2:
                distribution["0.0-0.2"] += 1
            elif score < 0.4:
                distribution["0.2-0.4"] += 1
            elif score < 0.6:
                distribution["0.4-0.6"] += 1
            elif score < 0.8:
                distribution["0.6-0.8"] += 1
            else:
                distribution["0.8-1.0"] += 1

        return distribution

    def _analyze_timing_patterns(self) -> Dict[str, Any]:
        """Analyze timing patterns in detections."""
        if not self.detections:
            return {}

        # Placeholder for timing analysis
        return {
            "avg_time_to_transition": "Not implemented",
            "median_time_to_transition": "Not implemented",
        }

    def _analyze_agency_patterns(self) -> Dict[str, int]:
        """Analyze patterns by agency."""
        if not self.detections:
            return {}

        agency_counts = {}
        for detection in self.detections:
            agency = detection["sbir_award"]["agency"]
            agency_counts[agency] = agency_counts.get(agency, 0) + 1

        return agency_counts

    def _generate_detailed_analysis(self, stats: Dict[str, Any]) -> List[str]:
        """Generate detailed analysis section."""
        lines = ["DETAILED ANALYSIS", "-" * 50, "", "Score Distribution:"]

        for range_label, count in stats["score_distribution"].items():
            lines.append(f"  {range_label}: {count}")

        lines.extend(["", "Agency Breakdown:"])
        for agency, count in stats["agency_breakdown"].items():
            lines.append(f"  {agency}: {count}")

        return lines

    def _generate_detailed_markdown(self, stats: Dict[str, Any]) -> List[str]:
        """Generate detailed analysis section in markdown."""
        lines = ["## Detailed Analysis", "", "### Score Distribution", ""]

        for range_label, count in stats["score_distribution"].items():
            lines.append(f"- **{range_label}**: {count}")

        lines.extend(["", "### Agency Breakdown", ""])
        for agency, count in stats["agency_breakdown"].items():
            lines.append(f"- **{agency}**: {count}")

        return lines


class EvidenceViewer:
    """Viewer for evidence bundle files."""

    def __init__(self, evidence_dir: Path):
        self.evidence_dir = evidence_dir

    def discover_evidence_bundles(self) -> List[Dict[str, Any]]:
        """Discover all evidence bundle files."""
        bundles = []

        if not self.evidence_dir.exists():
            return bundles

        for file_path in self.evidence_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    bundle = json.load(f)
                    bundles.append(bundle)
            except Exception as e:
                logger.warning(f"Failed to load evidence bundle {file_path}: {e}")

        return bundles

    def view_single_detection(self, detection_id: str, format: str):
        """View a single detection's evidence."""
        evidence_file = self.evidence_dir / f"{detection_id}.json"

        if not evidence_file.exists():
            raise FileNotFoundError(f"Evidence file not found: {evidence_file}")

        with open(evidence_file, "r") as f:
            evidence = json.load(f)

        if format == "json":
            click.echo(json.dumps(evidence, indent=2))
        elif format == "full":
            self._print_full_evidence(evidence)
        else:  # summary
            self._print_summary_evidence(evidence)

    def list_detections(self, confidence: Optional[str], format: str):
        """List all detections, optionally filtered by confidence."""
        detections = self.discover_evidence_bundles()

        if confidence:
            detections = [d for d in detections if d.get("confidence") == confidence]

        if format == "json":
            click.echo(json.dumps(detections, indent=2))
        else:
            for detection in detections:
                click.echo(
                    f"{detection.get('detection_id', 'Unknown')}: {detection.get('confidence', 'N/A')} - {detection.get('likelihood_score', 0):.3f}"
                )

    def generate_report(self) -> str:
        """Generate comprehensive evidence report."""
        bundles = self.discover_evidence_bundles()

        lines = [
            "EVIDENCE BUNDLE REPORT",
            "=" * 50,
            "",
            f"Total Evidence Bundles: {len(bundles)}",
            "",
        ]

        if bundles:
            high_conf = sum(
                1 for b in bundles if b.get("confidence") == "High Confidence"
            )
            lines.append(f"High Confidence: {high_conf}")
            lines.append(f"Likely Transitions: {len(bundles) - high_conf}")

        return "\n".join(lines)

    def _print_full_evidence(self, evidence: Dict[str, Any]):
        """Print full evidence details."""
        click.echo(json.dumps(evidence, indent=2))

    def _print_summary_evidence(self, evidence: Dict[str, Any]):
        """Print summary of evidence."""
        click.echo(f"Detection ID: {evidence.get('detection_id', 'Unknown')}")
        click.echo(f"Confidence: {evidence.get('confidence', 'N/A')}")
        click.echo(f"Score: {evidence.get('likelihood_score', 0):.3f}")


# ============================================================================
# LEGACY COMMAND ALIASES (for backward compatibility)
# ============================================================================

# Individual command exports for backward compatibility with main.py
generate_summary_cmd = generate_summary
quick_stats_cmd = quick_stats
dual_report_cmd = dual_report
view_evidence_cmd = view_evidence
list_evidence_cmd = list_evidence
evidence_report_cmd = evidence_report
