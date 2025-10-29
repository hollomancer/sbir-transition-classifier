"""Database query helpers following SQLAlchemy v2 patterns.

This module consolidates common query patterns to:
- Reduce duplication across CLI and detection modules
- Encourage eager loading and efficient filtering
- Provide chunked iteration for large scans
- Support testing by accepting explicit sessions
"""

from typing import List, Optional, Iterator, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, selectinload

from ..core import models
from . import database as db_module
from ..config.schema import ConfigSchema
from ..config.loader import ConfigLoader


# ==============================================================================
# Vendor Queries
# ==============================================================================


def find_or_create_vendor(db: Session, name: str) -> models.Vendor:
    """
    Find existing vendor by name or create new one.

    Args:
        db: SQLAlchemy session
        name: Vendor name (will be trimmed)

    Returns:
        Vendor instance (existing or newly created)
    """
    name = name.strip() if name else ""
    if not name:
        raise ValueError("Vendor name cannot be empty")

    vendor = db.query(models.Vendor).filter(models.Vendor.name == name).first()
    if vendor:
        return vendor

    vendor = models.Vendor(name=name, created_at=datetime.utcnow())
    db.add(vendor)
    db.flush()
    return vendor


def find_vendors_by_name(db: Session, names: List[str]) -> Dict[str, models.Vendor]:
    """
    Bulk find vendors by names.

    Args:
        db: SQLAlchemy session
        names: List of vendor names to look up

    Returns:
        Dictionary mapping name to Vendor (only found vendors included)
    """
    if not names:
        return {}

    vendors = db.query(models.Vendor).filter(models.Vendor.name.in_(names)).all()
    return {v.name: v for v in vendors}


def get_vendor_count(db: Session) -> int:
    """Get total number of vendors in database."""
    return db.query(func.count(models.Vendor.id)).scalar() or 0


# ==============================================================================
# SBIR Award Queries
# ==============================================================================


def find_sbir_awards_by_vendor(
    db: Session, vendor_id: str, include_vendor: bool = False
) -> List[models.SbirAward]:
    """
    Find all SBIR awards for a vendor.

    Args:
        db: SQLAlchemy session
        vendor_id: Vendor ID to filter by
        include_vendor: If True, eagerly load vendor relationship

    Returns:
        List of SbirAward instances
    """
    query = db.query(models.SbirAward).filter(models.SbirAward.vendor_id == vendor_id)

    if include_vendor:
        query = query.options(selectinload(models.SbirAward.vendor))

    return query.all()


def find_sbir_awards_by_phase_and_agency(
    db: Session, phase: str, agency: str
) -> List[models.SbirAward]:
    """
    Find SBIR awards by phase and awarding agency.

    Args:
        db: SQLAlchemy session
        phase: Phase filter (e.g., "Phase II")
        agency: Awarding agency name

    Returns:
        List of matching SbirAward instances
    """
    return (
        db.query(models.SbirAward)
        .filter(models.SbirAward.phase == phase, models.SbirAward.agency == agency)
        .all()
    )


def find_sbir_awards_completed_after(
    db: Session, min_date: datetime
) -> List[models.SbirAward]:
    """
    Find SBIR awards completed on or after a date.

    Args:
        db: SQLAlchemy session
        min_date: Minimum completion date

    Returns:
        List of SbirAward instances
    """
    return (
        db.query(models.SbirAward)
        .filter(models.SbirAward.completion_date >= min_date)
        .all()
    )


def get_sbir_award_count(db: Session) -> int:
    """Get total number of SBIR awards in database."""
    return db.query(func.count(models.SbirAward.id)).scalar() or 0


def iter_sbir_awards_chunked(
    db: Session, chunk_size: int = 1000
) -> Iterator[List[models.SbirAward]]:
    """
    Iterate SBIR awards in chunks for memory-efficient processing.

    Args:
        db: SQLAlchemy session
        chunk_size: Number of records per chunk

    Yields:
        List of SbirAward instances (up to chunk_size per iteration)
    """
    query = db.query(models.SbirAward).order_by(models.SbirAward.id)
    chunk = []

    for award in query.yield_per(chunk_size):
        chunk.append(award)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


# ==============================================================================
# Contract Queries
# ==============================================================================


def find_contracts_by_vendor(
    db: Session, vendor_id: str, include_vendor: bool = False
) -> List[models.Contract]:
    """
    Find all contracts for a vendor.

    Args:
        db: SQLAlchemy session
        vendor_id: Vendor ID to filter by
        include_vendor: If True, eagerly load vendor relationship

    Returns:
        List of Contract instances
    """
    query = db.query(models.Contract).filter(models.Contract.vendor_id == vendor_id)

    if include_vendor:
        query = query.options(selectinload(models.Contract.vendor))

    return query.all()


def find_contracts_by_agency(db: Session, agency: str) -> List[models.Contract]:
    """
    Find all contracts awarded by a specific agency.

    Args:
        db: SQLAlchemy session
        agency: Awarding agency name

    Returns:
        List of Contract instances
    """
    return db.query(models.Contract).filter(models.Contract.agency == agency).all()


def find_contracts_started_after(
    db: Session, min_date: datetime
) -> List[models.Contract]:
    """
    Find contracts started on or after a date.

    Args:
        db: SQLAlchemy session
        min_date: Minimum start date

    Returns:
        List of Contract instances
    """
    return (
        db.query(models.Contract).filter(models.Contract.start_date >= min_date).all()
    )


def find_contracts_in_date_range(
    db: Session, start_date: datetime, end_date: datetime
) -> List[models.Contract]:
    """
    Find contracts within a date range.

    Args:
        db: SQLAlchemy session
        start_date: Earliest contract start date
        end_date: Latest contract start date

    Returns:
        List of Contract instances
    """
    return (
        db.query(models.Contract)
        .filter(
            and_(
                models.Contract.start_date >= start_date,
                models.Contract.start_date <= end_date,
            )
        )
        .all()
    )


def get_contract_count(db: Session) -> int:
    """Get total number of contracts in database."""
    return db.query(func.count(models.Contract.id)).scalar() or 0


def iter_contracts_chunked(
    db: Session, chunk_size: int = 5000
) -> Iterator[List[models.Contract]]:
    """
    Iterate contracts in chunks for memory-efficient processing.

    Args:
        db: SQLAlchemy session
        chunk_size: Number of records per chunk

    Yields:
        List of Contract instances (up to chunk_size per iteration)
    """
    query = db.query(models.Contract).order_by(models.Contract.id)
    chunk = []

    for contract in query.yield_per(chunk_size):
        chunk.append(contract)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


# ==============================================================================
# Detection Queries
# ==============================================================================


def find_detections_by_score(
    db: Session,
    min_score: float = 0.0,
    max_score: float = 1.0,
    include_evidence: bool = False,
) -> List[models.Detection]:
    """
    Find detections within a score range.

    Args:
        db: SQLAlchemy session
        min_score: Minimum likelihood score (inclusive)
        max_score: Maximum likelihood score (inclusive)
        include_evidence: If True, eagerly load related awards/contracts

    Returns:
        List of Detection instances
    """
    query = db.query(models.Detection).filter(
        and_(
            models.Detection.likelihood_score >= min_score,
            models.Detection.likelihood_score <= max_score,
        )
    )

    if include_evidence:
        query = query.options(
            selectinload(models.Detection.sbir_award),
            selectinload(models.Detection.contract),
        )

    return query.all()


def find_detections_by_confidence(
    db: Session, confidence: str, include_evidence: bool = False
) -> List[models.Detection]:
    """
    Find detections by confidence level.

    Args:
        db: SQLAlchemy session
        confidence: Confidence level (e.g., "High Confidence", "Likely")
        include_evidence: If True, eagerly load related awards/contracts

    Returns:
        List of Detection instances
    """
    query = db.query(models.Detection).filter(models.Detection.confidence == confidence)

    if include_evidence:
        query = query.options(
            selectinload(models.Detection.sbir_award),
            selectinload(models.Detection.contract),
        )

    return query.all()


def get_detection_count(db: Session) -> int:
    """Get total number of detections in database."""
    return db.query(func.count(models.Detection.id)).scalar() or 0


def get_detection_stats(db: Session) -> Dict[str, Any]:
    """
    Get summary statistics for all detections.

    Returns:
        Dictionary with keys: total_count, avg_score, max_score, min_score,
        confidence_distribution (dict mapping confidence -> count)
    """
    total = db.query(func.count(models.Detection.id)).scalar() or 0

    if total == 0:
        return {
            "total_count": 0,
            "avg_score": 0.0,
            "max_score": 0.0,
            "min_score": 0.0,
            "confidence_distribution": {},
        }

    avg_score = db.query(func.avg(models.Detection.likelihood_score)).scalar() or 0.0
    max_score = db.query(func.max(models.Detection.likelihood_score)).scalar() or 0.0
    min_score = db.query(func.min(models.Detection.likelihood_score)).scalar() or 0.0

    confidence_counts = (
        db.query(models.Detection.confidence, func.count(models.Detection.id))
        .group_by(models.Detection.confidence)
        .all()
    )

    return {
        "total_count": total,
        "avg_score": float(avg_score),
        "max_score": float(max_score),
        "min_score": float(min_score),
        "confidence_distribution": {conf: count for conf, count in confidence_counts},
    }


def iter_detections_chunked(
    db: Session, chunk_size: int = 1000
) -> Iterator[List[models.Detection]]:
    """
    Iterate detections in chunks for memory-efficient processing.

    Args:
        db: SQLAlchemy session
        chunk_size: Number of records per chunk

    Yields:
        List of Detection instances (up to chunk_size per iteration)
    """
    query = db.query(models.Detection).order_by(models.Detection.id)
    chunk = []

    for detection in query.yield_per(chunk_size):
        chunk.append(detection)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


def find_candidate_contracts(
    db: Session, sbir_award: models.SbirAward, config: ConfigSchema = None
):
    """
    Finds contract vehicles that were awarded to the same vendor within the configured time window
    after the completion of a given SBIR Phase I or Phase II award.

    Args:
        db: Database session
        sbir_award: SBIR award model
        config: Configuration schema (optional, loads default if not provided)
    """
    if config is None:
        try:
            config = ConfigLoader.load_default()
        except Exception:
            config = ConfigSchema()

    eligible_phases = set(config.detection.eligible_phases)

    if sbir_award.phase not in eligible_phases:
        return []

    # Prefer completion date; fall back to award date
    base_date = sbir_award.completion_date or sbir_award.award_date
    if not base_date:
        return []

    min_days = 30 * config.detection.timing.min_months_after_phase2
    max_days = 30 * config.detection.timing.max_months_after_phase2

    start_window = base_date + timedelta(days=min_days)
    end_window = base_date + timedelta(days=max_days)

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


# ==============================================================================
# Aggregate Queries (Cross-entity)
# ==============================================================================


def count_detections_by_agency(db: Session) -> Dict[str, int]:
    """
    Count detections grouped by awarding agency.

    Args:
        db: SQLAlchemy session

    Returns:
        Dictionary mapping agency name to detection count
    """
    results = (
        db.query(models.Contract.agency, func.count(models.Detection.id))
        .join(models.Detection.contract)
        .group_by(models.Contract.agency)
        .all()
    )
    return {agency: count for agency, count in results}


def count_detections_by_fiscal_year(db: Session) -> Dict[int, int]:
    """
    Count detections grouped by contract fiscal year.

    Args:
        db: SQLAlchemy session

    Returns:
        Dictionary mapping fiscal year to detection count
    """
    results = (
        db.query(
            func.extract("year", models.Contract.start_date).label("year"),
            func.count(models.Detection.id),
        )
        .join(models.Detection.contract)
        .group_by(func.extract("year", models.Contract.start_date))
        .all()
    )
    return {int(year): count for year, count in results}


def get_database_summary(db: Session) -> Dict[str, int]:
    """
    Get summary counts of all major entities in database.

    Args:
        db: SQLAlchemy session

    Returns:
        Dictionary with counts: vendors, sbir_awards, contracts, detections
    """
    return {
        "vendors": get_vendor_count(db),
        "sbir_awards": get_sbir_award_count(db),
        "contracts": get_contract_count(db),
        "detections": get_detection_count(db),
    }


# ==============================================================================
# Utility Functions
# ==============================================================================


def get_session() -> Session:
    """
    Get a new database session.

    Used at CLI entry points; tests should override SessionLocal.

    Returns:
        SQLAlchemy session instance
    """
    return db_module.SessionLocal()


def close_session(db: Session) -> None:
    """Close a database session."""
    if db:
        db.close()
