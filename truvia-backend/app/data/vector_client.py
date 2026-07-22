from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.config import settings
from app.data.postgres_client import is_sqlite
from app.models.knowledge import KnowledgeBaseChunk
import logging
import math
import re
import hashlib
from collections import Counter
from typing import List, Dict, Any

logger = logging.getLogger("truvia.vector")

# ---------------------------------------------------------------------------
# Offline, dependency-light *semantic-lexical* embedder (feature hashing).
#
# The previous implementation returned a vector derived only from the sum of a
# string's character codes. That made every text look nearly identical (a
# shifted sawtooth ramp), so cosine similarity was effectively meaningless and
# retrieval was random — a CBI/"digital arrest" question would surface QR-code
# fraud chunks. See scripts/_rag_diag.py.
#
# This replacement builds a real bag-of-terms vector via *feature hashing*
# (a.k.a. the hashing trick): each token/bigram is hashed into one of
# EMBEDDING_DIM buckets with a signed sub-linear TF weight, then the vector is
# L2-normalized. Cosine similarity then reflects genuine shared vocabulary
# between a question and a chunk — which is exactly what makes retrieval
# relevant for keyword-rich fraud-guidance content. It is fully deterministic,
# uses only numpy, and — critically — the SAME function is used to embed the
# knowledge base at ingestion time and the incoming question at query time, so
# the two vector spaces always match (no embedding-model mismatch).
#
# The dimensionality is kept at 1536 so the existing pgvector column
# (Vector(1536)) needs no schema migration.
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 1536
EMBEDDING_MODEL_VERSION = "hashing-tf-v2"

# Generic, non-discriminative words. Domain terms (upi, otp, kyc, cbi, bank,
# fraud, arrest, ...) are intentionally NOT stopped — they carry the signal.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "for", "on",
    "with", "how", "does", "do", "what", "why", "when", "who", "which", "i",
    "my", "me", "you", "your", "it", "this", "that", "if", "can", "should",
    "about", "from", "be", "as", "at", "by", "was", "were", "will", "would",
    "tell", "please", "someone", "they", "them", "their", "there", "here",
    "have", "has", "had", "not", "no", "yes", "get", "got", "any", "some",
    "into", "out", "up", "down", "so", "but", "then", "than", "also", "such",
    "these", "those", "am", "been", "being", "he", "she", "we", "us", "our",
}


def _tokenize(text_in: str) -> List[str]:
    return [
        t for t in re.findall(r"[a-z0-9]+", (text_in or "").lower())
        if len(t) >= 2 and t not in _STOPWORDS
    ]


def _terms(text_in: str) -> List[str]:
    """Unigrams + adjacent bigrams. Bigrams (e.g. 'digital_arrest',
    'collect_request', 'report_fraud') sharpen discrimination between advisories
    that share generic vocabulary."""
    toks = _tokenize(text_in)
    terms = list(toks)
    for i in range(len(toks) - 1):
        terms.append(f"{toks[i]}_{toks[i + 1]}")
    return terms


def _bucket_and_sign(term: str) -> tuple[int, float]:
    h = int(hashlib.md5(term.encode("utf-8")).hexdigest(), 16)
    idx = h % EMBEDDING_DIM
    sign = 1.0 if ((h >> 17) & 1) else -1.0
    return idx, sign


async def get_embedding(text_to_embed: str) -> List[float]:
    """Deterministic 1536-dim feature-hashing embedding (offline, numpy-only).

    Cosine similarity of two of these vectors is high when the texts share
    salient terms/bigrams and near-zero when they don't — real, meaningful
    retrieval, unlike the previous char-sum placeholder.
    """
    import numpy as np

    vec = np.zeros(EMBEDDING_DIM, dtype=np.float64)
    terms = _terms(text_to_embed or "")
    if not terms:
        return [0.0] * EMBEDDING_DIM

    for term, count in Counter(terms).items():
        idx, sign = _bucket_and_sign(term)
        # sub-linear term-frequency weighting
        vec[idx] += sign * (1.0 + math.log(count))

    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

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
