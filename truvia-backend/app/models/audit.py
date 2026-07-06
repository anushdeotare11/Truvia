import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.sql import func
from app.data.postgres_client import Base, is_sqlite

IPAddressType = String(50) if is_sqlite else INET
JSONType = JSON if is_sqlite else JSONB

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_type = Column(String(50), nullable=False, default="user")  # user, system, agent
    action = Column(String(100), nullable=False)  # case.assign, report.escalate, etc.
    entity_type = Column(String(50), nullable=False)  # cases, reports, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)  # soft polymorphic join
    diff_json = Column(JSONType, nullable=True)
    ip_address = Column(IPAddressType, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
