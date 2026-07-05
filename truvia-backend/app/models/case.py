import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    case_number = Column(String(50), nullable=False, unique=True)
    case_type = Column(String(50), nullable=False)  # single_report, ring_level
    assigned_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, default="open")  # open, in_review, escalated, closed
    priority = Column(String(50), nullable=False, default="medium")  # low, medium, high, urgent
    ai_summary = Column(Text, nullable=True)
    neo4j_ring_id = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    assigned_officer = relationship("User", back_populates="assigned_cases")
    case_reports = relationship("CaseReport", back_populates="case", cascade="all, delete-orphan")
    assignments = relationship("OfficerAssignment", back_populates="case", cascade="all, delete-orphan")
    packages = relationship("IntelligencePackage", back_populates="case", cascade="all, delete-orphan")

class CaseReport(Base):
    __tablename__ = "case_reports"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), primary_key=True)
    linked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    linked_reason = Column(Text, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="case_reports")
    report = relationship("Report", back_populates="cases_association")

class OfficerAssignment(Base):
    __tablename__ = "officer_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False)
    officer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    unassigned_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="assignments")

class IntelligencePackage(Base):
    __tablename__ = "intelligence_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False)
    package_json = Column(JSONB, nullable=False)
    package_type = Column(String(50), nullable=False)  # case_level, ring_level
    content_hash = Column(String(64), nullable=False)
    pdf_ref = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="packages")
    generator = relationship("User", back_populates="packages")
