from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class EvidenceOut(BaseModel):
    id: UUID
    evidence_type: str
    file_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ThreatScoreOut(BaseModel):
    id: UUID
    threat_score: int
    severity_band: str
    scam_category: str
    confidence_score: float
    reasoning_json: dict
    degraded_mode: bool
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReportOut(BaseModel):
    id: UUID
    user_id: UUID
    source_type: str
    raw_input_ref: str
    cleaned_text: Optional[str] = None
    detected_language: Optional[str] = None
    input_confidence: Optional[float] = None
    low_confidence_flag: bool
    status: str
    created_at: datetime
    evidence_items: List[EvidenceOut] = []
    threat_scores: List[ThreatScoreOut] = []

    class Config:
        from_attributes = True

class ReportCreateText(BaseModel):
    text_content: str = Field(..., min_length=10, max_length=10000)
