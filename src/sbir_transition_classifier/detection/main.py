from collections import Counter
from sqlalchemy.orm import Session, selectinload
from loguru import logger
from rich.table import Table
from ..core import models
from . import scoring
from ..db import database as db_module, queries
import datetime
import uuid
import multiprocessing as mp
from typing import List, Dict, Any, Tuple
import os


def _has_date_mismatch(contract) -> bool:
    """Check if contract has suspicious PIID/date mismatch."""
    import re

    if not contract.piid or not contract.start_date:
        return False

    # Extract year from PIID
    year_match = re.search(r"20\d{2}", contract.piid)
    if not year_match:
        return False

    piid_year = int(year_match.group())
    contract_year = contract.start_date.year

    # Flag contracts with >2 year difference as suspicious
    return abs(piid_year - contract_year) > 2


def process_award_chunk(
    payload: Tuple[List[str], int],
) -> Tuple[List[Dict[str, Any]], int]:
    """Process a chunk of award IDs and return detection data for bulk insert."""
    award_ids, expected_count = payload
    db = db_module.SessionLocal()
    detections_data = []

    try:
        # Re-query awards in this process to avoid session issues
        awards = (
            db.query(models.SbirAward)
            .options(selectinload(models.SbirAward.vendor))
            .filter(models.SbirAward.id.in_(award_ids))
            .all()
        )

        for award in awards:
            candidate_contracts = queries.find_candidate_contracts(db, award)

            for contract in candidate_contracts:
                # Data quality filter: Skip contracts with PIID/date mismatches
                if _has_date_mismatch(contract):
                    continue

                score = scoring.score_transition(award, contract)
                confidence = scoring.get_confidence_level(score)

                if score >= 0.2:
                    signals = scoring.get_confidence_signals(award, contract)
                    text_signals = scoring.get_text_based_signals(award, contract)

                    # Get vendor name safely
                    vendor_name = award.vendor.name if award.vendor else None

                    evidence = {
                        "detection_id": str(uuid.uuid4()),
                        "likelihood_score": score,
                        "confidence": confidence,
                        "reason_string": f"Transition detected with score {score:.3f}",
                        "source_sbir_award": {
                            "piid": award.award_piid,
                            "agency": award.agency,
                            "phase": award.phase,
                            "completion_date": str(award.completion_date)
                            if award.completion_date
                            else None,
                        },
                        "source_contract": {
                            "piid": contract.piid,
                            "agency": contract.agency,
                            "start_date": str(contract.start_date)
                            if contract.start_date
                            else None,
                            "competition_details": contract.competition_details,
                        },
                        "signals": {**signals, **text_signals},
                        "vendor_name": vendor_name,
                    }

                    detection_data = {
                        "sbir_award_id": award.id,
                        "contract_id": contract.id,
                        "likelihood_score": score,
                        "confidence": confidence,
                        "evidence_bundle": evidence,
                        "detection_date": datetime.datetime.utcnow(),
                    }
                    detections_data.append(detection_data)

    finally:
        db.close()

    # Use actual awards processed to keep progress accurate even if rows disappear
    return detections_data, len(awards) if awards else expected_count


def run_detection_for_award(db: Session, sbir_award: models.SbirAward):
    """Legacy function - kept for compatibility."""
    candidate_contracts = queries.find_candidate_contracts(db, sbir_award)

    for contract in candidate_contracts:
        score = scoring.score_transition(sbir_award, contract)
        confidence = scoring.get_confidence_level(score)

        if score >= 0.2:
            signals = scoring.get_confidence_signals(sbir_award, contract)
            text_signals = scoring.get_text_based_signals(sbir_award, contract)

            evidence = {
                "detection_id": str(uuid.uuid4()),
                "likelihood_score": score,
                "confidence": confidence,
                "reason_string": f"Transition detected with score {score:.3f}",
                "source_sbir_award": {
                    "piid": sbir_award.award_piid,
                    "agency": sbir_award.agency,
                    "phase": sbir_award.phase,
                    "completion_date": str(sbir_award.completion_date)
                    if sbir_award.completion_date
                    else None,
                },
                "source_contract": {
                    "piid": contract.piid,
                    "agency": contract.agency,
                    "start_date": str(contract.start_date)
                    if contract.start_date
                    else None,
                    "competition_details": contract.competition_details,
                },
                "signals": {**signals, **text_signals},
                "vendor_name": sbir_award.vendor.name if sbir_award.vendor else None,
            }

            detection = models.Detection(
                sbir_award_id=sbir_award.id,
                contract_id=contract.id,
                likelihood_score=score,
                confidence=confidence,
                evidence_bundle=evidence,
                detection_date=datetime.datetime.utcnow(),
            )
            db.add(detection)
    db.commit()


def run_full_detection(in_process: bool = False):
    """Runs parallel detection with bulk database operations.

    Args:
        in_process: If True, run chunk processing serially in the current process
                    (useful for testing). Default False (parallel multiprocessing).
    """
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
    )
    from rich.console import Console

    console = Console()
    db = db_module.SessionLocal()

    try:
        from ..config.loader import ConfigLoader

        try:
            eligible_phases = ConfigLoader.load_default().detection.eligible_phases
        except Exception:
            eligible_phases = ["Phase I", "Phase II"]
        console.print(
            f"🔍 Analyzing {', '.join(eligible_phases)} awards...", style="bold blue"
        )

        # Get awards that don't already have detections
        subquery = db.query(models.Detection.sbir_award_id).distinct()
        eligible_awards = (
            db.query(models.SbirAward)
            .filter(models.SbirAward.phase.in_(eligible_phases))
            .filter(~models.SbirAward.id.in_(subquery))
            .all()
        )

        total_awards = len(eligible_awards)
        if total_awards == 0:
            console.print(
                f"✅ All {', '.join(eligible_phases)} awards already processed.",
                style="green",
            )
            return

        console.print(f"📊 Found {total_awards:,} new awards to process", style="cyan")

        # Determine optimal number of workers (switch to single-process when in_process=True)
        if in_process:
            num_workers = 1
            console.print(
                "🚀 Running in single-process (in-process) mode for testing",
                style="yellow",
            )
        else:
            num_workers = min(4, os.cpu_count() or 1, max(1, total_awards // 1000))
            console.print(f"🚀 Using {num_workers} parallel workers", style="yellow")

        # Split award IDs into chunks for processing
        award_ids = [award.id for award in eligible_awards]
        dynamic_chunk_size = max(200, total_awards // (num_workers * 8) or 1)
        award_id_chunks = [
            award_ids[i : i + dynamic_chunk_size]
            for i in range(0, len(award_ids), dynamic_chunk_size)
        ]
        chunk_payloads = [(chunk, len(chunk)) for chunk in award_id_chunks]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("🔍 Detecting transitions", total=total_awards)

            all_detections = []
            total_processed = 0

            # In-process (serial) mode: call the chunk processor directly for easier testing
            if in_process or num_workers <= 1:
                for payload in chunk_payloads:
                    chunk_results, processed_count = process_award_chunk(payload)
                    all_detections.extend(chunk_results)
                    total_processed += processed_count
                    progress.update(task, advance=processed_count)
            else:
                # Process chunks in parallel using multiprocessing pool
                with mp.Pool(num_workers) as pool:
                    for chunk_results, processed_count in pool.imap(
                        process_award_chunk, chunk_payloads, chunksize=1
                    ):
                        all_detections.extend(chunk_results)
                        total_processed += processed_count
                        progress.update(task, advance=processed_count)

            # Ensure the progress bar reflects any rounding adjustments
            progress.update(task, completed=min(total_processed, total_awards))

        # Bulk insert all detections
        if all_detections:
            console.print(
                f"💾 Bulk inserting {len(all_detections)} detections...", style="cyan"
            )
            db.bulk_insert_mappings(models.Detection, all_detections)
            db.commit()
            confidence_counts = Counter(det["confidence"] for det in all_detections)
            summary_table = Table(title="Detection Summary", show_lines=False)
            summary_table.add_column("Confidence", style="cyan")
            summary_table.add_column("Detections", justify="right", style="green")
            summary_table.add_column("Avg Score", justify="right", style="yellow")

            scores_by_confidence: Dict[str, List[float]] = {}
            for det in all_detections:
                scores_by_confidence.setdefault(det["confidence"], []).append(
                    det["likelihood_score"]
                )

            for confidence, count in confidence_counts.most_common():
                avg_score = (
                    sum(scores_by_confidence[confidence]) / count if count else 0.0
                )
                summary_table.add_row(
                    confidence or "Unknown", f"{count:,}", f"{avg_score:.3f}"
                )

            console.print(summary_table)

            agency_counter = Counter(
                (
                    det["evidence_bundle"]["source_contract"].get("agency") or "Unknown"
                ).upper()
                for det in all_detections
            )

            top_agencies = agency_counter.most_common(5)
            if top_agencies:
                agency_table = Table(title="Top Contract Agencies", show_header=True)
                agency_table.add_column("Agency", style="cyan")
                agency_table.add_column("Detections", justify="right", style="green")
                for agency, count in top_agencies:
                    agency_table.add_row(agency, f"{count:,}")
                console.print(agency_table)

        if all_detections:
            console.print(
                f"✅ Detection complete. Found {len(all_detections)} new transitions.",
                style="green bold",
            )
        else:
            console.print(
                "⚠️  Detection complete. No new transitions met the configured thresholds.",
                style="yellow",
            )

    finally:
        db.close()


if __name__ == "__main__":
    print("Running full SBIR transition detection...")
    run_full_detection()
    print("Detection run complete.")
