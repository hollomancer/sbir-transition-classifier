from sqlalchemy.orm import Session
from loguru import logger
from ..core import models
from . import heuristics, scoring
from ..db.database import SessionLocal
import datetime
import uuid

def run_detection_for_award(db: Session, sbir_award: models.SbirAward):
    """Runs the detection process for a single SBIR award."""
    # Remove all logging during processing for clean UX
    candidate_contracts = heuristics.find_candidate_contracts(db, sbir_award)
    
    for contract in candidate_contracts:
        score = scoring.score_transition(sbir_award, contract)
        confidence = scoring.get_confidence_level(score)

        # Lowered threshold from 0.65 to 0.2 to capture more transitions
        if score >= 0.2:
            # Enhanced evidence bundle
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
    """Runs the detection process for all Phase II SBIR awards."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.console import Console
    
    console = Console()
    db: Session = SessionLocal()
    try:
        console.print("🔍 Analyzing Phase II awards...", style="bold blue")
        
        # Get awards that don't already have detections
        subquery = db.query(models.Detection.sbir_award_id).distinct()
        phase_ii_awards = (db.query(models.SbirAward)
                          .filter(models.SbirAward.phase == 'Phase II')
                          .filter(~models.SbirAward.id.in_(subquery))
                          .all())
        
        total_awards = len(phase_ii_awards)
        if total_awards == 0:
            console.print("✅ All Phase II awards already processed.", style="green")
            return
            
        console.print(f"📊 Found {total_awards:,} new awards to process", style="cyan")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            
            task = progress.add_task("🔍 Detecting transitions", total=total_awards)
            
            new_detections = 0
            for i, award in enumerate(phase_ii_awards, 1):
                # Count detections before processing
                before_count = db.query(models.Detection).count()
                
                run_detection_for_award(db, award)
                
                # Count detections after processing
                after_count = db.query(models.Detection).count()
                new_detections += (after_count - before_count)
                
                if i % 50 == 0:
                    db.commit()
                
                progress.update(task, advance=1)
        
        # Final commit
        db.commit()
        console.print(f"✅ Detection complete. Found {new_detections} new transitions.", style="green bold")
        
    finally:
        db.close()

if __name__ == '__main__':
    print("Running full SBIR transition detection...")
    run_full_detection()
    print("Detection run complete.")
