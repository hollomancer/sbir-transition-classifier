"""Data quality validation for SBIR transition detection."""

import re
from typing import List, Tuple
from sqlalchemy.orm import Session
from ..db import models


def extract_year_from_piid(piid: str) -> str:
    """Extract fiscal year from PIID format."""
    # Look for 4-digit year patterns in PIID
    year_match = re.search(r'20\d{2}', piid)
    return year_match.group() if year_match else 'unknown'


def find_date_mismatches(db: Session) -> List[Tuple[str, str, str, str]]:
    """Find contracts where PIID year doesn't match start_date year."""
    contracts = db.query(models.Contract).all()
    mismatches = []
    
    for contract in contracts:
        if not contract.start_date:
            continue
            
        start_year = str(contract.start_date.year)
        piid_year = extract_year_from_piid(contract.piid)
        
        if piid_year != 'unknown' and piid_year != start_year:
            mismatches.append((
                contract.piid,
                contract.agency,
                piid_year,
                start_year
            ))
    
    return mismatches


def flag_suspicious_detections(db: Session) -> int:
    """Flag detections involving contracts with date mismatches."""
    mismatches = find_date_mismatches(db)
    suspicious_piids = {mismatch[0] for mismatch in mismatches}
    
    # Count detections involving suspicious contracts
    suspicious_count = (
        db.query(models.Detection)
        .join(models.Contract)
        .filter(models.Contract.piid.in_(suspicious_piids))
        .count()
    )
    
    return suspicious_count
