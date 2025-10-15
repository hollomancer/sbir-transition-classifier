import uuid
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..db.database import Base

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    identifiers = relationship("VendorIdentifier", back_populates="vendor")
    sbir_awards = relationship("SbirAward", back_populates="vendor")
    contracts = relationship("Contract", back_populates="vendor")

class VendorIdentifier(Base):
    __tablename__ = "vendor_identifiers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    identifier_type = Column(String)
    identifier_value = Column(String, unique=True, index=True)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="identifiers")

class SbirAward(Base):
    __tablename__ = "sbir_awards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    award_piid = Column(String)
    phase = Column(String)
    agency = Column(String)
    award_date = Column(DateTime)
    completion_date = Column(DateTime, index=True)
    topic = Column(String)
    raw_data = Column(JSON)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="sbir_awards")

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    piid = Column(String, unique=True, index=True)
    parent_piid = Column(String, index=True)
    agency = Column(String)
    start_date = Column(DateTime, index=True)
    naics_code = Column(String)
    psc_code = Column(String)
    competition_details = Column(JSON)
    raw_data = Column(JSON)
    created_at = Column(DateTime)
    vendor = relationship("Vendor", back_populates="contracts")

class Detection(Base):
    __tablename__ = "detections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sbir_award_id = Column(UUID(as_uuid=True), ForeignKey("sbir_awards.id"))
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"))
    likelihood_score = Column(Float, index=True)
    confidence = Column(String)
    evidence_bundle = Column(JSON)
    detection_date = Column(DateTime)
    sbir_award = relationship("SbirAward")
    contract = relationship("Contract")
