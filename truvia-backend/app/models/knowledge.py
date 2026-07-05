import uuid
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.data.postgres_client import Base, is_sqlite

import json
from sqlalchemy import TypeDecorator

class JSONEncodedText(TypeDecorator):
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None
        
    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

# Use Text (JSON string) for SQLite, native Vector for PostgreSQL
EmbeddingType = JSONEncodedText if is_sqlite else Vector(1536)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    source = Column(String(50), nullable=False)  # RBI, MHA, NCRP, CERT-In, NPCI, custom
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), nullable=False, default="processing")  # processing, indexed, failed
    version = Column(Integer, nullable=False, default=1)
    
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    chunks = relationship("KnowledgeBaseChunk", back_populates="knowledge_base", cascade="all, delete-orphan")

class KnowledgeBaseChunk(Base):
    __tablename__ = "knowledge_base_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid())
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_base.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(EmbeddingType, nullable=False)  # 1536 dimensions for RAG embeddings
    embedding_model_version = Column(String(50), nullable=False)
    token_count = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="chunks")
