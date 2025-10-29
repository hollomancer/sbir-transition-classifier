"""Date utility functions for timing calculations and validation."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from ..config.schema import ConfigSchema


def calculate_timing_window(
    base_date: datetime, config: ConfigSchema
) -> Tuple[datetime, datetime]:
    """
    Calculate the timing window for contract detection based on configuration.

    Args:
        base_date: Base date (award completion or award date)
        config: Configuration schema with timing parameters

    Returns:
        Tuple of (start_window, end_window) datetimes
    """
    min_days = 30 * config.detection.timing.min_months_after_phase2
    max_days = 30 * config.detection.timing.max_months_after_phase2

    start_window = base_date + timedelta(days=min_days)
    end_window = base_date + timedelta(days=max_days)

    return start_window, end_window


def extract_year_from_piid(piid: str) -> Optional[int]:
    """
    Extract year from PIID (Procurement Instrument Identifier).

    Args:
        piid: Procurement Instrument Identifier string

    Returns:
        Year as integer if found, None otherwise
    """
    if not piid:
        return None

    # Extract year pattern (20XX)
    year_match = re.search(r"20\d{2}", piid)
    if not year_match:
        return None

    return int(year_match.group())


def has_date_mismatch(contract: Dict[str, Any], threshold_years: int = 2) -> bool:
    """
    Check if contract has suspicious PIID/date mismatch.

    A mismatch occurs when the year in the PIID differs significantly from
    the contract start date year, which may indicate data quality issues.

    Args:
        contract: Contract dictionary with 'piid' and 'start_date' keys
        threshold_years: Maximum allowed year difference (default: 2)

    Returns:
        True if mismatch detected, False otherwise
    """
    piid = contract.get("piid", "")
    start_date = contract.get("start_date")

    if not piid or not start_date:
        return False

    piid_year = extract_year_from_piid(piid)
    if piid_year is None:
        return False

    # Extract year from start_date (handles both datetime objects and strings)
    if hasattr(start_date, "year"):
        contract_year = start_date.year
    else:
        try:
            contract_year = int(str(start_date)[:4])
        except (ValueError, IndexError):
            return False

    # Flag contracts with year difference exceeding threshold
    return abs(piid_year - contract_year) > threshold_years


def get_months_between(date1: datetime, date2: datetime) -> float:
    """
    Calculate months between two dates.

    Args:
        date1: First date
        date2: Second date

    Returns:
        Number of months between dates (can be negative)
    """
    delta = date2 - date1
    return delta.days / 30.0


def is_within_timing_window(
    award_date: datetime,
    contract_date: datetime,
    config: ConfigSchema,
    completion_date: Optional[datetime] = None,
) -> bool:
    """
    Check if contract date falls within configured timing window after award.

    Args:
        award_date: SBIR award date
        contract_date: Contract start date
        config: Configuration schema with timing parameters
        completion_date: Optional completion date (preferred over award_date)

    Returns:
        True if contract is within timing window, False otherwise
    """
    base_date = completion_date or award_date
    if not base_date or not contract_date:
        return False

    start_window, end_window = calculate_timing_window(base_date, config)
    return start_window <= contract_date <= end_window
