"""Module 5: Live Scam Interceptor — data model (Spec §5).

Two new tables following the established schema conventions (UUID PKs,
timestamptz, CHECK-constraint enums, snake_case, ON DELETE RESTRICT by default
with the documented CASCADE/SET NULL exceptions). Postgres is the source of
truth (see alembic/versions/0005_add_live_sessions.py); these ORM models also
back the SQLite fallback bootstrap used in dev.
"""
import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    Integer,
    SmallInteger,
    UniqueConstraint,
    Index,
)
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base


class LiveSession(Base):
    """A stateful, turn-by-turn live scam-interception session (Spec §5.4.1)."""

    __tablename__ = "live_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    # FK -> users.id, ON DELETE RESTRICT (a session is evidentiary once it exists)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # CHECK (status IN ('active','ended','escalated'))
    status = Column(String(50), nullable=False, default="active")
    # CHECK (current_severity_band IN ('low','moderate','high','critical'))
    # denormalized for fast list queries; updated after every turn
    current_severity_band = Column(String(50), nullable=False, default="low")
    # CHECK (current_score BETWEEN 0 AND 100)
    current_score = Column(SmallInteger, nullable=False, default=0)
    # set once confidently classified, may start NULL
    scam_category = Column(String(100), nullable=True)
    # first time the "high" threshold was crossed (drives once-per-crossing banner)
    intervention_shown_at = Column(DateTime(timezone=True), nullable=True)
    # FK -> cases.id, ON DELETE SET NULL — set if escalated
    linked_case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # A turn has no meaning without its session — intentional CASCADE exception.
    turns = relationship(
        "LiveSessionTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="LiveSessionTurn.turn_index",
    )

    __table_args__ = (
        Index("idx_live_sessions_user_id", "user_id"),
        # Spec calls for a partial index WHERE status = 'active'; partial indexes
        # are Postgres-only, so the migration adds the partial form and this plain
        # index keeps the SQLite fallback functional.
        Index("idx_live_sessions_status", "status"),
    )


class LiveSessionTurn(Base):
    """One turn in a live session — the citizen's transcription of what the
    other party just said, plus its scoring output (Spec §5.4.2)."""

    __tablename__ = "live_session_turns"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    # FK -> live_sessions.id, ON DELETE CASCADE
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("live_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ordinal position in the conversation
    turn_index = Column(Integer, nullable=False)
    # what the citizen typed for this turn
    raw_text = Column(Text, nullable=False)
    # this turn's individual contribution/signal, CHECK (turn_score BETWEEN 0 AND 100)
    turn_score = Column(SmallInteger, nullable=False)
    # running trajectory score as of this turn — this is what gets charted
    cumulative_score = Column(SmallInteger, nullable=False)
    # same explainability shape as threat_scores.reasoning_json, reused
    flagged_phrases_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session = relationship("LiveSession", back_populates="turns")

    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_live_session_turns_session_turn"),
        Index("idx_live_session_turns_session_id", "session_id"),
    )
