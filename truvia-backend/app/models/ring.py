import uuid
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Numeric, Index
)
from sqlalchemy import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base


class FraudRing(Base):
    """Postgres mirror of a Neo4j :Ring node (Backend_Schema §9.1).

    NOTE (documented deviation): the Backend_Schema models Ring as a Neo4j-only,
    derived node. We additionally persist detected rings here so the Threat
    Intelligence Engine's ring endpoints, ring-scoped subgraphs and intelligence
    packages remain fully queryable from the authoritative Postgres store even
    when Neo4j is offline — consistent with §9.5's "the entire graph can be fully
    rebuilt from Postgres" guarantee. When Neo4j is reachable the clustering job
    writes the equivalent :Ring / :MEMBER_OF structure there as well, and
    `neo4j_ring_id` is the shared key across both stores (also stored on
    `cases.neo4j_ring_id` once a ring is promoted to an investigation).
    """

    __tablename__ = "fraud_rings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    # Shared identifier across Postgres and Neo4j (e.g. "ring-2026-07-3").
    neo4j_ring_id = Column(String(100), nullable=False, unique=True)
    algorithm = Column(String(50), nullable=False, default="python_louvain")  # gds_louvain | python_louvain
    algorithm_version = Column(String(50), nullable=False, default="v1")
    member_count = Column(Integer, nullable=False, default=0)
    complaint_count = Column(Integer, nullable=False, default=0)
    dominant_category = Column(String(100), nullable=True)
    aggregate_risk_score = Column(Numeric(5, 2), nullable=False, default=0.00)
    risk_tier = Column(String(50), nullable=False, default="low")  # low, moderate, high, critical
    first_activity_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    members = relationship("FraudRingMember", back_populates="ring", cascade="all, delete-orphan")


class FraudRingMember(Base):
    """Postgres mirror of a Neo4j (:Entity)-[:MEMBER_OF]->(:Ring) edge."""

    __tablename__ = "fraud_ring_members"

    ring_id = Column(UUID(as_uuid=True), ForeignKey("fraud_rings.id", ondelete="CASCADE"), primary_key=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    membership_confidence = Column(Numeric(4, 3), nullable=False, default=1.000)
    assigned_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    ring = relationship("FraudRing", back_populates="members")


Index("idx_fraud_ring_members_entity", FraudRingMember.entity_id)
Index("idx_fraud_rings_risk_tier", FraudRing.risk_tier)
