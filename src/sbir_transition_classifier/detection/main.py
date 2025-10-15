from sqlalchemy.orm import Session
from loguru import logger
from ..core import models
from . import heuristics, scoring
from ..db.database import SessionLocal
import datetime
import uuid

def run_detection_for_award(db: Session, sbir_award: models.SbirAward):
    """Runs the detection process for a single SBIR award."""
    logger.info(f"Running detection for award: {sbir_award.award_piid}")
    
    candidate_contracts = heuristics.find_candidate_contracts(db, sbir_award)
    logger.info(f"Found {len(candidate_contracts)} candidate contracts.")

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
    logger.info("Starting full detection run...")
    db: Session = SessionLocal()
    try:
        phase_ii_awards = db.query(models.SbirAward).filter(models.SbirAward.phase == 'Phase II').all()
        logger.info(f"Found {len(phase_ii_awards)} Phase II awards to process.")
        for award in phase_ii_awards:
            run_detection_for_award(db, award)
        logger.info("Full detection run complete.")
    finally:
        db.close()

if __name__ == '__main__':
    print("Running full SBIR transition detection...")
    run_full_detection()
    print("Detection run complete.")
