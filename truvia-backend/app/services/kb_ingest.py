"""Knowledge-base ingestion service (chunk + embed).

Factored from the real Section 5 ingestion approach used in
scripts/seed_guidelines.py (chunk ~250 chars -> get_embedding -> persist
knowledge_base_chunks). Reused by the Admin "Add Document" and "Re-index"
actions (App Flow §8.3/§8.4) so admin uploads go through the exact same
pipeline that powers RAG chat — no mocks.
"""
import logging
import re

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.vector_client import get_embedding, EMBEDDING_MODEL_VERSION
from app.models.knowledge import KnowledgeBase, KnowledgeBaseChunk

logger = logging.getLogger("truvia.services.kb_ingest")

# Sentence/paragraph-aware chunking. The advisories are short (≈550–710 chars),
# so a ~700-char target keeps most of a document intact as one coherent chunk
# instead of the previous fixed 250-char slices that cut mid-sentence (and even
# mid-word), which destroyed the context a passage needs to answer a question.
CHUNK_SIZE = 700
CHUNK_OVERLAP = 120


def _chunk(content: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Split on sentence boundaries and pack sentences up to `size` chars, with a
    small character overlap carried between adjacent chunks so a passage split
    across a boundary keeps its surrounding context. Never cuts mid-sentence."""
    content = (content or "").strip()
    if not content:
        return [""]

    # Sentence-ish boundaries: end punctuation followed by whitespace. Numbered
    # list items ("1) ... 2) ...") are naturally kept together up to `size`.
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", content) if s.strip()]
    if not sentences:
        return [content]

    chunks: list[str] = []
    cur = ""
    for sent in sentences:
        sent = sent.strip()
        if not cur:
            cur = sent
        elif len(cur) + 1 + len(sent) <= size:
            cur = f"{cur} {sent}"
        else:
            chunks.append(cur.strip())
            tail = cur[-overlap:].strip() if overlap and len(cur) > overlap else ""
            cur = f"{tail} {sent}".strip() if tail else sent
    if cur.strip():
        chunks.append(cur.strip())
    return chunks or [""]


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
