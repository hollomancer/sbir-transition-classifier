from sqlalchemy.orm import Session
from loguru import logger
from ..core import models
from . import heuristics, scoring
from ..db.database import SessionLocal
import datetime
import uuid
import json
import multiprocessing as mp
from typing import List, Dict, Any
import os

def process_award_chunk(award_ids: List[str]) -> List[Dict[str, Any]]:
    """Process a chunk of award IDs and return detection data for bulk insert."""
    db = SessionLocal()
    detections_data = []
    
    try:
        # Re-query awards in this process to avoid session issues
        awards = db.query(models.SbirAward).filter(models.SbirAward.id.in_(award_ids)).all()
        
        for award in awards:
            candidate_contracts = heuristics.find_candidate_contracts(db, award)
            
            for contract in candidate_contracts:
                score = scoring.score_transition(award, contract)
                confidence = scoring.get_confidence_level(score)

                if score >= 0.2:
                    signals = heuristics.get_confidence_signals(award, contract)
                    text_signals = heuristics.get_text_based_signals(award, contract)
                    
                    # Get vendor name safely
                    vendor_name = None
                    if award.vendor_id:
                        vendor = db.query(models.Vendor).filter(models.Vendor.id == award.vendor_id).first()
                        vendor_name = vendor.name if vendor else None
                    
                    evidence = {
                        "detection_id": str(uuid.uuid4()),
                        "likelihood_score": score,
                        "confidence": confidence,
                        "reason_string": f"Transition detected with score {score:.3f}",
                        "source_sbir_award": {
                            "piid": award.award_piid,
                            "agency": award.agency,
                            "phase": award.phase,
                            "completion_date": str(award.completion_date) if award.completion_date else None
                        },
                        "source_contract": {
                            "piid": contract.piid,
                            "agency": contract.agency,
                            "start_date": str(contract.start_date) if contract.start_date else None,
                            "competition_details": contract.competition_details
                        },
                        "signals": {**signals, **text_signals},
                        "vendor_name": vendor_name
                    }
                    
                    detection_data = {
                        'sbir_award_id': award.id,
                        'contract_id': contract.id,
                        'likelihood_score': score,
                        'confidence': confidence,
                        'evidence_bundle': evidence,
                        'detection_date': datetime.datetime.utcnow()
                    }
                    detections_data.append(detection_data)
    
    finally:
        db.close()
    
    return detections_data

def run_detection_for_award(db: Session, sbir_award: models.SbirAward):
    """Legacy function - kept for compatibility."""
    candidate_contracts = heuristics.find_candidate_contracts(db, sbir_award)
    
    for contract in candidate_contracts:
        score = scoring.score_transition(sbir_award, contract)
        confidence = scoring.get_confidence_level(score)

        if score >= 0.2:
            signals = heuristics.get_confidence_signals(sbir_award, contract)
            text_signals = heuristics.get_text_based_signals(sbir_award, contract)
            
            evidence = {
                "detection_id": str(uuid.uuid4()),
                "likelihood_score": score,
                "confidence": confidence,
                "reason_string": f"Transition detected with score {score:.3f}",
                "source_sbir_award": {
                    "piid": sbir_award.award_piid,
                    "agency": sbir_award.agency,
                    "phase": sbir_award.phase,
                    "completion_date": str(sbir_award.completion_date) if sbir_award.completion_date else None
                },
                "source_contract": {
                    "piid": contract.piid,
                    "agency": contract.agency,
                    "start_date": str(contract.start_date) if contract.start_date else None,
                    "competition_details": contract.competition_details
                },
                "signals": {**signals, **text_signals},
                "vendor_name": sbir_award.vendor.name if sbir_award.vendor else None
            }

            detection = models.Detection(
                sbir_award_id=sbir_award.id,
                contract_id=contract.id,
                likelihood_score=score,
                confidence=confidence,
                evidence_bundle=evidence,
                detection_date=datetime.datetime.utcnow()
            )
            db.add(detection)
    db.commit()

def run_full_detection():
    """Runs parallel detection with bulk database operations."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.console import Console
    
    console = Console()
    db = SessionLocal()
    
    try:
        # Load config to get eligible phases
        from .heuristics import load_config
        config = load_config()
        eligible_phases = config['candidate_selection']['eligible_phases']
        
        console.print(f"🔍 Analyzing {', '.join(eligible_phases)} awards...", style="bold blue")
        
        # Get awards that don't already have detections
        subquery = db.query(models.Detection.sbir_award_id).distinct()
        eligible_awards = (db.query(models.SbirAward)
                          .filter(models.SbirAward.phase.in_(eligible_phases))
                          .filter(~models.SbirAward.id.in_(subquery))
                          .all())
        
        total_awards = len(eligible_awards)
        if total_awards == 0:
            console.print(f"✅ All {', '.join(eligible_phases)} awards already processed.", style="green")
            return
            
        console.print(f"📊 Found {total_awards:,} new awards to process", style="cyan")
        
        # Determine optimal number of workers
        num_workers = min(4, os.cpu_count() or 1, max(1, total_awards // 1000))
        console.print(f"🚀 Using {num_workers} parallel workers", style="yellow")
        
        # Split award IDs into chunks for parallel processing
        award_ids = [award.id for award in eligible_awards]
        chunk_size = max(1, total_awards // num_workers)
        award_id_chunks = [award_ids[i:i + chunk_size] 
                          for i in range(0, len(award_ids), chunk_size)]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            
            task = progress.add_task("🔍 Detecting transitions", total=len(award_id_chunks))
            
            all_detections = []
            
            # Process chunks in parallel
            with mp.Pool(num_workers) as pool:
                for chunk_results in pool.imap(process_award_chunk, award_id_chunks):
                    all_detections.extend(chunk_results)
                    progress.update(task, advance=1)
        
        # Bulk insert all detections
        if all_detections:
            console.print(f"💾 Bulk inserting {len(all_detections)} detections...", style="cyan")
            db.bulk_insert_mappings(models.Detection, all_detections)
            db.commit()
        
        console.print(f"✅ Detection complete. Found {len(all_detections)} new transitions.", style="green bold")
        
    finally:
        db.close()

if __name__ == '__main__':
    print("Running full SBIR transition detection...")
    run_full_detection()
    print("Detection run complete.")
