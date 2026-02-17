from __future__ import annotations
from typing import List, Dict, Any
from pydantic import BaseModel, Field, field_validator

class Patient(BaseModel):
    name: str = "SYNTHETIC PATIENT"
    dob: str | None = None
    member_id: str | None = None
    insurance: str | Dict[str, Any] | None = None

    @field_validator("insurance", mode="before")
    @classmethod
    def normalize_insurance(cls, v):
        # If LLM returns object, normalize to payer/plan string only
        if isinstance(v, dict):
            payer = v.get("payer") or v.get("name") or v.get("insurance") or v.get("plan")
            return str(payer).strip() if payer else None
        return v

class Providers(BaseModel):
    billing_npi: str | None = None
    rendering_npi: str | None = None
    ordering_provider_name: str | None = None
    referring_provider_id: str | None = None

class ServiceLine(BaseModel):
    cpt_hcpcs: str
    units: int = 1
    modifiers: List[str] = Field(default_factory=list)
    diagnosis_pointer: List[int] = Field(default_factory=list)

class ClaimInfo(BaseModel):
    date_of_service: str | None = None
    place_of_service: str | None = None
    diagnoses: List[str] = Field(default_factory=list)
    lines: List[ServiceLine] = Field(default_factory=list)

class ClaimPacket(BaseModel):
    patient: Patient = Field(default_factory=Patient)
    providers: Providers = Field(default_factory=Providers)
    claim: ClaimInfo = Field(default_factory=ClaimInfo)
    meta: Dict[str, Any] = Field(default_factory=dict)