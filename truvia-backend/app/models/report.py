import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Integer, Numeric, SmallInteger
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_type = Column(String(50), nullable=False)  # screenshot, audio, text
    raw_input_ref = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=True)
    detected_language = Column(String(10), nullable=True)
    input_confidence = Column(Numeric(4, 3), nullable=True)
    low_confidence_flag = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="submitted")  # submitted, processing, scored, escalated, dismissed, failed
    city = Column(String(100), nullable=True)
    pipeline_stage = Column(String(50), nullable=True)  # ingesting, extracting_text, evaluating_threat, extracting_entities, indexing_graph, completed
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="reports")
    evidence_items = relationship("Evidence", back_populates="report", cascade="all, delete-orphan")
    threat_scores = relationship("ThreatScore", back_populates="report", cascade="all, delete-orphan")
    report_entities = relationship("ReportEntity", back_populates="report", cascade="all, delete-orphan")
    cases_association = relationship("CaseReport", back_populates="report", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # image, audio, text_paste, document
    file_ref = Column(Text, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash
    extraction_metadata_json = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    report = relationship("Report", back_populates="evidence_items")

class ThreatScore(Base):
    __tablename__ = "threat_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False)
    threat_score = Column(SmallInteger, nullable=False)  # 0 to 100
    severity_band = Column(String(50), nullable=False)  # low, moderate, high, critical
    scam_category = Column(String(100), nullable=False)
    confidence_score = Column(Numeric(4, 3), nullable=False)  # 0.0 to 1.0
    reasoning_json = Column(JSONB, nullable=False)
    degraded_mode = Column(Boolean, nullable=False, default=False)
    model_version = Column(String(50), nullable=False)
    is_current = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    report = relationship("Report", back_populates="threat_scores")

class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    type = Column(String(50), nullable=False)  # phone, upi, email, domain, device, ip, org
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=False)  # de-duplication key
    risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    risk_tier = Column(String(50), nullable=False, default="low")  # low, moderate, high, critical
    occurrence_count = Column(Integer, nullable=False, default=1)
    
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    appearances = relationship("ReportEntity", back_populates="entity", cascade="all, delete-orphan")

class ReportEntity(Base):
    __tablename__ = "report_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    raw_span = Column(Text, nullable=True)
    extraction_confidence = Column(Numeric(4, 3), nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    report = relationship("Report", back_populates="report_entities")
    entity = relationship("Entity", back_populates="appearances")

class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    entity_id_a = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    entity_id_b = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    relationship_type = Column(String(100), nullable=False)  # same_phone_used_in, same_upi_linked_to, etc.
    strength = Column(Numeric(4, 3), nullable=False, default=1.000)
    evidence_report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
