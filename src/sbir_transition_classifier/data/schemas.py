from pydantic import BaseModel
import uuid
from datetime import datetime
from typing import List, Optional, Any

class VendorIdentifierBase(BaseModel):
    identifier_type: str
    identifier_value: str

class VendorIdentifierCreate(VendorIdentifierBase):
    pass

class VendorIdentifier(VendorIdentifierBase):
    id: uuid.UUID
    vendor_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class VendorBase(BaseModel):
    name: str

class VendorCreate(VendorBase):
    pass

class Vendor(VendorBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    identifiers: List[VendorIdentifier] = []

    class Config:
        orm_mode = True

class SbirAwardBase(BaseModel):
    award_piid: str
    phase: str
    agency: str
    award_date: datetime
    completion_date: datetime
    topic: str
    raw_data: Optional[Any]

class SbirAwardCreate(SbirAwardBase):
    pass

class SbirAward(SbirAwardBase):
    id: uuid.UUID
    vendor_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class ContractBase(BaseModel):
    piid: str
    parent_piid: Optional[str]
    agency: str
    start_date: datetime
    naics_code: str
    psc_code: str
    competition_details: Optional[Any]
    raw_data: Optional[Any]

class ContractCreate(ContractBase):
    pass

class Contract(ContractBase):
    id: uuid.UUID
    vendor_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class DetectionBase(BaseModel):
    likelihood_score: float
    confidence: str
    evidence_bundle: Any

class DetectionCreate(DetectionBase):
    sbir_award_id: uuid.UUID
    contract_id: uuid.UUID

class Detection(DetectionBase):
    id: uuid.UUID
    sbir_award: SbirAward
    contract: Contract
    class Config:
        orm_mode = True

