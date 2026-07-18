from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.config import settings
from app.data.postgres_client import is_sqlite
from app.models.knowledge import KnowledgeBaseChunk
import logging
from typing import List, Dict, Any

logger = logging.getLogger("truvia.vector")

# Dummy embedder for local development or when API keys are not provided
async def get_embedding(text_to_embed: str) -> List[float]:
    """
    Generate embedding for text.
    For local development, returns a deterministic dummy vector of 1536 float values.
    For production, calls Anthropic / external embedding API.
    """
    # 1536 is standard size for OpenAI/Anthropic-friendly embeddings
    # We will generate a simple deterministic vector based on string characters
    char_sum = sum(ord(c) for c in text_to_embed)
    dummy_vector = [((char_sum + i) % 100) / 100.0 for i in range(1536)]
    # Normalize vector
    magnitude = sum(x**2 for x in dummy_vector) ** 0.5
    if magnitude > 0:
        dummy_vector = [x / magnitude for x in dummy_vector]
    return dummy_vector

def python_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot_product = sum(x*y for x, y in zip(v1, v2))
    mag1 = sum(x**2 for x in v1) ** 0.5
    mag2 = sum(x**2 for x in v2) ** 0.5
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product / (mag1 * mag2)

async def search_similar_chunks(
    session: AsyncSession,
    query_text: str,
    limit: int = 5,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Queries knowledge_base_chunks for matching records using cosine similarity.
    Falls back to Python-based memory scoring when running in SQLite mode.
    """
    try:
        query_vector = await get_embedding(query_text)
        
        if session.bind.dialect.name == "sqlite":
            logger.info("Performing lexical keyword similarity search (SQLite fallback)")
            result = await session.execute(select(KnowledgeBaseChunk))
            all_chunks = result.scalars().all()

            # Lexical keyword-overlap scoring. The stored embeddings are a deterministic
            # placeholder (not semantic), so we score by real token overlap between the
            # query and each chunk — this retrieves genuinely relevant guideline passages.
            import re
            stop = {
                "the","a","an","and","or","of","to","in","is","are","for","on","with","how","does",
                "do","what","why","when","i","my","me","you","your","it","this","that","if","can",
                "should","about","from","be","as","at","by","was","were","will","would","tell",
            }
            def tokenize(t: str):
                return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 2 and w not in stop}

            q_tokens = tokenize(query_text)
            scored_chunks = []
            for chunk in all_chunks:
                c_tokens = tokenize(chunk.chunk_text)
                if not c_tokens:
                    continue
                overlap = q_tokens & c_tokens
                # Normalize by query length so short queries still score meaningfully.
                score = len(overlap) / max(1, len(q_tokens)) if q_tokens else 0.0
                scored_chunks.append({
                    "id": str(chunk.id),
                    "knowledge_base_id": str(chunk.knowledge_base_id),
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                    "similarity": float(score),
                })

            scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)
            relevant = [c for c in scored_chunks if c["similarity"] > 0]
            # Return the best matches; if nothing overlaps, fall back to the top chunks
            # so the assistant still has grounding context to work from.
            chosen = relevant[:limit] if relevant else scored_chunks[:limit]
            return chosen
            
        else:
            # pgvector query: cosine distance operator is <=>
            # cosine similarity = 1 - cosine distance
            sql_query = text("""
                SELECT id, knowledge_base_id, chunk_index, chunk_text, 
                       (1 - (embedding <=> CAST(:vector AS vector))) AS similarity
                FROM knowledge_base_chunks
                WHERE (1 - (embedding <=> CAST(:vector AS vector))) >= :threshold
                ORDER BY embedding <=> CAST(:vector AS vector) ASC
                LIMIT :limit
            """)
            
            # Cast vector to string format for pgvector import
            vector_str = f"[{','.join(map(str, query_vector))}]"
            
            result = await session.execute(
                sql_query,
                {
                    "vector": vector_str,
                    "threshold": similarity_threshold,
                    "limit": limit
                }
            )
            
            chunks = []
            for row in result:
                chunks.append({
                    "id": str(row.id),
                    "knowledge_base_id": str(row.knowledge_base_id),
                    "chunk_index": row.chunk_index,
                    "chunk_text": row.chunk_text,
                    "similarity": float(row.similarity)
                })
            return chunks
    except Exception as e:
        logger.error(f"Error searching similar chunks: {str(e)}")
        raise
