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
from .output import ReportGenerator


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
        generator = ReportGenerator(results_dir)

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
        generator = ReportGenerator(results_dir)
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
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to results directory containing detection outputs",
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
    results_dir: Path,
    detection_id: Optional[str],
    format: str,
    confidence: Optional[str],
):
    """View evidence bundles from local files."""

    try:
        generator = ReportGenerator(results_dir)

        if detection_id:
            # View specific detection
            generator.view_single_detection(detection_id, format)
        else:
            # List all detections
            generator.list_detections(confidence, format)

    except Exception as e:
        logger.error(f"Evidence viewing failed: {e}")
        raise click.ClickException(f"Failed to view evidence: {e}")


@reports.command(name="list-evidence")
@click.option(
    "--results-dir",
    "-r",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to results directory containing detection outputs",
)
def list_evidence(results_dir: Path):
    """List all available evidence bundles."""

    try:
        generator = ReportGenerator(results_dir)
        generator.list_detections(None, "summary")

    except Exception as e:
        logger.error(f"Evidence listing failed: {e}")
        raise click.ClickException(f"Failed to list evidence: {e}")


@reports.command(name="evidence-report")
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
    help="Output file for evidence report",
)
def evidence_report(results_dir: Path, output: Optional[Path]):
    """Generate comprehensive evidence report."""

    try:
        generator = ReportGenerator(results_dir)
        report = generator.generate_text_report(include_details=True)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(report)
            click.echo(f"Evidence report written to: {output}")
        else:
            click.echo(report)

    except Exception as e:
        logger.error(f"Evidence report generation failed: {e}")
        raise click.ClickException(f"Failed to generate evidence report: {e}")
