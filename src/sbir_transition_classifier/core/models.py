import uuid
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from ..db.database import Base


class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)  # Add index for name lookups
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    identifiers = relationship("VendorIdentifier", back_populates="vendor")
    sbir_awards = relationship("SbirAward", back_populates="vendor")
    contracts = relationship("Contract", back_populates="vendor")


class VendorIdentifier(Base):
    __tablename__ = "vendor_identifiers"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(
        String(36), ForeignKey("vendors.id"), index=True
    )  # Add index for joins
    identifier_type = Column(String, index=True)  # Add index for type filtering
    identifier_value = Column(String, unique=True, index=True)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="identifiers")


class SbirAward(Base):
    __tablename__ = "sbir_awards"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(
        String(36), ForeignKey("vendors.id"), index=True
    )  # Add index for joins
    award_piid = Column(String, index=True)  # Add index for award lookups
    phase = Column(String, index=True)  # Add index for phase filtering
    agency = Column(String, index=True)  # Add index for agency filtering
    award_date = Column(DateTime, index=True)  # Add index for date filtering
    completion_date = Column(DateTime, index=True)
    topic = Column(String)
    raw_data = Column(JSON)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="sbir_awards")


class Contract(Base):
    __tablename__ = "contracts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vendor_id = Column(
        String(36), ForeignKey("vendors.id"), index=True
    )  # Add index for joins
    piid = Column(String, unique=True, index=True)
    parent_piid = Column(String, index=True)
    agency = Column(String, index=True)  # Add index for agency filtering
    start_date = Column(DateTime, index=True)
    naics_code = Column(String, index=True)  # Add index for NAICS filtering
    psc_code = Column(String, index=True)  # Add index for PSC filtering
    competition_details = Column(JSON)
    raw_data = Column(JSON)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="contracts")


class Detection(Base):
    __tablename__ = "detections"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sbir_award_id = Column(
        String(36), ForeignKey("sbir_awards.id"), index=True
    )  # Add index for joins
    contract_id = Column(
        String(36), ForeignKey("contracts.id"), index=True
    )  # Add index for joins
    likelihood_score = Column(Float, index=True)
    confidence = Column(String, index=True)  # Add index for confidence filtering
    evidence_bundle = Column(JSON)
    detection_date = Column(DateTime, index=True)  # Add index for date filtering
    sbir_award = relationship("SbirAward")
    contract = relationship("Contract")


# Add composite indexes for common query patterns
Index(
    "idx_vendor_agency_date",
    SbirAward.vendor_id,
    SbirAward.agency,
    SbirAward.completion_date,
)
Index(
    "idx_contract_vendor_agency",
    Contract.vendor_id,
    Contract.agency,
    Contract.start_date,
)
Index(
    "idx_detection_score_confidence", Detection.likelihood_score, Detection.confidence
)
