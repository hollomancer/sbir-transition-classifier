from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import timedelta
import yaml
import os
from pathlib import Path
from ..core import models

# Load configuration from YAML with robust path resolution
def load_config():
    # Get the project root directory (4 levels up from this file)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    config_path = project_root / 'config' / 'classification.yaml'
    
    if not config_path.exists():
        # Fallback to relative path
        config_path = Path('config/classification.yaml')
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

_config = load_config()

def find_candidate_contracts(db: Session, sbir_award: models.SbirAward):
    """
    Finds contract vehicles that were awarded to the same vendor within the configured time window
    after the start of a given SBIR Phase I or Phase II award.
    """
    if sbir_award.phase not in _config['candidate_selection']['eligible_phases']:
        return []

    if not sbir_award.award_date:
        return []

    start_window = sbir_award.award_date
    end_window = start_window + timedelta(days=_config['candidate_selection']['search_window_days'])

    candidates = (
        db.query(models.Contract)
        .filter(
            and_(
                models.Contract.vendor_id == sbir_award.vendor_id,
                models.Contract.start_date >= start_window,
                models.Contract.start_date <= end_window,
            )
        )
        .all()
    )

    return candidates

def get_department(agency_string: str) -> str:
    """Enhanced department extraction with better mapping."""
    if not agency_string: 
        return ""
    
    agency = agency_string.upper()
    
    # Department of Defense
    if any(x in agency for x in ['DEFENSE', 'AIR FORCE', 'NAVY', 'ARMY']):
        return 'DOD'
    # NASA
    elif 'NASA' in agency:
        return 'NASA'
    # Department of Energy
    elif 'ENERGY' in agency:
        return 'DOE'
    # General Services Administration
    elif 'GSA' in agency or 'GENERAL SERVICES' in agency:
        return 'GSA'
    # Department of Homeland Security
    elif 'HOMELAND' in agency:
        return 'DHS'
    # Default to first word
    else:
        return agency.split()[0] if agency else 'UNKNOWN'

def get_confidence_signals(sbir_award: models.SbirAward, contract: models.Contract) -> dict:
    """
    Enhanced confidence signals with relaxed agency matching.
    """
    signals = {}

    # Enhanced agency matching
    sbir_agency = (sbir_award.agency or '').upper()
    contract_agency = (contract.agency or '').upper()
    
    # Signal 1: Direct agency match
    signals['same_agency'] = sbir_agency == contract_agency

    # Signal 2: Department-level match
    signals['same_department'] = get_department(sbir_agency) == get_department(contract_agency)
    
    # Signal 3: GSA reseller logic (GSA often resells DoD contracts)
    signals['gsa_reseller'] = (
        ('GSA' in contract_agency or 'GENERAL SERVICES' in contract_agency) and
        ('DEFENSE' in sbir_agency or 'AIR FORCE' in sbir_agency or 'NAVY' in sbir_agency or 'ARMY' in sbir_agency)
    )
    
    # Signal 4: Cross-agency federal transition (still valid)
    signals['federal_transition'] = True  # Both are federal agencies
    
    # Signal 5: Enhanced competition analysis
    signals['sole_source'] = False
    signals['limited_competition'] = False
    signals['full_competition'] = False
    
    if contract.competition_details:
        extent_competed = str(contract.competition_details.get('extent_competed', '')).upper()
        
        if 'NOT AVAILABLE FOR COMPETITION' in extent_competed:
            signals['sole_source'] = True
        elif 'NOT COMPETED' in extent_competed or 'LIMITED' in extent_competed:
            signals['limited_competition'] = True
        elif 'FULL AND OPEN' in extent_competed:
            signals['full_competition'] = True

    return signals

def get_text_based_signals(sbir_award: models.SbirAward, contract: models.Contract) -> dict:
    """
    Analyzes text fields for signals linking an award and contract.
    """
    signals = {
        'sbir_in_description': False,
        'topic_in_description': False
    }

    if not contract.raw_data or not isinstance(contract.raw_data, dict):
        return signals

    description = contract.raw_data.get('description', '').lower()
    if not description:
        return signals

    if 'sbir' in description:
        signals['sbir_in_description'] = True

    if sbir_award.topic and sbir_award.topic.lower() in description:
        signals['topic_in_description'] = True

    return signals
