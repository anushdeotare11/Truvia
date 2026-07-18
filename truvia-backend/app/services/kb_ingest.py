"""Knowledge-base ingestion service (chunk + embed).

Factored from the real Section 5 ingestion approach used in
scripts/seed_guidelines.py (chunk ~250 chars -> get_embedding -> persist
knowledge_base_chunks). Reused by the Admin "Add Document" and "Re-index"
actions (App Flow §8.3/§8.4) so admin uploads go through the exact same
pipeline that powers RAG chat — no mocks.
"""
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.vector_client import get_embedding
from app.models.knowledge import KnowledgeBase, KnowledgeBaseChunk

logger = logging.getLogger("truvia.services.kb_ingest")

CHUNK_SIZE = 250
EMBEDDING_MODEL_VERSION = "custom-local-hash"


def _chunk(content: str, size: int = CHUNK_SIZE):
    content = content or ""
    return [content[i:i + size] for i in range(0, len(content), size)] or [""]


async def index_document(session: AsyncSession, kb: KnowledgeBase) -> int:
    """(Re)build chunks+embeddings for a KnowledgeBase row. Sets status.

    Deletes any existing chunks first (idempotent re-index), then writes fresh
    chunks. Marks the document 'indexed' on success, 'failed' on error.
    Returns the number of chunks written. Commits within.
    """
    try:
        await session.execute(
            delete(KnowledgeBaseChunk).where(KnowledgeBaseChunk.knowledge_base_id == kb.id)
        )
        chunks = _chunk(kb.content)
        for idx, chunk_text in enumerate(chunks):
            vector = await get_embedding(chunk_text)
            session.add(KnowledgeBaseChunk(
                knowledge_base_id=kb.id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=vector,
                embedding_model_version=EMBEDDING_MODEL_VERSION,
                token_count=len(chunk_text.split()),
            ))
        kb.status = "indexed"
        await session.commit()
        logger.info(f"Indexed {len(chunks)} chunks for knowledge_base {kb.id} ('{kb.title}')")
        return len(chunks)
    except Exception as e:
        await session.rollback()
        # Record the failure state honestly rather than swallowing it.
        try:
            kb.status = "failed"
            await session.commit()
        except Exception:
            await session.rollback()
        logger.error(f"Indexing failed for knowledge_base {kb.id}: {e}")
        raise


async def create_and_index(
    session: AsyncSession,
    *,
    source: str,
    title: str,
    content: str,
    source_url: str | None,
    added_by,
) -> KnowledgeBase:
    """Create a KnowledgeBase row (status=processing) and index it synchronously.

    Returns the persisted, indexed KnowledgeBase. Raises on ingestion failure
    (the row remains with status='failed' for visibility).
    """
    kb = KnowledgeBase(
        source=source,
        title=title,
        content=content,
        source_url=source_url,
        added_by=added_by,
        status="processing",
        version=1,
    )
    session.add(kb)
    await session.commit()
    await session.refresh(kb)
    await index_document(session, kb)
    await session.refresh(kb)
    return kb
