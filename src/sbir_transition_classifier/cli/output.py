"""Output file generation and reporting for detection results."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from loguru import logger
import click

from ..config.schema import ConfigSchema
from ..data.models import DetectionSession
from ..data.schemas import Detection


class DetectionOutputter:
    """Generates output files from detection results."""

    def __init__(self, config: ConfigSchema, session: DetectionSession):
        self.config = config
        self.session = session

    def generate_outputs(
        self, detections: List[Detection], output_dir: Path
    ) -> List[Path]:
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

        return output_files

    def _generate_jsonl(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate JSONL output file."""
        file_path = output_dir / "detections.jsonl"

        with open(file_path, "w", encoding="utf-8") as f:
            for detection in detections:
                record = {
                    "detection_id": str(detection.id),
                    "session_id": str(self.session.session_id),
                    "likelihood_score": detection.likelihood_score,
                    "confidence": detection.confidence,
                    "sbir_award": {
                        "piid": detection.sbir_award.award_piid,
                        "phase": detection.sbir_award.phase,
                        "agency": detection.sbir_award.agency,
                        "completion_date": detection.sbir_award.completion_date.isoformat(),
                        "topic": detection.sbir_award.topic,
                    },
                    "contract": {
                        "piid": detection.contract.piid,
                        "agency": detection.contract.agency,
                        "start_date": detection.contract.start_date.isoformat(),
                        "naics_code": detection.contract.naics_code,
                        "psc_code": detection.contract.psc_code,
                    },
                    "evidence_bundle": detection.evidence_bundle,
                    "created_at": datetime.utcnow().isoformat(),
                }

                f.write(json.dumps(record) + "\n")

        return file_path

    def _generate_csv(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate CSV output file."""
        file_path = output_dir / "detections.csv"

        # Flatten detection data for CSV
        records = []
        for detection in detections:
            record = {
                "detection_id": str(detection.id),
                "session_id": str(self.session.session_id),
                "likelihood_score": detection.likelihood_score,
                "confidence": detection.confidence,
                "sbir_piid": detection.sbir_award.award_piid,
                "sbir_phase": detection.sbir_award.phase,
                "sbir_agency": detection.sbir_award.agency,
                "sbir_completion_date": detection.sbir_award.completion_date.isoformat(),
                "sbir_topic": detection.sbir_award.topic,
                "contract_piid": detection.contract.piid,
                "contract_agency": detection.contract.agency,
                "contract_start_date": detection.contract.start_date.isoformat(),
                "contract_naics_code": detection.contract.naics_code,
                "contract_psc_code": detection.contract.psc_code,
                "agency_match": detection.sbir_award.agency
                == detection.contract.agency,
                "timing_days": (
                    detection.contract.start_date - detection.sbir_award.completion_date
                ).days,
                "created_at": datetime.utcnow().isoformat(),
            }
            records.append(record)

        df = pd.DataFrame(records)
        df.to_csv(file_path, index=False)

        return file_path

    def _generate_excel(self, detections: List[Detection], output_dir: Path) -> Path:
        """Generate Excel output file with multiple sheets."""
        file_path = output_dir / "detections.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            # Main detections sheet
            records = []
            for detection in detections:
                record = {
                    "Detection ID": str(detection.id),
                    "Likelihood Score": detection.likelihood_score,
                    "Confidence": detection.confidence,
                    "SBIR PIID": detection.sbir_award.award_piid,
                    "SBIR Phase": detection.sbir_award.phase,
                    "SBIR Agency": detection.sbir_award.agency,
                    "SBIR Completion": detection.sbir_award.completion_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "Contract PIID": detection.contract.piid,
                    "Contract Agency": detection.contract.agency,
                    "Contract Start": detection.contract.start_date.strftime(
                        "%Y-%m-%d"
                    ),
                    "Agency Match": detection.sbir_award.agency
                    == detection.contract.agency,
                    "Days After Completion": (
                        detection.contract.start_date
                        - detection.sbir_award.completion_date
                    ).days,
                }
                records.append(record)

            df = pd.DataFrame(records)
            df.to_excel(writer, sheet_name="Detections", index=False)

            # Summary statistics sheet
            report_generator = ReportGenerator(output_dir)
            summary_data = report_generator.calculate_statistics()
            summary_df = pd.DataFrame(
                list(summary_data.items()), columns=["Metric", "Value"]
            )
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        return file_path


class ReportGenerator:
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
        average_score = total_score / len(self.detections) if self.detections else 0.0

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

    def view_single_detection(self, detection_id: str, format: str):
        """View a single detection's evidence."""
        evidence_file = self.results_dir / f"{detection_id}.json"

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
        detections = self.detections

        if confidence:
            detections = [d for d in detections if d.get("confidence") == confidence]

        if format == "json":
            click.echo(json.dumps(detections, indent=2))
        else:
            for detection in detections:
                click.echo(
                    f"{detection.get('detection_id', 'Unknown')}: {detection.get('confidence', 'N/A')} - {detection.get('likelihood_score', 0):.3f}"
                )

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

    def _print_full_evidence(self, evidence: Dict[str, Any]):
        """Print full evidence details."""
        click.echo(json.dumps(evidence, indent=2))

    def _print_summary_evidence(self, evidence: Dict[str, Any]):
        """Print summary of evidence."""
        click.echo(f"Detection ID: {evidence.get('detection_id', 'Unknown')}")
        click.echo(f"Confidence: {evidence.get('confidence', 'N/A')}")
        click.echo(f"Score: {evidence.get('likelihood_score', 0):.3f}")
