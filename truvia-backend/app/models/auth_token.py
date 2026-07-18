import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, String
from sqlalchemy import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base


class PasswordResetToken(Base):
    """Real, single-use, expiring password-reset token.

    Used by the admin "force password reset" action (App Flow §8.2). No email
    service is configured, so the admin endpoint returns the reset link/token
    for out-of-band delivery — the token itself is a genuine, verifiable secret
    (only its SHA-256 hash is stored), never a faked success.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True)
    issued_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
