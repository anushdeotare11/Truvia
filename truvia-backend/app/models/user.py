import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Table
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base, is_sqlite

IPAddressType = String(50) if is_sqlite else INET

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    role = Column(String(50), nullable=False)  # citizen, officer, admin
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    officer_badge_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="active")  # active, suspended, pending_invite
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user")
    assigned_cases = relationship("Case", back_populates="assigned_officer")
    packages = relationship("IntelligencePackage", back_populates="generator")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(Text, nullable=False, unique=True)
    device_label = Column(String(255), nullable=True)
    ip_address = Column(IPAddressType, nullable=True)
    
    issued_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
